# Full-corpus extraction status (`claude-code` prompt v4.0)

Prompt: `prompts/claude_code_prompt.md` (v4.0). Extractor: Sonnet subagents, one fresh context per system, no ground-truth access.

- **Extracted:** 61 systems (below)
- **Pending:** 40 systems (codebase not downloaded: 38 repos failed to clone; MS024 partial checkout; MS083 has empty nested submodules)
- **No services in manifest (skipped):** 6 systems: MS002, MS058, MS065, MS099, MS108, MS111

Outputs live here (not in the gitignored `outputs/`). To evaluate with the repo's metrics, copy each file to `outputs/<MS_ID>/agent_extraction.json`.

## Extracted

| System | Services | Interfaces | Calls | Note |
| :--- | ---: | ---: | ---: | :--- |
| MS001 | 5 | 14 | 6 |  |
| MS004 | 9 | 56 | 28 |  |
| MS009 | 4 | 10 | 0 |  |
| MS010 | 5 | 7 | 1 |  |
| MS011 | 2 | 2 | 0 |  |
| MS015 | 11 | 52 | 50 |  |
| MS016 | 9 | 18 | 33 |  |
| MS017 | 3 | 4 | 0 |  |
| MS019 | 41 | 225 | 158 |  |
| MS020 | 4 | 11 | 3 |  |
| MS021 | 6 | 58 | 62 |  |
| MS023 | 6 | 83 | 10 |  |
| MS026 | 13 | 762 | 709 |  |
| MS028 | 39 | 178 | 0 |  |
| MS029 | 14 | 306 | 18 |  |
| MS031 | 3 | 16 | 4 |  |
| MS032 | 3 | 11 | 5 |  |
| MS038 | 46 | 0 | 0 | stream-connector library: no routes, RPC servers or consumers (real zero) |
| MS039 | 11 | 27 | 21 |  |
| MS040 | 13 | 36 | 35 |  |
| MS047 | 8 | 28 | 7 |  |
| MS048 | 6 | 44 | 6 | MCP tools, OTLP proxy and one extension left out (judgment calls) |
| MS049 | 3 | 64 | 1 |  |
| MS050 | 17 | 141 | 211 |  |
| MS051 | 6 | 192 | 59 |  |
| MS052 | 22 | 289 | 179 | 31 calls to enterprise-only or legacy paths left out (no matching route) |
| MS053 | 1 | 25 | 0 |  |
| MS054 | 5 | 0 | 0 | infrastructure only (Dockerfiles, compose, config): no handler code (real zero) |
| MS055 | 1 | 428 | 0 | ~80 Celery tasks excluded as same-service queues (prompt wording gap) |
| MS059 | 7 | 4 | 0 | Kafka Streams topologies and CLI-topic consumers are not captured by the prompt (known gap) |
| MS063 | 4 | 66 | 26 |  |
| MS064 | 2 | 0 | 0 | Helm config plus a shared library only |
| MS066 | 6 | 621 | 132 | manifest 'services' are top-level folders of one Go program; calls are in-process |
| MS067 | 2 | 33 | 1 |  |
| MS068 | 3 | 0 | 0 | manifest lists svelte/crates/packages only; the Rust backend is in `src/` (not a service) |
| MS069 | 2 | 0 | 0 | batch scrapers, no routes or consumers |
| MS070 | 17 | 137 | 87 |  |
| MS071 | 3 | 109 | 0 | manifest 'services' are directories of one Go monolith; no cross-service edges possible |
| MS072 | 4 | 343 | 20 |  |
| MS073 | 2 | 198 | 0 |  |
| MS074 | 2 | 142 | 0 |  |
| MS075 | 3 | 245 | 0 | web router, admin and chain-specific routes excluded as optional configuration |
| MS076 | 1 | 0 | 0 | only a BigQuery-emulator Dockerfile (no application code) |
| MS078 | 3 | 8 | 0 |  |
| MS079 | 7 | 30 | 0 |  |
| MS080 | 2 | 0 | 0 | routes live in external superdesk-core, outside the manifest folders |
| MS082 | 12 | 168 | 63 |  |
| MS086 | 6 | 839 | 407 |  |
| MS087 | 1 | 0 | 0 | only Hugo static assets |
| MS089 | 2 | 0 | 0 | manifest lists a React SPA and static assets only; the Rails API is not a listed service |
| MS092 | 2 | 0 | 0 | tracing library, not a service system |
| MS093 | 1 | 0 | 0 | standalone Kafka demo scripts with CLI-supplied topics (known gap) |
| MS094 | 1 | 0 | 0 | client SDK monorepo, no server code |
| MS098 | 9 | 128 | 56 |  |
| MS100 | 3 | 224 | 0 |  |
| MS101 | 2 | 59 | 0 | backend and storefront are one `src` service |
| MS102 | 3 | 57 | 0 | manifest 'Microservices' folder is one service containing all backends |
| MS106 | 13 | 24 | 4 |  |
| MS107 | 9 | 359 | 103 | some edges inferred from machinery-client function names (library source not in repo) |
| MS110 | 3 | 39 | 0 |  |
| MS112 | 1 | 6 | 0 |  |

## Pending

MS003, MS007, MS008, MS018, MS022, MS024, MS025, MS027, MS030, MS033, MS034, MS035, MS036, MS037, MS041, MS042, MS043, MS044, MS045, MS046, MS056, MS057, MS060, MS061, MS062, MS077, MS081, MS083, MS084, MS085, MS088, MS090, MS091, MS095, MS096, MS097, MS103, MS104, MS105, MS109
