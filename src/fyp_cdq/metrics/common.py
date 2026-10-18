"""Shared data models, call graph loaders, and partition resolution for coupling and cohesion metrics."""

import ast
from dataclasses import dataclass
from itertools import combinations
import json
import os
from pathlib import Path
import re
from typing import Callable, Dict, List, Optional, Set, Tuple

try:
    import javalang
except ImportError:
    javalang = None

from fyp_cdq.models import Partition


@dataclass(frozen=True)
class Operation:
    """Represents an operation/method signature in a service interface."""
    cls: str
    name: str
    params: tuple
    returns: str


@dataclass(frozen=True)
class Edge:
    """Represents a dependency or invocation edge between two components."""
    src: str
    dst: str
    type: str = "CALL"
    weight: float = 1.0


def jaccard_similarity(a, b) -> float:
    """Computes Jaccard similarity between two collections. Returns 1.0 if both empty."""
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def resolve_partition(
    microservices: Dict[str, List[str]],
    dataset_methods: Optional[dict] = None
) -> Callable[[str], Optional[str]]:
    """
    Constructs a cluster lookup function that resolves classes or methods to their microservice ID.
    Exact implementation from reference SOTA implementations.
    """
    method_partition = {}
    class_member_counts = {}

    class_fqn_to_simple = {}
    simple_to_class_fqn = {}
    if dataset_methods:
        for mid, mdata in dataset_methods.items():
            pkg = mdata.get("package", "")
            cls = mdata.get("class", "")
            if cls:
                fqn = f"{pkg}.{cls}" if pkg else cls
                class_fqn_to_simple[fqn] = cls
                simple_to_class_fqn.setdefault(cls, set()).add(fqn)

    for cid, members in microservices.items():
        for m in members:
            if "-res" in m:
                continue
            clean_m = m.split(" [")[0].strip()
            method_partition[clean_m] = cid
            if m != clean_m:
                method_partition[m] = cid

            if dataset_methods and clean_m in dataset_methods:
                m_info = dataset_methods[clean_m]
                pkg = m_info.get("package", "")
                cls = m_info.get("class", "")
                class_fqn = f"{pkg}.{cls}" if pkg else cls
                simple_cls = cls
            elif clean_m in class_fqn_to_simple:
                class_fqn = clean_m
                simple_cls = class_fqn_to_simple[clean_m]
            elif clean_m in simple_to_class_fqn:
                simple_cls = clean_m
                fqns = simple_to_class_fqn[clean_m]
                class_fqn = list(fqns)[0] if len(fqns) == 1 else clean_m
            elif "." in clean_m:
                last_seg = clean_m.split(".")[-1]
                if last_seg and last_seg[0].isupper():
                    class_fqn = clean_m
                    simple_cls = last_seg
                else:
                    class_fqn = clean_m.rsplit(".", 1)[0]
                    simple_cls = class_fqn.split(".")[-1]
            else:
                class_fqn = clean_m
                simple_cls = clean_m

            class_member_counts.setdefault(class_fqn, {})
            class_member_counts[class_fqn][cid] = class_member_counts[class_fqn].get(cid, 0) + 1
            if simple_cls != class_fqn:
                class_member_counts.setdefault(simple_cls, {})
                class_member_counts[simple_cls][cid] = class_member_counts[simple_cls].get(cid, 0) + 1

    class_partition = {}
    for class_name, counts in class_member_counts.items():
        majority_cid = max(counts.items(), key=lambda x: x[1])[0]
        class_partition[class_name] = majority_cid

    def get_cluster(node_id: Optional[str]) -> Optional[str]:
        if not node_id:
            return None
        clean_node = node_id.split(" [")[0].strip()
        if clean_node in method_partition:
            return method_partition[clean_node]
        if node_id in method_partition:
            return method_partition[node_id]
        if clean_node in class_partition:
            return class_partition[clean_node]
        if node_id in class_partition:
            return class_partition[node_id]
        simple_name = clean_node.split(".")[-1]
        if simple_name in class_partition:
            return class_partition[simple_name]
        if "." in clean_node:
            parent_cls = clean_node.rsplit(".", 1)[0]
            if parent_cls in class_partition:
                return class_partition[parent_cls]
            short_parent = parent_cls.split(".")[-1]
            if short_parent in class_partition:
                return class_partition[short_parent]
        return None

    return get_cluster


