"""Java class extractor using javalang AST with regex fallback."""

import os
import re
from pathlib import Path
from typing import List, Set
import javalang

from fyp_cdq.extractors.base import BaseExtractor


class JavaExtractor(BaseExtractor):
    """Extracts Java classes, interfaces, enums, and records from a source directory."""

    def __init__(self, include_tests: bool = False):
        self.include_tests = include_tests

    def extract_classes(self, source_dir: Path) -> List[str]:
        classes: Set[str] = set()
        if not source_dir.exists():
            return []

        # Find all Java files
        for root, dirs, files in os.walk(source_dir):
            root_path = Path(root)
            # Skip test directories if include_tests is False
            if not self.include_tests:
                rel_parts = [p.lower() for p in root_path.relative_to(source_dir).parts]
                if any(p in ["test", "tests"] for p in rel_parts):
                    continue

            for file in files:
                if file.endswith(".java"):
                    file_path = root_path / file
                    extracted = self._extract_from_file(file_path)
                    classes.update(extracted)

        return sorted(list(classes))

    def _extract_from_file(self, file_path: Path) -> List[str]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        results = []
        try:
            tree = javalang.parse.parse(code)
            pkg = tree.package.name if tree.package else ""

            # Check classes, interfaces, and enums
            for _, node in tree.filter(javalang.tree.ClassDeclaration):
                fqcn = f"{pkg}.{node.name}" if pkg else node.name
                results.append(fqcn)

            for _, node in tree.filter(javalang.tree.InterfaceDeclaration):
                fqcn = f"{pkg}.{node.name}" if pkg else node.name
                results.append(fqcn)

            for _, node in tree.filter(javalang.tree.EnumDeclaration):
                fqcn = f"{pkg}.{node.name}" if pkg else node.name
                results.append(fqcn)

        except Exception:
            # Fallback to regex parser if AST parsing encounters newer Java constructs
            results = self._extract_via_regex(code, file_path)

        return results

    def _extract_via_regex(self, code: str, file_path: Path) -> List[str]:
        pkg = ""
        pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_.]+)\s*;", code, re.MULTILINE)
        if pkg_match:
            pkg = pkg_match.group(1).strip()

        found = []
        pattern = r"\b(?:public|protected|private|static|final|abstract)*\s*(?:class|interface|enum|record)\s+([A-Za-z0-9_]+)"
        for match in re.finditer(pattern, code):
            cls_name = match.group(1).strip()
            fqcn = f"{pkg}.{cls_name}" if pkg else cls_name
            found.append(fqcn)

        if not found:
            # Ultimate fallback: filename as class name
            cls_name = file_path.stem
            found.append(f"{pkg}.{cls_name}" if pkg else cls_name)

        return found
