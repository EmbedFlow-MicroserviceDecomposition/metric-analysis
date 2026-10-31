"""Configuration paths and constants for fyp-cdq."""

from pathlib import Path

# Project Root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Submodule & Codebase Storage Directories
CODEBASES_DIR = PROJECT_ROOT / "codebases"
MICROSERVICES_DIR = CODEBASES_DIR / "microservices"
MONOLITHS_DIR = CODEBASES_DIR / "monoliths"

# Manifest Files
MICROSERVICES_JSON = MICROSERVICES_DIR / "microservices.json"
MONOLITHS_JSON = MONOLITHS_DIR / "monoliths.json"

# Output and Results Directories
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
GROUND_TRUTH_DIR = BENCHMARKS_DIR / "ground_truth"
CALIBRATION_RUNS_DIR = BENCHMARKS_DIR / "calibration_runs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Canonical Agent Extraction Filename
AGENT_EXTRACTION_FILENAME = "agent_extraction.json"

# Default NED Bounds
DEFAULT_NED_LO = 5
DEFAULT_NED_HI = 20
DEFAULT_NED_EPS = 0.5
