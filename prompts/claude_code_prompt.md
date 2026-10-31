# Microservice Interface & Inter-Service Call Extraction Prompt (`claude-code` — Claude Sonnet 5.5)

## Input Parameters
- `SYSTEM_ID`: `{{SYSTEM_ID}}`
- `CODEBASE_PATH`: `{{CODEBASE_PATH}}`
- `PARTITION_PATH`: `{{PARTITION_PATH}}`
- `OUTPUT_PATH`: `{{OUTPUT_PATH}}`
- `extractor_tool`: `"claude-code"`
- `prompt_version`: `"v1.0"`

---

## 1. Isolation & Ground-Truth Firewall
- **Permitted paths**: `{{CODEBASE_PATH}}`, `{{PARTITION_PATH}}`, `prompts/schema.json`.
- **Prohibited paths**: Do NOT read or search `benchmarks/ground_truth/`, `codebases/monoliths/`, `benchmarks/calibration_runs/`, or `outputs/{{SYSTEM_ID}}/*_score.json`.
- **Canonical Name Constraint**: All microservice IDs and class names in your output MUST be exact string matches from `{{PARTITION_PATH}}`. Never invent class names or service IDs.

---

## 2. Extraction Specification

### A. Exposed Interfaces (`microservices[service_id].exposed_interfaces`)
Inspect the classes listed for each microservice in `{{PARTITION_PATH}}` and extract all operations exposed across the service boundary:
1. **Include**:
   - **REST Controllers / HTTP Handlers**: Spring `@RestController`/`@Controller` endpoint methods (`@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`, `@RequestMapping`), JAX-RS `@Path` resource methods (`@GET`, `@POST`, etc.), ASP.NET `[ApiController]` action methods & Minimal API routes, Go HTTP handler functions/methods, Python FastAPI/Flask/Django view/route handlers, Node.js/NestJS/Express route & controller handlers.
   - **gRPC / RPC Operations**: Methods implementing `.proto` service interfaces or RPC handlers.
   - **Asynchronous Event / Command Listeners**: Methods consuming cross-service messages (`@KafkaListener`, `@RabbitListener`, Eventuate Tram command/event handlers, RabbitMQ `IIntegrationEventHandler`, NATS/AMQP consumers).
2. **Exclude**:
   - Internal domain entities, DTOs/VOs, database repositories/DAOs, Spring `@Configuration`/`@SpringBootApplication` classes, getters/setters, constructors, and private/internal helper methods.
   - Pure infrastructure services (e.g., Eureka discovery server, Spring Cloud Config server, Admin server) that declare no custom application endpoints should have `"exposed_interfaces": []`.
3. **Signature Normalization**:
   - Unwrap generic transport/reactive/async containers in `return_type` and `param_types`:
     - `ResponseEntity<T>`, `Optional<T>`, `Mono<T>`, `CompletableFuture<T>`, `Task<T>`, `ActionResult<T>`, `Task<ActionResult<T>>` $\to$ `T`.
     - `Flux<T>`, `Collection<T>`, `IEnumerable<T>`, `Set<T>`, `T[]` $\to$ `List<T>`.
     - Empty/void wrappers (`ResponseEntity<Void>`, `Mono<Void>`, `Task`, `IActionResult` without payload) $\to$ `"void"`.
   - Strip framework context arguments from `param_types` (`HttpServletRequest`, `HttpServletResponse`, `BindingResult`, `Pageable`, `Principal`, `CancellationToken`, `ServerCallContext`, `context.Context`, `http.ResponseWriter`, `*http.Request`, `*gin.Context`).
   - Keep simple type names (e.g., `"OwnerDetails"`, `"PetRequest"`, `"int"`, `"String"`, `"List<Visit>"`).
   - Set `"id"` to `"<SimpleClassName>.<method_name>"`.

### B. Inter-Service Call Edges (`inter_service_calls`)
Trace all cross-service calls where a class in `src_service` calls an exposed interface in `dst_service` (`src_service != dst_service`):
1. **Synchronous HTTP / REST**:
   - Inspect `WebClient`, `RestTemplate`, `@FeignClient`, `@HttpExchange`, `HttpClient`, `axios`, `fetch`, `requests`, `http.Client`.
   - Cross-reference URL templates, service discovery names (e.g., `http://visits-service/...`), and config files (`application.yml`, `appsettings.json`, `docker-compose.yml`) to resolve `dst_service`, `dst_class`, and `dst_interface_id`.
2. **gRPC / RPC**:
   - Match gRPC client stub calls in `src_class` (`src_service`) to the target gRPC server implementation class `dst_class` and method `dst_interface_id` in `dst_service`.
3. **Asynchronous Messaging**:
   - Match message/event/command producers in `src_class` (`src_service`) to the subscribing handler class `dst_class` and method `dst_interface_id` in `dst_service`.

---

## 3. Output Verification & Save
Save the JSON output to `{{OUTPUT_PATH}}` matching `prompts/schema.json`. Verify before finishing:
1. All keys in `microservices` match `{{PARTITION_PATH}}` 1-to-1.
2. Every `class_name`, `src_class`, and `dst_class` exists in `{{PARTITION_PATH}}` under its respective microservice.
3. Every `dst_interface_id` exists in `microservices[dst_service].exposed_interfaces`.
4. `src_service != dst_service` for all entries in `inter_service_calls`.
