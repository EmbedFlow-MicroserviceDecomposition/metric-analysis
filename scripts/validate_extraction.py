"""Validates LLM Agent extractions against Ground-Truth files and computes P/R/F1 & Metric Drift."""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fyp_cdq.config import GROUND_TRUTH_DIR, OUTPUTS_DIR
from fyp_cdq.extractors.agent_loader import validate_agent_extraction_schema
from fyp_cdq.metrics.chd import CHDMetric
from fyp_cdq.metrics.chm import CHMMetric
from fyp_cdq.metrics.ifn import IFNMetric
from fyp_cdq.metrics.sm import SMMetric
from fyp_cdq.models import AgentExtraction, Partition
from fyp_cdq.pipeline import resolve_system_codebase


def _prf1(gt_set: Set, pred_set: Set) -> Tuple[float, float, float, Set, Set]:
    """Returns (precision, recall, f1, false_positives, false_negatives)."""
    tp = len(gt_set & pred_set)
    fp_set = pred_set - gt_set
    fn_set = gt_set - pred_set
    if not gt_set and not pred_set:
        return 1.0, 1.0, 1.0, fp_set, fn_set
    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(gt_set) if gt_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return precision, recall, f1, fp_set, fn_set


def evaluate_single_system(
    system_id: str,
    gt_file: Path,
    pred_file: Path,
) -> Dict[str, any]:
    """Compares a single predicted extraction file against its Ground-Truth file."""
    part_file = OUTPUTS_DIR / system_id / "output.json"
    partition = Partition.from_json(part_file) if part_file.exists() else None
    _, ms_path = resolve_system_codebase(system_id)

    with open(pred_file, "r", encoding="utf-8") as f:
        raw_pred = json.load(f)

    schema_errors = validate_agent_extraction_schema(raw_pred, partition=partition)
    gt_ext = AgentExtraction.from_json(gt_file)
    pred_ext = AgentExtraction.from_dict(raw_pred)

    # 1. Interface sets: (service, simple_or_fqn_class, method_name)
    gt_ifaces = {
        (cid, iface.class_name, iface.method_name)
        for cid, ifaces in gt_ext.microservices.items()
        for iface in ifaces
    }
    pred_ifaces = {
        (cid, iface.class_name, iface.method_name)
        for cid, ifaces in pred_ext.microservices.items()
        for iface in ifaces
    }
    if_p, if_r, if_f1, if_fp, if_fn = _prf1(gt_ifaces, pred_ifaces)

    # 2. Interface with signatures: (service, class_name, method_name, tuple(param_types), return_type)
    gt_sigs = {
        (cid, iface.class_name, iface.method_name, tuple(iface.param_types), iface.return_type)
        for cid, ifaces in gt_ext.microservices.items()
        for iface in ifaces
    }
    pred_sigs = {
        (cid, iface.class_name, iface.method_name, tuple(iface.param_types), iface.return_type)
        for cid, ifaces in pred_ext.microservices.items()
        for iface in ifaces
    }
    sig_p, sig_r, sig_f1, _, _ = _prf1(gt_sigs, pred_sigs)

    # 3. Inter-service call sets:
    # 3a. Service-level directed edges: (src_service, dst_service)
    gt_svc_edges = {(c.src_service, c.dst_service) for c in gt_ext.inter_service_calls if c.src_service != c.dst_service}
    pred_svc_edges = {(c.src_service, c.dst_service) for c in pred_ext.inter_service_calls if c.src_service != c.dst_service}
    se_p, se_r, se_f1, _, _ = _prf1(gt_svc_edges, pred_svc_edges)

    # 3b. Class-level directed edges (for SM): (src_class, dst_class)
    gt_cls_edges = {(c.src_class, c.dst_class) for c in gt_ext.inter_service_calls if c.src_service != c.dst_service}
    pred_cls_edges = {(c.src_class, c.dst_class) for c in pred_ext.inter_service_calls if c.src_service != c.dst_service}
    ce_p, ce_r, ce_f1, ce_fp, ce_fn = _prf1(gt_cls_edges, pred_cls_edges)

    # 3c. Target interface invocations (for IFN): (src_service, dst_service, dst_interface_id)
    gt_iface_calls = {
        (c.src_service, c.dst_service, c.dst_interface_id)
        for c in gt_ext.inter_service_calls
        if c.src_service != c.dst_service
    }
    pred_iface_calls = {
        (c.src_service, c.dst_service, c.dst_interface_id)
        for c in pred_ext.inter_service_calls
        if c.src_service != c.dst_service
    }
    ic_p, ic_r, ic_f1, ic_fp, ic_fn = _prf1(gt_iface_calls, pred_iface_calls)

    # 4. Downstream Metric Drift (CHD, CHM, IFN, SM)
    metric_drift = {}
    if partition is not None:
        for m_cls in (CHDMetric, CHMMetric, IFNMetric, SMMetric):
            m_inst = m_cls()
            gt_res = m_inst.evaluate(partition=partition, ms_dir=ms_path, extraction_path=gt_file)
            pred_res = m_inst.evaluate(partition=partition, ms_dir=ms_path, extraction_path=pred_file)
            metric_drift[m_inst.name] = {
                "gt": round(gt_res.score, 4),
                "pred": round(pred_res.score, 4),
                "abs_err": round(abs(pred_res.score - gt_res.score), 4),
            }

    return {
        "system_id": system_id,
        "schema_valid": len(schema_errors) == 0,
        "schema_errors": schema_errors,
        "interfaces": {
            "gt_count": len(gt_ifaces),
            "pred_count": len(pred_ifaces),
            "precision": round(if_p, 4),
            "recall": round(if_r, 4),
            "f1": round(if_f1, 4),
            "signature_f1": round(sig_f1, 4),
            "false_positives": sorted(list(if_fp)),
            "false_negatives": sorted(list(if_fn)),
        },
        "inter_service_calls": {
            "gt_count": len(gt_iface_calls),
            "pred_count": len(pred_iface_calls),
            "service_edge_f1": round(se_f1, 4),
            "class_edge_precision": round(ce_p, 4),
            "class_edge_recall": round(ce_r, 4),
            "class_edge_f1": round(ce_f1, 4),
            "interface_call_precision": round(ic_p, 4),
            "interface_call_recall": round(ic_r, 4),
            "interface_call_f1": round(ic_f1, 4),
            "class_edge_fp": sorted(list(ce_fp)),
            "class_edge_fn": sorted(list(ce_fn)),
            "interface_call_fp": sorted(list(ic_fp)),
            "interface_call_fn": sorted(list(ic_fn)),
        },
        "metric_drift": metric_drift,
    }


