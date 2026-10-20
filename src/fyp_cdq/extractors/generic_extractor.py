"""Generic multi-language code element extractor."""

import ast
import os
import re
from pathlib import Path
from typing import List, Set

from fyp_cdq.extractors.base import BaseExtractor
from fyp_cdq.extractors.java_extractor import JavaExtractor, strip_java_comments_and_strings


_COMMON_EXCLUDE_DIRS = {
    ".git", ".github", ".idea", ".vscode", "node_modules", "vendor",
    "dist", "build", "target", "out", "bin", "obj", "coverage",
    "__pycache__", "venv", ".venv", ".gradle", ".mvn", "docs", "doc",
}

_TEST_DIRS = {"test", "tests", "testing", "__tests__", "testdata", "e2e", "integration_tests", "spec", "specs"}

_CSHARP_KEYWORDS = {
    "abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char",
    "checked", "class", "const", "continue", "decimal", "default", "delegate",
    "do", "double", "else", "enum", "event", "explicit", "extern", "false",
    "finally", "fixed", "float", "for", "foreach", "from", "goto", "if",
    "implicit", "in", "int", "interface", "internal", "is", "lock", "long",
    "namespace", "new", "null", "object", "operator", "out", "override",
    "params", "partial", "private", "protected", "public", "readonly", "record",
    "ref", "return", "sbyte", "sealed", "select", "short", "sizeof", "stackalloc",
    "static", "string", "struct", "switch", "this", "throw", "to", "true",
    "try", "typeof", "uint", "ulong", "unchecked", "unsafe", "ushort", "using",
    "value", "var", "virtual", "void", "volatile", "when", "where", "while", "yield",
}

_JS_CONFIG_PREFIXES = (
    "eslint", ".eslint", "jest.config", "webpack", "vite.config", "rollup.config",
    "babel.config", "postcss.config", "tailwind.config", "commitlint", "karma.conf",
    "protractor.conf", "gulpfile", "gruntfile", "next.config", "nuxt.config", "tsconfig",
    "playwright.config", "cypress.config", "vitest.config", "prettier",
)


