"""Detects microservices in a codebase repository and extracts the partition."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from fyp_cdq.config import MICROSERVICES_JSON
from fyp_cdq.extractors.base import BaseExtractor
from fyp_cdq.extractors.generic_extractor import GenericExtractor
from fyp_cdq.extractors.java_extractor import JavaExtractor
from fyp_cdq.models import Partition


class ServiceDetector:
    """Discovers microservice boundaries in a repository and extracts their classes."""

    EXCLUDE_DIRS = {
        ".git", ".github", ".idea", ".vscode", "docs", "doc", "scripts", "script",
        "gradle", ".mvn", "target", "build", "node_modules", "vendor", "test", "tests"
    }

    def __init__(self, include_infrastructure: bool = True):
        self.include_infrastructure = include_infrastructure

    def detect_and_extract(
        self, codebase_path: Path, system_name: str = ""
    ) -> Partition:
        """
        Extracts microservice partition.
        Prioritizes explicit services configuration in microservices.json.
        Only sniffs codebase directories if manifest is missing or incomplete.
        """
        # 1. Try manifest from microservices.json
        manifest_partition = self._extract_from_manifest(codebase_path, system_name)
        if manifest_partition and manifest_partition.service_count > 0:
            return manifest_partition

        # 2. Sniffing fallback (only when absolutely necessary)
        service_dirs = self.discover_service_directories(codebase_path)

        microservices: Dict[str, List[str]] = {}
        for service_name, sdir in service_dirs.items():
            extractor = self._get_extractor(sdir)
            classes = extractor.extract_classes(sdir)
            if classes:
                microservices[service_name] = classes

        return Partition(
            microservices=microservices,
            system_name=system_name or codebase_path.name,
            tool_or_system=f"Ground-Truth Architecture ({system_name or codebase_path.name})"
        )

    def _extract_from_manifest(self, codebase_path: Path, system_name: str) -> Optional[Partition]:
        """Loads pre-configured service locations from microservices.json without sniffing."""
        if not MICROSERVICES_JSON.exists():
            return None

        try:
            with open(MICROSERVICES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        # Lookup by system_id (e.g. MS010) or directory name
        entry = data.get(system_name)
        if not entry:
            for k, v in data.items():
                if v.get("path") == codebase_path.name or codebase_path.name.startswith(f"{k}_"):
                    entry = v
                    break

        if not entry or not entry.get("services"):
            return None

        lang = entry.get("language", "")
        is_multi_lang = "polyglot" in lang.lower() or "/" in lang
        microservices: Dict[str, List[str]] = {}

        for sname, rel_dir in entry["services"].items():
            sdir = (codebase_path / rel_dir).resolve()
            if sdir.is_dir():
                if is_multi_lang:
                    extractor = self._get_extractor(sdir, forced_language="")
                    classes = extractor.extract_classes(sdir)
                else:
                    extractor = self._get_extractor(sdir, forced_language=lang)
                    classes = extractor.extract_classes(sdir)
                    if not classes:
                        # Fallback to per-service language auto-detection (e.g. TS UI service in a Java repo)
                        fallback_ext = self._get_extractor(sdir, forced_language="")
                        classes = fallback_ext.extract_classes(sdir)
                if classes:
                    microservices[sname] = classes

        if microservices:
            return Partition(
                microservices=microservices,
                system_name=system_name or entry.get("name", codebase_path.name),
                tool_or_system=f"Ground-Truth Architecture ({system_name or codebase_path.name})"
            )
        return None

    def discover_service_directories(
        self, codebase_path: Path
    ) -> Dict[str, Path]:
        """
        Maps service name to its filesystem directory by sniffing codebase manifests.
        """
        if not codebase_path.exists():
            return {}

        discovered: Dict[str, Path] = {}

        # 1. Check Maven multi-module pom.xml
        pom_modules = self._discover_maven_modules(codebase_path)
        if pom_modules:
            for mod_name, mod_dir in pom_modules.items():
                discovered[mod_name] = mod_dir

        # 2. Check Gradle settings.gradle
        if not discovered:
            gradle_modules = self._discover_gradle_modules(codebase_path)
            if gradle_modules:
                for mod_name, mod_dir in gradle_modules.items():
                    discovered[mod_name] = mod_dir

        # 3. Check Docker Compose build contexts
        if not discovered:
            compose_services = self._discover_docker_compose_services(codebase_path)
            if compose_services:
                for sname, sdir in compose_services.items():
                    discovered[sname] = sdir

        # 4. Fallback: Top-level directories that contain source code
        if not discovered:
            discovered = self._discover_fallback_directories(codebase_path)

        # 5. Nested container directory: if still nothing found, inspect candidate subdirectories
        if not discovered:
            for sub in codebase_path.iterdir():
                if sub.is_dir() and sub.name not in self.EXCLUDE_DIRS and not sub.name.startswith("."):
                    sub_services = self._discover_fallback_directories(sub)
                    if not sub_services:
                        sub_services = self._discover_maven_modules(sub)
                    if sub_services:
                        for sname, sdir in sub_services.items():
                            discovered[sname] = sdir
                        if discovered:
                            break

        return discovered

    def _discover_maven_modules(self, root: Path) -> Dict[str, Path]:
        pom_file = root / "pom.xml"
        if not pom_file.exists():
            return {}

        modules = {}
        try:
            tree = ET.parse(pom_file)
            r = tree.getroot()
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}
            mods = r.findall(".//m:module", ns) or r.findall(".//module")
            for m in mods:
                if m.text and m.text.strip():
                    mod_name = m.text.strip()
                    mod_path = root / mod_name
                    if mod_path.is_dir():
                        modules[mod_name] = mod_path
        except Exception:
            pass
        return modules

    def _discover_gradle_modules(self, root: Path) -> Dict[str, Path]:
        settings = root / "settings.gradle"
        if not settings.exists():
            settings = root / "settings.gradle.kts"
            if not settings.exists():
                return {}

        modules = {}
        try:
            with open(settings, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            matches = re.findall(r"include\s*\(?['\"]([^'\"]+)['\"]\)?", content)
            for m in matches:
                clean_name = m.lstrip(":").replace(":", "/")
                mod_path = root / clean_name
                if mod_path.is_dir():
                    modules[clean_name.split("/")[-1]] = mod_path
        except Exception:
            pass
        return modules

    def _discover_docker_compose_services(self, root: Path) -> Dict[str, Path]:
        for cfile in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            cp = root / cfile
            if cp.exists():
                try:
                    with open(cp, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    services = {}
                    curr_svc = None
                    for line in lines:
                        svc_match = re.match(r"^ {2}([a-zA-Z0-9_\-]+):", line)
                        if svc_match:
                            curr_svc = svc_match.group(1)
                        build_match = re.search(r"^\s+(?:context|build):\s*([a-zA-Z0-9_\-./]+)", line)
                        if build_match and curr_svc:
                            rel_ctx = build_match.group(1).strip()
                            ctx_path = (root / rel_ctx).resolve()
                            if ctx_path.is_dir() and ctx_path != root.resolve():
                                services[curr_svc] = ctx_path
                    if services:
                        return services
                except Exception:
                    pass
        return {}

    def _discover_fallback_directories(self, root: Path) -> Dict[str, Path]:
        # Check container directories like src/, services/, apps/
        for container_name in ["src", "services", "apps"]:
            container = root / container_name
            if container.is_dir():
                sub_dirs = {}
                for p in container.iterdir():
                    if p.is_dir() and p.name not in self.EXCLUDE_DIRS and not p.name.startswith("."):
                        if self._has_source_files(p):
                            sub_dirs[p.name] = p
                if len(sub_dirs) > 1:
                    return sub_dirs

        dirs = {}
        for p in root.iterdir():
            if p.is_dir() and p.name not in self.EXCLUDE_DIRS and not p.name.startswith("."):
                if self._has_source_files(p):
                    dirs[p.name] = p
        return dirs

    def _has_source_files(self, path: Path) -> bool:
        exts = (
            "*.java", "*.kt", "*.scala", "*.go", "*.py", "*.cs",
            "*.js", "*.ts", "*.jsx", "*.tsx", "*.vue", "*.php",
            "*.rb", "*.rs", "*.ex", "*.cpp", "*.cc", "*.hpp", "*.h",
        )
        return any(any(path.rglob(ext)) for ext in exts)

    def _get_extractor(self, root: Path, forced_language: str = "") -> BaseExtractor:
        lang = forced_language.lower().strip()
        if lang == "java":
            return JavaExtractor()
        if "c#" in lang or ".net" in lang:
            return GenericExtractor(language="C#")
        if lang == "go" or "golang" in lang:
            return GenericExtractor(language="Go")
        if "python" in lang:
            return GenericExtractor(language="Python")
        if any(k in lang for k in ["node", "javascript", "typescript", "vue", "react"]):
            return GenericExtractor(language="Node.js")
        if "kotlin" in lang and "java" not in lang:
            return GenericExtractor(language="Kotlin")
        if "scala" in lang and "java" not in lang:
            return GenericExtractor(language="Scala")
        if "php" in lang:
            return GenericExtractor(language="PHP")
        if "ruby" in lang:
            return GenericExtractor(language="Ruby")
        if "rust" in lang:
            return GenericExtractor(language="Rust")
        if "elixir" in lang:
            return GenericExtractor(language="Elixir")
        if "c++" in lang or lang == "c":
            return GenericExtractor(language="C++")

        # Auto-detect from files in root (or use Polyglot extractor if multiple languages coexist)
        has_java = any(root.rglob("*.java"))
        has_kt = any(root.rglob("*.kt"))
        has_scala = any(root.rglob("*.scala"))
        if has_java and not (has_kt or has_scala):
            return JavaExtractor()
        if has_java or has_kt or has_scala:
            return GenericExtractor(language="Polyglot")
        if any(root.rglob("*.cs")):
            return GenericExtractor(language="C#")
        if any(root.rglob("*.go")):
            return GenericExtractor(language="Go")
        if any(root.rglob("*.py")):
            return GenericExtractor(language="Python")
        if any(root.rglob("*.rs")):
            return GenericExtractor(language="Rust")
        if any(root.rglob("*.ex")):
            return GenericExtractor(language="Elixir")
        if any(root.rglob("*.php")):
            return GenericExtractor(language="PHP")
        if any(root.rglob("*.rb")):
            return GenericExtractor(language="Ruby")
        if any(root.rglob("*.cpp")) or any(root.rglob("*.cc")):
            return GenericExtractor(language="C++")
        if any(root.rglob("*.ts")) or any(root.rglob("*.js")) or any(root.rglob("*.vue")):
            return GenericExtractor(language="Node.js")
        return GenericExtractor(language="Polyglot")
