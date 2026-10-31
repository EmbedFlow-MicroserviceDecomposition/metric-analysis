# Calibration & Subagent Orchestration Guide (`fyp-cdq`)

This guide is designed for **both human researchers and autonomous orchestrator agents** running the multi-tool prompt calibration workflow across:
1. **`antigravity-cli`** (Gemini Flash 3.8) — Prompt: `prompts/antigravity_prompt.md`
2. **`claude-code`** (Claude Sonnet 5.5) — Prompt: `prompts/claude_code_prompt.md`
3. **`codex`** (Codex Sol 6.1) — Prompt: `prompts/codex_prompt.md`

---

## 1. Overview of the Calibration Loop

Our goal is to extract two structural artifacts from standalone microservice codebases that static parsers cannot reliably resolve across network/process boundaries:
1. **Exposed Interfaces (`microservices[service_id].exposed_interfaces`)**: Used to calculate **CHD** and **CHM**.
2. **Inter-Service Call Edges (`inter_service_calls`)**: Used to calculate **IFN** (unique `dst_interface_id` per target service) and **SM** (merged with static intra-service call edges $\mu_k$).

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Curate Ground Truths for 20 Stratified Systems                       │
│    benchmarks/ground_truth/MSxxx.json                                   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Run Extractor in Isolated Context (Fresh Chat OR Isolated Subagent)  │
│    Input ONLY:                                                          │
│      • prompts/<tool>_prompt.md                                         │
│      • outputs/<MS_ID>/output.json (canonical service & class names)    │
│      • codebases/microservices/<MS_ID>_*/                               │
│    Output:                                                              │
│      • benchmarks/calibration_runs/<tool>/<version>/<MS_ID>.json        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Score Against Ground Truth (Orchestrator / Researcher ONLY)          │
│    uv run python scripts/validate_extraction.py \                       │
│      --pred-dir benchmarks/calibration_runs/<tool>/<version>            │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. Inspect FP/FN & Metric Drift (ΔCHD, ΔCHM, ΔIFN, ΔSM)                 │
│    • If F1 >= 0.85 and MAE <= 0.05 -> Freeze Winning Tool + Prompt!     │
│    • Else -> Harden prompts/<tool>_prompt.md -> Increment <version>     │
│      -> Repeat Step 2 in brand-new isolated contexts.                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Using Isolated Subagents for Calibration (Agent-Friendly Workflow)

Researchers **can** use an orchestrator agent inside `antigravity-cli`, `claude-code`, or `codex` to automate the calibration loop across the 20 benchmark systems by spawning **isolated subagents** (one subagent per system `MSxxx`).

### CRITICAL Anti-Contamination Rules (Strict Context Firewall)
When an **Orchestrator Agent** spawns an **Extractor Subagent** for system `<MS_ID>`:

1. **Fresh Context per System**:
   - Never reuse a subagent across multiple `MSxxx` systems or across prompt versions (`v1` $\to$ `v2`). Always spawn a brand-new subagent (`invoke_subagent` in Antigravity, `Task` subagent in Claude Code, or headless CLI process).
2. **Strict Read Scope for Extractor Subagents**:
   - **ALLOWED to read**:
     - `prompts/<tool>_prompt.md`
     - `prompts/schema.json`
     - `outputs/<MS_ID>/output.json`
     - `codebases/microservices/<MS_ID>_*/`
   - **FORBIDDEN to read**:
     - `benchmarks/ground_truth/` (Ground-truth answers!)
     - `codebases/monoliths/` (Monolith codebases!)
     - `benchmarks/calibration_runs/` (Previous calibration runs or validation reports!)
     - `outputs/<MS_ID>/*_score.json`
3. **Orchestrator-Only Validation**:
   - Once the Extractor Subagents finish writing `benchmarks/calibration_runs/<tool>/<version>/<MS_ID>.json`, the **Orchestrator Agent** runs `uv run python scripts/validate_extraction.py` to compute Precision, Recall, F1, and downstream metric drift ($\Delta\text{CHD}, \Delta\text{CHM}, \Delta\text{IFN}, \Delta\text{SM}$).
   - When hardening `prompts/<tool>_prompt.md`, the Orchestrator must add **generalizable architectural/language rules** (e.g., *"Unwrap Spring `ResponseEntity<T>` to `T`"*, *"Resolve `@FeignClient(name = ...)` to the matching service directory"*), **NEVER** system-specific hardcoded answers (e.g., do not write *"In MS001, OwnerResource calls Visits"*).

