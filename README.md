# Comparative Decomposition Quality (CDQ)

Evaluation framework for benchmarking software architecture quality and decomposition metrics on real-world and reference microservice systems.

Part of the Final Year Project (FYP): **"Automatic Microservice Decomposition using Improved Code Embedding"**.

---

## 📌 Motivation & Objectives

While monolithic decomposition research has proposed numerous decomposition tools (e.g., Mono2Micro, FoMo, CARGO, CHGNN), systematic evaluation on the **target microservices themselves** provides critical ground truth baselines.

This repository:
1. **Curates and links benchmark microservice codebases** via Git submodules (`codebases/microservices/`).
2. **Standardizes architecture partitions** across Java, C# .NET, Go, Python, and Node.js microservices into universal `output.json` schemas.
3. **Evaluates quantitative decomposition metrics**, starting with **Non-Extreme Distribution (NED)** implemented directly in `src/fyp_cdq/metrics/ned.py`, with an extensible architecture designed for multi-codebase comparative metrics.
4. **Maintains minimal code duplication and standalone operation**: No TSV tables or custom submodule scripts are executed at runtime. All codebase exploration is performed directly on the repository structures.

---

## 📐 Non-Extreme Distribution (NED)

**NED** evaluates service-size equity, penalizing partitions that fall outside the empirically accepted non-extreme size window:
- **Fixed Bounds NED** (default $[5, 20]$ classes):
  $$NED_{\text{fixed}} = 1 - \frac{\sum_{k=1}^K |C_k| \cdot \mathbb{I}(|C_k| < lo \lor |C_k| > hi)}{\sum_{k=1}^K |C_k|}$$
- **Relative Bounds NED** (CHGNN variant, $\epsilon=0.5$):
  $$NED_{\text{relative}} = \frac{\sum_{k=1}^K |C_k| \cdot \mathbb{I}(\lfloor \mu(1-\epsilon) \rfloor \le |C_k| \le \lceil \mu(1+\epsilon) \rceil)}{\sum_{k=1}^K |C_k|}$$
  where $\mu = \frac{\text{Total Classes}}{K}$.

High-quality microservice architectures adhere to bounded contexts with balanced partitions, yielding scores close to $1.0$.

---

## 🚀 Quickstart

