# Microservice Interface & Inter-Service Call Extraction Prompt (`claude-code` — Claude Sonnet 5.5)

## Input Parameters
- `SYSTEM_ID`: `{{SYSTEM_ID}}`
- `CODEBASE_PATH`: `{{CODEBASE_PATH}}`
- `MANIFEST_PATH`: `{{MANIFEST_PATH}}` (default: `codebases/microservices/microservices.json`)
- `OUTPUT_PATH`: `{{OUTPUT_PATH}}`
- `extractor_tool`: `"claude-code"`
- `prompt_version`: `"v2.0"`
- `status`: `"pending_manual_review"`

---

## 1. Isolation & Ground-Truth Firewall
- **Permitted paths**: `{{CODEBASE_PATH}}`, `{{MANIFEST_PATH}}` (for `{{SYSTEM_ID}}`), `prompts/schema.json`.
- **Prohibited paths**: Do NOT read, list, or search `benchmarks/` (ground truth, guides, calibration runs), `codebases/monoliths/`, `outputs/`, or other systems' codebases.
- **Canonical Service Constraint**: Every microservice key (`microservices` keys, `src_service`, `dst_service`) MUST match `microservices.json["{{SYSTEM_ID}}"]["services"]` 1-to-1. Never invent service IDs. Include every manifest service, using `"exposed_interfaces": []` when it exposes nothing.

---

## 2. Extraction Specification

### A. Exposed Interfaces (`microservices[service_id].exposed_interfaces`)
For each `(service_id, rel_dir)` in `microservices.json["{{SYSTEM_ID}}"]["services"]`, inspect the source files inside `{{CODEBASE_PATH}}/<rel_dir>` and extract every operation that is **callable across the service boundary by another service or an external client**. Base each record on source evidence, never on names alone.

#### A.1 Include
- **REST / HTTP handlers**
  - *Java*: Spring `@RestController` / `@Controller` methods (`@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`, `@RequestMapping`), JAX-RS `@Path` methods, **and Spring Data REST repository query methods** declared in interfaces annotated `@RepositoryRestResource` (they are served over HTTP with no controller; the endpoint is `/<path>/{id}` for `findById`, `/<path>/search/<method>` for custom finders, `/<path>` for `findAll`). Plain repositories/DAOs without that annotation are NOT exposed.
  - *C#*: `[ApiController]` / `ControllerBase` action methods and Minimal API `Map*` handlers (route-registration helpers: use the helper's name as `method_name`).
  - *Go*: HTTP handlers registered on a router/mux (`gin`, `echo`, `chi`, `mux`, `net/http`), including handlers of a BFF/frontend server that perform business actions.
  - *Python*: every active (non-commented) routed view in `urls.py`/blueprints/decorators (`@app.route`, `@router.get`, `APIView`/`ViewSet`/function views), and Celery `@shared_task` / `@app.task` consumers.
  - *PHP*: controller actions with `@Route` / `#[Route]`.
  - *Node.js / TypeScript*: NestJS `@Controller` methods, Express/Fastify `app.<verb>` / `router.<verb>` handlers.
- **gRPC / RPC**: every method a struct/class implements for a registered gRPC service (`*ImplBase`, `Unimplemented*Server`, `*Servicer`, `@GrpcMethod`, Go server structs registered with `Register*Server`). Include placeholder methods that satisfy the contract. For Go: a struct registered as the server for a service exposes **every RPC of that service, including methods promoted from embedded structs**; list promoted methods under the embedding struct, and also under the embedded struct if that struct is separately registered for its own service. For server-streaming RPCs, return `List<T>`.
- **GraphQL (NestJS / similar)**: leaf `@Query`, `@Mutation` and `@ResolveField` resolver methods that do real work.
- **Asynchronous consumers** (cross-service only): `@KafkaListener`, `@RabbitListener`, `@StreamListener`, Eventuate Tram command/event handlers, `IIntegrationEventHandler.Handle` / `HandleMessageAsync` (record the one public handler, not its private per-event overloads), Celery tasks, AMQP/NATS consumer loops (for a loop in Go `main()`, use `class_name` `"main"`, `method_name` `"main"`), and NestJS CQRS `@Saga()` / EventStore handlers that react to events **published by another service**.