def format_markdown_report(results: List[Dict[str, any]]) -> str:
    """Formats validation results across one or more systems into a Markdown report."""
    lines = ["# Agent Extraction Validation Report\n"]
    if not results:
        lines.append("No systems evaluated.\n")
        return "\n".join(lines)

    n = len(results)
    schema_pass = sum(1 for r in results if r["schema_valid"])
    mean_if_f1 = sum(r["interfaces"]["f1"] for r in results) / n
    mean_sig_f1 = sum(r["interfaces"]["signature_f1"] for r in results) / n
    mean_ce_f1 = sum(r["inter_service_calls"]["class_edge_f1"] for r in results) / n
    mean_ic_f1 = sum(r["inter_service_calls"]["interface_call_f1"] for r in results) / n

    lines.append("## 1. Aggregate Summary")
    lines.append(f"- **Systems Evaluated**: {n}")
    lines.append(f"- **Schema & Partition Conformance**: {schema_pass}/{n} ({schema_pass / n * 100:.1f}%)")
    lines.append(f"- **Macro Interface Identification F1**: `{mean_if_f1:.4f}` (Signature F1: `{mean_sig_f1:.4f}`)")
    lines.append(f"- **Macro Inter-Service Class Edge F1 (SM)**: `{mean_ce_f1:.4f}`")
    lines.append(f"- **Macro Inter-Service Interface Call F1 (IFN)**: `{mean_ic_f1:.4f}`\n")

    lines.append("## 2. Per-System Breakdown\n")
    lines.append("| System | Schema | GT Ifaces | Pred Ifaces | Iface F1 | Class Edge F1 | Iface Call F1 | ΔCHD | ΔCHM | ΔIFN | ΔSM |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for r in results:
        md = r["metric_drift"]
        d_chd = f"{md['CHD']['abs_err']:.4f}" if "CHD" in md else "N/A"
        d_chm = f"{md['CHM']['abs_err']:.4f}" if "CHM" in md else "N/A"
        d_ifn = f"{md['IFN']['abs_err']:.4f}" if "IFN" in md else "N/A"
        d_sm = f"{md['SM']['abs_err']:.4f}" if "SM" in md else "N/A"
        lines.append(
            f"| `{r['system_id']}` | {'PASS' if r['schema_valid'] else 'FAIL'} | "
            f"{r['interfaces']['gt_count']} | {r['interfaces']['pred_count']} | "
            f"`{r['interfaces']['f1']:.4f}` | `{r['inter_service_calls']['class_edge_f1']:.4f}` | "
            f"`{r['inter_service_calls']['interface_call_f1']:.4f}` | "
            f"{d_chd} | {d_chm} | {d_ifn} | {d_sm} |"
        )

    lines.append("\n## 3. Diagnostic Error Analysis (False Positives & False Negatives)\n")
    for r in results:
        sid = r["system_id"]
        has_diag = (
            r["schema_errors"]
            or r["interfaces"]["false_positives"]
            or r["interfaces"]["false_negatives"]
            or r["inter_service_calls"]["interface_call_fp"]
            or r["inter_service_calls"]["interface_call_fn"]
        )
        if not has_diag:
            lines.append(f"### `{sid}`: Perfect Match (0 Errors)\n")
            continue

        lines.append(f"### `{sid}`")
        if r["schema_errors"]:
            lines.append("- **Schema/Partition Errors**:")
            for err in r["schema_errors"]:
                lines.append(f"  - `{err}`")
        if r["interfaces"]["false_positives"]:
            lines.append(f"- **Interface False Positives ({len(r['interfaces']['false_positives'])})**:")
            for fp in r["interfaces"]["false_positives"][:10]:
                lines.append(f"  - `{fp}`")
        if r["interfaces"]["false_negatives"]:
            lines.append(f"- **Interface False Negatives ({len(r['interfaces']['false_negatives'])})**:")
            for fn in r["interfaces"]["false_negatives"][:10]:
                lines.append(f"  - `{fn}`")
        if r["inter_service_calls"]["interface_call_fp"]:
            lines.append(f"- **Inter-Service Call False Positives ({len(r['inter_service_calls']['interface_call_fp'])})**:")
            for fp in r["inter_service_calls"]["interface_call_fp"][:10]:
                lines.append(f"  - `{fp}`")
        if r["inter_service_calls"]["interface_call_fn"]:
            lines.append(f"- **Inter-Service Call False Negatives ({len(r['inter_service_calls']['interface_call_fn'])})**:")
            for fn in r["inter_service_calls"]["interface_call_fn"][:10]:
                lines.append(f"  - `{fn}`")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate LLM Agent extraction against Ground Truth.")
    parser.add_argument("--system", type=str, default=None, help="Single system ID (e.g. MS001)")
    parser.add_argument("--pred", type=str, default=None, help="Path to single predicted JSON file")
    parser.add_argument("--pred-dir", type=str, default=None, help="Directory containing <MS_ID>.json predictions")
    parser.add_argument("--gt-dir", type=str, default=str(GROUND_TRUTH_DIR), help="Ground-truth directory")
    parser.add_argument("--include-unverified", action="store_true", help="Include ground-truth files not yet marked 'verified'")
    parser.add_argument("--report-out", type=str, default=None, help="Optional path to save Markdown report")
    args = parser.parse_args()

    gt_dir = Path(args.gt_dir)
    results = []

    if args.system and args.pred:
        gt_file = gt_dir / f"{args.system}.json"
        if not gt_file.exists():
            raise FileNotFoundError(f"Ground-truth file not found: {gt_file}")
        res = evaluate_single_system(args.system, gt_file, Path(args.pred))
        results.append(res)
    elif args.pred_dir:
        pred_dir = Path(args.pred_dir)
        for gt_file in sorted(gt_dir.glob("MS*.json")):
            gt_ext = AgentExtraction.from_json(gt_file)
            if gt_ext.status != "verified" and not args.include_unverified:
                continue
            sid = gt_ext.system_id
            pred_file = pred_dir / f"{sid}.json"
            if pred_file.exists():
                results.append(evaluate_single_system(sid, gt_file, pred_file))
    else:
        parser.error("Provide either (--system and --pred) or --pred-dir.")

    report_md = format_markdown_report(results)
    print(report_md)

    if args.report_out:
        out_p = Path(args.report_out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(report_md, encoding="utf-8")
        print(f"\nSaved validation report to {out_p}")


if __name__ == "__main__":
    main()
