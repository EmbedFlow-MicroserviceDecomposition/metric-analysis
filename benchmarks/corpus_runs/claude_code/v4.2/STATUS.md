# Re-extraction status (`claude-code` prompt v4.2)

Systems whose manifest, prompt rules or checkout changed after the v4.0 run (see `../v4/RERUN.md`). One Sonnet subagent per system, no ground-truth access.

All files pass schema, manifest-key, id, destination and evidence-line checks. These checks do not measure accuracy.

## Current corpus

For each system with services in the manifest, use the `v4.2` file if it exists, otherwise the `v4.0` file. Ignore `v4.0` files for systems that now have no services.

**90 systems** (41 from v4.2, 49 from v4.0): 13,223 interfaces, 3,106 calls.

## Ground-truth check

MS106 is the only re-run system with ground truth: interface F1 0.88 (v4.0) to 1.00, class-edge and call F1 1.00 in both, signature F1 0.54 to 0.45.

## Re-extracted

| System | Services | v4.0 interfaces / calls | v4.2 interfaces / calls | Note |
| :--- | ---: | ---: | ---: | :--- |
| MS019 | 45 | 225 / 158 | 234 / 158 |  |
| MS024 | 2 | 0 / 0 | 647 / 0 | controllers now inside the listed folder |
| MS027 | 2 | 0 / 0 | 91 / 21 | three calls come from `SegmentHelper` methods that nothing in `controller` invokes |
| MS029 | 6 | 306 / 18 | 560 / 19 | includes 254 console GWT-RPC methods; v4.0 listed none: needs review |
| MS033 | 5 | 13 / 1 | 23 / 7 |  |
| MS036 | 13 | 130 / 0 | 131 / 2 | `CarRepository` declares no methods; only inherited `findAll` recorded |
| MS040 | 18 | 36 / 35 | 46 / 49 | includes five calls from the React Native app; MCP-mode calls omitted |
| MS042 | 14 | 30 / 0 | 45 / 36 |  |
| MS044 | 14 | 0 / 0 | 35 / 25 |  |
| MS045 | 21 | 156 / 0 | 55 / 38 | lists the `daprApps_v1` apps (Dapr social network, video pipeline, video sharing); the name "swarm-ecommerce" does not describe them |
| MS050 | 8 | 141 / 211 | 138 / 37 | fewer calls than v4.0 because the CLI is no longer a service; applicationset-to-reposerver generator edges omitted |
| MS051 | 7 | 192 / 59 | 185 / 74 |  |
| MS055 | 1 | 428 / 0 | 1356 / 0 | run-to-run difference: this run lists every GraphQL field resolver, v4.0 listed only queries and mutations |
| MS060 | 1 | 1 / 0 | 1 / 0 |  |
| MS061 | 1 | 55 / 0 | 55 / 0 |  |
| MS062 | 1 | 26 / 0 | 26 / 0 |  |
| MS063 | 2 | 66 / 26 | 100 / 23 |  |
| MS064 | 17 | 0 / 0 | 196 / 8 | one agent command was blocked by a safety check; nothing was removed |
| MS066 | 8 | 621 / 132 | 484 / 317 | proxy REST and mixcoord handlers lie outside service folders; some in-process coordinator calls counted |
| MS067 | 1 | 33 / 1 | 72 / 0 | run-to-run difference: 72 interfaces vs 33 on the same folder; the one v4.0 call came from a folder no longer listed |
| MS068 | 2 | 0 / 0 | 71 / 0 |  |
| MS071 | 13 | 109 / 0 | 96 / 27 |  |
| MS074 | 1 | 142 / 0 | 147 / 0 |  |
| MS075 | 3 | 245 / 0 | 475 / 31 | run-to-run difference: web routes nearly doubled (v4.0 excluded optional configurations): needs review |
| MS076 | 1 | 0 / 0 | 352 / 0 | verbs and CGI parameter types approximate; agent ran one `git status` outside its allowed reads |
| MS077 | 1 | 830 / 0 | 1105 / 0 | much higher count than v4.0 (HTML verbs inferred); needs review |
| MS081 | 4 | 13 / 6 | 20 / 9 |  |
| MS084 | 4 | 7 / 0 | 7 / 0 |  |
| MS088 | 1 | 412 / 0 | 412 / 0 |  |
| MS089 | 2 | 0 / 0 | 172 / 0 |  |
| MS091 | 1 | 189 / 0 | 192 / 0 |  |
| MS095 | 4 | 146 / 225 | 146 / 223 |  |
| MS097 | 3 | 66 / 0 | 67 / 0 |  |
| MS100 | 1 | 224 / 0 | 222 / 0 |  |
| MS101 | 2 | 59 / 0 | 66 / 1 |  |
| MS102 | 8 | 57 / 0 | 64 / 9 |  |
| MS103 | 5 | 21 / 13 | 21 / 15 |  |
| MS105 | 5 | 5 / 0 | 5 / 6 |  |
| MS106 | 13 | 24 / 4 | 30 / 4 |  |
| MS108 | 3 | - | 6 / 1 | one shared-`src` consumer recorded under mooc-backend |
| MS110 | 2 | 39 / 0 | 40 / 0 | includes `/api/v1/health` although only browser code calls it (should be excluded) |