#### A.2 Exclude
- Entities, DTOs, plain repositories/DAOs, configuration, DI wiring, `main()` bootstrap of HTTP servers, worker lifecycle hooks (`StartAsync`/`StopAsync`), getters/setters, constructors, private helpers.
- Outbound client stubs (`@FeignClient`, Refit interfaces, generated gRPC `*Client`/`*Stub`): they are callers, not exposed interfaces.
- **Health, status, debug and plumbing endpoints**: `/health`, `/healthz`, `/_healthz`, `/ready`, `/readiness`, gRPC `Health.Check`/`Watch`, `/metrics`, `/debug/*`, `/memory`, `/free`, `/build`, `/oups`, `/robots.txt`, static-asset routes, scaffold `GET /` hello/banner handlers, debug status servlets, framework exception-handler / error views, and circuit-breaker fallback handlers (`/fallback`).
- **UI-rendering handlers**: controllers, servlets or handlers whose job is to render an HTML page, form or view (MVC `View()`, JSP, Razor, Thymeleaf, `HttpServlet` `handleGET`/`handlePOST` that forward to a page, login/consent/logout UI flows, HTML form handlers). A service made only of these has `"exposed_interfaces": []`.
- **Browser SPAs** (React/Vue/Angular bundles served by `webpack`, `react-scripts`, `nginx`, `express.static`, including a catch-all `GET /*` that returns `index.html`): `"exposed_interfaces": []`.
- Empty namespace-grouping GraphQL resolvers that only `return {}`; handlers whose body is commented out or a no-op (`return null`); routes that are commented out; the unused duplicate when a real and a dummy/test implementation exist for one RPC (keep the real one).
- Local, in-process events that never leave the service (e.g. a framework `@EventListener`) and internal queues whose producer and consumer are in the same service.

#### A.3 Signature Normalization
- Unwrap transport/async wrappers in `return_type` and `param_types`, recursively: `ResponseEntity<T>`, `Optional<T>`, `Mono<T>`, `CompletableFuture<T>`, `Task<T>`, `ActionResult<T>`, `Task<ActionResult<T>>` → `T`. `Flux<T>`, `Collection<T>`, `IEnumerable<T>`, `Set<T>`, `T[]` → `List<T>`. Empty/void wrappers (`ResponseEntity<Void>`, `Mono<Void>`, `Task`, bare `IActionResult`) → `"void"`.
- Remove framework context arguments from `param_types`: `HttpServletRequest`, `HttpServletResponse`, `BindingResult`, `Model`, `Pageable`, `Principal`, `CancellationToken`, `ServerCallContext`, `context.Context`, `http.ResponseWriter`, `*http.Request`, `*gin.Context`, Express `req`/`res`, Vert.x `RoutingContext`, parent/context decorators.
- For messaging handlers, use the message payload type `T` (not `CommandMessage<T>` / `DomainEventEnvelope<T>`).
- Use simple domain type names (`"Owner"`, `"int"`, `"String"`, `"List<Visit>"`). Keep a declared type as written when nothing more specific can be established (for example `Object`).

