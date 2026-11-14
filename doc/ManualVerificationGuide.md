# Manual Interface Verification Guide
**Purpose:** Step-by-step checklist to manually verify every exposed interface and inter-service call in all 5 ground truth call graphs.  
**Branch:** `phase_01/eshin` · Ground truth files: `benchmarks/ground_truth/MS0XX.json`

---

## How to Read This Guide

For each system you will:
1. **Open** the listed source file(s) in your editor
2. **Look for** the annotation / pattern shown
3. **Tick** each interface as confirmed ✅ or flag ❌ if wrong

> [!IMPORTANT]
> Always use the **canonical microservices subfolder** listed for each system — do NOT look in monolith or CI/CD copies of the same code.

---

## Verification Checklist Key

| Mark | Meaning |
|---|---|
| `[ ]` | Not yet checked |
| `[✅]` | Confirmed correct |
| `[❌]` | Issue found — note what's wrong |

---

---

# MS010 — amazon-ecs-java-microservices

**Canonical source root:**
```
codebases/microservices/MS010_amazon-ecs-java-microservices/
  2_ECS_Java_Spring_PetClinic_Microservices/
```

**What to look for:** `@RequestMapping`, `@GetMapping`, `@RepositoryRestResource`

---

## Service: `spring-petclinic-rest-owner`

### File to open:
```
.../spring-petclinic-rest-owner/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
```
**Check:**
- `[ ]` Line 45 — `@RequestMapping(value = "/owner/{ownerId}/getVisits", method = RequestMethod.GET)` → confirms `getOwnerVisits` endpoint

```
.../owner/OwnerRepository.java
```
**Check (look for `@RepositoryRestResource` or `@RestResource`):**
- `[ ]` `findById(Integer)` — exposed at `GET /owner/{id}`
- `[ ]` `findByLastName(@Param("lastName") String lastName)` — exposed at `GET /owner/search/findByLastName`

---

## Service: `spring-petclinic-rest-pet`

### File to open:
```
.../spring-petclinic-rest-pet/src/main/java/org/springframework/samples/petclinic/pet/PetRepository.java
```
**Check:**
- `[ ]` `findById(Integer)` → `GET /pet/{id}`
- `[ ]` `findPetTypes()` → `GET /pet/search/findPetTypes`

---

## Service: `spring-petclinic-rest-system`

```
.../spring-petclinic-rest-system/.../system/ApplicationController.java
.../spring-petclinic-rest-system/.../system/CrashController.java
```
**Check:**
- `[ ]` `ApplicationController.home()` → `@RequestMapping("/")` exists
- `[ ]` `CrashController.triggerException()` → `@RequestMapping("/oups")` exists

---

## Service: `spring-petclinic-rest-vet`

```
.../spring-petclinic-rest-vet/.../vet/VetRepository.java
```
**Check:**
- `[ ]` `findAll()` → `GET /vet` via `@RepositoryRestResource`

---

## Service: `spring-petclinic-rest-visit`

```
.../spring-petclinic-rest-visit/.../visit/VisitRepository.java
```
**Check:**
- `[ ]` `findByPetId(@Param("petId") Integer)` → `GET /visit/search/findByPetId`

---

## Inter-Service Call — MS010

### File to open:
```
.../spring-petclinic-rest-owner/.../owner/OwnerController.java  — Line 59
```
**Check:**
- `[ ]` `restTemplate.getForObject("http://"+serviceEndpoint+"/pet/"+petId, Pet.class)` exists at or near line 59

---

---

# MS016 — pitstop

**Canonical source root:**
```
codebases/microservices/MS016_pitstop/src/
```

**What to look for:**
- REST: `[HttpGet]`, `[HttpPost]`, `[HttpPut]`, `[Route(...)]` attributes on controller methods
- Messaging: `IMessageHandler` / `HandleMessageAsync` implementations
- Caller: Refit interface methods called inside WebApp controllers

---

## Service: `CustomerManagementAPI`

