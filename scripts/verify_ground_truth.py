"""Verification gates for a curated Ground-Truth extraction file.

Gate A (structure):  schema validity, and every class resolves -- via the same
                     lookup SM uses -- to the service it is declared under.
Gate B (evidence):   every call's evidence cites `path:line` and the backticked
                     snippet appears verbatim on that line of the codebase.
Gate C (coverage):   every outbound-call / entry-point site found by grep is
                     either cited by the ground truth or explicitly excluded.

Usage:
    uv run python scripts/verify_ground_truth.py MS032
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

from fyp_cdq.config import GROUND_TRUTH_DIR, OUTPUTS_DIR
from fyp_cdq.extractors.agent_loader import validate_agent_extraction_schema
from fyp_cdq.metrics.common import resolve_partition_with_clusters
from fyp_cdq.models import Partition
from fyp_cdq.pipeline import resolve_system_codebase

CURATION_DIR = GROUND_TRUTH_DIR.parent / "curation"

SOURCE_GLOBS = ("*.java", "*.kt", "*.cs", "*.go", "*.py", "*.js", "*.ts")
SKIP_PARTS = {"test", "tests", "target", "build", "node_modules", "vendor", ".git", "mocks"}

# Sites that may originate a cross-service call.
OUTBOUND_PATTERNS = [
    r"@FeignClient", r"RestTemplate\b.*\.(get|post|put|delete|exchange|patch)\w*\(",
    r"\.(get|post|put|delete|patch)ForObject\(", r"\.(get|post|put|delete|patch)ForEntity\(",
    r"WebClient.*\.(baseUrl|uri)\(", r"\.uri\(\s*\"", r"baseUrl\(\s*\"http",
    r"\boutput\(\)\.send\(", r"StreamBridge", r"KafkaTemplate", r"RabbitTemplate",
    r"convertAndSend\(", r"\.Publish(Async)?\(", r"\w*[Hh]ttp[Cc]lient\w*\??\.(Get|Post|Put|Delete|Patch|Send)\w*Async\(",
    r"\bfetch\(", r"axios\.", r"\.(get|post|put|patch|delete)\(\s*[`\"']/", r"requests\.(get|post|put|delete)\(", r"http\.(Get|Post)\(",
    r"\.NewRequest\(", r"pb\.New\w+Client\(",
    r"LoadBalanced(CRUD|Image|Recommender|Store)Operations\b", r"ServiceLoadBalancer\s*\.\s*(loadBalance|multicast)\w*\(",
]
# Sites that may expose an operation across the service boundary.
ENTRYPOINT_PATTERNS = [
    r"@(Get|Post|Put|Delete|Patch|Request)Mapping", r"@(GET|POST|PUT|DELETE|PATCH)\b", r"@WebServlet\b",
    r"@StreamListener", r"@KafkaListener", r"@RabbitListener", r"@JmsListener",
    r"\[Http(Get|Post|Put|Delete|Patch)", r"\.Map(Get|Post|Put|Delete)\(",
    r"pb\.Register\w+Server\(",
]

# The snippet must be the whole backticked part: a stray backtick inside it would truncate the check.
_EVIDENCE_RE = re.compile(r"^(?P<path>[^\s:]+):(?P<line>\d+)\s+`(?P<snippet>[^`]+)`\s*$")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _source_files(ms_path: Path) -> List[Path]:
    files = []
    for glob in SOURCE_GLOBS:
        for f in ms_path.rglob(glob):
            if not SKIP_PARTS.intersection(f.relative_to(ms_path).parts):
                files.append(f)
    return sorted(files)


def _resolve_file(ms_path: Path, ref: str) -> List[Path]:
    direct = ms_path / ref
    if direct.is_file():
        return [direct]
    return [f for f in ms_path.rglob(Path(ref).name) if str(f).endswith(ref)]


def gate_a(gt: dict, partition: Partition) -> List[str]:
    errors = list(validate_agent_extraction_schema(gt, partition=partition))
    _, get_cluster = resolve_partition_with_clusters(partition.microservices)
    all_classes = {c for members in partition.microservices.values() for c in members}

    def check_class(cls: str, declared: str, where: str) -> None:
        if cls not in all_classes:
            errors.append(f"{where}: '{cls}' is not a fully-qualified class name from output.json.")
        resolved = get_cluster(cls)
        if resolved != declared:
            errors.append(f"{where}: '{cls}' resolves to service '{resolved}', but is declared under '{declared}'.")

    iface_ids: Dict[str, Set[str]] = {}
    for svc, obj in gt["microservices"].items():
        iface_ids[svc] = set()
        for i, iface in enumerate(obj["exposed_interfaces"]):
            where = f"microservices['{svc}'][{i}]"
            check_class(iface["class_name"], svc, where)
            base_id = f"{iface['class_name'].split('.')[-1]}.{iface['method_name']}"
            # Collisions are disambiguated by the shortest unique namespace suffix or an HTTP-verb suffix.
            ns = iface["class_name"].split(".")[:-1]
            allowed = {base_id} | {f"{'.'.join(ns[i:])}.{base_id}" for i in range(len(ns))}
            allowed |= {f"{base_id}[{verb}]" for verb in ("GET", "POST", "PUT", "PATCH", "DELETE")}
            allowed.add(f"{base_id}({','.join(iface['param_types'])})")  # same-verb overloads
            if iface["id"] not in allowed:
                errors.append(f"{where}: id '{iface['id']}' should be '{base_id}' (or qualified on collision).")
            if iface["id"] in iface_ids[svc]:
                errors.append(f"{where}: duplicate interface id '{iface['id']}'.")
            iface_ids[svc].add(iface["id"])

    seen: Set[Tuple[str, str, str, str]] = set()
    for i, call in enumerate(gt["inter_service_calls"]):
        where = f"inter_service_calls[{i}]"
        check_class(call["src_class"], call["src_service"], where)
        check_class(call["dst_class"], call["dst_service"], where)
        if call["dst_interface_id"] not in iface_ids.get(call["dst_service"], set()):
            errors.append(f"{where}: dst_interface_id '{call['dst_interface_id']}' is not exposed by '{call['dst_service']}'.")
        key = (call["src_class"], call["src_method"], call["dst_service"], call["dst_interface_id"])
        if key in seen:
            errors.append(f"{where}: duplicate call {key}.")
        seen.add(key)
    return errors


def gate_b(gt: dict, ms_path: Path) -> Tuple[List[str], Set[Tuple[Path, int]]]:
    errors: List[str] = []
    cited: Set[Tuple[Path, int]] = set()
    for i, call in enumerate(gt["inter_service_calls"]):
        for part in call.get("evidence", "").split(" | "):
            m = _EVIDENCE_RE.match(part.strip())
            if not m:
                errors.append(f"inter_service_calls[{i}]: evidence part not in `path:line \\`snippet\\`` form: {part!r}")
                continue
            files = _resolve_file(ms_path, m["path"])
            if len(files) != 1:
                errors.append(f"inter_service_calls[{i}]: evidence path '{m['path']}' matches {len(files)} files.")
                continue
            lines = files[0].read_text(encoding="utf-8", errors="replace").splitlines()
            line_no = int(m["line"])
            if not 1 <= line_no <= len(lines) or _norm(m["snippet"]) not in _norm(lines[line_no - 1]):
                errors.append(f"inter_service_calls[{i}]: snippet not found on {m['path']}:{line_no}: {m['snippet']!r}")
                continue
            cited.add((files[0].resolve(), line_no))
    return errors, cited


def gate_c(gt: dict, ms_path: Path, cited: Set[Tuple[Path, int]], exclusions: dict) -> List[str]:
    """Every grep hit must be cited by a call, be an exposed interface, or be explicitly excluded."""
    excluded = {(e["path"], int(e["line"])) for e in exclusions.get("excluded_sites", [])}
    # Shared client libraries whose outbound sites are attributed to their in-service callers.
    excluded_outbound_dirs = tuple(e["path"] for e in exclusions.get("excluded_outbound_paths", []))
    iface_counts = Counter(
        (iface["class_name"].split(".")[-1], iface["method_name"])
        for obj in gt["microservices"].values() for iface in obj["exposed_interfaces"]
    )
    # Mapping annotations inside a caller's own client file (e.g. a Feign interface) describe the
    # outgoing request, not an entry point.
    src_stems = {
        Path(c["src_class"]).stem if "/" in c["src_class"] else c["src_class"].split(".")[-1]
        for c in gt["inter_service_calls"]
    }
    out_re = re.compile("|".join(OUTBOUND_PATTERNS))
    entry_re = re.compile("|".join(ENTRYPOINT_PATTERNS))
    method_re = re.compile(r"\b(\w+)\s*\(")
    unaccounted = []
    entry_sites: Dict[Tuple[str, str], List[str]] = {}
    servlet_classes: Dict[str, str] = {}
    subclasses: Dict[str, List[str]] = {}
    sources = [(f, f.read_text(encoding="utf-8", errors="replace").splitlines()) for f in _source_files(ms_path)]
    for f, lines in sources:
        for sub, base in re.findall(r"\bclass\s+(\w+)(?:<[^>]*>)?\s+extends\s+(\w+)", "\n".join(lines)):
            subclasses.setdefault(base, []).append(sub)
    for f, lines in sources:
        rel = str(f.relative_to(ms_path))
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if (rel, idx) in excluded or s.startswith(("import ", "package ", "//", "*", "/*")) \
                    or re.match(r"using\s+[\w.]+\s*;", s):
                continue
            if out_re.search(line) and (f.resolve(), idx) not in cited:
                if not (excluded_outbound_dirs and rel.startswith(excluded_outbound_dirs)):
                    unaccounted.append(f"OUTBOUND   {rel}:{idx}  {line.strip()[:110]}")
            elif entry_re.search(line):
                if (f.resolve(), idx) in cited and f.stem in src_stems:
                    continue
                if "@WebServlet" in line:
                    servlet_classes[f.stem] = f"{rel}:{idx}  {line.strip()[:90]}"
                    continue
                if re.search(r"\b(class|interface)\s+\w+", " ".join(lines[idx - 1: idx + 4])):
                    continue  # type-level mapping (e.g. @RequestMapping("/v1") on a controller)
                # The annotated method is the first signature line after any stacked attributes,
                # comments or preprocessor directives; stopping there keeps a neighbouring method
                # from masking a missing interface.
                signature = line
                for nxt in lines[idx: idx + 8]:
                    s = nxt.strip()
                    if s and not s.startswith(("@", "[", "//", "*", "/*", "#")) and "(" in s:
                        signature = nxt
                        break
                names = method_re.findall(signature)
                key = (f.stem, names[0] if names else "?")
                entry_sites.setdefault(key, []).append(f"{rel}:{idx}  {line.strip()[:90]}")
    # Endpoints declared in a base class are served by each concrete subclass, so they are required there.
    required: Dict[Tuple[str, str], List[str]] = {}
    for (cls, meth), sites in entry_sites.items():
        for owner in subclasses.get(cls, [cls]):
            required.setdefault((owner, meth), []).extend(sites)
    # Count-based so that overloads (e.g. GET and POST Login) cannot mask each other.
    for key, sites in required.items():
        if len(sites) > iface_counts.get(key, 0):
            unaccounted.extend(f"ENTRYPOINT {s}  ({key[0]}.{key[1]}: {len(sites)} in code, "
                               f"{iface_counts.get(key, 0)} in ground truth)" for s in sites)
    iface_classes = {cls for cls, _ in iface_counts}
    unaccounted.extend(f"ENTRYPOINT {site}  (servlet {cls} has no interface in ground truth)"
                       for cls, site in servlet_classes.items() if cls not in iface_classes)
    return unaccounted


def main() -> None:
    parser = argparse.ArgumentParser(description="Run verification gates A-C on a ground-truth file.")
    parser.add_argument("system_id")
    args = parser.parse_args()

    sid = args.system_id
    _, ms_path = resolve_system_codebase(sid)
    gt = json.loads((GROUND_TRUTH_DIR / f"{sid}.json").read_text(encoding="utf-8"))
    partition = Partition.from_json(OUTPUTS_DIR / sid / "output.json")
    excl_file = CURATION_DIR / f"{sid}.exclusions.json"
    exclusions = json.loads(excl_file.read_text(encoding="utf-8")) if excl_file.exists() else {}

    a_errors = gate_a(gt, partition)
    b_errors, cited = gate_b(gt, ms_path)
    c_unaccounted = gate_c(gt, ms_path, cited, exclusions)

    n_ifaces = sum(len(o["exposed_interfaces"]) for o in gt["microservices"].values())
    print(f"{sid}: {len(gt['microservices'])} services, {n_ifaces} interfaces, {len(gt['inter_service_calls'])} calls")
    for name, problems in (("A structure", a_errors), ("B evidence", b_errors), ("C coverage", c_unaccounted)):
        print(f"\nGate {name}: {'PASS' if not problems else f'FAIL ({len(problems)})'}")
        for p in problems:
            print(f"  - {p}")
    sys.exit(1 if (a_errors or b_errors or c_unaccounted) else 0)


if __name__ == "__main__":
    main()