class GenericExtractor(BaseExtractor):
    """Extracts classes, structs, or components across C#, Python, Go, JS/TS, Kotlin, Scala, PHP, Ruby, Rust, Elixir, C++."""

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
        elif self.language == "go" or "golang" in self.language:
            return self._extract_go(source_dir)
        elif any(k in self.language for k in ["javascript", "typescript", "node", "vue", "react"]):
            return self._extract_js(source_dir)
        elif "kotlin" in self.language:
            return self._extract_kotlin(source_dir)
        elif "scala" in self.language:
            return self._extract_scala(source_dir)
        elif "php" in self.language:
            return self._extract_php(source_dir)
        elif "ruby" in self.language:
            return self._extract_ruby(source_dir)
        elif "rust" in self.language:
            return self._extract_rust(source_dir)
        elif "elixir" in self.language:
            return self._extract_elixir(source_dir)
        elif "c++" in self.language or self.language == "c":
            return self._extract_cpp(source_dir)
        else:
            return self._extract_polyglot(source_dir)

    def _should_skip_dir(self, d: str, extra_excludes: Set[str] = frozenset()) -> bool:
        dl = d.lower()
        if d.startswith(".") or dl in _COMMON_EXCLUDE_DIRS or dl in extra_excludes:
            return True
        if not self.include_tests and (dl in _TEST_DIRS or dl.endswith("_test") or dl.endswith("_tests") or dl.endswith("-tests") or dl.endswith(".tests") or dl.endswith(".test")):
            return True
        return False

    def _extract_csharp(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        pattern = re.compile(
            r"(?:^|[\s};\]])"
            r"(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|ref)[ \t\r\n]+)*"
            r"(?:class|interface|struct|record(?:[ \t]+class|[ \t]+struct)?)[ \t]+([A-Za-z_][A-Za-z0-9_]*)\b"
        )
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d, {"migrations"})]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS or p.endswith(".tests") or p.endswith(".test") for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(".cs"):
                    continue
                if f.endswith(".Designer.cs") or f.endswith(".g.cs") or f in ("AssemblyInfo.cs", "GlobalUsings.cs"):
                    continue
                if not self.include_tests and (f.endswith("Tests.cs") or f.endswith("Test.cs")):
                    continue
                file_path = Path(root) / f
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                    code = fp.read()

                cleaned = strip_java_comments_and_strings(code)
                ns = ""
                ns_match = re.search(r"^\s*namespace\s+([a-zA-Z0-9_.]+)", cleaned, re.MULTILINE)
                if ns_match:
                    ns = ns_match.group(1).strip()

                found_in_file = False
                for match in pattern.finditer(cleaned):
                    # Ensure not preceded by ':' (e.g. `where T : class`)
                    start_pos = match.start()
                    prefix = cleaned[max(0, start_pos - 5):start_pos + 1]
                    if ":" in prefix:
                        continue
                    cname = match.group(1)
                    if cname.lower() in _CSHARP_KEYWORDS:
                        continue
                    elements.add(f"{ns}.{cname}" if ns else cname)
                    found_in_file = True

                if not found_in_file and (
                    file_path.stem.lower() in ("program", "startup")
                    or re.search(r"\bMap(?:Get|Post|Put|Delete|Patch|GrpcService)\b", cleaned)
                ):
                    elements.add(f"{ns}.{file_path.stem}" if ns else file_path.stem)
        return sorted(list(elements))

    def _extract_python(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        skip_files = {"tests.py", "conftest.py", "setup.py", "manage.py", "wsgi.py", "asgi.py"}
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d, {"migrations", "static", "templates", "locale", "fixtures"})]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(".py") or (f.startswith("__") and f != "__main__.py") or f.endswith(("_pb2.py", "_pb2_grpc.py")):
                    continue
                if not self.include_tests and (f in skip_files or f.startswith("test_") or f.endswith("_test.py")):
                    continue
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
        pattern = re.compile(r"\btype[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]+(?:struct|interface)\b")
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d, {"mocks", "mock"})]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if f.endswith(".go") and not f.endswith("_test.go") and not f.endswith(".pb.go"):
                    file_path = Path(root) / f
                    rel_pkg = file_path.parent.relative_to(source_dir).as_posix().replace("/", ".")
                    if rel_pkg == ".":
                        rel_pkg = source_dir.name
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        code = fp.read()

                    cleaned = strip_java_comments_and_strings(code)
                    pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_]+)", cleaned, re.MULTILINE)
                    pkg = pkg_match.group(1) if pkg_match else rel_pkg

                    found = False
                    for match in pattern.finditer(cleaned):
                        elements.add(f"{pkg}.{match.group(1)}")
                        found = True
                    if not found:
                        elements.add(f"{pkg}.{file_path.stem}")
        return sorted(list(elements))

    def _extract_js(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        valid_exts = (".js", ".ts", ".jsx", ".tsx", ".mjs", ".vue")
        invalid_suffixes = (
            ".min.js", ".d.ts", ".spec.ts", ".spec.js", ".spec.tsx", ".spec.jsx",
            ".test.ts", ".test.js", ".test.tsx", ".test.jsx", ".e2e-spec.ts",
            ".config.js", ".config.ts", ".config.mjs", ".config.cjs", ".conf.js",
        )
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d, {"public", "assets", "migrations", "seeds", "typings"})]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                fl = f.lower()
                if not fl.endswith(valid_exts):
                    continue
                if fl.endswith(invalid_suffixes) or fl.startswith(_JS_CONFIG_PREFIXES):
                    continue
                file_path = Path(root) / f
                rel_name = file_path.relative_to(source_dir).as_posix()
                elements.add(rel_name)
        return sorted(list(elements))

    def _extract_kotlin(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        pattern = re.compile(
            r"(?:^|[\s};)])"
            r"(?:(?:public|private|protected|internal|open|abstract|sealed|data|enum|annotation|value|inline|inner)[ \t\r\n]+)*"
            r"(?:class|interface|object)[ \t]+([A-Za-z_][A-Za-z0-9_]*)\b"
        )
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d)]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(".kt"):
                    continue
                if not self.include_tests and (f.endswith("Test.kt") or f.endswith("Tests.kt") or f.endswith("Spec.kt")):
                    continue
                file_path = Path(root) / f
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                cleaned = strip_java_comments_and_strings(code)
                pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_.]+)", cleaned, re.MULTILINE)
                pkg = pkg_match.group(1).strip() if pkg_match else ""
                found = False
                for match in pattern.finditer(cleaned):
                    cname = match.group(1)
                    elements.add(f"{pkg}.{cname}" if pkg else cname)
                    found = True
                if not found:
                    elements.add(f"{pkg}.{file_path.stem}" if pkg else file_path.stem)
        return sorted(list(elements))

    def _extract_scala(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        pattern = re.compile(
            r"(?:^|[\s};)])"
            r"(?:(?:private|protected|final|abstract|sealed|implicit|case|lazy)[ \t\r\n]+)*"
            r"(?:class|trait|object)[ \t]+([A-Za-z_][A-Za-z0-9_]*)\b"
        )
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d)]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(".scala"):
                    continue
                if not self.include_tests and (f.endswith("Test.scala") or f.endswith("Spec.scala") or f.endswith("Suite.scala")):
                    continue
                file_path = Path(root) / f
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                cleaned = strip_java_comments_and_strings(code)
                pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_.]+)", cleaned, re.MULTILINE)
                pkg = pkg_match.group(1).strip() if pkg_match else ""
                found = False
                for match in pattern.finditer(cleaned):
                    cname = match.group(1)
                    elements.add(f"{pkg}.{cname}" if pkg else cname)
                    found = True
                if not found:
                    elements.add(f"{pkg}.{file_path.stem}" if pkg else file_path.stem)
        return sorted(list(elements))

    def _extract_php(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        pattern = re.compile(r"\b(?:class|interface|trait|enum)[ \t]+([A-Za-z_][A-Za-z0-9_]*)\b")
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d, {"migrations", "storage", "cache", "public", "views"})]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(".php") or (not self.include_tests and f.endswith("Test.php")):
                    continue
                file_path = Path(root) / f
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                cleaned = strip_java_comments_and_strings(code)
                ns_match = re.search(r"^\s*namespace\s+([a-zA-Z0-9_\\]+)\s*;", cleaned, re.MULTILINE)
                ns = ns_match.group(1).replace("\\", ".") if ns_match else ""
                found = False
                for match in pattern.finditer(cleaned):
                    cname = match.group(1)
                    elements.add(f"{ns}.{cname}" if ns else cname)
                    found = True
                if not found:
                    elements.add(file_path.relative_to(source_dir).as_posix())
        return sorted(list(elements))

    def _extract_ruby(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        pattern = re.compile(r"^\s*(?:class|module)[ \t]+([A-Z][A-Za-z0-9_:]*)", re.MULTILINE)
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d, {"db", "config", "public", "tmp", "log", "bin"})]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(".rb") or f in ("Gemfile.rb", "routes.rb", "seeds.rb", "schema.rb"):
                    continue
                if not self.include_tests and (f.endswith("_spec.rb") or f.endswith("_test.rb")):
                    continue
                file_path = Path(root) / f
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                found = False
                for match in pattern.finditer(code):
                    cname = match.group(1).replace("::", ".")
                    elements.add(cname)
                    found = True
                if not found:
                    elements.add(file_path.relative_to(source_dir).with_suffix("").as_posix().replace("/", "."))
        return sorted(list(elements))

    def _extract_rust(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        pattern = re.compile(r"\b(?:pub(?:\([^)]*\))?[ \t]+)?(?:struct|enum|trait)[ \t]+([A-Za-z_][A-Za-z0-9_]*)\b")
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d)]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(".rs") or f == "build.rs":
                    continue
                file_path = Path(root) / f
                rel_mod = file_path.relative_to(source_dir).with_suffix("").as_posix().replace("/", ".")
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                cleaned = strip_java_comments_and_strings(code)
                found = False
                for match in pattern.finditer(cleaned):
                    elements.add(f"{rel_mod}.{match.group(1)}")
                    found = True
                if not found:
                    elements.add(rel_mod)
        return sorted(list(elements))

    def _extract_elixir(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        pattern = re.compile(r"^\s*defmodule[ \t]+([A-Z][A-Za-z0-9_.]*)", re.MULTILINE)
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d, {"deps", "_build", "priv"})]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(".ex"):
                    continue
                file_path = Path(root) / f
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                for match in pattern.finditer(code):
                    elements.add(match.group(1))
        return sorted(list(elements))

    def _extract_cpp(self, source_dir: Path) -> List[str]:
        elements: Set[str] = set()
        valid_exts = (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h")
        pattern = re.compile(r"\b(?:class|struct)[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*(?:final[ \t]*)?(?::|\{)")
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d, {"third_party", "thirdparty", "external", "cmake"})]
            rel_parts = [p.lower() for p in Path(root).relative_to(source_dir).parts]
            if not self.include_tests and any(p in _TEST_DIRS for p in rel_parts):
                continue
            for f in files:
                if not f.endswith(valid_exts):
                    continue
                if not self.include_tests and (f.endswith("_test.cpp") or f.endswith("_test.cc") or f.startswith("test_")):
                    continue
                file_path = Path(root) / f
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                cleaned = strip_java_comments_and_strings(code)
                found = False
                for match in pattern.finditer(cleaned):
                    elements.add(match.group(1))
                    found = True
                if not found and f.endswith((".cpp", ".cc", ".cxx")):
                    elements.add(file_path.stem)
        return sorted(list(elements))

    def _extract_polyglot(self, source_dir: Path) -> List[str]:
        """Extracts classes from a directory by running all relevant language extractors on source files."""
        elements: Set[str] = set()
        java_ext = JavaExtractor(include_tests=self.include_tests)
        elements.update(java_ext.extract_classes(source_dir))
        elements.update(self._extract_kotlin(source_dir))
        elements.update(self._extract_scala(source_dir))
        elements.update(self._extract_csharp(source_dir))
        elements.update(self._extract_go(source_dir))
        elements.update(self._extract_python(source_dir))
        elements.update(self._extract_js(source_dir))
        elements.update(self._extract_php(source_dir))
        elements.update(self._extract_ruby(source_dir))
        elements.update(self._extract_rust(source_dir))
        elements.update(self._extract_elixir(source_dir))
        elements.update(self._extract_cpp(source_dir))
        return sorted(list(elements))