```
src/CustomerManagementAPI/Controllers/CustomersController.cs
```
**Check (look for `[Http*]` or `[Route]` attributes):**
- `[ ]` `GetAllAsync()` → `[HttpGet]` → `GET /api/customers`
- `[ ]` `GetByCustomerId(string)` → `[HttpGet("{customerId}")]` → `GET /api/customers/{customerId}`
- `[ ]` `RegisterAsync(RegisterCustomer)` → `[HttpPost]` → `POST /api/customers`
- `[ ]` Line 47 — `_messagePublisher.PublishMessageAsync(...)` exists (confirms outbound MSG call)

---

## Service: `VehicleManagementAPI`

```
src/VehicleManagementAPI/Controllers/VehiclesController.cs
```
**Check:**
- `[ ]` `GetAllAsync()` → `[HttpGet]`
- `[ ]` `GetByLicenseNumber(string)` → `[HttpGet("{licenseNumber}")]`
- `[ ]` `RegisterAsync(RegisterVehicle)` → `[HttpPost]`
- `[ ]` Line 54 — `_messagePublisher.PublishMessageAsync(...)` exists

---

## Service: `WorkshopManagementAPI`

```
src/WorkshopManagementAPI/Controllers/RefDataController.cs
src/WorkshopManagementAPI/Controllers/WorkshopPlanningController.cs
```
**Check in `RefDataController.cs`:**
- `[ ]` `GetCustomers()` → `GET /api/refdata/customers`
- `[ ]` `GetCustomerByCustomerId(string)` → `GET /api/refdata/customers/{customerId}`
- `[ ]` `GetVehicles()` → `GET /api/refdata/vehicles`
- `[ ]` `GetVehicleByLicenseNumber(string)` → `GET /api/refdata/vehicles/{licenseNumber}`

**Check in `WorkshopPlanningController.cs`:**
- `[ ]` `GetByDate(DateTime)` → `GET /api/workshopplanning/{planningDate}`
- `[ ]` `GetMaintenanceJobAsync(DateTime, Guid)` → `GET /api/workshopplanning/{planningDate}/jobs/{jobId}`
- `[ ]` `PlanMaintenanceJobAsync(DateTime, PlanMaintenanceJob)` → `POST /api/workshopplanning/{planningDate}/jobs`
- `[ ]` `FinishMaintenanceJobAsync(DateTime, Guid, FinishMaintenanceJob)` → `PUT /api/workshopplanning/{planningDate}/jobs/{jobId}/finish`

**Check command handlers (MSG publishers):**
```
src/WorkshopManagementAPI/CommandHandlers/PlanMaintenanceJobCommandHandler.cs   — Line 35
src/WorkshopManagementAPI/CommandHandlers/FinishMaintenanceJobCommandHandler.cs — Line 35
```
- `[ ]` Both have `_messagePublisher.PublishMessageAsync(...)` at/near line 35

---

## Service: `AuditlogService`

```
src/AuditlogService/AuditLogWorker.cs
```
**Check:**
- `[ ]` Class implements `IMessageHandler` or similar and has `HandleMessageAsync(string, string)` method
- `[ ]` Subscribed to `rabbitmq/pitstop` exchange

---

## Service: `InvoiceService`

```
src/InvoiceService/InvoiceWorker.cs
```
- `[ ]` Has `HandleMessageAsync(string, string)` → listens on `rabbitmq/pitstop`

---

## Service: `NotificationService`

```
src/NotificationService/NotificationWorker.cs
```
- `[ ]` Has `HandleMessageAsync(string, string)` → listens on `rabbitmq/pitstop`

---

## Service: `WorkshopManagementEventHandler`

```
src/WorkshopManagementEventHandler/EventHandlerWorker.cs
```
- `[ ]` Has `HandleMessageAsync(string, string)` → listens on `rabbitmq/pitstop`

---

## Service: `TimeService`

```
src/TimeService/TimeWorker.cs   — Line 39
```
- `[ ]` Line 39 has `_messagePublisher.PublishMessageAsync(...)` (confirms 3 outbound MSG calls to Audit/Invoice/Notification)

