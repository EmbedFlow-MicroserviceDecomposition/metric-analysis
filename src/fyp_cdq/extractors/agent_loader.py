"""Loader and converter for LLM-extracted or Ground-Truth microservice interfaces and call edges."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fyp_cdq.config import AGENT_EXTRACTION_FILENAME, MICROSERVICES_JSON
from fyp_cdq.metrics.common import Edge, Operation
from fyp_cdq.models import AgentExtraction, Partition


def load_manifest_services(system_id: str, manifest_path: Optional[Path] = None) -> Optional[Set[str]]:
    """
    Loads the canonical microservice IDs for `system_id` from `codebases/microservices/microservices.json`.
    Returns None if `system_id` is empty, the manifest does not exist, or `system_id` is not present.
    """
    if not system_id:
        return None
    m_path = Path(manifest_path) if manifest_path is not None else MICROSERVICES_JSON
    if not m_path.is_file():
        return None
    try:
        data = json.loads(m_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    entry = data.get(system_id)
    if not entry or not isinstance(entry.get("services"), dict):
        return None
    return set(entry["services"].keys())


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


def extraction_to_inter_service_edges(
    extraction: AgentExtraction,
    qualify_with_service_id: bool = True,
) -> List[Edge]:
    """
    Converts `inter_service_calls` from an `AgentExtraction` into deduplicated directed
    `Edge` objects for Structural Modularity (`SM`).
    When `qualify_with_service_id=True`, endpoints are namespaced as `<service_id>::<class_name>`
    so calls between same-named classes in different services are never dropped or conflated.
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
        if not src_cls or not dst_cls:
            continue
        if qualify_with_service_id:
            src_node = f"{call.src_service}::{src_cls}"
            dst_node = f"{call.dst_service}::{dst_cls}"
        else:
            if src_cls == dst_cls:
                continue
            src_node = src_cls
            dst_node = dst_cls
        pair = (src_node, dst_node)
        if pair not in seen:
            seen.add(pair)
            edges.append(Edge(src=src_node, dst=dst_node, type="CALL", weight=1.0))
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
    manifest_services: Optional[Set[str]] = None,
) -> List[str]:
    """
    Validates raw JSON dictionary against the canonical `agent_extraction.json` schema,
    checking microservice keys against `codebases/microservices/microservices.json` (or `partition` fallback),
    per-service interface ID uniqueness, and `dst_interface_id` referential integrity.
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

    if manifest_services is None:
        manifest_services = load_manifest_services(data.get("system_id", ""))

    if manifest_services is not None:
        known_services = manifest_services
        source_label = "microservices.json"
    elif partition is not None:
        known_services = set(partition.microservices.keys())
        source_label = "partition"
    else:
        known_services = set(ms_map.keys())
        source_label = "payload"

    if manifest_services is not None or partition is not None:
        missing_svcs = known_services - set(ms_map.keys())
        extra_svcs = set(ms_map.keys()) - known_services
        if missing_svcs:
            errors.append(f"Missing canonical microservices in 'microservices' (from {source_label}): {sorted(missing_svcs)}")
        if extra_svcs:
            errors.append(f"Unknown microservices in 'microservices' (not in {source_label}): {sorted(extra_svcs)}")

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
            if not str(iface.get("class_name", "")).strip():
                errors.append(f"microservices['{cid}'].exposed_interfaces[{idx}] has empty 'class_name'.")
            if not str(iface.get("method_name", "")).strip():
                errors.append(f"microservices['{cid}'].exposed_interfaces[{idx}] has empty 'method_name'.")
            iface_id = str(iface.get("id", "")).strip()
            if not iface_id:
                errors.append(f"microservices['{cid}'].exposed_interfaces[{idx}] has empty 'id'.")
            elif iface_id in declared_interface_ids[cid]:
                errors.append(f"microservices['{cid}'] contains duplicate exposed_interface id '{iface_id}'.")
            else:
                declared_interface_ids[cid].add(iface_id)

    calls = data.get("inter_service_calls")
    if not isinstance(calls, list):
        errors.append("'inter_service_calls' must be a list.")
    else:
        for idx, call in enumerate(calls):
            if not isinstance(call, dict):
                errors.append(f"inter_service_calls[{idx}] must be an object.")
                continue
            for k in ("src_service", "src_class", "src_method", "dst_service", "dst_class", "dst_interface_id"):
                if not str(call.get(k, "")).strip():
                    errors.append(f"inter_service_calls[{idx}] missing or empty required field '{k}'.")
            src_s = call.get("src_service", "")
            dst_s = call.get("dst_service", "")
            if src_s and dst_s and src_s == dst_s:
                errors.append(f"inter_service_calls[{idx}] has src_service == dst_service ('{src_s}').")
            if manifest_services is not None or partition is not None:
                if src_s and src_s not in known_services:
                    errors.append(f"inter_service_calls[{idx}] unknown src_service '{src_s}'.")
                if dst_s and dst_s not in known_services:
                    errors.append(f"inter_service_calls[{idx}] unknown dst_service '{dst_s}'.")
            dst_iface = str(call.get("dst_interface_id", "")).strip()
            if dst_s and dst_iface and dst_s in declared_interface_ids:
                if dst_iface not in declared_interface_ids[dst_s]:
                    errors.append(
                        f"inter_service_calls[{idx}] dst_interface_id '{dst_iface}' "
                        f"not found in microservices['{dst_s}'].exposed_interfaces."
                    )

    return errors
