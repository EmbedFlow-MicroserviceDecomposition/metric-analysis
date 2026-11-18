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
    r"convertAndSend\(", r"\.Publish(Async)?\(", r"HttpClient\b.*\.(Get|Post|Put|Delete|Send)\w*Async\(",
    r"\bfetch\(", r"axios\.", r"requests\.(get|post|put|delete)\(", r"http\.(Get|Post)\(",
    r"\.NewRequest\(", r"pb\.New\w+Client\(",
]
# Sites that may expose an operation across the service boundary.
ENTRYPOINT_PATTERNS = [
    r"@(Get|Post|Put|Delete|Patch|Request)Mapping", r"@(GET|POST|PUT|DELETE|PATCH)\b",
    r"@StreamListener", r"@KafkaListener", r"@RabbitListener", r"@JmsListener",
    r"\[Http(Get|Post|Put|Delete|Patch)", r"\.Map(Get|Post|Put|Delete)\(",
    r"pb\.Register\w+Server\(",
]

_EVIDENCE_RE = re.compile(r"^(?P<path>[^\s:]+):(?P<line>\d+)\s+`(?P<snippet>[^`]+)`")


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
            expected_id = f"{iface['class_name'].split('.')[-1]}.{iface['method_name']}"
            if iface["id"] != expected_id:
                errors.append(f"{where}: id '{iface['id']}' should be '{expected_id}'.")
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
    iface_methods = {
        (iface["class_name"].split(".")[-1], iface["method_name"])
        for obj in gt["microservices"].values() for iface in obj["exposed_interfaces"]
    }
    out_re = re.compile("|".join(OUTBOUND_PATTERNS))
    entry_re = re.compile("|".join(ENTRYPOINT_PATTERNS))
    method_re = re.compile(r"\b(\w+)\s*\(")
    unaccounted = []
    for f in _source_files(ms_path):
        rel = str(f.relative_to(ms_path))
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines, 1):
            if (rel, idx) in excluded:
                continue
            if out_re.search(line) and (f.resolve(), idx) not in cited:
                unaccounted.append(f"OUTBOUND   {rel}:{idx}  {line.strip()[:110]}")
            elif entry_re.search(line):
                # The annotated method's signature is on one of the next few lines.
                window = " ".join(lines[idx - 1: idx + 4])
                if re.search(r"\b(class|interface)\s+\w+", window):
                    continue  # type-level mapping (e.g. @RequestMapping("/v1") on a controller)
                names = {n for n in method_re.findall(window.split(")", 1)[-1])}
                if not any((f.stem, n) in iface_methods for n in names):
                    unaccounted.append(f"ENTRYPOINT {rel}:{idx}  {line.strip()[:110]}")
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
