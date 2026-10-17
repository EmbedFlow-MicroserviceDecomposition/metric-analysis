"""Base metric interface for decomposition and architecture evaluation."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from fyp_cdq.models import MetricResult, Partition


class BaseMetric(ABC):
    """Abstract base class for all evaluation metrics."""

    name: str = "BaseMetric"
    needs_monolith: bool = False

    def parse_cli_args(self, args: List[str]) -> Dict[str, Any]:
        """Parses CLI parameters specific to this metric."""
        return {}

    @abstractmethod
    def evaluate(
        self,
        partition: Partition,
        ms_dir: Path,
        mono_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        **kwargs
    ) -> MetricResult:
        """
        Calculates the metric for a given microservices partition.
        Optional mono_dir is passed for metrics requiring monolith codebase.
        If output_dir is provided, saves <metric>_score.json.
        """
        pass
