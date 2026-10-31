"""Scaffolds Ground-Truth JSON files for the 20 stratified calibration systems."""

import argparse
from pathlib import Path
from typing import List

from fyp_cdq.config import CALIBRATION_RUNS_DIR, GROUND_TRUTH_DIR, OUTPUTS_DIR
from fyp_cdq.metrics.common import extract_microservice_published_ops
from fyp_cdq.models import AgentExtraction, InterfaceSpec, Partition
from fyp_cdq.pipeline import resolve_system_codebase

# 20 Stratified Benchmark Systems across Languages, Scale, and Communication Patterns
CALIBRATION_SYSTEMS: List[str] = [
    "MS001",  # Java (Spring Boot REST + WebClient + API Gateway, Monolith pair)
    "MS004",  # Java (FTGO: Eventuate Tram Events/Commands + REST + Sagas, Monolith pair)
    "MS007",  # Java (Coolstore: REST + JMS/Messaging + Gateway, Monolith pair)
    "MS010",  # Java (AWS ECS Spring PetClinic REST microservices, Monolith pair)
    "MS011",  # Java (Spring Cloud Eureka + Gateway + RestTemplate, Monolith pair)
    "MS015",  # C#/.NET (eShop: RabbitMQ EventBus + gRPC + Minimal APIs, Monolith pair)
    "MS016",  # C#/.NET (Pitstop: RabbitMQ Event-driven + REST APIs)
    "MS017",  # Node.js (Express REST microservices, Monolith pair)
    "MS020",  # Java (PiggyMetrics: Spring Cloud FeignClient + OAuth2 + RabbitMQ)
    "MS021",  # Java (TeaStore: JAX-RS Jersey REST + RegistryClient)
    "MS030",  # Java (Spring Cloud Feign + Discovery)
    "MS031",  # Java (Spring Cloud OpenFeign + Gateway)
    "MS032",  # Java (Event-sourcing + Feign/REST)
    "MS039",  # Polyglot (Online Boutique: Go/Python/Node/C#/Java gRPC)
    "MS043",  # Go (DeathStarBench HotelReservation: gRPC microservices)
    "MS047",  # Polyglot (Robot Shop: Node/Python/Java/Go/PHP REST + AMQP)
    "MS070",  # Go (Boulder Let's Encrypt CA: gRPC microservices)
    "MS078",  # C#/.NET (Clean Architecture Manga: REST APIs)
    "MS098",  # TypeScript (Ultimate Backend: NestJS gRPC + CQRS EventBus)
    "MS106",  # Python (Email MicroAPI: FastAPI/Flask REST microservices)
]


def scaffold_system_ground_truth(
    system_id: str,
    out_dir: Path = GROUND_TRUTH_DIR,
    prepopulate_candidates: bool = False,
    force: bool = False,
) -> Path:
    """Creates a ground-truth JSON file for `system_id` in `benchmarks/ground_truth/`."""
    out_file = out_dir / f"{system_id}.json"
    if out_file.exists() and not force:
        existing = AgentExtraction.from_json(out_file)
        if existing.status == "verified":
            return out_file

    _, ms_path = resolve_system_codebase(system_id)
    part_file = OUTPUTS_DIR / system_id / "output.json"
    if not part_file.exists():
        raise FileNotFoundError(f"Partition file not found at {part_file}. Run NED evaluation first.")
    partition = Partition.from_json(part_file)

    ms_interfaces = {cid: [] for cid in partition.microservices}
    if prepopulate_candidates:
        ops_per_ms = extract_microservice_published_ops(ms_path, partition)
        for cid, ops in ops_per_ms.items():
            for op in sorted(ops, key=lambda o: (o.cls, o.name)):
                simple_cls = op.cls.split(".")[-1]
                ms_interfaces[cid].append(
                    InterfaceSpec(
                        id=f"{simple_cls}.{op.name}",
                        class_name=op.cls,
                        method_name=op.name,
                        param_types=list(op.params),
                        return_type=op.returns,
                        protocol="REST",
                        endpoint="",
                    )
                )

    extraction = AgentExtraction(
        system_id=system_id,
        extractor_tool="ground_truth",
        prompt_version="v1.0",
        microservices=ms_interfaces,
        inter_service_calls=[],
        status="pending_manual_review",
    )
    extraction.save_json(out_file)
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Ground-Truth JSON templates for calibration systems.")
    parser.add_argument(
        "--systems",
        nargs="*",
        default=CALIBRATION_SYSTEMS,
        help="List of system IDs to scaffold (defaults to the 20 stratified calibration systems).",
    )
    parser.add_argument(
        "--prepopulate-candidates",
        action="store_true",
        help="Pre-populate exposed_interfaces with static parser candidates to speed up manual curation.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing ground-truth files even if marked 'verified'.",
    )
    args = parser.parse_args()

    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    for tool_dir in ("antigravity_cli", "claude_code", "codex"):
        t_path = CALIBRATION_RUNS_DIR / tool_dir
        t_path.mkdir(parents=True, exist_ok=True)
        gitkeep = t_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    for sys_id in args.systems:
        out_file = scaffold_system_ground_truth(
            sys_id,
            out_dir=GROUND_TRUTH_DIR,
            prepopulate_candidates=args.prepopulate_candidates,
            force=args.force,
        )
        print(f"[OK] {sys_id} -> {out_file}")


if __name__ == "__main__":
    main()