---

## REST Caller Verification — `WebApp`

```
src/WebApp/Controllers/CustomerManagementController.cs
src/WebApp/Controllers/VehicleManagementController.cs
src/WebApp/Controllers/WorkshopManagementController.cs
```
**Spot-check these line numbers:**

| File | Line | Expected call |
|---|---|---|
| `CustomerManagementController.cs` | 23 | `_customerManagementAPI.GetCustomers()` |
| `CustomerManagementController.cs` | 36 | `_customerManagementAPI.GetCustomerById(id)` |
| `CustomerManagementController.cs` | 60 | `_customerManagementAPI.RegisterCustomer(cmd)` |
| `VehicleManagementController.cs` | 26 | `_vehicleManagementAPI.GetVehicles()` |
| `VehicleManagementController.cs` | 37 | `_vehicleManagementAPI.GetVehicleByLicenseNumber(...)` |
| `VehicleManagementController.cs` | 38 | `_customerManagementAPI.GetCustomerById(...)` |
| `VehicleManagementController.cs` | 55 | `_customerManagementAPI.GetCustomers()` |
| `VehicleManagementController.cs` | 74 | `_vehicleManagementAPI.RegisterVehicle(...)` |
| `WorkshopManagementController.cs` | 34 | `_workshopManagementAPI.GetWorkshopPlanning(...)` |
| `WorkshopManagementController.cs` | 53 | `_workshopManagementAPI.GetMaintenanceJob(...)` |
| `WorkshopManagementController.cs` | 84 | `_workshopManagementAPI.GetMaintenanceJob(...)` |
| `WorkshopManagementController.cs` | 110 | `_workshopManagementAPI.GetVehicleByLicenseNumber(...)` |
| `WorkshopManagementController.cs` | 111 | `_workshopManagementAPI.GetCustomerById(...)` |
| `WorkshopManagementController.cs` | 116 | `_workshopManagementAPI.PlanMaintenanceJob(...)` |
| `WorkshopManagementController.cs` | 158 | `_workshopManagementAPI.FinishMaintenanceJob(...)` |
| `WorkshopManagementController.cs` | 176 | `_workshopManagementAPI.GetVehicles()` |

---

---

# MS031 — sample-spring-microservices-new

**Canonical source root:**
```
codebases/microservices/MS031_sample-spring-microservices-new/
```

**What to look for:** `@RestController`, `@RequestMapping`, `@GetMapping`, `@PostMapping`, `@FeignClient`

---

## Service: `employee-service`

```
employee-service/src/main/java/pl/piomin/services/employee/controller/EmployeeController.java
```
**Check annotations on each method:**
- `[ ]` `add(@RequestBody Employee)` → `@PostMapping` → `POST /`
- `[ ]` `findAll()` → `@GetMapping` → `GET /`
- `[ ]` `findById(@PathVariable Long id)` → `@GetMapping("/{id}")` → `GET /{id}`
- `[ ]` `findByDepartment(@PathVariable Long departmentId)` → `@GetMapping("/department/{departmentId}")` → `GET /department/{departmentId}`
- `[ ]` `findByOrganization(@PathVariable Long organizationId)` → `@GetMapping("/organization/{organizationId}")` → `GET /organization/{organizationId}`

---

## Service: `department-service`

```
department-service/src/main/java/pl/piomin/services/department/controller/DepartmentController.java
```
**Check:**
- `[ ]` `add(@RequestBody Department)` → `@PostMapping` → `POST /`
- `[ ]` `findAll()` → `@GetMapping` → `GET /`
- `[ ]` `findById(@PathVariable Long id)` → `@GetMapping("/{id}")`
- `[ ]` `findByOrganization(@PathVariable Long organizationId)` → `@GetMapping("/organization/{organizationId}")`
- `[ ]` `findByOrganizationWithEmployees(@PathVariable Long organizationId)` → `@GetMapping("/organization/{organizationId}/with-employees")`
- `[ ]` **Line 53** — `employeeClient.findByDepartment(d.getId())` exists (Feign call to employee-service)

