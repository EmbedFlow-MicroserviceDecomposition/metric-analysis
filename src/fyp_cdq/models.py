"""Data models for microservice systems, partitions, and metric results."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class MicroserviceSystem:
    """Represents a microservice system codebase located on the filesystem."""
    system_id: str
    name: str
    path: Path
    monolith_path: Optional[Path] = None


@dataclass
class Partition:
    """Represents a decomposition partition mapping microservice IDs to member classes."""
    microservices: Dict[str, List[str]]
    system_name: str = ""
    tool_or_system: str = "Ground-Truth Architecture"

    def to_dict(self) -> dict:
        return {
            "system": self.system_name,
            "tool": self.tool_or_system,
            "microservices": self.microservices
        }

    def save_json(self, file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def from_json(cls, file_path: Path) -> "Partition":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            microservices=data.get("microservices", {}),
            system_name=data.get("system", data.get("dataset", "")),
            tool_or_system=data.get("tool", "")
        )

    @property
    def sizes(self) -> Dict[str, int]:
        return {svc: len(classes) for svc, classes in self.microservices.items()}

    @property
    def total_classes(self) -> int:
        return sum(len(classes) for classes in self.microservices.values())

    @property
    def service_count(self) -> int:
        return len(self.microservices)


@dataclass
class MetricResult:
    """Represents the quantitative evaluation result of a metric."""
    metric: str
    score: float
    score_relative: Optional[float] = None
    bounds: Dict = field(default_factory=dict)
    microservice_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        res = {
            "metric": self.metric,
            "score": self.score,
        }
        if self.score_relative is not None:
            res["score_absolute"] = self.score
            res["score_relative"] = self.score_relative
        if self.bounds:
            res["bounds"] = self.bounds
        res["microservice_scores"] = self.microservice_scores
        if self.metadata:
            res["metadata"] = self.metadata
        return res

    def save_json(self, file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)


@dataclass
class InterfaceSpec:
    """Represents a published/exposed interface operation of a microservice."""
    id: str
    class_name: str
    method_name: str
    param_types: List[str] = field(default_factory=list)
    return_type: str = "void"
    protocol: str = "REST"
    endpoint: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "param_types": list(self.param_types),
            "return_type": self.return_type,
            "protocol": self.protocol,
            "endpoint": self.endpoint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InterfaceSpec":
        cls_name = data.get("class_name", "")
        method_name = data.get("method_name", "")
        default_id = f"{cls_name.split('.')[-1]}.{method_name}" if cls_name and method_name else ""
        return cls(
            id=data.get("id") or default_id,
            class_name=cls_name,
            method_name=method_name,
            param_types=list(data.get("param_types", [])),
            return_type=data.get("return_type", "void") or "void",
            protocol=data.get("protocol", "REST"),
            endpoint=data.get("endpoint", ""),
        )


@dataclass
class InterServiceCall:
    """Represents a directed inter-microservice invocation edge."""
    src_service: str
    src_class: str
    src_method: str
    dst_service: str
    dst_class: str
    dst_interface_id: str
    protocol: str = "REST"
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "src_service": self.src_service,
            "src_class": self.src_class,
            "src_method": self.src_method,
            "dst_service": self.dst_service,
            "dst_class": self.dst_class,
            "dst_interface_id": self.dst_interface_id,
            "protocol": self.protocol,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InterServiceCall":
        dst_cls = data.get("dst_class", "")
        dst_iface = data.get("dst_interface_id") or dst_cls.split(".")[-1]
        return cls(
            src_service=data.get("src_service", ""),
            src_class=data.get("src_class", ""),
            src_method=data.get("src_method", ""),
            dst_service=data.get("dst_service", ""),
            dst_class=dst_cls,
            dst_interface_id=dst_iface,
            protocol=data.get("protocol", "REST"),
            evidence=data.get("evidence", ""),
        )


@dataclass
class AgentExtraction:
    """Container for LLM-extracted or Ground-Truth microservice interfaces and inter-service calls."""
    system_id: str
    extractor_tool: str = "ground_truth"
    prompt_version: str = "v1.0"
    microservices: Dict[str, List[InterfaceSpec]] = field(default_factory=dict)
    inter_service_calls: List[InterServiceCall] = field(default_factory=list)
    status: str = "verified"

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "extractor_tool": self.extractor_tool,
            "prompt_version": self.prompt_version,
            "status": self.status,
            "microservices": {
                cid: {"exposed_interfaces": [iface.to_dict() for iface in ifaces]}
                for cid, ifaces in self.microservices.items()
            },
            "inter_service_calls": [call.to_dict() for call in self.inter_service_calls],
        }

    def save_json(self, file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentExtraction":
        ms_raw = data.get("microservices", {})
        ms_parsed: Dict[str, List[InterfaceSpec]] = {}
        for cid, cid_data in ms_raw.items():
            if isinstance(cid_data, dict):
                raw_list = cid_data.get("exposed_interfaces", [])
            elif isinstance(cid_data, list):
                raw_list = cid_data
            else:
                raw_list = []
            ms_parsed[cid] = [InterfaceSpec.from_dict(item) for item in raw_list]

        calls_raw = data.get("inter_service_calls", [])
        calls_parsed = [InterServiceCall.from_dict(item) for item in calls_raw]

        return cls(
            system_id=data.get("system_id", ""),
            extractor_tool=data.get("extractor_tool", "unknown"),
            prompt_version=data.get("prompt_version", "v1.0"),
            microservices=ms_parsed,
            inter_service_calls=calls_parsed,
            status=data.get("status", "verified"),
        )

    @classmethod
    def from_json(cls, file_path: Path) -> "AgentExtraction":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