#### A.4 Identifiers
- `class_name`: the declared class, FQN, struct (`<pkg>.<Struct>` for Go) or, when the handler is a plain function, the module/file identifier (e.g. `views`, `tasks`, `server.js`).
- `method_name`: the declared method or function name.
- `id`: `"<SimpleClassName>.<method_name>"`, unique within the service. If two methods share a name (overloads, versions), add a short suffix describing the difference (for example `"VisitResource.readByPetId"`).
- **Anonymous inline route callbacks** (Express `app.get('/cart/:id', (req, res) => ...)`): set `class_name` to the route file (`"server.js"`), `method_name` to lowercase snake_case `<verb>_<route_tokens>` (drop a leading generic `/api`, replace `/` and `:` with `_`; e.g. `GET /api/orders/:id` → `get_orders_id`, `POST /shipping/:id` → `post_shipping_id`), and `id` to `"server.<method_name>"`. Apply the same idea to other anonymous handlers: never invent camelCase names.
- `endpoint`: `"<VERB> <full path>"` for HTTP (combine class-level and method-level paths; omit configuration context paths), the RPC `Service/method` for gRPC, the queue/topic/event type for messaging.

### B. Inter-Service Call Edges (`inter_service_calls`)
Trace every call where code in `src_service` invokes an exposed interface in `dst_service` (`src_service != dst_service`).

1. **Synchronous HTTP / REST**
   - Inspect `WebClient`, `RestTemplate`, `RestClient`, `@FeignClient`, `@HttpExchange`, `HttpClient`, Refit, server-side `axios` / `fetch` / `requests` / `http.Get`/`Post`, and programmatic clients in coded BFF/composition gateways.
   - Resolve service names, URLs and environment/config values (`application.yml`, `appsettings.json`, `docker-compose.yml`, `.env`) to the target service, then to the exact target handler (HTTP verb + path), including Spring Data REST repository methods.
   - `src_class` is the class that actually contains the call (the caller), and `dst_class` is the `class_name` of the target interface.
2. **gRPC / RPC**: match each client-stub call to the server struct/class registered for **that stub's service type** and its method. A client of the full service resolves to the struct registered for the full service (which includes promoted methods); a read-only client type resolves to the read-only struct.
3. **Asynchronous messaging**: match each publisher (`KafkaTemplate.send`, `RabbitTemplate.convertAndSend`, `DomainEventPublisher.publish`, `CommandProducer.send`, `EventBus.PublishAsync`, `eventBus.publish`, Celery `.delay()` / direct task invocation, AMQP publish) to every active cross-service consumer of that event/command/queue. Use one edge per distinct publisher method and consumer interface. Ignore events whose publisher or subscriber action is commented out.
4. **Do NOT record**
   - Declarative reverse-proxy / gateway route rules (`GatewayRoute`, Zuul / Spring Cloud Gateway YAML, fluent `.route(r -> r.path(...).uri(...))`, nginx `proxy_pass`) and wildcard (`/**`) routes. Use protocol `REST` only for real programmatic client calls.
   - Calls made from browser-side code (SPA bundles, static frontend `fetch`/`axios`): such services have no outgoing calls.
   - Infrastructure plumbing: service-registry registration/heartbeat/discovery (Eureka, `register`/`unregister`/`getInstances`), tracing/metrics exporters, OAuth2/OIDC token introspection or JWT middleware, authorization-guard or RBAC policy checks, configuration reloaders.
   - Same-service calls, calls to external third-party APIs, unimplemented stubs, and calls whose target interface does not exist in the canonical services.
5. **Evidence**: `"evidence"` MUST be `"<file path relative to CODEBASE_PATH>:<line> <short code snippet>"` citing the caller's line; add the target line after `->` if useful.

---

## 3. Output Verification & Save
Write the JSON to `{{OUTPUT_PATH}}` matching `prompts/schema.json` with `"system_id"`, `"extractor_tool": "claude-code"`, `"prompt_version": "v2.0"`, `"status": "pending_manual_review"`. Verify before finishing:
1. All keys in `microservices` match `microservices.json["{{SYSTEM_ID}}"]["services"]` 1-to-1.
2. Interface `"id"` values are unique within each microservice.
3. Every `dst_interface_id` exists in `microservices[dst_service].exposed_interfaces`, and `dst_class` equals that interface's `class_name`.
4. `src_service != dst_service` for all `inter_service_calls`, and no duplicate calls (same `src_service`, `src_class`, `src_method`, `dst_service`, `dst_interface_id`).
