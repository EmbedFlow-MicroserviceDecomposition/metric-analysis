"""Shared data models, call graph loaders, microservice published-operation extractors, and partition resolution."""

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

from fyp_cdq.config import MICROSERVICES_JSON
from fyp_cdq.extractors.java_extractor import strip_java_comments_and_strings
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


def resolve_partition_with_clusters(
    microservices: Dict[str, List[str]],
    dataset_methods: Optional[dict] = None
) -> Tuple[Dict[str, Set[str]], Callable[[Optional[str]], Optional[str]]]:
    """
    Constructs a cluster map (cid -> set of classes) and a lookup function
    that resolves classes or methods to their microservice ID.
    Exact implementation from reference SOTA implementations (sm_sota.py / ifn_sota.py).
    """
    method_partition = {}
    class_member_counts = {}
    class_clusters: Dict[str, Set[str]] = {cid: set() for cid in microservices}

    class_fqn_to_simple = {}
    simple_to_class_fqn = {}
    if dataset_methods:
        for mid, mdata in dataset_methods.items():
            pkg = mdata.get("package", "")
            cls = mdata.get("class", "")
            if cls:
                fqn = f"{pkg}.{cls}" if pkg and not cls.startswith(pkg) else cls
                simple = cls.split(".")[-1]
                class_fqn_to_simple[fqn] = simple
                simple_to_class_fqn.setdefault(simple, set()).add(fqn)

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
                class_fqn = f"{pkg}.{cls}" if pkg and not cls.startswith(pkg) else cls
                simple_cls = cls.split(".")[-1]
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
                simple_to_class_fqn.setdefault(simple_cls, set()).add(class_fqn)
                class_member_counts.setdefault(simple_cls, {})
                class_member_counts[simple_cls][cid] = class_member_counts[simple_cls].get(cid, 0) + 1

    class_partition = {}
    for class_name, counts in class_member_counts.items():
        majority_cid = max(counts.items(), key=lambda x: x[1])[0]
        class_partition[class_name] = majority_cid

    for c, cid in class_partition.items():
        if "." in c or c not in simple_to_class_fqn:
            class_clusters.setdefault(cid, set()).add(c)

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

    return class_clusters, get_cluster


def resolve_partition(
    microservices: Dict[str, List[str]],
    dataset_methods: Optional[dict] = None
) -> Callable[[Optional[str]], Optional[str]]:
    """Constructs a cluster lookup function that resolves classes or methods to their microservice ID."""
    _, get_cluster = resolve_partition_with_clusters(microservices, dataset_methods)
    return get_cluster


def published_ops(get_cluster, clusters: Set[str], calls: List[Tuple[str, Operation]]) -> Dict[str, Set[Operation]]:
    """Identifies operations on each service that are invoked by other services (from a monolith call graph)."""
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


def _resolve_method_class_fqn(method_id: str, mdata: dict) -> str:
    pkg = mdata.get("package", "")
    cls = mdata.get("class", "")
    if cls:
        if pkg and not cls.startswith(f"{pkg}."):
            return f"{pkg}.{cls}"
        return cls
    return method_id.rsplit(".", 1)[0] if "." in method_id else method_id


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
                caller_cls = _resolve_method_class_fqn(caller_id, mdata)
                method_calls = mdata.get("calls", [])
                for callee_id in method_calls:
                    callee_data = methods.get(callee_id, {})
                    callee_cls = _resolve_method_class_fqn(callee_id, callee_data)
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
                seen = set()
                for caller_id, mdata in methods.items():
                    caller_cls = _resolve_method_class_fqn(caller_id, mdata)
                    calls = mdata.get("calls", [])
                    for callee_id in calls:
                        callee_data = methods.get(callee_id, {})
                        callee_cls = _resolve_method_class_fqn(callee_id, callee_data)
                        if caller_cls != callee_cls and (caller_cls, callee_cls) not in seen:
                            seen.add((caller_cls, callee_cls))
                            edges.append(Edge(caller_cls, callee_cls, "CALL", 1.0))

    return edges


# ==============================================================================
# 1. Monolith Call Graph Extraction (for IFN, SM, and monolith-mode CHD/CHM)
# ==============================================================================

_CODEBASE_EXTRACTION_CACHE: Dict[str, Tuple[List[Tuple[str, Operation]], List[Edge], Dict[str, dict]]] = {}

_EXCLUDE_DIRS = {
    ".git", ".github", ".idea", ".vscode", "docs", "doc", "scripts", "script",
    "gradle", ".mvn", "target", "build", "node_modules", "vendor", "test", "tests",
    "__pycache__", "venv", ".venv", "dist", "out", "bin", "obj",
}

_WRAPPER_TYPES = {
    "ResponseEntity", "HttpEntity", "Optional", "Mono", "Flux", "CompletableFuture",
    "Future", "ListenableFuture", "Single", "Observable", "Flowable", "Maybe",
    "Response", "ApiResponse", "Result", "Callable", "DeferredResult", "Task",
    "ValueTask", "ActionResult", "IActionResult",
}

_COLLECTION_TYPES = {
    "List", "ArrayList", "LinkedList", "Set", "HashSet", "TreeSet", "Collection",
    "Iterable", "Page", "Slice", "Stream", "IEnumerable", "IList", "ICollection",
    "IReadOnlyList", "IReadOnlyCollection",
}


def _sanitize_java_for_javalang(code: str) -> str:
    """Normalizes Java 14+ text blocks and record headers so javalang can parse modern Java files."""
    s = re.sub(r'"""[\s\S]*?"""', '""', code)
    # Convert `record Name(...)` headers (with optional nested annotations in record components) to `class Name`
    s = re.sub(
        r"\brecord\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((?:[^(){}]|\([^()]*\))*?\)\s*(implements\s+[^{]+)?\{",
        r"class \1 \2{",
        s,
    )
    return s


def _format_javalang_type(t) -> str:
    """Formats a javalang Type node, unwrapping transport/async wrappers and preserving generic domain arguments."""
    if t is None:
        return "void"
    name = getattr(t, "name", None) or str(t)
    args = getattr(t, "arguments", None)
    if args:
        inner_types = []
        for arg in args:
            arg_type = getattr(arg, "type", None)
            if arg_type is not None:
                inner_types.append(_format_javalang_type(arg_type))
        if inner_types:
            if name in _WRAPPER_TYPES:
                if name == "Flux":
                    return f"List<{inner_types[0]}>"
                return inner_types[0]
            if name in _COLLECTION_TYPES:
                return f"List<{inner_types[0]}>"
            return f"{name}<{', '.join(inner_types)}>"
    if getattr(t, "dimensions", None):
        return f"List<{name}>"
    return name