---

## Service: `organization-service`

```
organization-service/src/main/java/pl/piomin/services/organization/controller/OrganizationController.java
```
**Check:**
- `[ ]` `add(@RequestBody Organization)` → `@PostMapping`
- `[ ]` `findAll()` → `@GetMapping`
- `[ ]` `findById(@PathVariable Long id)` → `@GetMapping("/{id}")`
- `[ ]` `findByIdWithDepartments(@PathVariable Long id)` → `@GetMapping("/{id}/with-departments")`
- `[ ]` `findByIdWithDepartmentsAndEmployees(@PathVariable Long id)` → `@GetMapping("/{id}/with-departments-and-employees")`
- `[ ]` `findByIdWithEmployees(@PathVariable Long id)` → `@GetMapping("/{id}/with-employees")`

**Check Feign calls (lines 56, 64, 72):**
- `[ ]` Line 56 — `departmentClient.findByOrganization(organization.getId())`
- `[ ]` Line 64 — `departmentClient.findByOrganizationWithEmployees(organization.getId())`
- `[ ]` Line 72 — `employeeClient.findByOrganization(organization.getId())`

---

## Infrastructure Services

```
discovery-service/  →  look for @EnableEurekaServer
config-service/     →  look for @EnableConfigServer
gateway-service/    →  look for application.yml routes (no @RestController)
```
- `[ ]` None of these have `@RestController` or any `@*Mapping` endpoints (confirms `exposed_interfaces: []`)

---

---

# MS047 — robot-shop

**Canonical source root:**
```
codebases/microservices/MS047_robot-shop/
```

**What to look for by language:**
| Service | Lang | Pattern |
|---|---|---|
| catalogue, user, cart | Node.js | `app.get(...)`, `app.post(...)`, `app.delete(...)` in `server.js` |
| shipping | Java | `@GetMapping`, `@PostMapping`, `@RequestMapping` on `Controller.java` |
| ratings | PHP | `@Route(...)` annotation in Symfony controller |
| payment | Python | `@app.route(...)` Flask decorator |
| dispatch | Go | `amqp.Dial(...)` + queue consume loop in `main.go` |

---

## Service: `catalogue` — Node.js

```
catalogue/server.js
```
**Check `app.get(...)` / `app.post(...)` calls:**
- `[ ]` `app.get('/health', ...)` → `GET /health`
- `[ ]` `app.get('/products', ...)` → `GET /products`
- `[ ]` `app.get('/product/:sku', ...)` → `GET /product/:sku`
- `[ ]` `app.get('/products/:cat', ...)` → `GET /products/:cat`
- `[ ]` `app.get('/categories', ...)` → `GET /categories`
- `[ ]` `app.get('/search/:text', ...)` → `GET /search/:text`
- `[ ]` **Line 362** — `request('http://'+catalogueHost+':8080/product/'+sku, ...)` does NOT exist here — this line is in `cart/server.js` (not catalogue)

---

## Service: `user` — Node.js

```
user/server.js
```
**Check:**
- `[ ]` `app.get('/health', ...)` → `GET /health`
- `[ ]` `app.get('/uniqueid', ...)` → `GET /uniqueid`
- `[ ]` `app.get('/check/:id', ...)` → `GET /check/:id`
- `[ ]` `app.get('/users', ...)` → `GET /users`
- `[ ]` `app.post('/login', ...)` → `POST /login`
- `[ ]` `app.post('/register', ...)` → `POST /register`
- `[ ]` `app.post('/order/:id', ...)` → `POST /order/:id`
- `[ ]` `app.get('/history/:id', ...)` → `GET /history/:id`

---

## Service: `cart` — Node.js

