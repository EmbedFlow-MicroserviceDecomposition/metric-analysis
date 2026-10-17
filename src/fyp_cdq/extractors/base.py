"""Base class extractor interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class BaseExtractor(ABC):
    """Abstract base class for extracting code elements (classes/components)."""

    @abstractmethod
    def extract_classes(self, source_dir: Path) -> List[str]:
        """
        Scans source_dir and extracts a list of fully qualified class or component identifiers.
        """
        pass