---

## 3. Tool-Specific Execution Instructions

### Option A: `antigravity-cli` (Gemini Flash 3.8)
- **Via Subagents inside Antigravity**:
  Invoke a fresh `self` subagent per system with the prompt template in `prompts/antigravity_prompt.md`, substituting:
  - `{{SYSTEM_ID}}` $\to$ e.g. `MS001`
  - `{{CODEBASE_PATH}}` $\to$ e.g. `codebases/microservices/MS001_spring-petclinic-microservices`
  - `{{PARTITION_PATH}}` $\to$ e.g. `outputs/MS001/output.json`
  - `{{OUTPUT_PATH}}` $\to$ e.g. `benchmarks/calibration_runs/antigravity_cli/v1/MS001.json`

### Option B: `claude-code` (Claude Sonnet 5.5)
- **Via Fresh CLI Session per System**:
  ```bash
  claude -p "Read prompts/claude_code_prompt.md and execute the extraction for SYSTEM_ID=MS001, CODEBASE_PATH=codebases/microservices/MS001_spring-petclinic-microservices, PARTITION_PATH=outputs/MS001/output.json, writing the result to benchmarks/calibration_runs/claude_code/v1/MS001.json"
  ```
- **Via Subagents inside Claude Code**:
  Use the `Task` tool to launch one isolated subagent per `MSxxx` system with the parameters above.

### Option C: `codex` (Codex Sol 6.1)
- **Via Fresh CLI Session per System**:
  ```bash
  codex exec "Read prompts/codex_prompt.md and execute the extraction for SYSTEM_ID=MS001, CODEBASE_PATH=codebases/microservices/MS001_spring-petclinic-microservices, PARTITION_PATH=outputs/MS001/output.json, writing the result to benchmarks/calibration_runs/codex/v1/MS001.json"
  ```

---

## 4. Running Validation & Interpreting Scores

### Validate a Single System
```bash
uv run python scripts/validate_extraction.py \
  --system MS001 \
  --pred benchmarks/calibration_runs/antigravity_cli/v1/MS001.json
```

### Validate an Entire Tool Iteration Across All Curated Ground-Truth Systems
```bash
uv run python scripts/validate_extraction.py \
  --pred-dir benchmarks/calibration_runs/antigravity_cli/v1 \
  --report-out benchmarks/calibration_runs/antigravity_cli/v1/validation_report.md
```

### Target Validity Thresholds Before Full-Corpus Rollout
A tool + prompt pair is ready for full-corpus extraction (~98 systems) when across the 20 verified ground-truth systems:
1. **Schema & Partition Validity**: `100%` of generated JSON files pass `validate_agent_extraction_schema()` with zero unknown services or hallucinated class names.
2. **Exposed Interface Identification**: Macro F1 $\ge 0.85$ on `(service, class_name, method_name)`.
3. **Inter-Service Call Identification**: Macro F1 $\ge 0.85$ on `(src_service, dst_service, dst_interface_id)` and `(src_class, dst_class)`.
4. **Downstream Metric Drift**: Mean Absolute Error (MAE) $\le 0.05$ on `CHD`, `CHM`, `SM` and $\le 0.5$ interfaces on `IFN`.

---

## 5. Full-Corpus Production Extraction (Phase 3)

Once the winning tool and prompt version are selected:
1. Run the winning prompt on every microservice system `MSxxx`, saving outputs to `outputs/<MS_ID>/agent_extraction.json`.
2. Re-evaluate all 5 metrics across all systems:
   ```bash
   uv run python scripts/batch_eval.py
   ```
3. Regenerate all 5 analytical reports and figures:
   ```bash
   for m in ned chd chm ifn sm; do uv run python analysis/${m}.py; done
   ```