def published_ops(get_cluster, clusters: Set[str], calls: List[Tuple[str, Operation]]) -> Dict[str, Set[Operation]]:
    """Identifies operations on each service that are invoked by other services."""
    ops = {cid: set() for cid in clusters}
    for caller, op in calls:
        ci, cj = get_cluster(caller), get_cluster(op.cls)
        if ci is None or cj is None or ci == cj:
            continue
        if cj in ops:
            ops[cj].add(op)
    return ops


def pairwise_mean(ops: Set[Operation], similarity_fn: Callable[[Operation, Operation], float]) -> float:
    """Computes mean pairwise similarity over published operations. Returns 1.0 if < 2 operations."""
    ops_list = sorted(ops, key=lambda o: (o.cls, o.name, o.params, o.returns))
    if len(ops_list) < 2:
        return 1.0
    pairs = list(combinations(ops_list, 2))
    return sum(similarity_fn(a, b) for a, b in pairs) / len(pairs)


def load_calls_from_dataset(dataset_path: Path) -> Tuple[List[Tuple[str, Operation]], Dict[str, dict]]:
    """Loads method call signatures from an external dataset.json if available."""
    calls = []
    dataset_methods = {}
    dataset_file = dataset_path if dataset_path.is_file() else (dataset_path / "dataset.json")

    if dataset_file.exists():
        with open(dataset_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            methods = data.get("methods", {})
            dataset_methods = methods
            for caller_id, mdata in methods.items():
                caller_cls = mdata.get("class", caller_id.rsplit(".", 1)[0] if "." in caller_id else caller_id)
                method_calls = mdata.get("calls", [])
                for callee_id in method_calls:
                    callee_data = methods.get(callee_id, {})
                    callee_cls = callee_data.get("class", callee_id.rsplit(".", 1)[0] if "." in callee_id else callee_id)
                    callee_name = callee_data.get("method_name", callee_id.split(".")[-1])
                    callee_params = tuple(callee_data.get("parameters", []))
                    callee_returns = callee_data.get("return_type", "void")

                    op = Operation(cls=callee_cls, name=callee_name, params=callee_params, returns=callee_returns)
                    calls.append((caller_cls, op))

    return calls, dataset_methods


def load_edges_from_dataset(dataset_path: Path) -> List[Edge]:
    """Loads invocation edges from an external dataset.json if available."""
    edges = []
    dataset_file = dataset_path if dataset_path.is_file() else (dataset_path / "dataset.json")

    if dataset_file.exists():
        with open(dataset_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "edges" in data and data["edges"]:
                for e in data["edges"]:
                    edges.append(Edge(e["src"], e["dst"], e.get("type", "CALL"), float(e.get("weight", 1.0))))
            elif "methods" in data:
                methods = data["methods"]
                for caller_id, mdata in methods.items():
                    caller_cls = mdata.get("class", caller_id.rsplit(".", 1)[0] if "." in caller_id else caller_id)
                    calls = mdata.get("calls", [])
                    for callee in calls:
                        callee_cls = callee.rsplit(".", 1)[0] if "." in callee else callee
                        edges.append(Edge(caller_cls, callee_cls, "CALL", 1.0))

    return edges


_CODEBASE_EXTRACTION_CACHE: Dict[str, Tuple[List[Tuple[str, Operation]], List[Edge], Dict[str, dict]]] = {}


def extract_codebase_operations_and_calls(
    codebase_path: Path,
    partition: Partition,
) -> Tuple[List[Tuple[str, Operation]], List[Edge], Dict[str, dict]]:
    """
    Extracts declared operations and invocation calls directly from the codebase.
    Used when no external dataset.json is provided.
    """
    cache_key = f"{codebase_path.resolve()}::{sorted(partition.microservices.keys())}"
    if cache_key in _CODEBASE_EXTRACTION_CACHE:
        return _CODEBASE_EXTRACTION_CACHE[cache_key]

    methods_dict: Dict[str, Operation] = {}
    methods_by_name: Dict[str, List[Operation]] = {}
    calls: List[Tuple[str, Operation]] = []
    edges: List[Edge] = []
    dataset_methods: Dict[str, dict] = {}

    get_cluster = resolve_partition(partition.microservices)

    parsed_java_classes = []
    parsed_python_classes = []
    other_source_files = []

    exclude_dirs = {
        ".git", ".github", ".idea", ".vscode", "docs", "doc", "scripts", "script",
        "gradle", ".mvn", "target", "build", "node_modules", "vendor", "test", "tests"
    }

    # 1. Single-pass file scan and operation extraction
    for root, dirs, files in os.walk(codebase_path):
        dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs and not d.startswith(".")]
        for f in files:
            file_path = Path(root) / f
            if f.endswith(".java") and javalang:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        code = fp.read()
                    tree = javalang.parse.parse(code)
                    pkg = tree.package.name if tree.package else ""
                    for _, cls_node in tree.filter(javalang.tree.ClassDeclaration):
                        cname = f"{pkg}.{cls_node.name}" if pkg else cls_node.name
                        for m in cls_node.methods:
                            ret = m.return_type.name if m.return_type else "void"
                            params = tuple(p.type.name for p in m.parameters if hasattr(p, "type") and p.type)
                            op = Operation(cls=cname, name=m.name, params=params, returns=ret)
                            full_id = f"{cname}.{m.name}"
                            methods_dict[full_id] = op
                            methods_by_name.setdefault(m.name, []).append(op)
                            dataset_methods[full_id] = {
                                "package": pkg,
                                "class": cname,
                                "method_name": m.name,
                                "parameters": list(params),
                                "return_type": ret,
                            }
                        parsed_java_classes.append((cname, cls_node))
                except Exception:
                    pass
            elif f.endswith(".py"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        tree = ast.parse(fp.read())
                    mod_name = file_path.stem
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            cls_name = f"{mod_name}.{node.name}"
                            funcs = []
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    params = tuple(arg.arg for arg in item.args.args if arg.arg != "self")
                                    ret = "object"
                                    op = Operation(cls=cls_name, name=item.name, params=params, returns=ret)
                                    full_id = f"{cls_name}.{item.name}"
                                    methods_dict[full_id] = op
                                    methods_by_name.setdefault(item.name, []).append(op)
                                    dataset_methods[full_id] = {
                                        "package": mod_name,
                                        "class": cls_name,
                                        "method_name": item.name,
                                        "parameters": list(params),
                                        "return_type": ret,
                                    }
                                    funcs.append(item)
                            parsed_python_classes.append((cls_name, funcs))
                except Exception:
                    pass
            elif f.endswith(".go"):
                _extract_go_operations(file_path, methods_dict, methods_by_name, dataset_methods)
                other_source_files.append(file_path)
            elif f.endswith(".cs"):
                _extract_csharp_operations(file_path, methods_dict, methods_by_name, dataset_methods)
                other_source_files.append(file_path)

    # 2. Second pass: extract call invocations from parsed memory structures
    for caller_cls, cls_node in parsed_java_classes:
        caller_cluster = get_cluster(caller_cls)
        if not caller_cluster:
            continue
        for m in cls_node.methods:
            for _, inv in m.filter(javalang.tree.MethodInvocation):
                m_name = inv.member
                if m_name in methods_by_name:
                    for target_op in methods_by_name[m_name]:
                        target_cluster = get_cluster(target_op.cls)
                        if target_cluster and target_cluster != caller_cluster:
                            calls.append((caller_cls, target_op))
                            edges.append(Edge(src=caller_cls, dst=target_op.cls, type="CALL"))

    for caller_cls, funcs in parsed_python_classes:
        caller_cluster = get_cluster(caller_cls)
        if not caller_cluster:
            continue
        for item in funcs:
            for sub in ast.walk(item):
                if isinstance(sub, ast.Call):
                    func_name = None
                    if isinstance(sub.func, ast.Name):
                        func_name = sub.func.id
                    elif isinstance(sub.func, ast.Attribute):
                        func_name = sub.func.attr
                    if func_name and func_name in methods_by_name:
                        for target_op in methods_by_name[func_name]:
                            target_cluster = get_cluster(target_op.cls)
                            if target_cluster and target_cluster != caller_cluster:
                                calls.append((caller_cls, target_op))
                                edges.append(Edge(src=caller_cls, dst=target_op.cls, type="CALL"))

    for file_path in other_source_files:
        _extract_generic_calls(file_path, methods_by_name, get_cluster, calls, edges)

    result = (calls, edges, dataset_methods)
    _CODEBASE_EXTRACTION_CACHE[cache_key] = result
    return result


def _extract_java_operations(file_path: Path, methods_dict, methods_by_name, dataset_methods):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        tree = javalang.parse.parse(code)
        pkg = tree.package.name if tree.package else ""

        for _, cls_node in tree.filter(javalang.tree.ClassDeclaration):
            cname = f"{pkg}.{cls_node.name}" if pkg else cls_node.name
            for m in cls_node.methods:
                ret = m.return_type.name if m.return_type else "void"
                params = tuple(p.type.name for p in m.parameters if hasattr(p, "type") and p.type)
                op = Operation(cls=cname, name=m.name, params=params, returns=ret)
                full_id = f"{cname}.{m.name}"
                methods_dict[full_id] = op
                methods_by_name.setdefault(m.name, []).append(op)
                dataset_methods[full_id] = {
                    "package": pkg,
                    "class": cname,
                    "method_name": m.name,
                    "parameters": list(params),
                    "return_type": ret,
                }
    except Exception:
        pass


def _extract_java_calls(file_path: Path, methods_by_name, get_cluster, calls, edges):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        tree = javalang.parse.parse(code)
        pkg = tree.package.name if tree.package else ""

        for _, cls_node in tree.filter(javalang.tree.ClassDeclaration):
            caller_cls = f"{pkg}.{cls_node.name}" if pkg else cls_node.name
            caller_cluster = get_cluster(caller_cls)
            if not caller_cluster:
                continue

            for m in cls_node.methods:
                for _, inv in m.filter(javalang.tree.MethodInvocation):
                    m_name = inv.member
                    if m_name in methods_by_name:
                        for target_op in methods_by_name[m_name]:
                            target_cluster = get_cluster(target_op.cls)
                            if target_cluster and target_cluster != caller_cluster:
                                calls.append((caller_cls, target_op))
                                edges.append(Edge(src=caller_cls, dst=target_op.cls, type="CALL"))
    except Exception:
        pass


def _extract_python_operations(file_path: Path, methods_dict, methods_by_name, dataset_methods):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read())
        mod_name = file_path.stem
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cls_name = f"{mod_name}.{node.name}"
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        params = tuple(arg.arg for arg in item.args.args if arg.arg != "self")
                        ret = "object"
                        op = Operation(cls=cls_name, name=item.name, params=params, returns=ret)
                        full_id = f"{cls_name}.{item.name}"
                        methods_dict[full_id] = op
                        methods_by_name.setdefault(item.name, []).append(op)
                        dataset_methods[full_id] = {
                            "package": mod_name,
                            "class": cls_name,
                            "method_name": item.name,
                            "parameters": list(params),
                            "return_type": ret,
                        }
    except Exception:
        pass


def _extract_python_calls(file_path: Path, methods_by_name, get_cluster, calls, edges):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read())
        mod_name = file_path.stem
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                caller_cls = f"{mod_name}.{node.name}"
                caller_cluster = get_cluster(caller_cls)
                if not caller_cluster:
                    continue
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        for sub in ast.walk(item):
                            if isinstance(sub, ast.Call):
                                func_name = None
                                if isinstance(sub.func, ast.Name):
                                    func_name = sub.func.id
                                elif isinstance(sub.func, ast.Attribute):
                                    func_name = sub.func.attr
                                if func_name and func_name in methods_by_name:
                                    for target_op in methods_by_name[func_name]:
                                        target_cluster = get_cluster(target_op.cls)
                                        if target_cluster and target_cluster != caller_cluster:
                                            calls.append((caller_cls, target_op))
                                            edges.append(Edge(src=caller_cls, dst=target_op.cls, type="CALL"))
    except Exception:
        pass