```
cart/server.js
```
**Check:**
- `[ ]` `app.get('/health', ...)` → `GET /health`
- `[ ]` `app.get('/cart/:id', ...)` → `GET /cart/:id`
- `[ ]` `app.delete('/cart/:id', ...)` → `DELETE /cart/:id`
- `[ ]` `app.get('/add/:id/:sku/:qty', ...)` → `GET /add/:id/:sku/:qty`
- `[ ]` `app.get('/update/:id/:sku/:qty', ...)` → `GET /update/:id/:sku/:qty`
- `[ ]` `app.get('/item/delete/:id/:sku', ...)` → `GET /item/delete/:id/:sku`
- `[ ]` `app.post('/shipping/:id', ...)` → `POST /shipping/:id`
- `[ ]` **Line 362** — `request('http://'+catalogueHost+':8080/product/'+sku, ...)` → confirms call to catalogue

---

## Service: `shipping` — Java

```
shipping/src/main/java/com/instana/robotshop/shipping/Controller.java
```
**Check `@GetMapping` / `@PostMapping`:**
- `[ ]` `health()` → `@GetMapping("/health")`
- `[ ]` `count()` → `@GetMapping("/count")`
- `[ ]` `codes()` → `@GetMapping("/codes")`
- `[ ]` `cities(@PathVariable String code)` → `@GetMapping("/cities/{code}")`
- `[ ]` `match(@PathVariable String code, @PathVariable String text)` → `@GetMapping("/match/{code}/{text}")`
- `[ ]` `caclc(@PathVariable long id)` → `@GetMapping("/calc/{id}")`
- `[ ]` `confirm(@PathVariable String id, @RequestBody String body)` → `@PostMapping("/confirm/{id}")`
- `[ ]` **Line 137** — `helper.addToCart(id, body)` → confirms call to cart service

---

## Service: `ratings` — PHP / Symfony

```
ratings/src/Controller/RatingsApiController.php
ratings/src/Controller/HealthController.php
```
**Check `@Route` annotations:**
- `[ ]` `HealthController.__invoke()` → `@Route("/_health")` with `GET` method
- `[ ]` `RatingsApiController.put(...)` → `@Route("/api/rate/{sku}/{score}", methods={"PUT"})`
- `[ ]` `RatingsApiController.get(...)` → `@Route("/api/fetch/{sku}", methods={"GET"})`
- `[ ]` **Line 49 in `RatingsApiController.php`** — `$this->catalogueService->checkSKU($sku)` → confirms call to catalogue

---

## Service: `payment` — Python / Flask

```
payment/payment.py
```
**Check `@app.route(...)` decorators:**
- `[ ]` `@app.route('/health', methods=['GET'])` → `get_health` function
- `[ ]` `@app.route('/pay/<id>', methods=['POST'])` → `pay` function
- `[ ]` **Line 64** — `requests.get('http://{user}:8080/check/{id}')` → call to user service
- `[ ]` **Line 101** — `queueOrder({...})` → AMQP publish to dispatch
- `[ ]` **Line 106** — `requests.post('http://{user}:8080/order/{id}', ...)` → call to user service
- `[ ]` **Line 116** — `requests.delete('http://{cart}:8080/cart/{id}')` → call to cart service

---

## Service: `dispatch` — Go

```
dispatch/main.go
```
**Check:**
- `[ ]` `amqp.Dial(...)` or `amqp.DialTLS(...)` present → confirms AMQP connection
- `[ ]` `ch.Consume(...)` with queue name `robot-shop/orders` or similar → confirms it is a consumer
- `[ ]` No `http.HandleFunc` or REST server setup → confirms `exposed_interfaces` only has the Messaging endpoint

---

## `web` and `mongodb` — confirm no interfaces

- `[ ]` `web/` → only contains `nginx.conf` / static files, no application routes
- `[ ]` `mongo/` or `mongodb/` → only init scripts, no REST/gRPC server

---

---

# MS098 — ultimate-backend

**Canonical source root:**
```
codebases/microservices/MS098_ultimate-backend/apps/
```

**What to look for:**
- gRPC controllers: `@GrpcMethod('ServiceName', 'MethodName')` decorator on NestJS class methods
- GraphQL resolvers: `@Query()`, `@Mutation()`, `@ResolveField()` + `rpc?.SvcName.svc.method(...)` calls
- Messaging: `@Process('queue_name')` decorator (Bull)

