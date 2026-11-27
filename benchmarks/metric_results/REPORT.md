# Metrics from the `claude-code` corpus extractions

NED, CHD, CHM, IFN and SM for **89 of the 90 systems** that have services in the manifest. These are **provisional**: read [Limitations](#limitations) before comparing systems.

## How to reproduce

```bash
uv run python scripts/run_corpus_eval.py
```

- Input: the `v4.2` extraction if it exists, otherwise `v4.0` (`benchmarks/corpus_runs/claude_code/`).
- Output: `claude_code/summary.csv` and, per system, `output.json` (service-to-class partition) and five `*_score.json` files.
- Service source code is read from the pinned submodules. NED uses only the code, CHD, CHM and IFN use the extraction, and SM uses both (calls inside a service from code, calls between services from the extraction).
- Two consecutive runs produced identical files.

**Not computed:** MS076 (`bmo`, Perl). No classes were detected, so it has no partition.

## Summary

Direction: CHD, CHM and SM higher is better; IFN lower is better; NED as implemented is the share of services with an extreme size, so lower is better.

**74 systems with two or more services** (use these for decomposition comparisons):

| Metric | Mean | Median | Min | Max |
| :--- | ---: | ---: | ---: | ---: |
| NED (fixed 5–20) | 0.709 | 0.750 | 0.000 | 1.000 |
| NED (relative) | 0.448 | 0.420 | 0.000 | 1.000 |
| CHD | 0.572 | 0.565 | 0.093 | 1.000 |
| CHM | 0.572 | 0.600 | 0.031 | 1.000 |
| IFN | 3.443 | 1.038 | 0.000 | 65.167 |
| SM | 0.043 | 0.034 | -0.130 | 0.226 |

The other 15 systems have one service. IFN is 0 and relative NED is 0 for all of them by construction.

## Limitations

### 1. CHD and CHM are inflated by a default score

A service with fewer than two interfaces scores **1.0**. This applies to 246 of 582 scored services, in 62 systems. Averaging only services with two or more interfaces (83 systems have at least one):

| Metric | As computed | Without default services | Systems that move by more than 0.1 |
| :--- | ---: | ---: | ---: |
| CHD | 0.471 | 0.246 | 52 |
| CHM | 0.507 | 0.278 | 51 |

For example, MS069 has no interfaces at all and scores CHD 1.0 and CHM 1.0. The committed scores keep the current definition; whether to change it is an open decision.

### 2. IFN of 0 can mean no calls were recorded

18 multi-service systems have no recorded inter-service call, so IFN is 0, the best value: MS009, MS011, MS017, MS018, MS024, MS028, MS059, MS068, MS069, MS073, MS078, MS079, MS080, MS084, MS089, MS096, MS097, MS110. This has not been checked system by system.

### 3. SM depends on static analysis that finds nothing in some systems

No call inside a service was found for MS017, MS043, MS045, MS060, MS074, MS088, MS098, MS104 and MS108 (Ruby, Go, TypeScript, Python, PHP, Node.js). Their SM reflects only calls between services, or is 0.

### 4. Extraction runs are not consistent

Different runs read the prompt differently (see PR #7). On MS055, the one disputed system whose v4.0 and v4.2 files have the same service keys:

| MS055 | v4.0 | v4.2 |
| :--- | ---: | ---: |
| CHD | 0.208 | 0.105 |
| CHM | 0.083 | 0.184 |

MS029, MS067, MS075 and MS077 also differ between runs and should be treated the same way.

### 5. Some services are not scored

Services with no detected classes are left out of the partition: `media-frontend` (MS042) and `nginx-web-server` (MS044). In MS044, 9 recorded calls involve the missing service. Class detection has not been audited for the other systems, and NED depends on it directly.

### 6. The README describes NED differently

`README.md` gives a class-weighted formula and says scores near 1.0 are good. `src/fyp_cdq/metrics/ned.py` counts services, and lower is better. The NED table in the README does not match these results.

## Check against ground truth

The same code was run on the 15 ground-truth files marked `verified`. These are calibration systems the prompt was tuned on, so agreement on the rest of the corpus is likely to be lower. SM shares its static edges between both sides, so only its calls between services are really compared.

| Metric | Mean absolute difference | Largest difference | Systems within 0.01 |
| :--- | ---: | :--- | ---: |
| CHD | 0.007 | 0.051 (MS047) | 13 / 15 |
| CHM | 0.011 | 0.088 (MS070) | 11 / 15 |
| IFN | 0.008 | 0.118 (MS070) | 14 / 15 |
| SM | <0.001 | <0.001 | 15 / 15 |

The five files marked `pending_manual_review` (MS007, MS011, MS015, MS030, MS043) were excluded. They record no inter-service calls and some differ widely from the extractions, so they need review.

## All results

`Thin` is the number of services with fewer than two interfaces (see limitation 1).

| System | Name | Services | Thin | Interfaces | Calls | NED | NED rel. | CHD | CHM | IFN | SM |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MS001 | spring-petclinic-microservices | 5 | 3 | 14 | 6 | 0.000 | 0.000 | 0.678 | 0.643 | 1.200 | 0.096 |
| MS004 | ftgo-application | 9 | 1 | 56 | 28 | 0.556 | 0.222 | 0.356 | 0.265 | 2.778 | 0.075 |
| MS007 | coolstore-microservice | 8 | 4 | 20 | 11 | 0.286 | 0.286 | 0.695 | 0.693 | 1.250 | 0.134 |
| MS008 | cargotracker | 1 | 0 | 8 | 0 | 1.000 | 0.000 | 0.266 | 0.554 | 0.000 | 0.028 |
| MS009 | unishop-monolith-to-microservices | 4 | 2 | 10 | 0 | 0.500 | 0.750 | 0.777 | 0.708 | 0.000 | 0.086 |
| MS010 | amazon-ecs-java-microservices | 5 | 3 | 7 | 1 | 0.800 | 0.200 | 0.718 | 0.600 | 0.200 | 0.083 |
| MS011 | monolith-vs-microservices | 2 | 2 | 2 | 0 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.111 |
| MS015 | eShop | 11 | 5 | 52 | 50 | 0.545 | 0.818 | 0.637 | 0.582 | 3.182 | 0.079 |
| MS016 | pitstop | 9 | 6 | 18 | 33 | 0.667 | 0.667 | 0.751 | 0.715 | 1.889 | 0.152 |
| MS017 | monolith-to-microservices | 3 | 1 | 4 | 0 | 1.000 | 0.000 | 0.833 | 0.333 | 0.000 | 0.000 |
| MS018 | benchmarking-monolith-to-microservices | 2 | 1 | 3 | 0 | 1.000 | 0.000 | 0.650 | 0.833 | 0.000 | 0.062 |
| MS019 | train-ticket | 45 | 7 | 234 | 158 | 0.111 | 0.156 | 0.447 | 0.684 | 2.222 | 0.105 |
| MS020 | piggymetrics | 4 | 0 | 11 | 3 | 0.250 | 0.000 | 0.349 | 0.250 | 0.750 | 0.096 |
| MS021 | TeaStore | 6 | 1 | 58 | 62 | 0.333 | 0.333 | 0.269 | 0.482 | 4.500 | 0.076 |
| MS022 | mall-swarm | 6 | 2 | 246 | 7 | 0.333 | 1.000 | 0.413 | 0.452 | 0.833 | 0.053 |
| MS023 | microservices-platform | 6 | 2 | 83 | 10 | 0.667 | 0.667 | 0.439 | 0.497 | 1.000 | 0.020 |
| MS024 | jeecg-boot | 2 | 1 | 647 | 0 | 1.000 | 1.000 | 0.532 | 0.587 | 0.000 | 0.004 |
| MS025 | xxl-job | 3 | 0 | 57 | 8 | 0.667 | 0.667 | 0.289 | 0.415 | 2.667 | 0.044 |
| MS026 | spinnaker | 13 | 3 | 762 | 709 | 1.000 | 0.769 | 0.301 | 0.411 | 25.154 | 0.007 |
| MS027 | pravega | 2 | 0 | 91 | 21 | 1.000 | 0.000 | 0.093 | 0.265 | 9.500 | 0.008 |
| MS028 | besu | 39 | 36 | 178 | 0 | 0.632 | 0.763 | 0.949 | 0.931 | 0.000 | 0.089 |
| MS029 | kapua | 6 | 1 | 560 | 19 | 0.833 | 0.667 | 0.457 | 0.543 | 1.833 | 0.038 |
| MS030 | sample-spring-microservices | 2 | 0 | 11 | 1 | 0.000 | 0.000 | 0.302 | 0.217 | 0.500 | 0.090 |
| MS031 | sample-spring-microservices-new | 3 | 0 | 16 | 4 | 0.000 | 0.000 | 0.383 | 0.411 | 1.333 | 0.203 |
| MS032 | event-sourcing-microservices-example | 3 | 0 | 11 | 5 | 0.000 | 0.000 | 0.296 | 0.472 | 1.000 | 0.098 |
| MS033 | java-microservice | 5 | 1 | 23 | 7 | 0.400 | 0.400 | 0.380 | 0.370 | 1.200 | 0.082 |
| MS034 | microservices-sample | 3 | 1 | 4 | 2 | 0.333 | 0.333 | 0.333 | 0.333 | 0.667 | 0.077 |
| MS035 | micro-company | 10 | 5 | 30 | 15 | 0.500 | 0.000 | 0.695 | 0.681 | 1.000 | 0.107 |
| MS036 | java-microservices-examples | 13 | 2 | 131 | 2 | 0.500 | 0.700 | 0.283 | 0.356 | 0.154 | 0.062 |
| MS037 | abixen-platform | 5 | 2 | 133 | 18 | 0.600 | 0.800 | 0.491 | 0.466 | 1.400 | 0.048 |
| MS039 | microservices-demo | 11 | 6 | 27 | 21 | 0.727 | 0.364 | 0.644 | 0.611 | 1.364 | 0.068 |
| MS040 | opentelemetry-demo | 18 | 11 | 46 | 49 | 0.556 | 0.722 | 0.701 | 0.691 | 1.556 | 0.099 |
| MS042 | DeathStarBench-socialNetwork | 13 | 6 | 45 | 36 | 0.923 | 0.077 | 0.728 | 0.689 | 1.846 | 0.172 |
| MS043 | DeathStarBench-hotelReservation | 10 | 7 | 20 | 18 | 0.900 | 0.100 | 0.838 | 0.983 | 1.200 | -0.059 |
| MS044 | DeathStarBench-mediaMicroservices | 13 | 4 | 35 | 25 | 1.000 | 0.000 | 0.688 | 0.649 | 1.077 | 0.226 |
| MS045 | DeathStarBench-swarm-ecommerce | 21 | 12 | 55 | 38 | 0.833 | 0.167 | 0.800 | 0.709 | 1.714 | -0.038 |
| MS047 | robot-shop | 8 | 3 | 28 | 7 | 0.667 | 0.667 | 0.467 | 0.644 | 0.750 | 0.009 |
| MS048 | jaeger | 6 | 4 | 44 | 6 | 1.000 | 1.000 | 0.742 | 0.677 | 1.000 | 0.001 |
| MS049 | thanos | 3 | 2 | 64 | 1 | 1.000 | 1.000 | 0.721 | 0.701 | 0.333 | 0.001 |
| MS050 | argo-cd | 8 | 5 | 138 | 37 | 0.750 | 0.625 | 0.702 | 0.660 | 2.875 | 0.049 |
| MS051 | kubevirt | 7 | 0 | 185 | 74 | 0.714 | 0.571 | 0.261 | 0.346 | 10.429 | 0.001 |
| MS052 | consul | 22 | 20 | 289 | 179 | 0.762 | 0.952 | 0.921 | 0.913 | 5.864 | 0.024 |
| MS053 | faas | 1 | 0 | 25 | 0 | 1.000 | 0.000 | 0.119 | 0.520 | 0.000 | 0.008 |
| MS055 | saleor | 1 | 0 | 1356 | 0 | 1.000 | 0.000 | 0.105 | 0.184 | 0.000 | 0.000 |
| MS056 | example-voting-app | 3 | 3 | 3 | 1 | 1.000 | 0.000 | 1.000 | 1.000 | 0.333 | -0.130 |
| MS057 | rasa_nlu | 1 | 0 | 37 | 0 | 1.000 | 0.000 | 0.055 | 0.292 | 0.000 | 0.002 |
| MS059 | examples | 7 | 6 | 4 | 0 | 0.714 | 0.714 | 0.919 | 0.921 | 0.000 | 0.050 |
| MS060 | agile-lorawan-support | 1 | 1 | 1 | 0 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| MS061 | marathon | 1 | 0 | 55 | 0 | 1.000 | 0.000 | 0.053 | 0.187 | 0.000 | 0.004 |
| MS062 | front-end | 1 | 0 | 26 | 0 | 0.000 | 0.000 | 0.145 | 0.431 | 0.000 | 0.012 |
| MS063 | kudu | 2 | 0 | 100 | 23 | 1.000 | 0.000 | 0.250 | 0.031 | 6.000 | 0.005 |
| MS064 | hmda-platform | 17 | 7 | 196 | 8 | 0.588 | 0.882 | 0.770 | 0.680 | 0.294 | 0.105 |
| MS066 | milvus | 8 | 0 | 484 | 317 | 1.000 | 0.500 | 0.248 | 0.070 | 26.250 | 0.001 |
| MS067 | mailcow-dockerized | 1 | 0 | 72 | 0 | 1.000 | 0.000 | 0.112 | 0.241 | 0.000 | 0.007 |
| MS068 | crates.io | 2 | 1 | 71 | 0 | 1.000 | 1.000 | 0.558 | 0.551 | 0.000 | 0.001 |
| MS069 | openstates-scrapers | 2 | 2 | 0 | 0 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.003 |
| MS070 | boulder | 17 | 9 | 137 | 87 | 0.294 | 0.412 | 0.640 | 0.566 | 4.294 | 0.018 |
| MS071 | cortex | 13 | 2 | 96 | 27 | 0.769 | 0.462 | 0.372 | 0.344 | 2.000 | 0.015 |
| MS072 | growi | 4 | 1 | 343 | 20 | 1.000 | 1.000 | 0.281 | 0.519 | 3.750 | 0.018 |
| MS073 | tasking-manager | 2 | 1 | 198 | 0 | 1.000 | 0.000 | 0.526 | 0.782 | 0.000 | 0.001 |
| MS074 | hyrax | 1 | 0 | 147 | 0 | 1.000 | 0.000 | 0.060 | 0.338 | 0.000 | 0.000 |
| MS075 | blockscout | 3 | 0 | 475 | 31 | 1.000 | 0.333 | 0.526 | 0.600 | 3.000 | -0.000 |
| MS076 | bmo | - | 0 | 352 | 0 | - | - | - | - | - | - |
| MS077 | Mayan-EDMS | 1 | 0 | 1105 | 0 | 1.000 | 0.000 | 0.239 | 0.390 | 0.000 | 0.000 |
| MS078 | clean-architecture-manga | 3 | 2 | 8 | 0 | 1.000 | 0.333 | 0.758 | 0.714 | 0.000 | 0.036 |
| MS079 | eShopModernizing | 7 | 4 | 30 | 0 | 1.000 | 0.429 | 0.667 | 0.645 | 0.000 | 0.032 |
| MS080 | superdesk | 2 | 2 | 0 | 0 | 0.500 | 1.000 | 1.000 | 1.000 | 0.000 | 0.016 |
| MS081 | coolstore-microservices | 4 | 1 | 20 | 9 | 0.750 | 0.750 | 0.464 | 0.440 | 2.250 | -0.045 |
| MS082 | taskcluster | 12 | 1 | 168 | 63 | 0.300 | 0.300 | 0.307 | 0.661 | 2.250 | 0.130 |
| MS083 | reportportal | 6 | 2 | 367 | 24 | 1.000 | 1.000 | 0.442 | 0.516 | 3.167 | 0.011 |
| MS084 | micro-frontends | 4 | 2 | 7 | 0 | 0.750 | 0.500 | 0.547 | 0.675 | 0.000 | 0.026 |
| MS086 | cds | 6 | 3 | 839 | 407 | 0.833 | 0.833 | 0.638 | 0.623 | 65.167 | 0.003 |
| MS088 | Markus | 1 | 0 | 412 | 0 | 1.000 | 0.000 | 0.025 | 0.462 | 0.000 | 0.000 |
| MS089 | Farmbot-Web-App | 2 | 1 | 172 | 0 | 1.000 | 1.000 | 0.529 | 0.602 | 0.000 | 0.001 |
| MS091 | codalab-competitions | 1 | 0 | 192 | 0 | 1.000 | 0.000 | 0.123 | 0.360 | 0.000 | 0.002 |
| MS095 | waypoint | 4 | 2 | 146 | 223 | 1.000 | 0.750 | 0.579 | 0.608 | 24.750 | 0.001 |
| MS096 | Veniqa | 4 | 2 | 77 | 0 | 0.750 | 0.500 | 0.529 | 0.599 | 0.000 | 0.014 |
| MS097 | FightPandemics | 3 | 2 | 67 | 0 | 0.667 | 1.000 | 0.693 | 0.743 | 0.000 | 0.019 |
| MS098 | ultimate-backend | 9 | 0 | 128 | 56 | 0.778 | 0.333 | 0.375 | 0.067 | 5.667 | -0.000 |
| MS100 | rucio | 1 | 0 | 222 | 0 | 1.000 | 0.000 | 0.234 | 0.231 | 0.000 | 0.001 |
| MS101 | spryker-demoshop | 2 | 0 | 66 | 1 | 1.000 | 0.000 | 0.282 | 0.260 | 0.500 | 0.004 |
| MS102 | Practical.CleanArchitecture | 8 | 0 | 64 | 9 | 1.000 | 0.625 | 0.281 | 0.217 | 0.750 | 0.060 |
| MS103 | run-aspnetcore-microservices | 5 | 1 | 21 | 15 | 1.000 | 0.400 | 0.576 | 0.278 | 1.600 | 0.066 |
| MS104 | web | 1 | 0 | 32 | 0 | 1.000 | 0.000 | 0.100 | 0.523 | 0.000 | 0.000 |
| MS105 | go-micro-services | 5 | 5 | 5 | 6 | 1.000 | 0.000 | 1.000 | 1.000 | 0.800 | -0.069 |
| MS106 | email-microapi | 13 | 4 | 30 | 4 | 0.615 | 0.077 | 0.479 | 0.446 | 0.077 | 0.038 |
| MS107 | lagoon | 9 | 5 | 359 | 103 | 0.444 | 0.556 | 0.666 | 0.708 | 5.333 | 0.035 |
| MS108 | php-ddd-example | 3 | 1 | 6 | 1 | 0.333 | 0.000 | 0.822 | 0.389 | 0.333 | -0.002 |
| MS110 | flagr | 2 | 1 | 40 | 0 | 1.000 | 0.000 | 0.573 | 0.579 | 0.000 | 0.007 |
| MS112 | rasa-sdk | 1 | 0 | 6 | 0 | 1.000 | 0.000 | 0.141 | 0.033 | 0.000 | 0.012 |
