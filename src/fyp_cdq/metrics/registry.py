"""Central metric registry for managing and extending evaluation metrics."""

from typing import Dict, List, Optional
from fyp_cdq.metrics.base import BaseMetric
from fyp_cdq.metrics.ned import NEDMetric


class MetricRegistry:
    """Registry pattern to support pluggable microservice evaluation metrics."""

    def __init__(self):
        self._metrics: Dict[str, BaseMetric] = {}
        # Register baseline state-of-the-art metric
        self.register(NEDMetric())

    def register(self, metric: BaseMetric) -> None:
        self._metrics[metric.name.upper()] = metric

    def get(self, name: str) -> Optional[BaseMetric]:
        return self._metrics.get(name.upper())

    def list_metrics(self) -> List[str]:
        return list(self._metrics.keys())

    def get_metrics_requiring_monolith(self) -> List[str]:
        return [m.name for m in self._metrics.values() if m.needs_monolith]

    def get_metrics_microservice_only(self) -> List[str]:
        return [m.name for m in self._metrics.values() if not m.needs_monolith]


# Global instance
registry = MetricRegistry()