def extract_codebase_operations_and_calls(
    codebase_path: Path,
    partition: Partition,
) -> Tuple[List[Tuple[str, Operation]], List[Edge], Dict[str, dict]]:
    """
    Extracts declared operations and class-to-class call graph edges from a monolith codebase.
    Resolves Java imports, field types, parameter types, and local variable types (matching SOTA dataset.py).
    """
    cache_key = f"{codebase_path.resolve()}::{sorted(partition.microservices.keys())}"
    if cache_key in _CODEBASE_EXTRACTION_CACHE:
        return _CODEBASE_EXTRACTION_CACHE[cache_key]

    methods_dict: Dict[str, Operation] = {}
    methods_by_class_and_name: Dict[Tuple[str, str], Operation] = {}
    methods_by_name: Dict[str, List[Operation]] = {}
    classes_by_simple: Dict[str, Set[str]] = {}
    dataset_methods: Dict[str, dict] = {}

    parsed_java_units = []
    parsed_python_classes = []
    other_source_files = []

    # Pass 1: Discover all classes and methods in the codebase
    for root, dirs, files in os.walk(codebase_path):
        dirs[:] = [d for d in dirs if d.lower() not in _EXCLUDE_DIRS and not d.startswith(".")]
        for f in files:
            file_path = Path(root) / f
            if f.endswith(".java") and f not in ("package-info.java", "module-info.java") and javalang:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        code = fp.read()
                    sanitized = _sanitize_java_for_javalang(code)
                    tree = javalang.parse.parse(sanitized)
                    pkg = tree.package.name if tree.package else ""
                    imports = {}
                    wildcard_pkgs = []
                    if tree.imports:
                        for imp in tree.imports:
                            if imp.wildcard:
                                wildcard_pkgs.append(imp.path)
                            else:
                                short_name = imp.path.split(".")[-1]
                                imports[short_name] = imp.path

                    for decl_type in (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration, javalang.tree.EnumDeclaration):
                        for _, cls_node in tree.filter(decl_type):
                            cname = f"{pkg}.{cls_node.name}" if pkg else cls_node.name
                            classes_by_simple.setdefault(cls_node.name, set()).add(cname)
                            for m in getattr(cls_node, "methods", []):
                                ret = _format_javalang_type(m.return_type)
                                params = tuple(_format_javalang_type(p.type) for p in m.parameters if hasattr(p, "type") and p.type)
                                op = Operation(cls=cname, name=m.name, params=params, returns=ret)
                                full_id = f"{cname}.{m.name}"
                                methods_dict[full_id] = op
                                methods_by_class_and_name[(cname, m.name)] = op
                                methods_by_name.setdefault(m.name, []).append(op)
                                dataset_methods[full_id] = {
                                    "id": full_id,
                                    "package": pkg,
                                    "class": cls_node.name,
                                    "method_name": m.name,
                                    "parameters": list(params),
                                    "return_type": ret,
                                    "calls": [],
                                }
                            parsed_java_units.append((pkg, imports, wildcard_pkgs, cname, cls_node))
                except Exception:
                    pass
            elif f.endswith(".py") and not f.startswith("test_") and not f.endswith("_test.py"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        tree = ast.parse(fp.read())
                    mod_name = file_path.stem
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            cls_name = f"{mod_name}.{node.name}"
                            classes_by_simple.setdefault(node.name, set()).add(cls_name)
                            funcs = []
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    params = tuple(arg.arg for arg in item.args.args if arg.arg != "self")
                                    ret = "object"
                                    op = Operation(cls=cls_name, name=item.name, params=params, returns=ret)
                                    full_id = f"{cls_name}.{item.name}"
                                    methods_dict[full_id] = op
                                    methods_by_class_and_name[(cls_name, item.name)] = op
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
            elif f.endswith(".go") and not f.endswith("_test.go"):
                _extract_go_operations(file_path, methods_dict, methods_by_name, dataset_methods)
                other_source_files.append(file_path)
            elif f.endswith(".cs") and not f.endswith(".Designer.cs"):
                _extract_csharp_operations(file_path, methods_dict, methods_by_name, dataset_methods)
                other_source_files.append(file_path)

    def _resolve_java_type(type_name: str, pkg: str, imports: Dict[str, str], wildcard_pkgs: List[str]) -> str:
        if not type_name:
            return ""
        base_type = type_name.split("<")[0].strip()
        if base_type in imports:
            return imports[base_type]
        same_pkg_fqn = f"{pkg}.{base_type}" if pkg else base_type
        if same_pkg_fqn in classes_by_simple.get(base_type, set()):
            return same_pkg_fqn
        for wpkg in wildcard_pkgs:
            cand = f"{wpkg}.{base_type}"
            if cand in classes_by_simple.get(base_type, set()):
                return cand
        cands = classes_by_simple.get(base_type, set())
        if len(cands) == 1:
            return next(iter(cands))
        return same_pkg_fqn

    calls: List[Tuple[str, Operation]] = []
    edges: List[Edge] = []
    edges_seen: Set[Tuple[str, str]] = set()

    # Pass 2: Extract resolved method calls and class-to-class edges
    for pkg, imports, wildcard_pkgs, caller_cls, cls_node in parsed_java_units:
        field_types: Dict[str, str] = {}
        for field in getattr(cls_node, "fields", []):
            ftype = field.type.name if hasattr(field.type, "name") else str(field.type)
            resolved_ftype = _resolve_java_type(ftype, pkg, imports, wildcard_pkgs)
            for decl in field.declarators:
                field_types[decl.name] = resolved_ftype
                field_types[f"this.{decl.name}"] = resolved_ftype

        for m in getattr(cls_node, "methods", []):
            param_types: Dict[str, str] = {}
            for param in m.parameters:
                ptype = param.type.name if hasattr(param.type, "name") else ""
                param_types[param.name] = _resolve_java_type(ptype, pkg, imports, wildcard_pkgs)

            local_types: Dict[str, str] = {}
            if m.body:
                for _, loc in m.filter(javalang.tree.LocalVariableDeclaration):
                    ltype = loc.type.name if hasattr(loc.type, "name") else ""
                    resolved_ltype = _resolve_java_type(ltype, pkg, imports, wildcard_pkgs)
                    for decl in loc.declarators:
                        local_types[decl.name] = resolved_ltype

                for inv_path, inv in m.filter(javalang.tree.MethodInvocation):
                    inv_name = inv.member
                    qualifier = inv.qualifier
                    if not qualifier and inv_path:
                        # Handle `this.field.method()` where javalang places MemberReference in This.selectors
                        for ancestor in reversed(inv_path):
                            selectors = getattr(ancestor, "selectors", None)
                            if selectors and inv in selectors:
                                idx = selectors.index(inv)
                                if idx > 0 and isinstance(selectors[idx - 1], javalang.tree.MemberReference):
                                    qualifier = selectors[idx - 1].member
                                break
                    target_cls = None
                    if qualifier:
                        q_clean = qualifier[5:] if qualifier.startswith("this.") else qualifier
                        target_cls = (
                            local_types.get(q_clean)
                            or param_types.get(q_clean)
                            or field_types.get(q_clean)
                            or imports.get(q_clean)
                        )
                        if not target_cls and q_clean in classes_by_simple:
                            target_cls = _resolve_java_type(q_clean, pkg, imports, wildcard_pkgs)
                        if not target_cls:
                            target_cls = qualifier
                    else:
                        target_cls = caller_cls

                    full_caller_id = f"{caller_cls}.{m.name}"
                    if full_caller_id in dataset_methods and target_cls:
                        dataset_methods[full_caller_id]["calls"].append(f"{target_cls}.{inv_name}")

                    if target_cls and target_cls != caller_cls:
                        if (caller_cls, target_cls) not in edges_seen:
                            edges_seen.add((caller_cls, target_cls))
                            edges.append(Edge(src=caller_cls, dst=target_cls, type="CALL", weight=1.0))

                        target_op = methods_by_class_and_name.get((target_cls, inv_name))
                        if not target_op:
                            # Check simple class name match in methods_by_name
                            target_simple = target_cls.split(".")[-1]
                            for cand_op in methods_by_name.get(inv_name, []):
                                if cand_op.cls == target_cls or cand_op.cls.split(".")[-1] == target_simple:
                                    target_op = cand_op
                                    break
                        if target_op:
                            calls.append((caller_cls, target_op))

                # Constructor invocations (`new TargetClass(...)`)
                for _, creator in m.filter(javalang.tree.ClassCreator):
                    ctype = creator.type.name if hasattr(creator.type, "name") else ""
                    target_cls = _resolve_java_type(ctype, pkg, imports, wildcard_pkgs)
                    if target_cls and target_cls != caller_cls:
                        if (caller_cls, target_cls) not in edges_seen:
                            edges_seen.add((caller_cls, target_cls))
                            edges.append(Edge(src=caller_cls, dst=target_cls, type="CALL", weight=1.0))

    get_cluster = resolve_partition(partition.microservices, dataset_methods)

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
                        cands = methods_by_name[func_name]
                        if len(cands) == 1:
                            target_op = cands[0]
                            if target_op.cls != caller_cls:
                                calls.append((caller_cls, target_op))
                                if (caller_cls, target_op.cls) not in edges_seen:
                                    edges_seen.add((caller_cls, target_op.cls))
                                    edges.append(Edge(src=caller_cls, dst=target_op.cls, type="CALL", weight=1.0))

    for file_path in other_source_files:
        _extract_generic_calls(file_path, methods_by_name, get_cluster, calls, edges)

    result = (calls, edges, dataset_methods)
    _CODEBASE_EXTRACTION_CACHE[cache_key] = result
    return result


# ==============================================================================
# 2. Standalone Microservice Published Operations Extractor (for CHD and CHM)
# ==============================================================================

_MS_PUBLISHED_OPS_CACHE: Dict[str, Dict[str, Set[Operation]]] = {}

_JAVA_ENDPOINT_ANNOTATIONS = {
    "RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping",
    "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "Path",
    "MessageMapping", "SubscribeMapping", "KafkaListener", "RabbitListener", "JmsListener",
    "StreamListener", "SqsListener", "EventListener", "TransactionalEventListener",
    "QueryMapping", "MutationMapping", "SubscriptionMapping", "SchemaMapping",
    "Tool", "WebMethod", "FunctionName", "GrpcMethod", "Handler",
    "RepositoryRestResource", "RestResource",
}

_JAVA_CONTROLLER_ANNOTATIONS = {
    "RestController", "Controller", "Path", "GrpcService", "DubboService",
    "WebService", "GraphQLApi", "Endpoint", "WebEndpoint", "RestControllerEndpoint",
    "FeignClient", "HttpExchange", "RepositoryRestResource", "RestResource",
}

_JAVA_SERVICE_ANNOTATIONS = {
    "Service", "Component", "Stateless", "Stateful", "Singleton", "ApplicationScoped", "RequestScoped",
}

_JAVA_ENTITY_OR_CONFIG_ANNOTATIONS = {
    "Entity", "Table", "Embeddable", "MappedSuperclass", "Document",
    "Configuration", "SpringBootApplication", "ConfigurationProperties",
    "Repository", "Aspect", "ControllerAdvice", "RestControllerAdvice",
}

_JAVA_CONTROLLER_SUFFIXES = (
    "Controller", "Resource", "Endpoint", "Endpoints", "Rest", "Servlet",
    "Handler", "Facade", "Delegate", "GrpcService", "GrpcImpl", "RpcService",
    "Api", "ControllerImpl", "ResourceImpl", "ChatClient", "Tools",
)

_JAVA_SERVICE_SUFFIXES = (
    "Service", "ServiceImpl", "Manager", "UseCase", "Interactor",
    "Processor", "Consumer", "Listener", "Client", "Provider",
)

_JAVA_NON_OPERATION_CLASS_SUFFIXES = (
    "Application", "Config", "Configuration", "Properties", "Exception", "Error",
    "Entity", "Dto", "DTO", "VO", "PO", "Model", "Request", "Response",
    "Builder", "Repository", "Dao", "DAO", "Mapper", "Constants", "Utils", "Util",
)

_JAVA_FRAMEWORK_PARAM_TYPES = {
    "HttpServletRequest", "HttpServletResponse", "HttpSession", "BindingResult",
    "Errors", "Model", "ModelMap", "RedirectAttributes", "UriComponentsBuilder",
    "Principal", "Authentication", "Pageable", "ServerWebExchange", "Continuation",
    "WebRequest", "NativeWebRequest", "Locale", "TimeZone", "OutputStream", "Writer",
}

_BOILERPLATE_METHODS = {
    "main", "toString", "equals", "hashCode", "canEqual", "clone", "compareTo",
    "builder", "build", "init", "destroy", "close", "afterPropertiesSet",
    "configure", "contextLoads", "get", "set",
}


def _is_trivial_accessor(name: str, param_count: int, return_type: str) -> bool:
    if name in _BOILERPLATE_METHODS:
        return True
    if name.startswith("get") and len(name) > 3 and name[3].isupper() and param_count == 0 and return_type != "void":
        return True
    if name.startswith("is") and len(name) > 2 and name[2].isupper() and param_count == 0 and return_type in ("boolean", "Boolean", "bool"):
        return True
    if name.startswith("set") and len(name) > 3 and name[3].isupper() and param_count == 1 and return_type in ("void", "Void"):
        return True
    return False


def _resolve_service_directories(ms_dir: Path, partition: Partition) -> Dict[str, Path]:
    """Resolves each microservice cluster ID in `partition` to its directory on disk."""
    service_dirs: Dict[str, Path] = {}
    if MICROSERVICES_JSON.exists():
        try:
            with open(MICROSERVICES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            entry = data.get(partition.system_name)
            if not entry:
                for k, v in data.items():
                    if v.get("path") == ms_dir.name or ms_dir.name.startswith(f"{k}_"):
                        entry = v
                        break
            if entry and entry.get("services"):
                for cid in partition.microservices:
                    rel = entry["services"].get(cid)
                    if rel:
                        cand = (ms_dir / rel).resolve()
                        if cand.is_dir():
                            service_dirs[cid] = cand
        except Exception:
            pass

    for cid in partition.microservices:
        if cid not in service_dirs:
            cand = (ms_dir / cid).resolve()
            if cand.is_dir():
                service_dirs[cid] = cand
            else:
                for container in ("src", "services", "apps", "packages"):
                    sub = (ms_dir / container / cid).resolve()
                    if sub.is_dir():
                        service_dirs[cid] = sub
                        break
    return service_dirs


def extract_microservice_published_ops(
    ms_dir: Path,
    partition: Partition,
) -> Dict[str, Set[Operation]]:
    """
    Extracts published/exposed operations for each microservice directly from its source code
    using a 3-tier hierarchy:
      Tier 1: Explicit API endpoints, Controllers, REST resources, RPC services, message/event handlers.
      Tier 2: Service-layer classes/interfaces (if the microservice has no Tier-1 endpoints).
      Tier 3: Public non-entity business methods (fallback if neither Tier 1 nor Tier 2 exists).
    """
    cache_key = f"{ms_dir.resolve()}::{sorted(partition.microservices.keys())}"
    if cache_key in _MS_PUBLISHED_OPS_CACHE:
        return _MS_PUBLISHED_OPS_CACHE[cache_key]

    clusters = set(partition.microservices.keys())
    ops_per_ms: Dict[str, Set[Operation]] = {cid: set() for cid in clusters}
    service_dirs = _resolve_service_directories(ms_dir, partition)

    for cid in clusters:
        sdir = service_dirs.get(cid)
        if sdir and sdir.is_dir():
            ops_per_ms[cid] = _extract_service_dir_published_ops(sdir, cid)

    # If any cluster did not have a dedicated directory (e.g. virtual partition over a single root),
    # scan ms_dir and assign operations via resolve_partition
    missing_cids = [cid for cid in clusters if cid not in service_dirs]
    if missing_cids:
        get_cluster = resolve_partition(partition.microservices)
        fallback_ops = _extract_partitioned_dir_published_ops(ms_dir, get_cluster, set(missing_cids))
        for cid in missing_cids:
            ops_per_ms[cid] = fallback_ops.get(cid, set())

    _MS_PUBLISHED_OPS_CACHE[cache_key] = ops_per_ms
    return ops_per_ms


def _extract_service_dir_published_ops(sdir: Path, cid: str) -> Set[Operation]:
    tier1: Set[Operation] = set()
    tier2: Set[Operation] = set()
    tier3: Set[Operation] = set()

    for root, dirs, files in os.walk(sdir):
        dirs[:] = [d for d in dirs if d.lower() not in _EXCLUDE_DIRS and not d.startswith(".")]
        rel_parts = [p.lower() for p in Path(root).relative_to(sdir).parts]
        if any(p in ("test", "tests", "testing", "__tests__", "testdata", "e2e", "migrations") for p in rel_parts):
            continue

        for f in files:
            fl = f.lower()
            file_path = Path(root) / f
            if fl.endswith(".java") and f not in ("package-info.java", "module-info.java") and not fl.endswith(("test.java", "tests.java", "it.java")):
                _collect_java_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith(".cs") and not fl.endswith((".designer.cs", ".g.cs", "test.cs", "tests.cs", "grpc.cs")):
                _collect_csharp_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith(".py") and not (f.startswith("__") and f != "__main__.py") and not f.startswith("test_") and not fl.endswith(("_test.py", "_pb2.py", "_pb2_grpc.py")) and f not in ("setup.py", "conftest.py", "manage.py", "wsgi.py", "asgi.py", "tests.py"):
                _collect_python_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith(".go") and not fl.endswith(("_test.go", ".pb.go")):
                _collect_go_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith((".ts", ".js", ".tsx", ".jsx")) and not fl.endswith((".spec.ts", ".spec.js", ".test.ts", ".test.js", ".d.ts", ".min.js", ".config.js", ".config.ts", "_pb.js", "_grpc_pb.js")):
                _collect_js_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith((".kt", ".scala")) and not fl.endswith(("test.kt", "spec.kt", "test.scala", "spec.scala")):
                _collect_jvm_other_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith(".php") and not fl.endswith("test.php"):
                _collect_php_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith(".rb") and not fl.endswith(("_spec.rb", "_test.rb")):
                _collect_ruby_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith(".rs") and f != "build.rs":
                _collect_rust_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith(".ex"):
                _collect_elixir_file_ops(file_path, tier1, tier2, tier3)
            elif fl.endswith((".cpp", ".cc", ".hpp", ".h")) and not fl.endswith(("_test.cpp", "_test.cc")):
                _collect_cpp_file_ops(file_path, tier1, tier2, tier3)

    if tier1:
        return tier1
    if tier2:
        return tier2
    return tier3


def _extract_partitioned_dir_published_ops(root_dir: Path, get_cluster, target_cids: Set[str]) -> Dict[str, Set[Operation]]:
    t1: Dict[str, Set[Operation]] = {c: set() for c in target_cids}
    t2: Dict[str, Set[Operation]] = {c: set() for c in target_cids}
    t3: Dict[str, Set[Operation]] = {c: set() for c in target_cids}

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d.lower() not in _EXCLUDE_DIRS and not d.startswith(".")]
        for f in files:
            file_path = Path(root) / f
            f_t1, f_t2, f_t3 = set(), set(), set()
            if f.endswith(".java") and f not in ("package-info.java", "module-info.java"):
                _collect_java_file_ops(file_path, f_t1, f_t2, f_t3)
            elif f.endswith(".py") and not f.startswith("__"):
                _collect_python_file_ops(file_path, f_t1, f_t2, f_t3)
            elif f.endswith(".go") and not f.endswith("_test.go"):
                _collect_go_file_ops(file_path, f_t1, f_t2, f_t3)
            elif f.endswith(".cs") and not f.endswith(".Designer.cs"):
                _collect_csharp_file_ops(file_path, f_t1, f_t2, f_t3)
            for op in f_t1:
                cid = get_cluster(op.cls)
                if cid in target_cids:
                    t1[cid].add(op)
            for op in f_t2:
                cid = get_cluster(op.cls)
                if cid in target_cids:
                    t2[cid].add(op)
            for op in f_t3:
                cid = get_cluster(op.cls)
                if cid in target_cids:
                    t3[cid].add(op)

    return {cid: (t1[cid] or t2[cid] or t3[cid]) for cid in target_cids}


def _collect_java_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    parsed_ok = False
    if javalang:
        try:
            sanitized = _sanitize_java_for_javalang(code)
            tree = javalang.parse.parse(sanitized)
            pkg = tree.package.name if tree.package else ""

            for decl_type in (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration):
                is_interface = (decl_type is javalang.tree.InterfaceDeclaration)
                for _, cls_node in tree.filter(decl_type):
                    cls_name = cls_node.name
                    cname = f"{pkg}.{cls_name}" if pkg else cls_name
                    cls_anns = {a.name.split(".")[-1] for a in getattr(cls_node, "annotations", [])}

                    if cls_anns & _JAVA_ENTITY_OR_CONFIG_ANNOTATIONS:
                        continue

                    is_controller_cls = bool(cls_anns & _JAVA_CONTROLLER_ANNOTATIONS) or cls_name.endswith(_JAVA_CONTROLLER_SUFFIXES)
                    is_service_cls = (
                        bool(cls_anns & _JAVA_SERVICE_ANNOTATIONS)
                        or cls_name.endswith(_JAVA_SERVICE_SUFFIXES)
                        or (is_interface and not cls_name.endswith(("Repository", "Dao", "DAO", "Mapper")))
                    )
                    is_non_op_cls = cls_name.endswith(_JAVA_NON_OPERATION_CLASS_SUFFIXES)

                    for m in getattr(cls_node, "methods", []):
                        mods = set(getattr(m, "modifiers", []) or [])
                        if "private" in mods:
                            continue
                        m_anns = {a.name.split(".")[-1] for a in getattr(m, "annotations", [])}
                        ret = _format_javalang_type(m.return_type)
                        if ret == "record":
                            continue
                        params = tuple(
                            _format_javalang_type(p.type)
                            for p in m.parameters
                            if hasattr(p, "type") and p.type and _format_javalang_type(p.type) not in _JAVA_FRAMEWORK_PARAM_TYPES
                        )
                        op = Operation(cls=cname, name=m.name, params=params, returns=ret)

                        if m_anns & _JAVA_ENDPOINT_ANNOTATIONS:
                            tier1.add(op)
                        elif is_controller_cls and m.name not in _BOILERPLATE_METHODS and not _is_trivial_accessor(m.name, len(params), ret):
                            tier1.add(op)
                        elif is_service_cls and not _is_trivial_accessor(m.name, len(params), ret):
                            tier2.add(op)
                        elif not is_non_op_cls and "public" in mods and not _is_trivial_accessor(m.name, len(params), ret):
                            tier3.add(op)
            parsed_ok = True
        except Exception:
            parsed_ok = False

    if not parsed_ok:
        # Regex fallback for Java 16+ files with `record` or pattern-matching switch
        cleaned = strip_java_comments_and_strings(code)
        if re.search(r"\brecord\s+[A-Za-z_]", cleaned) and not re.search(r"@(?:RestController|Controller|Service)\b", code):
            # Pure record DTO file
            return
        pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_.]+)\s*;", cleaned, re.MULTILINE)
        pkg = pkg_match.group(1).strip() if pkg_match else ""
        cls_name = file_path.stem
        cname = f"{pkg}.{cls_name}" if pkg else cls_name
        is_ctrl = bool(re.search(r"@(?:RestController|Controller|Path|GrpcService)\b", code)) or cls_name.endswith(_JAVA_CONTROLLER_SUFFIXES)
        is_svc = bool(re.search(r"@(?:Service|Component)\b", code)) or cls_name.endswith(_JAVA_SERVICE_SUFFIXES)
        if not is_ctrl and not is_svc and cls_name.endswith(_JAVA_NON_OPERATION_CLASS_SUFFIXES):
            return
        method_pat = re.compile(
            r"(?:@(?:RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|GET|POST|PUT|DELETE|Tool|KafkaListener|RabbitListener|EventListener)\b[^;{]*?)?"
            r"\bpublic\s+(?:static\s+|final\s+|synchronized\s+)*([A-Za-z0-9_<>?,\[\]\s]+?)\s+([a-z][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\{"
        )
        for match in method_pat.finditer(cleaned):
            ret_raw = match.group(1).strip().split()[-1]
            mname = match.group(2).strip()
            params_raw = match.group(3).strip()
            p_list = []
            if params_raw:
                for p in params_raw.split(","):
                    tokens = [tok for tok in p.strip().split() if not tok.startswith("@") and tok != "final"]
                    if len(tokens) >= 2:
                        ptype = tokens[-2]
                        if ptype not in _JAVA_FRAMEWORK_PARAM_TYPES:
                            p_list.append(ptype)
            op = Operation(cls=cname, name=mname, params=tuple(p_list), returns=ret_raw)
            if is_ctrl and not _is_trivial_accessor(mname, len(p_list), ret_raw):
                tier1.add(op)
            elif is_svc and not _is_trivial_accessor(mname, len(p_list), ret_raw):
                tier2.add(op)
            elif not _is_trivial_accessor(mname, len(p_list), ret_raw):
                tier3.add(op)


