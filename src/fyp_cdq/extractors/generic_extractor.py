"""Generic multi-language code element extractor."""

import ast
import os
import re
from pathlib import Path
from typing import List, Set

from fyp_cdq.extractors.base import BaseExtractor


class GenericExtractor(BaseExtractor):
    """Extracts classes, structs, or components for C#, Python, Go, TypeScript/JavaScript."""

    def __init__(self, language: str = "Polyglot", include_tests: bool = False):
        self.language = language.lower()
        self.include_tests = include_tests

    def extract_classes(self, source_dir: Path) -> List[str]:
        if not source_dir.exists():
            return []

        if "c#" in self.language or ".net" in self.language:
            return self._extract_csharp(source_dir)
        elif "python" in self.language:
            return self._extract_python(source_dir)
        elif "go" in self.language:
            return self._extract_go(source_dir)
        elif any(k in self.language for k in ["javascript", "typescript", "node"]):
            return self._extract_js(source_dir)
        else:
            return self._extract_fallback(source_dir)

    def _extract_csharp(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        for root, dirs, files in os.walk(source_dir):
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in ["test", "tests"] for p in rel_parts):
                continue
            for f in files:
                if f.endswith(".cs") and not f.endswith(".Designer.cs"):
                    file_path = Path(root) / f
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        code = fp.read()
                    
                    ns = ""
                    ns_match = re.search(r"^\s*namespace\s+([a-zA-Z0-9_.]+)", code, re.MULTILINE)
                    if ns_match:
                        ns = ns_match.group(1).strip()
                    
                    pattern = r"\b(?:public|internal|private|protected)*\s*(?:static|sealed|abstract)*\s*(?:class|interface|struct|record)\s+([A-Za-z0-9_]+)"
                    for match in re.finditer(pattern, code):
                        cname = match.group(1)
                        elements.add(f"{ns}.{cname}" if ns else cname)
                    if not elements:
                        elements.add(f"{ns}.{file_path.stem}" if ns else file_path.stem)
        return sorted(list(elements))

    def _extract_python(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        for root, dirs, files in os.walk(source_dir):
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in ["test", "tests"] for p in rel_parts):
                continue
            for f in files:
                if f.endswith(".py") and not f.startswith("__"):
                    file_path = Path(root) / f
                    rel_mod = file_path.relative_to(source_dir).with_suffix("").as_posix().replace("/", ".")
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        try:
                            tree = ast.parse(fp.read())
                            classes_in_file = [
                                f"{rel_mod}.{node.name}"
                                for node in ast.walk(tree)
                                if isinstance(node, ast.ClassDef)
                            ]
                            if classes_in_file:
                                elements.update(classes_in_file)
                            else:
                                elements.add(rel_mod)
                        except Exception:
                            elements.add(rel_mod)
        return sorted(list(elements))

    def _extract_go(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        for root, dirs, files in os.walk(source_dir):
            if not self.include_tests and any(t in root.lower() for t in ["test", "tests"]):
                continue
            for f in files:
                if f.endswith(".go") and not f.endswith("_test.go"):
                    file_path = Path(root) / f
                    rel_pkg = file_path.parent.relative_to(source_dir).as_posix().replace("/", ".")
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        code = fp.read()
                    
                    pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_]+)", code, re.MULTILINE)
                    pkg = pkg_match.group(1) if pkg_match else rel_pkg
                    
                    # Structs and interfaces
                    pattern = r"type\s+([A-Z][A-Za-z0-9_]*)\s+(?:struct|interface)"
                    found = False
                    for match in re.finditer(pattern, code):
                        elements.add(f"{pkg}.{match.group(1)}")
                        found = True
                    if not found:
                        elements.add(f"{pkg}.{file_path.stem}")
        return sorted(list(elements))

    def _extract_js(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        for root, dirs, files in os.walk(source_dir):
            if any(p in root for p in ["node_modules", ".git", "dist", "build"]):
                continue
            if not self.include_tests and any(t in root.lower() for t in ["test", "tests"]):
                continue
            for f in files:
                if (f.endswith(".js") or f.endswith(".ts")) and not f.endswith(".min.js"):
                    file_path = Path(root) / f
                    rel_name = file_path.relative_to(source_dir).as_posix()
                    elements.add(rel_name)
        return sorted(list(elements))

    def _extract_fallback(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        for root, dirs, files in os.walk(source_dir):
            if any(p in root for p in [".git", "build", "target", "node_modules"]):
                continue
            for f in files:
                if not f.startswith("."):
                    file_path = Path(root) / f
                    elements.add(file_path.relative_to(source_dir).as_posix())
        return sorted(list(elements))
