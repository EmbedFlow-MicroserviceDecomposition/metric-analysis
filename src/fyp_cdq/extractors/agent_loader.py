"""Loader and converter for LLM-extracted or Ground-Truth microservice interfaces and call edges."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fyp_cdq.config import AGENT_EXTRACTION_FILENAME
from fyp_cdq.metrics.common import Edge, Operation
from fyp_cdq.models import AgentExtraction, Partition


def resolve_agent_extraction_path(
    ms_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    extraction_path: Optional[Path] = None,
) -> Optional[Path]:
    """
    Resolves the path to `agent_extraction.json` if provided via CLI or present in output_dir/ms_dir.
    """
    if extraction_path is not None:
        ext_p = Path(extraction_path)
        if ext_p.is_file():
            return ext_p
        cand = ext_p / AGENT_EXTRACTION_FILENAME
        if cand.is_file():
            return cand
        raise FileNotFoundError(f"Agent extraction file not found at '{extraction_path}'.")

    if output_dir is not None:
        cand = Path(output_dir) / AGENT_EXTRACTION_FILENAME
        if cand.is_file():
            return cand

    if ms_dir is not None:
        cand = Path(ms_dir) / AGENT_EXTRACTION_FILENAME
        if cand.is_file():
            return cand

    return None


def load_agent_extraction(file_path: Path) -> AgentExtraction:
    """Loads an `AgentExtraction` instance from a JSON file."""
    return AgentExtraction.from_json(Path(file_path))


def extraction_to_published_ops(
    extraction: AgentExtraction,
    clusters: Set[str],
) -> Dict[str, Set[Operation]]:
    """
    Converts `exposed_interfaces` from an `AgentExtraction` into `Dict[str, Set[Operation]]`
    suitable for `calculate_chd` and `calculate_chm`.
    """
    ops_per_ms: Dict[str, Set[Operation]] = {cid: set() for cid in clusters}
    for cid in clusters:
        ifaces = extraction.microservices.get(cid, [])
        for iface in ifaces:
            if not iface.method_name:
                continue
            cls_name = iface.class_name or cid
            op = Operation(
                cls=cls_name,
                name=iface.method_name,
                params=tuple(iface.param_types),
                returns=iface.return_type or "void",
            )
            ops_per_ms[cid].add(op)
    return ops_per_ms


def extraction_to_inter_service_edges(extraction: AgentExtraction) -> List[Edge]:
    """
    Converts `inter_service_calls` from an `AgentExtraction` into deduplicated `(src_class, dst_class)`
    `Edge` objects for Structural Modularity (`SM`).
    """
    edges: List[Edge] = []
    seen: Set[Tuple[str, str]] = set()
    for call in extraction.inter_service_calls:
        if not call.src_service or not call.dst_service:
            continue
        if call.src_service == call.dst_service:
            continue
        src_cls = call.src_class
        dst_cls = call.dst_class
        if not src_cls or not dst_cls or src_cls == dst_cls:
            continue
        pair = (src_cls, dst_cls)
        if pair not in seen:
            seen.add(pair)
            edges.append(Edge(src=src_cls, dst=dst_cls, type="CALL", weight=1.0))
    return edges


def calculate_ifn_from_extraction(
    extraction: AgentExtraction,
    clusters: Set[str],
) -> Tuple[float, Dict[str, float]]:
    """
    Calculates Interface Number (IFN) directly from an `AgentExtraction` by counting
    unique `dst_interface_id` per target microservice `cj` invoked by external microservices `ci != cj`.
    """
    K = len(clusters)
    if K == 0:
        return 0.0, {}

    interfaces_per_ms: Dict[str, Set[str]] = {cid: set() for cid in clusters}

    for call in extraction.inter_service_calls:
        ci = call.src_service
        cj = call.dst_service
        if not ci or not cj or ci == cj:
            continue
        if ci not in clusters or cj not in clusters:
            continue
        iface_id = call.dst_interface_id or call.dst_class
        if iface_id:
            interfaces_per_ms[cj].add(iface_id)

    microservice_scores = {cid: float(len(ifaces)) for cid, ifaces in interfaces_per_ms.items()}
    overall_ifn = sum(microservice_scores.values()) / K
    return overall_ifn, microservice_scores


def validate_agent_extraction_schema(
    data: dict,
    partition: Optional[Partition] = None,
) -> List[str]:
    """
    Validates raw JSON dictionary against the canonical `agent_extraction.json` schema
    and (optionally) checks service & class membership against a canonical `Partition`.
    Returns a list of error strings (empty if valid).
    """
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["Root element must be a JSON object."]

    for req_key in ("system_id", "microservices", "inter_service_calls"):
        if req_key not in data:
            errors.append(f"Missing required root key: '{req_key}'.")

    ms_map = data.get("microservices")
    if not isinstance(ms_map, dict):
        errors.append("'microservices' must be an object mapping service IDs to {'exposed_interfaces': [...]}.")
        ms_map = {}

    known_services = set(partition.microservices.keys()) if partition else set(ms_map.keys())
    known_classes_per_svc: Dict[str, Set[str]] = {}
    if partition:
        for cid, clist in partition.microservices.items():
            known_classes_per_svc[cid] = set(clist) | {c.split(".")[-1] for c in clist}

        missing_svcs = known_services - set(ms_map.keys())
        extra_svcs = set(ms_map.keys()) - known_services
        if missing_svcs:
            errors.append(f"Missing canonical microservices in 'microservices': {sorted(missing_svcs)}")
        if extra_svcs:
            errors.append(f"Unknown microservices in 'microservices' (not in output.json): {sorted(extra_svcs)}")

    declared_interface_ids: Dict[str, Set[str]] = {cid: set() for cid in ms_map}

    for cid, cid_obj in ms_map.items():
        if not isinstance(cid_obj, dict) or "exposed_interfaces" not in cid_obj:
            errors.append(f"microservices['{cid}'] must be an object containing 'exposed_interfaces' list.")
            continue
        ifaces = cid_obj.get("exposed_interfaces")
        if not isinstance(ifaces, list):
            errors.append(f"microservices['{cid}'].exposed_interfaces must be a list.")
            continue
        for idx, iface in enumerate(ifaces):
            if not isinstance(iface, dict):
                errors.append(f"microservices['{cid}'].exposed_interfaces[{idx}] must be an object.")
                continue
            for k in ("id", "class_name", "method_name", "param_types", "return_type"):
                if k not in iface:
                    errors.append(f"microservices['{cid}'].exposed_interfaces[{idx}] missing key '{k}'.")
            iface_id = iface.get("id", "")
            if iface_id:
                declared_interface_ids[cid].add(iface_id)
            cls_name = iface.get("class_name", "")
            if partition and cid in known_classes_per_svc and cls_name:
                if cls_name not in known_classes_per_svc[cid] and cls_name.split(".")[-1] not in known_classes_per_svc[cid]:
                    errors.append(
                        f"microservices['{cid}'].exposed_interfaces[{idx}] class_name '{cls_name}' "
                        f"not found in canonical partition classes for '{cid}'."
                    )

    calls = data.get("inter_service_calls")
    if not isinstance(calls, list):
        errors.append("'inter_service_calls' must be a list.")
    else:
        for idx, call in enumerate(calls):
            if not isinstance(call, dict):
                errors.append(f"inter_service_calls[{idx}] must be an object.")
                continue
            for k in ("src_service", "src_class", "dst_service", "dst_class", "dst_interface_id"):
                if not call.get(k):
                    errors.append(f"inter_service_calls[{idx}] missing or empty required field '{k}'.")
            src_s = call.get("src_service", "")
            dst_s = call.get("dst_service", "")
            if src_s and dst_s and src_s == dst_s:
                errors.append(f"inter_service_calls[{idx}] has src_service == dst_service ('{src_s}').")
            if partition:
                if src_s and src_s not in known_services:
                    errors.append(f"inter_service_calls[{idx}] unknown src_service '{src_s}'.")
                if dst_s and dst_s not in known_services:
                    errors.append(f"inter_service_calls[{idx}] unknown dst_service '{dst_s}'.")
                src_cls = call.get("src_class", "")
                if src_s in known_classes_per_svc and src_cls:
                    if src_cls not in known_classes_per_svc[src_s] and src_cls.split(".")[-1] not in known_classes_per_svc[src_s]:
                        errors.append(
                            f"inter_service_calls[{idx}] src_class '{src_cls}' not found in canonical classes for '{src_s}'."
                        )
                dst_cls = call.get("dst_class", "")
                if dst_s in known_classes_per_svc and dst_cls:
                    if dst_cls not in known_classes_per_svc[dst_s] and dst_cls.split(".")[-1] not in known_classes_per_svc[dst_s]:
                        errors.append(
                            f"inter_service_calls[{idx}] dst_class '{dst_cls}' not found in canonical classes for '{dst_s}'."
                        )

    return errors