def _unwrap_csharp_type(t: str) -> str:
    t = t.strip()
    for wrapper in ("Task", "ValueTask", "ActionResult", "IActionResult", "TypedResults", "Results"):
        m = re.match(rf"^{wrapper}<(.+)>$", t)
        if m:
            return _unwrap_csharp_type(m.group(1))
    if t in ("IActionResult", "ActionResult", "Task", "ValueTask", "IResult"):
        return "void"
    for coll in ("IEnumerable", "IList", "ICollection", "IReadOnlyList", "IReadOnlyCollection", "List", "HashSet"):
        m = re.match(rf"^{coll}<(.+)>$", t)
        if m:
            return f"List<{_unwrap_csharp_type(m.group(1))}>"
    return t


def _collect_csharp_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    cleaned = strip_java_comments_and_strings(code)
    ns_match = re.search(r"^\s*namespace\s+([a-zA-Z0-9_.]+)", cleaned, re.MULTILINE)
    ns = ns_match.group(1).strip() if ns_match else ""
    cls_match = re.search(r"\b(?:class|interface)[ \t]+([A-Za-z_][A-Za-z0-9_]*)", cleaned)
    cls_name = cls_match.group(1) if cls_match else file_path.stem
    cname = f"{ns}.{cls_name}" if ns else cls_name

    is_non_op = cls_name.endswith(("Context", "Migration", "Startup", "Program", "Options", "Settings", "Dto", "DTO", "Entity", "Model", "Event", "Exception", "Extensions"))
    is_ctrl = not is_non_op and (
        bool(re.search(r"\[(?:ApiController|Route)\b", code))
        or bool(re.search(r":\s*(?:ControllerBase|Controller|Hub|[A-Za-z0-9_.]*Base)\b", cleaned))
        or "ServerCallContext" in code
        or cls_name.endswith(("Controller", "Api", "Apis", "Endpoints", "Endpoint", "Hub", "IntegrationEventHandler", "CommandHandler", "QueryHandler"))
    )
    is_svc = not is_non_op and (cls_name.endswith(("Service", "Manager", "Handler", "Consumer", "Processor", "Client")) or cls_name.startswith("I"))

    method_pat = re.compile(
        r"((?:\[\s*Http(?:Get|Post|Put|Delete|Patch)[^\]]*\]\s*)*)"
        r"\b(?:public|internal)\s+(?:virtual\s+|override\s+|async\s+|static\s+)*([A-Za-z0-9_<>?,\[\]]+)\s+([A-Z][A-Za-z0-9_]*)\s*\(([^)]*)\)"
    )
    found_methods = False
    for match in method_pat.finditer(code):
        attrs = match.group(1)
        ret = _unwrap_csharp_type(match.group(2).strip())
        if ret == "record":
            continue
        mname = match.group(3).strip()
        if mname == cls_name or mname in ("Dispose", "ToString", "Equals", "GetHashCode", "Main", "Configure", "ConfigureServices"):
            continue
        params_raw = match.group(4).strip()
        p_list = []
        if params_raw:
            for p in params_raw.split(","):
                p_clean = re.sub(r"\[[^\]]*\]", "", p).strip()
                if not p_clean or p_clean.startswith("this "):
                    continue
                tokens = p_clean.split("=")[0].strip().split()
                if len(tokens) >= 2:
                    ptype = _unwrap_csharp_type(tokens[-2])
                    if ptype not in ("CancellationToken", "HttpContext", "ServerCallContext", "ILogger"):
                        p_list.append(ptype)
        op = Operation(cls=cname, name=mname, params=tuple(p_list), returns=ret)
        found_methods = True
        if attrs or is_ctrl:
            tier1.add(op)
        elif is_svc:
            tier2.add(op)
        elif not is_non_op:
            tier3.add(op)

    if not found_methods:
        # Minimal API route mappings when no explicit C# methods are declared
        for m in re.finditer(r"\bMap(Get|Post|Put|Delete|Patch)\s*\(\s*\"([^\"]*)\"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)", code):
            verb, route, handler = m.group(1), m.group(2), m.group(3)
            if handler not in ("async", "context", "req", "http"):
                tier1.add(Operation(cls=cname, name=handler, params=(verb.lower(),), returns="object"))