This project is managed with [`uv`](https://github.com/astral-sh/uv).

### 1. Installation

```bash
# Clone this repository (with submodules if public)
git clone --recurse-submodules <repo_url>
cd fyp-cdq

# Install dependencies into virtual environment
uv sync
```

### 2. Running Metric Evaluations

The evaluation CLI runs in the form:
`uv run python scripts/run_eval.py <system_id> <metric> [options]`

#### Example 1: Evaluate MS010 with custom bounds

```bash
uv run python scripts/run_eval.py MS010 ned --lo 3 --eps 0.25
```

#### Example 2: Evaluate MS001 (Spring PetClinic) with default bounds

```bash
uv run python scripts/run_eval.py MS001 ned
```

#### Example 3: Evaluate MS016 (Pitstop Garage Management)

```bash
uv run python scripts/run_eval.py MS016 ned
```

### 3. Error Handling

- **Unsupported metric**:
  ```bash
  uv run python scripts/run_eval.py MS010 unknown_metric
  # Error: Unsupported metric 'unknown_metric'. Supported metrics: NED
  ```
- **Missing or unsupported monolith requirement**:
  If a metric requires both monolith and microservice codebases and the monolith is missing, an error is reported immediately:
  `Error: Metric '<name>' requires both monolith and microservice codebases, but monolith codebase was not found for '<system>'.`

---

## 📦 Managing Git Submodules

Submodules are added directly using standard Git commands. For fast setup and minimal storage consumption, shallow clones (`--depth 1`) are used:

```bash
# Add a microservice codebase submodule
git submodule add --depth 1 https://github.com/spring-petclinic/spring-petclinic-microservices.git codebases/microservices/MS001_spring-petclinic-microservices

# Add a monolithic counterpart submodule (for later dual-codebase metrics)
git submodule add --depth 1 https://github.com/spring-projects/spring-petclinic.git codebases/monoliths/P01_spring-petclinic
```

---

## 📊 Benchmark Results

| System ID | System Name | Primary Language | Services Detected | Total Classes | NED (Fixed $[5,20]$) | NED (Relative $\epsilon=0.5$) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **MS001** | [Spring PetClinic (Microservices)](https://github.com/spring-petclinic/spring-petclinic-microservices) | Java | 8 | 60 | **0.9500** | 0.4333 |
| **MS004** | [FTGO (Food To Go)](https://github.com/microservices-patterns/ftgo-application) | Java | 8 | 83 | **0.3976** | 0.3976 |
| **MS007** | [Red Hat CoolStore](https://github.com/jbossdemocentral/coolstore-microservice) | Java | 4 | 33 | **0.6923** | 0.5000 |
| **MS008** | [Cargo Tracker](https://github.com/eclipse-ee4j/cargotracker) | Java | 1 | 105 | **0.0000** | 1.0000 |
| **MS009** | [AWS UniShop](https://github.com/aws-samples/unishop-monolith-to-microservices) | Java | 2 | 62 | **0.0806** | 0.0000 |
| **MS010** | [Amazon ECS Modernization](https://github.com/aws-samples/amazon-ecs-java-microservices) | Java | 3 | 78 | **0.0000** | 0.0000 |
| **MS011** | [Monolith vs Microservices](https://github.com/annaojdowska/monolith-vs-microservices) | Java | 5 | 9 | **0.0000** | 1.0000 |
| **MS015** | [Microsoft eShop](https://github.com/dotnet/eShop) | C# .NET | 5 | 200 | **0.0924** | 0.1576 |
| **MS016** | [Pitstop Garage Management](https://github.com/EdwinVW/pitstop) | C# .NET | 15 | 215 | **0.5618** | 0.4551 |
| **MS017** | [Google Cloud FancyStore](https://github.com/googlecodelabs/monolith-to-microservices) | Node.js | 3 | 3 | **0.0000** | 1.0000 |
| **MS018** | [Maharjan Benchmark](https://github.com/rokinmaharjan/benchmarking-monolith-to-microservices) | Node.js | 1 | 4 | **0.0000** | 1.0000 |
| **MS020** | [PiggyMetrics](https://github.com/sqshq/piggymetrics) | Java | 9 | 74 | **0.5946** | 0.1216 |
| **MS021** | [TeaStore](https://github.com/DescartesResearch/TeaStore) | Java | 10 | 136 | **0.4926** | 0.4559 |

Outputs and metric JSONs are persisted under `outputs/<system_id>/`:
- `output.json`: Standardized microservice partition (`{"system": ..., "microservices": {...}}`).
- `ned_score.json`: Quantitative scores and service-level breakdown.

---

## 🏗️ Repository Architecture

```
fyp-cdq/
├── pyproject.toml              # UV project configuration and dependencies
├── uv.lock                     # Locked dependencies
├── README.md                   # Project documentation and benchmark report
├── .gitignore                  # Git ignore rules (includes references/)
├── .gitmodules                 # Submodule definitions (public https:// URLs)
├── references/                 # Ignored reference scripts (ned_sota.py, build_tsvs.py)
├── recon_tables/               # Reference reconciliation tables
├── codebases/                  # Submodules
│   ├── microservices/          # Cloned microservices codebases
│   └── monoliths/              # Cloned monolithic codebases (for dual-codebase metrics)
├── scripts/
│   └── run_eval.py             # CLI runner for metric evaluation
├── src/fyp_cdq/                # Core modular Python package
│   ├── config.py               # Central paths and constants
│   ├── models.py               # MicroserviceSystem, Partition, MetricResult
│   ├── extractors/
│   │   ├── base.py             # BaseExtractor interface
│   │   ├── java_extractor.py   # Java AST parser (javalang + regex fallback)
│   │   ├── generic_extractor.py# Polyglot parser (C#, Python, Go, Node.js)
│   │   └── service_detector.py # Auto-detects microservices via POM/Gradle/Docker
│   ├── metrics/
│   │   ├── base.py             # BaseMetric interface (needs_monolith flag)
│   │   ├── ned.py              # Self-contained NED metric evaluator
│   │   └── registry.py         # Pluggable metric registry
│   └── pipeline.py             # Single-system single-metric evaluator
├── outputs/                    # Output partitions and score JSONs
└── tests/                      # Automated test suite (pytest)
    ├── test_ned.py
    ├── test_extractors.py
    ├── test_models.py
    └── test_pipeline.py
```

---

## 🧪 Testing

Run the test suite using `pytest`:

```bash
uv run pytest
```
