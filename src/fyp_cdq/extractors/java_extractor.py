"""Java class extractor using javalang AST with comment-safe regex fallback."""

import os
import re
from pathlib import Path
from typing import List, Set
import javalang

from fyp_cdq.extractors.base import BaseExtractor


_JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "record", "return", "short",
    "static", "strictfp", "super", "switch", "synchronized", "this", "throw",
    "throws", "transient", "try", "var", "void", "volatile", "while", "yield",
    "true", "false", "null", "permits", "sealed",
}

_EXCLUDE_DIRS = {
    ".git", ".github", ".idea", ".vscode", "target", "build",
    "node_modules", "vendor", ".gradle", ".mvn", "dist", "out",
}


def strip_java_comments_and_strings(code: str) -> str:
    """Removes comments, text blocks, and string/char literals while preserving structure."""
    pattern = re.compile(
        r'"""[\s\S]*?"""'          # Java 15+ text blocks
        r'|"(?:\\.|[^"\\])*"'      # String literals
        r"|'(?:\\.|[^'\\])*'"      # Char literals
        r"|/\*[\s\S]*?\*/"         # Block / Javadoc comments
        r"|//[^\r\n]*"             # Line comments
    )
    def _replacer(match: re.Match) -> str:
        s = match.group(0)
        if s.startswith("/") :
            return "\n" if "\n" in s else " "
        return '""'
    return pattern.sub(_replacer, code)


class JavaExtractor(BaseExtractor):
    """Extracts Java classes, interfaces, enums, and records from a source directory."""

    def __init__(self, include_tests: bool = False):
        self.include_tests = include_tests

    def extract_classes(self, source_dir: Path) -> List[str]:
        classes: Set[str] = set()
        if not source_dir.exists():
            return []

        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [
                d for d in dirs
                if d.lower() not in _EXCLUDE_DIRS
                and not d.startswith(".")
                and (self.include_tests or d.lower() not in ("test", "tests"))
            ]
            root_path = Path(root)
            if not self.include_tests:
                rel_parts = [p.lower() for p in root_path.relative_to(source_dir).parts]
                if any(p in ("test", "tests") for p in rel_parts):
                    continue

            for file in files:
                if file.endswith(".java"):
                    if file in ("package-info.java", "module-info.java"):
                        continue
                    if not self.include_tests and (file.endswith("Test.java") or file.endswith("Tests.java") or file.endswith("IT.java")):
                        continue
                    file_path = root_path / file
                    extracted = self._extract_from_file(file_path)
                    classes.update(extracted)

        return sorted(list(classes))

    def _extract_from_file(self, file_path: Path) -> List[str]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        results = []
        try:
            # Replace Java 15+ text blocks so javalang can parse modern Java files
            sanitized = re.sub(r'"""[\s\S]*?"""', '""', code)
            tree = javalang.parse.parse(sanitized)
            pkg = tree.package.name if tree.package else ""

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
            results = self._extract_via_regex(code, file_path)

        return results

    def _extract_via_regex(self, code: str, file_path: Path) -> List[str]:
        cleaned = strip_java_comments_and_strings(code)
        pkg = ""
        pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_.]+)\s*;", cleaned, re.MULTILINE)
        if pkg_match:
            pkg = pkg_match.group(1).strip()

        found = []
        pattern = re.compile(
            r"(?:^|[\s};)])"
            r"(?:(?:public|protected|private|static|final|abstract|sealed|non-sealed|strictfp)[ \t\r\n]+)*"
            r"(?:class|interface|enum|record)[ \t]+([A-Za-z_][A-Za-z0-9_]*)\b"
        )
        for match in pattern.finditer(cleaned):
            cls_name = match.group(1).strip()
            if cls_name in _JAVA_KEYWORDS:
                continue
            fqcn = f"{pkg}.{cls_name}" if pkg else cls_name
            found.append(fqcn)

        if not found and file_path.stem not in ("package-info", "module-info"):
            cls_name = file_path.stem
            found.append(f"{pkg}.{cls_name}" if pkg else cls_name)

        return found