def _collect_python_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(code)
    except Exception:
        return

    stem = file_path.stem.lower()
    rel_parts_lower = [p.lower() for p in file_path.parts[-3:]]
    is_api_file = any(
        k in stem or any(k in p for p in rel_parts_lower)
        for k in ("view", "views", "route", "routes", "router", "api", "controller", "endpoint", "handler", "resource", "rpc", "servicer", "server", "task", "tasks")
    )
    is_svc_file = any(k in stem for k in ("service", "services", "manager", "client", "worker", "consumer", "processor"))
    is_model_or_cfg = stem in ("models", "model", "schemas", "schema", "config", "settings", "admin", "apps", "urls", "constants", "exceptions", "serializers")

    def _has_route_decorator(node) -> bool:
        for dec in getattr(node, "decorator_list", []):
            dec_str = ast.unparse(dec).lower() if hasattr(ast, "unparse") else ""
            if any(k in dec_str for k in ("route", ".get(", ".post(", ".put(", ".delete(", ".patch(", "api_view", "action", "rpc", "event_handler", "task", "http", "endpoint")):
                return True
        return False

    def _build_py_op(cls_label: str, fn_node) -> Operation:
        params = []
        for arg in fn_node.args.args:
            if arg.arg in ("self", "cls", "request", "info", "context"):
                continue
            if arg.annotation and hasattr(ast, "unparse"):
                ann = ast.unparse(arg.annotation)
                params.append(f"{arg.arg}:{ann}")
            else:
                params.append(arg.arg)
        ret = "object"
        if fn_node.returns and hasattr(ast, "unparse"):
            ret = ast.unparse(fn_node.returns)
        return Operation(cls=cls_label, name=fn_node.name, params=tuple(params), returns=ret)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") or node.name in ("main", "create_app"):
                continue
            op = _build_py_op(file_path.stem, node)
            if _has_route_decorator(node) or is_api_file:
                tier1.add(op)
            elif is_svc_file:
                tier2.add(op)
            elif not is_model_or_cfg:
                tier3.add(op)
        elif isinstance(node, ast.ClassDef):
            cname = f"{file_path.stem}.{node.name}"
            bases = [ast.unparse(b) if hasattr(ast, "unparse") else "" for b in node.bases]
            is_ctrl_cls = is_api_file or any(
                k in b for b in bases for k in ("View", "ViewSet", "Resource", "Handler", "Servicer", "Controller", "Router")
            ) or node.name.endswith(("View", "ViewSet", "Resource", "Controller", "Handler", "Servicer", "API"))
            is_svc_cls = is_svc_file or node.name.endswith(("Service", "Manager", "Client", "Processor", "Consumer", "Worker"))
            is_entity_cls = is_model_or_cfg or any(
                k in b for b in bases for k in ("Model", "Base", "BaseModel", "Schema", "Serializer", "Exception", "Enum")
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("_"):
                        continue
                    op = _build_py_op(cname, item)
                    if _has_route_decorator(item) or is_ctrl_cls:
                        tier1.add(op)
                    elif is_svc_cls:
                        tier2.add(op)
                    elif not is_entity_cls:
                        tier3.add(op)


def _collect_go_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    cleaned = strip_java_comments_and_strings(code)
    pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_]+)", cleaned, re.MULTILINE)
    pkg = pkg_match.group(1) if pkg_match else file_path.parent.name
    stem = file_path.stem.lower()
    is_handler_file = any(k in stem or k in pkg.lower() for k in ("handler", "controller", "server", "transport", "endpoint", "router", "api", "grpc", "rpc", "http"))
    is_svc_file = any(k in stem or k in pkg.lower() for k in ("service", "usecase", "manager", "client", "processor"))

    # Match both receiver methods `func (r *Recv) Name(params) returns` and functions `func Name(params) returns`
    pattern = re.compile(
        r"\bfunc\s+(?:\(\s*\w*\s*\*?([A-Za-z0-9_]+)\s*\)\s*)?([a-zA-Z][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(\([^)]*\)|[A-Za-z0-9_.*\[\]]+)?"
    )
    for match in pattern.finditer(cleaned):
        recv = match.group(1)
        mname = match.group(2)
        if mname.startswith(("New", "new", "Test", "Benchmark")) or mname in ("main", "Main", "init", "Init", "String", "Error", "Close", "ServeHTTP", "Run"):
            continue
        cls = f"{pkg}.{recv}" if recv else f"{pkg}.{file_path.stem}"
        params_raw = match.group(3).strip()
        p_list = []
        is_http_or_rpc_sig = mname.lower().endswith("handler")
        if params_raw:
            for p in params_raw.split(","):
                p_str = p.strip()
                if any(k in p_str for k in ("ResponseWriter", "http.Request", "gin.Context", "echo.Context", "fiber.Ctx", "context.Context")):
                    is_http_or_rpc_sig = True
                    continue
                toks = p_str.split()
                if toks:
                    p_list.append(toks[-1].lstrip("*"))
        if not is_http_or_rpc_sig and mname[0].islower():
            continue
        ret_raw = (match.group(4) or "void").strip()
        if ret_raw.startswith("(") and ret_raw.endswith(")"):
            ret_parts = [r.strip().split()[-1].lstrip("*") for r in ret_raw[1:-1].split(",") if r.strip()]
            ret_parts = [r for r in ret_parts if r != "error"]
            ret = ret_parts[0] if ret_parts else "void"
        else:
            ret = ret_raw.lstrip("*")
            if ret == "error":
                ret = "void"

        op = Operation(cls=cls, name=mname, params=tuple(p_list), returns=ret)
        is_recv_ctrl = bool(recv and any(k in recv.lower() for k in ("handler", "controller", "server", "endpoint", "api", "transport")))
        is_recv_svc = bool(recv and any(k in recv.lower() for k in ("service", "usecase", "manager", "client")))
        if is_http_or_rpc_sig or is_recv_ctrl or is_handler_file:
            tier1.add(op)
        elif is_recv_svc or is_svc_file:
            tier2.add(op)
        else:
            tier3.add(op)