---

## Service: `service-webhook`

```
apps/service-webhook/src/webhook/webhook.controller.ts
```
**Check `@GrpcMethod` decorators:**
- `[ ]` `@GrpcMethod('WebhookService', 'CreateWebhook')` on `createWebhook(...)`
- `[ ]` `@GrpcMethod('WebhookService', 'DeleteWebhook')` on `deleteWebhook(...)`
- `[ ]` `@GrpcMethod('WebhookService', 'FindWebhook')` on `findWebhook(...)`
- `[ ]` `@GrpcMethod('WebhookService', 'ReadWebhook')` on `readWebhook(...)`
- `[ ]` `@GrpcMethod('WebhookService', 'UpdateWebhook')` on `updateWebhook(...)`

---

## Service: `service-access`

```
apps/service-access/src/access-token/access-token.controller.ts
```
**Check `@GrpcMethod` decorators:**
- `[ ]` `@GrpcMethod('AccessService', 'CreateAccess')` on `createAccess(...)`
- `[ ]` `@GrpcMethod('AccessService', 'DeleteAccess')` on `deleteAccess(...)`
- `[ ]` `@GrpcMethod('AccessService', 'FindAccess')` on `findAccess(...)`
- `[ ]` `@GrpcMethod('AccessService', 'HasRights')` on `hasRights(...)`
- `[ ]` `@GrpcMethod('AccessService', 'ReadAccess')` on `readAccess(...)`

---

## Service: `service-billing`

```
apps/service-billing/src/billings/billings.controller.ts
```
**Check (19 methods — spot-check these critical ones):**
- `[ ]` `@GrpcMethod('BillingService', 'CreateCustomer')` on `createCustomer(...)` → called by `service-account`
- `[ ]` `@GrpcMethod('BillingService', 'CreateSubscription')` on `createSubscription(...)` → called by `service-tenant`
- `[ ]` `@GrpcMethod('BillingService', 'CancelSubscription')` on `cancelSubscription(...)`
- `[ ]` `@GrpcMethod('BillingService', 'ChangeSubscription')` on `changeSubscription(...)`
- `[ ]` Remaining 15 methods follow same `@GrpcMethod('BillingService', '...')` pattern

---

## Service: `service-account`

```
apps/service-account/src/accounts/accounts.controller.ts
```
**Check:**
- `[ ]` `@GrpcMethod('AccountService', 'Create')` on `create(...)`
- `[ ]` `@GrpcMethod('AccountService', 'ForgotPassword')` on `forgotPassword(...)`
- `[ ]` `@GrpcMethod('AccountService', 'VerifyAccount')` on `verifyAccount(...)`
- `[ ]` `@GrpcMethod('AccountService', 'VerifyActivationLink')` on `verifyActivationLink(...)`
- `[ ]` Remaining 9 methods follow same pattern

**Check outbound calls (backend-to-backend):**
```
apps/service-account/src/accounts/sagas/handlers/register-user.handler.ts
```
- `[ ]` **Line 145** — `rpc?.role.svc.addUserToRole(...)` or equivalent gRPC call to role service
- `[ ]` **Line 153** — `rpc?.billing.svc.createCustomer(...)` or equivalent gRPC call to billing service

---

## Service: `service-tenant`

```
apps/service-tenant/src/tenants/tenants.controller.ts
apps/service-tenant/src/members/members.controller.ts
```
**Check:**
- `[ ]` `@GrpcMethod('TenantService', 'CreateTenant')` on `createTenant(...)`
- `[ ]` `@GrpcMethod('TenantService', 'InviteMember')` on `inviteMember(...)` in `members.controller.ts`
- `[ ]` Remaining 10 methods follow same pattern

