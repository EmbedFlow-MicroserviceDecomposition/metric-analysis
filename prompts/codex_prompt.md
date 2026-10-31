# Microservice Interface & Inter-Service Call Extraction Prompt (`codex` — Codex Sol 6.1)

## Target Configuration
- `SYSTEM_ID`: `{{SYSTEM_ID}}`
- `CODEBASE_PATH`: `{{CODEBASE_PATH}}`
- `PARTITION_PATH`: `{{PARTITION_PATH}}`
- `OUTPUT_PATH`: `{{OUTPUT_PATH}}`
- `extractor_tool`: `"codex"`
- `prompt_version`: `"v1.0"`

---

## 1. Hard Constraints
1. **Read Scope**: Only read `{{PARTITION_PATH}}`, `prompts/schema.json`, and files inside `{{CODEBASE_PATH}}`. Never access `benchmarks/ground_truth/`, `codebases/monoliths/`, or `benchmarks/calibration_runs/`.
2. **Exact Canonical Identifiers**:
   - Every key in `"microservices"`, `"src_service"`, and `"dst_service"` MUST be an exact key from the `"microservices"` map in `{{PARTITION_PATH}}`.
   - Every `"class_name"`, `"src_class"`, and `"dst_class"` MUST be an exact string from that service's class list in `{{PARTITION_PATH}}`.

---

## 2. Extraction Rules

### Part 1: `microservices[service_id].exposed_interfaces`
For each microservice in `{{PARTITION_PATH}}`, inspect its source files in `{{CODEBASE_PATH}}` and extract all operations exposed to external callers:
- **Included Operations**:
  - HTTP/REST controller & router handlers (Spring `@GetMapping`/`@PostMapping`/`@PutMapping`/`@DeleteMapping`/`@RequestMapping`, JAX-RS `@Path`/`@GET`/`@POST`, ASP.NET `[HttpGet]`/`[HttpPost]`/`MapGet`, Go HTTP handlers, Python FastAPI/Flask/Django routes, JS/TS Express/NestJS routes).
  - gRPC / RPC service implementation methods.
  - Cross-service message/event/command listener methods (`@KafkaListener`, `@RabbitListener`, Eventuate Tram handlers, RabbitMQ integration event handlers).
- **Excluded Methods**:
  - Entities, DTOs, repositories/DAOs, configuration classes, `main()` methods, constructors, getters/setters, and internal private/helper methods.
- **Type Formatting**:
  - Unwrap `ResponseEntity<T>`, `Optional<T>`, `Mono<T>`, `CompletableFuture<T>`, `Task<T>`, `ActionResult<T>` to `T`.
  - Normalize collection types (`Flux<T>`, `IEnumerable<T>`, `Set<T>`, `T[]`) to `List<T>`.
  - Remove framework context parameters (`HttpServletRequest`, `HttpServletResponse`, `BindingResult`, `Pageable`, `Principal`, `CancellationToken`, `ServerCallContext`, `context.Context`, `http.ResponseWriter`, `*http.Request`, `*gin.Context`).
  - Set `"id": "<SimpleClassName>.<method_name>"`.

### Part 2: `inter_service_calls`
Find all directed cross-service invocations (`src_service != dst_service`):
- Trace HTTP client calls (`WebClient`, `RestTemplate`, `@FeignClient`, `@HttpExchange`, `HttpClient`, `axios`, `fetch`, `requests`), gRPC client stub calls, and message/event producer calls from `src_class` (in `src_service`) to `dst_class` and `dst_interface_id` (in `dst_service`).
- Ensure every `"dst_interface_id"` matches an `"id"` declared in `microservices[dst_service].exposed_interfaces`.

---

## 3. Write & Validate Output
Write the JSON document to `{{OUTPUT_PATH}}` following `prompts/schema.json`.