def _collect_js_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    cleaned = strip_java_comments_and_strings(code)
    stem = file_path.stem
    stem_l = stem.lower()
    rel_l = file_path.as_posix().lower()
    is_ctrl = any(k in stem_l or f"/{k}/" in rel_l for k in ("controller", "controllers", "route", "routes", "router", "handler", "handlers", "resolver", "resolvers", "api", "endpoint", "server"))
    is_svc = any(k in stem_l or f"/{k}/" in rel_l for k in ("service", "services", "usecase", "manager", "client", "provider"))

    # 1. Express / Fastify / Koa routes: app.get('/orders/:id', ...) or router.post('/users', ...)
    route_pat = re.compile(r"\b(?:app|router|server|fastify|api)\s*\.\s*(get|post|put|delete|patch)\s*\(\s*['\"`]([^'\"`]+)['\"`]")
    for match in route_pat.finditer(code):
        verb = match.group(1).lower()
        path_str = match.group(2)
        seg_words = [w for w in re.findall(r"[A-Za-z0-9]+", path_str) if w.lower() not in ("api", "v1", "v2", "v3")]
        op_name = f"{verb}_{'_'.join(seg_words)}" if seg_words else verb
        params = tuple(re.findall(r":([A-Za-z0-9_]+)", path_str)) or (verb,)
        tier1.add(Operation(cls=stem, name=op_name, params=params, returns="object"))

    # 2. NestJS / TS class methods or standard JS/TS functions
    method_pat = re.compile(
        r"((?:@(?:Get|Post|Put|Delete|Patch|MessagePattern|EventPattern|Query|Mutation|GrpcMethod)\b[^;{]*)*)"
        r"\b(?:public\s+|async\s+|export\s+)*(?:function\s+)?([a-zA-Z_][A-Za-z0-9_]*)\s*\(([^(){};'\"`]*)\)\s*(?::\s*([A-Za-z0-9_<>|\[\]]+))?\s*\{"
    )
    js_skip = {
        "if", "for", "while", "switch", "catch", "function", "constructor", "render",
        "ngOnInit", "componentDidMount", "useEffect", "describe", "it", "test", "beforeEach", "afterEach",
    }
    for match in method_pat.finditer(cleaned):
        decs = match.group(1)
        mname = match.group(2)
        if mname in js_skip or mname.startswith("_"):
            continue
        params_raw = match.group(3).strip()
        p_list = []
        if params_raw:
            for p in params_raw.split(","):
                p_clean = re.sub(r"@[A-Za-z0-9_]+(?:\([^)]*\))?", "", p).strip()
                if ":" in p_clean:
                    ptype = p_clean.split(":", 1)[1].split("=")[0].strip()
                    p_list.append(ptype)
                else:
                    pname = p_clean.split("=")[0].strip()
                    if pname and pname not in ("req", "res", "next", "ctx"):
                        p_list.append(pname)
        ret = (match.group(4) or "object").strip()
        m_wrap = re.match(r"^Promise<(.+)>$", ret)
        if m_wrap:
            ret = m_wrap.group(1)
        op = Operation(cls=stem, name=mname, params=tuple(p_list), returns=ret)
        if decs or is_ctrl:
            tier1.add(op)
        elif is_svc:
            tier2.add(op)
        else:
            tier3.add(op)