**Check outbound calls (backend-to-backend):**
```
apps/service-tenant/src/tenants/sagas/handlers/create-tenant.handler.ts
apps/service-tenant/src/members/sagas/handlers/accept-invitation.handler.ts
apps/service-tenant/src/members/sagas/handlers/remove-member.handler.ts
apps/service-tenant/src/members/sagas/handlers/invite-member.handler.ts
```
- `[ ]` `create-tenant.handler.ts:105` — gRPC call to `billing.createSubscription`
- `[ ]` `create-tenant.handler.ts:127` — gRPC call to `role.addUserToRole`
- `[ ]` `accept-invitation.handler.ts:67` — gRPC call to `role.addUserToRole`
- `[ ]` `remove-member.handler.ts:93` — gRPC call to `role.removeUserFromRole`
- `[ ]` `invite-member.handler.ts:111` — gRPC call to `role.addUserToRole`

---

## Service: `service-notification`

```
apps/service-notification/src/email/queue/auth.process.ts
```
**Check:**
- `[ ]` `@Process('processUserRegister')` or `@Processor('notification_queue')` decorator is present
- `[ ]` Method `processUserRegister(@InjectQueue(...) job: Job<UserEntity>)` exists

---

## Service: `service-role`

```
apps/service-role/src/roles/roles.controller.ts
```
**Check:**
- `[ ]` `@GrpcMethod('RoleService', 'AddUserToRole')` on `addUserToRole(...)`
- `[ ]` `@GrpcMethod('RoleService', 'RemoveUserFromRole')` on `removeUserFromRole(...)`
- `[ ]` `@GrpcMethod('RoleService', 'ReadUserRoles')` on `readUserRoles(...)`
- `[ ]` `@GrpcMethod('RoleService', 'HasRights')` on `hasRights(...)`

---

## Service: `api-admin` (gateway — confirm no gRPC server)

```
apps/api-admin/src/
```
**Check:**
- `[ ]` There is NO `@GrpcMethod(...)` anywhere in `api-admin/src/`
- `[ ]` There IS `@Query()`, `@Mutation()`, `@ResolveField()` in resolver files
- `[ ]` Resolver files call `rpc?.xxx.svc.method(...)` to downstream services

**Spot-check resolver lines:**
```
apps/api-admin/src/app/modules/account/
apps/api-admin/src/app/modules/billing/
apps/api-admin/src/app/modules/tenant/
```

| File | Line | Expected gRPC call |
|---|---|---|
| `accounts-mutation.resolver.ts` | 96 | `rpc?.account.svc.create(...)` |
| `accounts-mutation.resolver.ts` | 104 | `rpc?.account.svc.forgotPassword(...)` |
| `billings-mutation.resolver.ts` | 31 | `rpc?.billing.svc.changeSubscription(...)` |
| `billings.resolver.ts` | 34 | `rpc?.billing.svc.readInvoice(...)` |
| `tenants-mutation.resolver.ts` | 36 | `rpc?.tenant.svc.createTenant(...)` |
| `webhooks-mutation.resolver.ts` | 62 | `rpc?.webhook.svc.createWebhook(...)` |

---

---

## Verification Summary Template

After going through each system, record your findings here:

| System | Interfaces Checked | Calls Checked | Issues Found |
|---|---|---|---|
| MS010 | 9 / 9 | 1 / 1 | |
| MS016 | 18 / 18 | 33 / 33 | |
| MS031 | 16 / 16 | 4 / 4 | |
| MS047 | 34 / 34 | 7 / 7 | |
| MS098 | 69 / 69 | 49 / 49 | |

> [!TIP]
> **Fastest way to verify:** Use `Ctrl+F` (or `grep`) on the annotation pattern for each file. For example:  
> - Java: search `@RequestMapping` or `@GetMapping`  
> - C#: search `[HttpGet]` or `[HttpPost]`  
> - Node.js: search `app.get(` or `app.post(`  
> - Python: search `@app.route(`  
> - PHP: search `@Route(`  
> - TypeScript/NestJS: search `@GrpcMethod(`  
> - Go: search `amqp` or `Consume(`

> [!NOTE]
> **For inter-service calls**, go to the exact line number in the evidence field and confirm the call expression matches the endpoint of the destination service.
