# Full-corpus extraction status (`claude-code` prompt v4.0)

Prompt: `prompts/claude_code_prompt.md` (v4.0). Extractor: Sonnet subagents, one fresh context per system, no ground-truth access.

- **Extracted:** 20 systems (below)
- **Pending:** 81 systems (codebase submodule not downloaded yet, or extraction not run yet)
- **No services in manifest (skipped):** 6 systems: MS002, MS058, MS065, MS099, MS108, MS111

Outputs live here (not in the gitignored `outputs/`). To evaluate with the repo's metrics, copy each file to `outputs/<MS_ID>/agent_extraction.json`.

## Extracted

| System | Services | Interfaces | Calls | Note |
| :--- | ---: | ---: | ---: | :--- |
| MS001 | 5 | 14 | 6 |  |
| MS004 | 9 | 56 | 28 |  |
| MS010 | 5 | 7 | 1 |  |
| MS016 | 9 | 18 | 33 |  |
| MS017 | 3 | 4 | 0 |  |
| MS019 | 41 | 225 | 158 |  |
| MS020 | 4 | 11 | 3 |  |
| MS021 | 6 | 58 | 62 |  |
| MS031 | 3 | 16 | 4 |  |
| MS032 | 3 | 11 | 5 |  |
| MS039 | 11 | 27 | 21 |  |
| MS047 | 8 | 28 | 7 |  |
| MS067 | 2 | 33 | 1 |  |
| MS068 | 3 | 0 | 0 | manifest lists svelte/crates/packages only; the Rust backend is in `src/` (not a service) |
| MS070 | 17 | 137 | 87 |  |
| MS075 | 3 | 245 | 0 |  |
| MS078 | 3 | 8 | 0 |  |
| MS089 | 2 | 0 | 0 | manifest lists a React SPA and static assets only; the Rails API is not a listed service |
| MS098 | 9 | 128 | 56 |  |
| MS106 | 13 | 24 | 4 |  |

## Pending

MS003, MS007, MS008, MS009, MS011, MS015, MS018, MS022, MS023, MS024, MS025, MS026, MS027, MS028, MS029, MS030, MS033, MS034, MS035, MS036, MS037, MS038, MS040, MS041, MS042, MS043, MS044, MS045, MS046, MS048, MS049, MS050, MS051, MS052, MS053, MS054, MS055, MS056, MS057, MS059, MS060, MS061, MS062, MS063, MS064, MS066, MS069, MS071, MS072, MS073, MS074, MS076, MS077, MS079, MS080, MS081, MS082, MS083, MS084, MS085, MS086, MS087, MS088, MS090, MS091, MS092, MS093, MS094, MS095, MS096, MS097, MS100, MS101, MS102, MS103, MS104, MS105, MS107, MS109, MS110, MS112