def _collect_jvm_other_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    cleaned = strip_java_comments_and_strings(code)
    stem = file_path.stem
    is_ctrl = bool(re.search(r"@(?:RestController|Controller|Path)\b", code)) or stem.endswith(_JAVA_CONTROLLER_SUFFIXES)
    is_svc = bool(re.search(r"@(?:Service|Component)\b", code)) or stem.endswith(_JAVA_SERVICE_SUFFIXES)
    # Kotlin `fun name(p: Type): Ret` or Scala `def name(p: Type): Ret`
    pat = re.compile(r"\b(?:fun|def)\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?::\s*([A-Za-z0-9_<>?,\[\]]+))?")
    for match in pat.finditer(cleaned):
        mname = match.group(1)
        if mname in ("main", "toString", "equals", "hashCode", "apply", "unapply"):
            continue
        params_raw = match.group(2).strip()
        p_list = []
        if params_raw:
            for p in params_raw.split(","):
                if ":" in p:
                    p_list.append(p.split(":", 1)[1].split("=")[0].strip())
        ret = (match.group(3) or "Unit").strip()
        op = Operation(cls=stem, name=mname, params=tuple(p_list), returns=ret)
        if is_ctrl:
            tier1.add(op)
        elif is_svc:
            tier2.add(op)
        else:
            tier3.add(op)