def _extract_go_operations(file_path: Path, methods_dict, methods_by_name, dataset_methods):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_]+)", code, re.MULTILINE)
        pkg = pkg_match.group(1) if pkg_match else file_path.parent.name
        
        # Regex for Go methods: func (r *Receiver) Method(p1 Type1) ReturnType
        pattern = r"func\s*\(\s*\w+\s*\*?([A-Za-z0-9_]+)\s*\)\s*([A-Z][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*([A-Za-z0-9_.*]+)?"
        for match in re.finditer(pattern, code):
            cls = f"{pkg}.{match.group(1)}"
            mname = match.group(2)
            params_raw = match.group(3).strip()
            params = tuple(p.split()[-1] for p in params_raw.split(",")) if params_raw else ()
            ret = match.group(4).strip() if match.group(4) else "void"
            op = Operation(cls=cls, name=mname, params=params, returns=ret)
            full_id = f"{cls}.{mname}"
            methods_dict[full_id] = op
            methods_by_name.setdefault(mname, []).append(op)
            dataset_methods[full_id] = {
                "package": pkg,
                "class": cls,
                "method_name": mname,
                "parameters": list(params),
                "return_type": ret,
            }
    except Exception:
        pass


def _extract_csharp_operations(file_path: Path, methods_dict, methods_by_name, dataset_methods):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        ns_match = re.search(r"^\s*namespace\s+([a-zA-Z0-9_.]+)", code, re.MULTILINE)
        ns = ns_match.group(1).strip() if ns_match else ""
        cls_match = re.search(r"\bclass\s+([A-Za-z0-9_]+)", code)
        cls_name = cls_match.group(1) if cls_match else file_path.stem
        cname = f"{ns}.{cls_name}" if ns else cls_name

        pattern = r"\b(?:public|protected|internal)\s+(?:async\s+)?([A-Za-z0-9_<>]+)\s+([A-Z][A-Za-z0-9_]*)\s*\(([^)]*)\)"
        for match in re.finditer(pattern, code):
            ret = match.group(1).strip()
            mname = match.group(2).strip()
            params_raw = match.group(3).strip()
            params = tuple(p.strip().split()[0] for p in params_raw.split(",")) if params_raw else ()
            op = Operation(cls=cname, name=mname, params=params, returns=ret)
            full_id = f"{cname}.{mname}"
            methods_dict[full_id] = op
            methods_by_name.setdefault(mname, []).append(op)
            dataset_methods[full_id] = {
                "package": ns,
                "class": cname,
                "method_name": mname,
                "parameters": list(params),
                "return_type": ret,
            }
    except Exception:
        pass


def _extract_generic_calls(file_path: Path, methods_by_name, get_cluster, calls, edges):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        caller_cls = file_path.stem
        caller_cluster = get_cluster(caller_cls)
        if not caller_cluster:
            return

        invoked = set(re.findall(r"\b([A-Za-z0-9_]+)\s*\(", code))
        for m_name in invoked:
            if m_name in methods_by_name:
                for target_op in methods_by_name[m_name]:
                    target_cluster = get_cluster(target_op.cls)
                    if target_cluster and target_cluster != caller_cluster:
                        calls.append((caller_cls, target_op))
                        edges.append(Edge(src=caller_cls, dst=target_op.cls, type="CALL"))
    except Exception:
        pass
