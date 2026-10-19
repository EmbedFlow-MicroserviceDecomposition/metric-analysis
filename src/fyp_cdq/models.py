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