def _collect_php_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    cleaned = strip_java_comments_and_strings(code)
    stem = file_path.stem
    is_ctrl = "controller" in stem.lower() or "handler" in stem.lower()
    is_svc = any(k in stem.lower() for k in ("service", "creator", "finder", "renamer", "authenticator", "storer", "usecase"))
    for match in re.finditer(r"\bpublic\s+function\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?::\s*\??([A-Za-z0-9_\\]+))?", cleaned):
        mname = match.group(1)
        if mname.startswith("__") and mname != "__invoke":
            continue
        op_name = stem if mname == "__invoke" else mname
        params_raw = match.group(2).strip()
        p_list = []
        if params_raw:
            for p in params_raw.split(","):
                toks = p.strip().split("=")[0].strip().split()
                if len(toks) >= 2:
                    p_list.append(toks[0].lstrip("?\\"))
                elif toks:
                    p_list.append(toks[0].lstrip("$"))
        ret = (match.group(3) or "void").split("\\")[-1]
        op = Operation(cls=stem, name=op_name, params=tuple(p_list), returns=ret)
        if is_ctrl:
            tier1.add(op)
        elif is_svc:
            tier2.add(op)
        else:
            tier3.add(op)


def _collect_ruby_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    stem = file_path.stem
    is_ctrl = "controller" in stem.lower() or "api" in stem.lower() or "endpoint" in stem.lower()
    is_svc = "service" in stem.lower() or "worker" in stem.lower() or "job" in stem.lower()
    for match in re.finditer(r"^\s*def\s+([a-zA-Z_][A-Za-z0-9_]*)(?:\(([^)]*)\))?", code, re.MULTILINE):
        mname = match.group(1)
        if mname in ("initialize", "self"):
            continue
        params_raw = (match.group(2) or "").strip()
        p_list = [p.split("=")[0].strip() for p in params_raw.split(",") if p.strip()] if params_raw else []
        op = Operation(cls=stem, name=mname, params=tuple(p_list), returns="object")
        if is_ctrl:
            tier1.add(op)
        elif is_svc:
            tier2.add(op)
        else:
            tier3.add(op)


def _collect_rust_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    cleaned = strip_java_comments_and_strings(code)
    stem = file_path.stem
    is_ctrl = any(k in stem.lower() for k in ("handler", "controller", "route", "api", "server", "rpc"))
    for match in re.finditer(r"\bpub\s+(?:async\s+)?fn\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:->\s*([^{]+))?", cleaned):
        mname = match.group(1)
        if mname in ("new", "default", "main", "fmt"):
            continue
        params_raw = match.group(2).strip()
        p_list = []
        if params_raw:
            for p in params_raw.split(","):
                if ":" in p:
                    p_list.append(p.split(":", 1)[1].strip().lstrip("&"))
        ret = (match.group(3) or "void").strip()
        op = Operation(cls=stem, name=mname, params=tuple(p_list), returns=ret)
        if is_ctrl:
            tier1.add(op)
        else:
            tier2.add(op)


def _collect_elixir_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    stem = file_path.stem
    is_ctrl = any(k in stem.lower() for k in ("controller", "router", "endpoint", "rpc", "channel", "view"))
    for match in re.finditer(r"^\s*def\s+([a-z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)", code, re.MULTILINE):
        mname = match.group(1)
        if mname.startswith("_") or mname in ("init", "call", "child_spec", "start_link"):
            continue
        params_raw = match.group(2).strip()
        p_list = [p.strip().split("\\")[0].strip() for p in params_raw.split(",") if p.strip() and p.strip() != "conn"]
        op = Operation(cls=stem, name=mname, params=tuple(p_list), returns="term")
        if is_ctrl:
            tier1.add(op)
        else:
            tier2.add(op)


def _collect_cpp_file_ops(file_path: Path, tier1: Set[Operation], tier2: Set[Operation], tier3: Set[Operation]) -> None:
    try:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    cleaned = strip_java_comments_and_strings(code)
    stem = file_path.stem
    is_svc = any(k in stem.lower() for k in ("handler", "service", "server", "controller", "api"))
    for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_:<>*&]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:override\s*)?\{", cleaned):
        ret = match.group(1).strip()
        mname = match.group(2).strip()
        if ret in ("if", "for", "while", "switch", "return", "else") or mname == stem or mname == "main":
            continue
        params_raw = match.group(3).strip()
        p_list = []
        if params_raw:
            for p in params_raw.split(","):
                toks = [t for t in p.strip().split() if t not in ("const", "auto")]
                if len(toks) >= 2:
                    p_list.append(toks[-2].strip("&*"))
        op = Operation(cls=stem, name=mname, params=tuple(p_list), returns=ret)
        if is_svc:
            tier1.add(op)
        else:
            tier2.add(op)


def _extract_go_operations(file_path: Path, methods_dict, methods_by_name, dataset_methods):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_]+)", code, re.MULTILINE)
        pkg = pkg_match.group(1) if pkg_match else file_path.parent.name

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
            if m_name in methods_by_name and len(methods_by_name[m_name]) == 1:
                target_op = methods_by_name[m_name][0]
                target_cluster = get_cluster(target_op.cls)
                if target_cluster and target_cluster != caller_cluster:
                    calls.append((caller_cls, target_op))
                    edges.append(Edge(src=caller_cls, dst=target_op.cls, type="CALL"))
    except Exception:
        pass


# ==============================================================================
# 3. Standalone Microservice Intra-Service Call Edge Extractor (for SM)
# ==============================================================================

_MS_INTRA_EDGES_CACHE: Dict[str, List[Edge]] = {}

_SOURCE_EXTENSIONS = (
    ".java", ".py", ".go", ".cs", ".ts", ".js", ".tsx", ".jsx",
    ".kt", ".scala", ".php", ".rb", ".rs", ".ex", ".cpp", ".cc", ".hpp", ".h",
)


def extract_intra_service_edges(
    ms_dir: Path,
    partition: Partition,
) -> List[Edge]:
    """
    Extracts intra-microservice class-to-class dependency/call edges (mu_k in SM)
    directly from each microservice's source directory.
    All returned edges are strictly internal to a single microservice (src != dst,
    get_cluster(src) == get_cluster(dst)) and deduplicated at the (src, dst) pair level.
    """
    cache_key = f"{ms_dir.resolve()}::{sorted(partition.microservices.keys())}"
    if cache_key in _MS_INTRA_EDGES_CACHE:
        return list(_MS_INTRA_EDGES_CACHE[cache_key])

    service_dirs = _resolve_service_directories(ms_dir, partition)
    all_edges: List[Edge] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for cid, member_classes in partition.microservices.items():
        if len(member_classes) < 2:
            continue

        sdir = service_dirs.get(cid, ms_dir)
        if not sdir or not sdir.is_dir():
            continue

        sub_partition = Partition(
            microservices={cid: list(member_classes)},
            system_name=f"{partition.system_name}_{cid}",
        )
        clusters_map, get_sub_cluster = resolve_partition_with_clusters(sub_partition.microservices)
        canonical_members = clusters_map.get(cid, set(member_classes))

        # 1. AST-resolved Java/Python method & constructor call edges within sdir
        _, ast_edges, _ = extract_codebase_operations_and_calls(sdir, sub_partition)
        for e in ast_edges:
            if get_sub_cluster(e.src) == cid and get_sub_cluster(e.dst) == cid:
                # Normalize to canonical names if possible
                src_c = _normalize_to_canonical(e.src, canonical_members)
                dst_c = _normalize_to_canonical(e.dst, canonical_members)
                if src_c and dst_c and src_c != dst_c and (src_c, dst_c) not in seen_pairs:
                    seen_pairs.add((src_c, dst_c))
                    all_edges.append(Edge(src=src_c, dst=dst_c, type="CALL", weight=1.0))

        # 2. Multi-language symbol/type/call reference edges within sdir across member classes
        simple_to_canonical: Dict[str, List[str]] = {}
        for m_cls in canonical_members:
            simple = m_cls.split(".")[-1].split("/")[-1]
            if len(simple) >= 3:
                simple_to_canonical.setdefault(simple, []).append(m_cls)

        unique_simples = {s: c_list[0] for s, c_list in simple_to_canonical.items() if len(c_list) == 1}
        if len(unique_simples) < 2:
            continue

        for root, dirs, files in os.walk(sdir):
            dirs[:] = [d for d in dirs if d.lower() not in _EXCLUDE_DIRS and not d.startswith(".")]
            rel_parts = [p.lower() for p in Path(root).relative_to(sdir).parts]
            if any(p in ("test", "tests", "testing", "__tests__", "testdata", "e2e", "migrations") for p in rel_parts):
                continue

            for f in files:
                fl = f.lower()
                if not fl.endswith(_SOURCE_EXTENSIONS):
                    continue
                if fl.endswith(("test.java", "tests.java", "it.java", "_test.go", ".pb.go", "_test.py", ".spec.ts", ".test.ts", ".spec.js", ".test.js")):
                    continue
                file_path = Path(root) / f
                stem = file_path.stem
                caller_cls = unique_simples.get(stem)
                if not caller_cls:
                    # Check if stem matches any canonical class suffix
                    cands = simple_to_canonical.get(stem, [])
                    if len(cands) == 1:
                        caller_cls = cands[0]
                if not caller_cls:
                    continue

                try:
                    code = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                cleaned = strip_java_comments_and_strings(code)
                tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", cleaned))

                for tok in tokens:
                    callee_cls = unique_simples.get(tok)
                    if callee_cls and callee_cls != caller_cls:
                        if (caller_cls, callee_cls) not in seen_pairs:
                            seen_pairs.add((caller_cls, callee_cls))
                            all_edges.append(Edge(src=caller_cls, dst=callee_cls, type="CALL", weight=1.0))

    _MS_INTRA_EDGES_CACHE[cache_key] = list(all_edges)
    return all_edges


def _normalize_to_canonical(cls_name: str, canonical_members: Set[str]) -> Optional[str]:
    if cls_name in canonical_members:
        return cls_name
    simple = cls_name.split(".")[-1]
    matches = [c for c in canonical_members if c.split(".")[-1] == simple]
    if len(matches) == 1:
        return matches[0]
    return cls_name if matches else None

