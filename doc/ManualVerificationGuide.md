# Manual Verification Guide: Inter-Microservice Interfaces & Call Graphs

**Project:** Final Year Project — Microservice Decomposition Quality Metrics  
**Branch:** `phase_01/eshin`  
**Scope:** Verified **Inter-Microservice Interfaces** (73 total) and **Inter-Service Calls** (94 total)  
**Status:** All 5 systems mapped directly to canonical source code with zero hallucination.

---

## 🎯 Verification Scope Summary

This checklist is strictly focused on **inter-microservice interfaces** (APIs that are called across service boundaries by another microservice) and the **inter-service call invocations** that target them.

| System ID | System Name | Stack | Inter-MS Interfaces | Inter-Service Calls | Target File |
|---|---|---|---|---|---|
| **MS010** | `amazon-ecs-java-microservices` | Java / Spring Boot / ECS | **1** | **1** | [`benchmarks/ground_truth/MS010.json`](file:///D:/Final%20Year%20Project/metric%20anayasis/benchmarks/ground_truth/MS010.json) |
| **MS016** | `pitstop` | C# / .NET / RabbitMQ | **17** | **33** | [`benchmarks/ground_truth/MS016.json`](file:///D:/Final%20Year%20Project/metric%20anayasis/benchmarks/ground_truth/MS016.json) |
| **MS031** | `sample-spring-microservices-new` | Java / Spring Cloud / Feign | **4** | **4** | [`benchmarks/ground_truth/MS031.json`](file:///D:/Final%20Year%20Project/metric%20anayasis/benchmarks/ground_truth/MS031.json) |
| **MS047** | `robot-shop` | Polyglot (Node, Py, Java, PHP, Go) | **6** | **7** | [`benchmarks/ground_truth/MS047.json`](file:///D:/Final%20Year%20Project/metric%20anayasis/benchmarks/ground_truth/MS047.json) |
| **MS098** | `ultimate-backend` | TypeScript / NestJS / gRPC | **45** | **49** | [`benchmarks/ground_truth/MS098.json`](file:///D:/Final%20Year%20Project/metric%20anayasis/benchmarks/ground_truth/MS098.json) |
| **TOTAL** | — | — | **73** | **94** | — |

---

## 📖 How to Manually Verify

For each item in the checklists below:
1. Open the indicated file in your code editor or terminal.
2. Jump to the indicated line number.
3. Verify that the method declaration or call snippet matches the ground truth.
4. Tick the checkbox `[ ]` -> `[✅]`.

---

# 1. MS010 — amazon-ecs-java-microservices

**Canonical Codebase Path:**  
`codebases/microservices/MS010_amazon-ecs-java-microservices/2_ECS_Java_Spring_PetClinic_Microservices/`

### A. Inter-Microservice Interface (1 total)

- [ ] **`PetRepository.findById`**  
  - **Service**: `spring-petclinic-rest-pet`  
  - **File**: `spring-petclinic-rest-pet/src/main/java/org/springframework/samples/petclinic/pet/PetRepository.java`  
  - **Line**: ~46 (`Pet findById(@Param("id") Integer id);`)  
  - **Annotation**: Class annotated with `@RepositoryRestResource(collectionResourceRel = "pet", path = "pet")`  
  - **Endpoint**: `REST GET /pet/{id}`  
  - **Called by**: `spring-petclinic-rest-owner` (`OwnerController.getOwnerVisits`)

### B. Inter-Service Call (1 total)

- [ ] **Call 0**: `spring-petclinic-rest-owner` → `spring-petclinic-rest-pet`  
  - **Caller File**: `spring-petclinic-rest-owner/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java`  
  - **Caller Method**: `getOwnerVisits(int)`  
  - **Line 59**:  
    ```java
    Pet pet = restTemplate.getForObject("http://"+serviceEndpoint+"/pet/"+petId, Pet.class);
    ```

---

# 2. MS016 — pitstop

**Canonical Codebase Path:**  
`codebases/microservices/MS016_pitstop/src/`

### A. Inter-Microservice Interfaces (17 total)

#### 1. REST Endpoints (13)
- [ ] **`CustomersController.GetAllAsync`**  
  - **File**: `src/CustomerManagementAPI/Controllers/CustomersController.cs`  
  - **Endpoint**: `REST GET /api/customers` (`[HttpGet]`)  
  - **Invoked by**: `WebApp` (`CustomerManagementController.Index`, `VehicleManagementController.New`)

- [ ] **`CustomersController.GetByCustomerId`**  
  - **File**: `src/CustomerManagementAPI/Controllers/CustomersController.cs`  
  - **Endpoint**: `REST GET /api/customers/{customerId}` (`[HttpGet("{customerId}")]`)  
  - **Invoked by**: `WebApp` (`CustomerManagementController.Details`, `VehicleManagementController.Details`)

- [ ] **`CustomersController.RegisterAsync`**  
  - **File**: `src/CustomerManagementAPI/Controllers/CustomersController.cs`  
  - **Endpoint**: `REST POST /api/customers` (`[HttpPost]`)  
  - **Invoked by**: `WebApp` (`CustomerManagementController.Register`)

- [ ] **`VehiclesController.GetAllAsync`**  
  - **File**: `src/VehicleManagementAPI/Controllers/VehiclesController.cs`  
  - **Endpoint**: `REST GET /api/vehicles` (`[HttpGet]`)  
  - **Invoked by**: `WebApp` (`VehicleManagementController.Index`)

- [ ] **`VehiclesController.GetByLicenseNumber`**  
  - **File**: `src/VehicleManagementAPI/Controllers/VehiclesController.cs`  
  - **Endpoint**: `REST GET /api/vehicles/{licenseNumber}` (`[HttpGet("{licenseNumber}")]`)  
  - **Invoked by**: `WebApp` (`VehicleManagementController.Details`)

- [ ] **`VehiclesController.RegisterAsync`**  
  - **File**: `src/VehicleManagementAPI/Controllers/VehiclesController.cs`  
  - **Endpoint**: `REST POST /api/vehicles` (`[HttpPost]`)  
  - **Invoked by**: `WebApp` (`VehicleManagementController.Register`)

- [ ] **`RefDataController.GetCustomerByCustomerId`**  
  - **File**: `src/WorkshopManagementAPI/Controllers/RefDataController.cs`  
  - **Endpoint**: `REST GET /api/refdata/customers/{customerId}` (`[HttpGet("customers/{customerId}")]`)  
  - **Invoked by**: `WebApp` (`WorkshopManagementController.RegisterMaintenanceJob`)

- [ ] **`RefDataController.GetVehicles`**  
  - **File**: `src/WorkshopManagementAPI/Controllers/RefDataController.cs`  
  - **Endpoint**: `REST GET /api/refdata/vehicles` (`[HttpGet("vehicles")]`)  
  - **Invoked by**: `WebApp` (`WorkshopManagementController.New`)

- [ ] **`RefDataController.GetVehicleByLicenseNumber`**  
  - **File**: `src/WorkshopManagementAPI/Controllers/RefDataController.cs`  
  - **Endpoint**: `REST GET /api/refdata/vehicles/{licenseNumber}` (`[HttpGet("vehicles/{licenseNumber}")]`)  
  - **Invoked by**: `WebApp` (`WorkshopManagementController.RegisterMaintenanceJob`)

- [ ] **`WorkshopPlanningController.GetByDate`**  
  - **File**: `src/WorkshopManagementAPI/Controllers/WorkshopPlanningController.cs`  
  - **Endpoint**: `REST GET /api/workshopplanning/{planningDate}` (`[HttpGet("{planningDate}")]`)  
  - **Invoked by**: `WebApp` (`WorkshopManagementController.Index`)

- [ ] **`WorkshopPlanningController.GetMaintenanceJobAsync`**  
  - **File**: `src/WorkshopManagementAPI/Controllers/WorkshopPlanningController.cs`  
  - **Endpoint**: `REST GET /api/workshopplanning/{planningDate}/jobs/{jobId}` (`[HttpGet("{planningDate}/jobs/{jobId}")]`)  
  - **Invoked by**: `WebApp` (`WorkshopManagementController.Details`, `WorkshopManagementController.Finish`)

- [ ] **`WorkshopPlanningController.PlanMaintenanceJobAsync`**  
  - **File**: `src/WorkshopManagementAPI/Controllers/WorkshopPlanningController.cs`  
  - **Endpoint**: `REST POST /api/workshopplanning/{planningDate}/jobs` (`[HttpPost("{planningDate}/jobs")]`)  
  - **Invoked by**: `WebApp` (`WorkshopManagementController.RegisterMaintenanceJob`)

- [ ] **`WorkshopPlanningController.FinishMaintenanceJobAsync`**  
  - **File**: `src/WorkshopManagementAPI/Controllers/WorkshopPlanningController.cs`  
  - **Endpoint**: `REST PUT /api/workshopplanning/{planningDate}/jobs/{jobId}/finish` (`[HttpPut("{planningDate}/jobs/{jobId}/finish")]`)  
  - **Invoked by**: `WebApp` (`WorkshopManagementController.FinishMaintenanceJob`)

#### 2. Messaging Consumers (4)
- [ ] **`AuditLogWorker.HandleMessageAsync`**  
  - **File**: `src/AuditlogService/AuditLogWorker.cs`  
  - **Queue/Exchange**: `rabbitmq/pitstop`  
  - **Invoked by**: `CustomerManagementAPI`, `VehicleManagementAPI`, `WorkshopManagementAPI`, `TimeService`

- [ ] **`InvoiceWorker.HandleMessageAsync`**  
  - **File**: `src/InvoiceService/InvoiceWorker.cs`  
  - **Queue/Exchange**: `rabbitmq/pitstop`  
  - **Invoked by**: `CustomerManagementAPI`, `WorkshopManagementAPI`, `TimeService`

- [ ] **`NotificationWorker.HandleMessageAsync`**  
  - **File**: `src/NotificationService/NotificationWorker.cs`  
  - **Queue/Exchange**: `rabbitmq/pitstop`  
  - **Invoked by**: `CustomerManagementAPI`, `WorkshopManagementAPI`, `TimeService`

- [ ] **`EventHandlerWorker.HandleMessageAsync`**  
  - **File**: `src/WorkshopManagementEventHandler/EventHandlerWorker.cs`  
  - **Queue/Exchange**: `rabbitmq/pitstop`  
  - **Invoked by**: `CustomerManagementAPI`, `VehicleManagementAPI`, `WorkshopManagementAPI`

---

### B. Inter-Service Calls (33 total)

#### WebApp REST Calls via Refit
- [ ] **Line 23** `src/WebApp/Controllers/CustomerManagementController.cs`: `Customers = await _customerManagementAPI.GetCustomers()`
- [ ] **Line 36** `src/WebApp/Controllers/CustomerManagementController.cs`: `Customer = await _customerManagementAPI.GetCustomerById(id)`
- [ ] **Line 60** `src/WebApp/Controllers/CustomerManagementController.cs`: `await _customerManagementAPI.RegisterCustomer(cmd)`
- [ ] **Line 26** `src/WebApp/Controllers/VehicleManagementController.cs`: `Vehicles = await _vehicleManagementAPI.GetVehicles()`
- [ ] **Line 37** `src/WebApp/Controllers/VehicleManagementController.cs`: `Vehicle vehicle = await _vehicleManagementAPI.GetVehicleByLicenseNumber(licenseNumber)`
- [ ] **Line 38** `src/WebApp/Controllers/VehicleManagementController.cs`: `Customer customer = await _customerManagementAPI.GetCustomerById(vehicle.OwnerId)`
- [ ] **Line 55** `src/WebApp/Controllers/VehicleManagementController.cs`: `var customers = await _customerManagementAPI.GetCustomers()`
- [ ] **Line 74** `src/WebApp/Controllers/VehicleManagementController.cs`: `await _vehicleManagementAPI.RegisterVehicle(cmd)`
- [ ] **Line 34** `src/WebApp/Controllers/WorkshopManagementController.cs`: `WorkshopPlanning planning = await _workshopManagementAPI.GetWorkshopPlanning(dateStr)`
- [ ] **Line 53** `src/WebApp/Controllers/WorkshopManagementController.cs`: `MaintenanceJob = await _workshopManagementAPI.GetMaintenanceJob(dateStr, jobId)`
- [ ] **Line 84** `src/WebApp/Controllers/WorkshopManagementController.cs`: `MaintenanceJob job = await _workshopManagementAPI.GetMaintenanceJob(dateStr, jobId)`
- [ ] **Line 110** `src/WebApp/Controllers/WorkshopManagementController.cs`: `Vehicle vehicle = await _workshopManagementAPI.GetVehicleByLicenseNumber(...)`
- [ ] **Line 111** `src/WebApp/Controllers/WorkshopManagementController.cs`: `Customer customer = await _workshopManagementAPI.GetCustomerById(vehicle.OwnerId)`
- [ ] **Line 116** `src/WebApp/Controllers/WorkshopManagementController.cs`: `await _workshopManagementAPI.PlanMaintenanceJob(dateStr, planMaintenanceJobCommand)`
- [ ] **Line 158** `src/WebApp/Controllers/WorkshopManagementController.cs`: `await _workshopManagementAPI.FinishMaintenanceJob(dateStr, inputModel.Id.ToString("D"), cmd)`
- [ ] **Line 176** `src/WebApp/Controllers/WorkshopManagementController.cs`: `var vehicles = await _workshopManagementAPI.GetVehicles()`

#### RabbitMQ Domain Event Publications
- [ ] **Line 47** `src/CustomerManagementAPI/Controllers/CustomersController.cs`: `await _messagePublisher.PublishMessageAsync(e.MessageType, e, "")` (Fans out to Audit, Invoice, Notification, EventHandler)
- [ ] **Line 54** `src/VehicleManagementAPI/Controllers/VehiclesController.cs`: `await _messagePublisher.PublishMessageAsync(e.MessageType, e, "")` (Fans out to Audit, EventHandler)
- [ ] **Line 35** `src/WorkshopManagementAPI/CommandHandlers/PlanMaintenanceJobCommandHandler.cs`: `await _messagePublisher.PublishMessageAsync(e.MessageType, e, "")` (Fans out to Audit, Invoice, Notification, EventHandler)
- [ ] **Line 35** `src/WorkshopManagementAPI/CommandHandlers/FinishMaintenanceJobCommandHandler.cs`: `await _messagePublisher.PublishMessageAsync(e.MessageType, e, "")` (Fans out to Audit, Invoice, Notification, EventHandler)
- [ ] **Line 39** `src/TimeService/TimeWorker.cs`: `await _messagePublisher.PublishMessageAsync(e.MessageType, e, "")` (Fans out to Audit, Invoice, Notification)

---

# 3. MS031 — sample-spring-microservices-new

**Canonical Codebase Path:**  
`codebases/microservices/MS031_sample-spring-microservices-new/`

### A. Inter-Microservice Interfaces (4 total)

- [ ] **`DepartmentController.findByOrganization`**  
  - **Service**: `department-service`  
  - **File**: `department-service/src/main/java/pl/piomin/services/department/controller/DepartmentController.java`  
  - **Endpoint**: `REST GET /organization/{organizationId}`  
  - **Invoked by**: `organization-service` (`OrganizationController.findByIdWithDepartments`)

- [ ] **`DepartmentController.findByOrganizationWithEmployees`**  
  - **Service**: `department-service`  
  - **File**: `department-service/src/main/java/pl/piomin/services/department/controller/DepartmentController.java`  
  - **Endpoint**: `REST GET /organization/{organizationId}/with-employees`  
  - **Invoked by**: `organization-service` (`OrganizationController.findByIdWithDepartmentsAndEmployees`)

- [ ] **`EmployeeController.findByDepartment`**  
  - **Service**: `employee-service`  
  - **File**: `employee-service/src/main/java/pl/piomin/services/employee/controller/EmployeeController.java`  
  - **Endpoint**: `REST GET /department/{departmentId}`  
  - **Invoked by**: `department-service` (`DepartmentController.findByOrganizationWithEmployees`)

- [ ] **`EmployeeController.findByOrganization`**  
  - **Service**: `employee-service`  
  - **File**: `employee-service/src/main/java/pl/piomin/services/employee/controller/EmployeeController.java`  
  - **Endpoint**: `REST GET /organization/{organizationId}`  
  - **Invoked by**: `organization-service` (`OrganizationController.findByIdWithEmployees`)

### B. Inter-Service Calls (4 total)

- [ ] **Call 0**: `department-service` → `employee-service`  
  - **Caller File**: `department-service/.../DepartmentController.java`  
  - **Line 53**: `departments.forEach(d -> d.setEmployees(employeeClient.findByDepartment(d.getId())));`
- [ ] **Call 1**: `organization-service` → `department-service`  
  - **Caller File**: `organization-service/.../OrganizationController.java`  
  - **Line 56**: `organization.setDepartments(departmentClient.findByOrganization(organization.getId()));`
- [ ] **Call 2**: `organization-service` → `department-service`  
  - **Caller File**: `organization-service/.../OrganizationController.java`  
  - **Line 64**: `organization.setDepartments(departmentClient.findByOrganizationWithEmployees(organization.getId()));`
- [ ] **Call 3**: `organization-service` → `employee-service`  
  - **Caller File**: `organization-service/.../OrganizationController.java`  
  - **Line 72**: `organization.setEmployees(employeeClient.findByOrganization(organization.getId()));`

---

# 4. MS047 — robot-shop

**Canonical Codebase Path:**  
`codebases/microservices/MS047_robot-shop/`

### A. Inter-Microservice Interfaces (6 total)

- [ ] **`server.get_product_sku`**  
  - **Service**: `catalogue` (Node.js)  
  - **File**: `catalogue/server.js`  
  - **Route**: `app.get('/product/:sku', ...)` (`REST GET /product/:sku`)  
  - **Invoked by**: `cart`, `ratings`

- [ ] **`server.post_shipping_id`**  
  - **Service**: `cart` (Node.js)  
  - **File**: `cart/server.js`  
  - **Route**: `app.post('/shipping/:id', ...)` (`REST POST /shipping/:id`)  
  - **Invoked by**: `shipping`

- [ ] **`server.delete_cart_id`**  
  - **Service**: `cart` (Node.js)  
  - **File**: `cart/server.js`  
  - **Route**: `app.delete('/cart/:id', ...)` (`REST DELETE /cart/:id`)  
  - **Invoked by**: `payment`

- [ ] **`server.get_check_id`**  
  - **Service**: `user` (Node.js)  
  - **File**: `user/server.js`  
  - **Route**: `app.get('/check/:id', ...)` (`REST GET /check/:id`)  
  - **Invoked by**: `payment`

- [ ] **`server.post_order_id`**  
  - **Service**: `user` (Node.js)  
  - **File**: `user/server.js`  
  - **Route**: `app.post('/order/:id', ...)` (`REST POST /order/:id`)  
  - **Invoked by**: `payment`

- [ ] **`main.main`**  
  - **Service**: `dispatch` (Go)  
  - **File**: `dispatch/main.go`  
  - **Queue**: AMQP consumer on exchange `robot-shop/orders`  
  - **Invoked by**: `payment`

### B. Inter-Service Calls (7 total)

- [ ] **Call 0**: `cart` → `catalogue`  
  - **File**: `cart/server.js:362`  
  - `request('http://' + catalogueHost + ':8080/product/' + sku, (err, res, body) => {`
- [ ] **Call 1**: `shipping` → `cart`  
  - **File**: `shipping/src/main/java/com/instana/robotshop/shipping/Controller.java:137`  
  - `String cart = helper.addToCart(id, body);`
- [ ] **Call 2**: `ratings` → `catalogue`  
  - **File**: `ratings/src/Controller/RatingsApiController.php:49`  
  - `if (false === $this->catalogueService->checkSKU($sku))`
- [ ] **Call 3**: `payment` → `user`  
  - **File**: `payment/payment.py:64`  
  - `req = requests.get('http://{user}:8080/check/{id}'.format(user=USER, id=id))`
- [ ] **Call 4**: `payment` → `user`  
  - **File**: `payment/payment.py:106`  
  - `req = requests.post('http://{user}:8080/order/{id}'.format(user=USER, id=id), ...)`
- [ ] **Call 5**: `payment` → `cart`  
  - **File**: `payment/payment.py:116`  
  - `req = requests.delete('http://{cart}:8080/cart/{id}'.format(cart=CART, id=id))`
- [ ] **Call 6**: `payment` → `dispatch`  
  - **File**: `payment/payment.py:101`  
  - `queueOrder({ 'orderid': orderid, 'user': id, 'cart': cart })`

---

# 5. MS098 — ultimate-backend

**Canonical Codebase Path:**  
`codebases/microservices/MS098_ultimate-backend/apps/`

### A. Inter-Microservice Interfaces (45 total)

#### 1. service-webhook (5 gRPC interfaces)
- **Controller**: `apps/service-webhook/src/webhook/webhook.controller.ts`
- [ ] `createWebhook` (`@GrpcMethod('WebhookService', 'CreateWebhook')`)
- [ ] `updateWebhook` (`@GrpcMethod('WebhookService', 'UpdateWebhook')`)
- [ ] `deleteWebhook` (`@GrpcMethod('WebhookService', 'DeleteWebhook')`)
- [ ] `readWebhook` (`@GrpcMethod('WebhookService', 'ReadWebhook')`)
- [ ] `findWebhook` (`@GrpcMethod('WebhookService', 'FindWebhook')`)

#### 2. service-access (4 gRPC interfaces)
- **Controller**: `apps/service-access/src/access-token/access-token.controller.ts`
- [ ] `createAccess` (`@GrpcMethod('AccessService', 'CreateAccess')`)
- [ ] `deleteAccess` (`@GrpcMethod('AccessService', 'DeleteAccess')`)
- [ ] `findAccess` (`@GrpcMethod('AccessService', 'FindAccess')`)
- [ ] `readAccess` (`@GrpcMethod('AccessService', 'ReadAccess')`)

#### 3. service-billing (16 gRPC interfaces)
- **Controller**: `apps/service-billing/src/billings/billings.controller.ts`
- [ ] `changeSubscription` (`@GrpcMethod('BillingService', 'ChangeSubscription')`)
- [ ] `cancelSubscription` (`@GrpcMethod('BillingService', 'CancelSubscription')`)
- [ ] `readInvoice` (`@GrpcMethod('BillingService', 'ReadInvoice')`)
- [ ] `findInvoices` (`@GrpcMethod('BillingService', 'FindInvoices')`)
- [ ] `readSubscription` (`@GrpcMethod('BillingService', 'ReadSubscription')`)
- [ ] `findSubscriptions` (`@GrpcMethod('BillingService', 'FindSubscriptions')`)
- [ ] `readCard` (`@GrpcMethod('BillingService', 'ReadCard')`)
- [ ] `findCards` (`@GrpcMethod('BillingService', 'FindCards')`)
- [ ] `createCard` (`@GrpcMethod('BillingService', 'CreateCard')`)
- [ ] `deleteCard` (`@GrpcMethod('BillingService', 'DeleteCard')`)
- [ ] `setDefaultCard` (`@GrpcMethod('BillingService', 'SetDefaultCard')`)
- [ ] `readPlan` (`@GrpcMethod('BillingService', 'ReadPlan')`)
- [ ] `findPlans` (`@GrpcMethod('BillingService', 'FindPlans')`)
- [ ] `findStripePlans` (`@GrpcMethod('BillingService', 'FindStripePlans')`)
- [ ] `createCustomer` (`@GrpcMethod('BillingService', 'CreateCustomer')`) — invoked by `service-account`
- [ ] `createSubscription` (`@GrpcMethod('BillingService', 'CreateSubscription')`) — invoked by `service-tenant`

#### 4. service-account (6 gRPC interfaces)
- **Controller**: `apps/service-account/src/accounts/accounts.controller.ts`
- [ ] `create` (`@GrpcMethod('AccountService', 'Create')`)
- [ ] `forgotPassword` (`@GrpcMethod('AccountService', 'ForgotPassword')`)
- [ ] `resendVerificationCode` (`@GrpcMethod('AccountService', 'ResendVerificationCode')`)
- [ ] `verifyAccount` (`@GrpcMethod('AccountService', 'VerifyAccount')`)
- [ ] `verifyActivationLink` (`@GrpcMethod('AccountService', 'VerifyActivationLink')`)
- [ ] `read` (`@GrpcMethod('AccountService', 'Read')`)

#### 5. service-tenant (11 gRPC interfaces)
- **Controllers**:
  - `apps/service-tenant/src/tenants/tenants.controller.ts`
  - `apps/service-tenant/src/members/members.controller.ts`
- [ ] `TenantsController.createTenant` (`@GrpcMethod('TenantService', 'CreateTenant')`)
- [ ] `TenantsController.updateTenant` (`@GrpcMethod('TenantService', 'UpdateTenant')`)
- [ ] `TenantsController.deleteTenant` (`@GrpcMethod('TenantService', 'DeleteTenant')`)
- [ ] `TenantsController.tenantAvailable` (`@GrpcMethod('TenantService', 'TenantAvailable')`)
- [ ] `TenantsController.readTenant` (`@GrpcMethod('TenantService', 'ReadTenant')`)
- [ ] `TenantsController.findTenant` (`@GrpcMethod('TenantService', 'FindTenant')`)
- [ ] `MembersController.inviteMember` (`@GrpcMethod('TenantService', 'InviteMember')`)
- [ ] `MembersController.updateMember` (`@GrpcMethod('TenantService', 'UpdateMember')`)
- [ ] `MembersController.deleteMember` (`@GrpcMethod('TenantService', 'DeleteMember')`)
- [ ] `MembersController.readMember` (`@GrpcMethod('TenantService', 'ReadMember')`)
- [ ] `MembersController.findMembers` (`@GrpcMethod('TenantService', 'FindMembers')`)

#### 6. service-role (3 gRPC interfaces)
- **Controller**: `apps/service-role/src/roles/roles.controller.ts`
- [ ] `readUserRoles` (`@GrpcMethod('RoleService', 'ReadUserRoles')`)
- [ ] `addUserToRole` (`@GrpcMethod('RoleService', 'AddUserToRole')`)
- [ ] `removeUserFromRole` (`@GrpcMethod('RoleService', 'RemoveUserFromRole')`)

---

### B. Inter-Service Calls (49 total)

#### 1. GraphQL Gateway (`api-admin`) → Downstream gRPC (42 calls)
- [ ] **Line 22** `apps/api-admin/src/app/modules/access-token/access-token.resolver.ts`: `ctx.rpc.access.svc.createAccess(...)`
- [ ] **Line 38** `apps/api-admin/src/app/modules/access-token/access-token.resolver.ts`: `ctx.rpc.access.svc.deleteAccess(...)`
- [ ] **Line 56** `apps/api-admin/src/app/modules/access-token/access-token.resolver.ts`: `ctx.rpc.access.svc.findAccess(...)`
- [ ] **Line 62** `apps/api-admin/src/app/modules/access-token/access-token.resolver.ts`: `ctx.rpc.access.svc.readAccess(...)`
- [ ] **Line 96** `apps/api-admin/src/app/modules/account/accounts-mutation.resolver.ts`: `ctx.rpc.account.svc.create(...)`
- [ ] **Line 104** `apps/api-admin/src/app/modules/account/accounts-mutation.resolver.ts`: `ctx.rpc.account.svc.forgotPassword(...)`
- [ ] **Line 114** `apps/api-admin/src/app/modules/account/accounts-mutation.resolver.ts`: `ctx.rpc.account.svc.resendVerificationCode(...)`
- [ ] **Line 142** `apps/api-admin/src/app/modules/account/accounts-mutation.resolver.ts`: `ctx.rpc.account.svc.verifyAccount(...)`
- [ ] **Line 163** `apps/api-admin/src/app/modules/account/accounts-mutation.resolver.ts`: `ctx.rpc.account.svc.verifyActivationLink(...)`
- [ ] **Line 31** `apps/api-admin/src/app/modules/billing/billings-mutation.resolver.ts`: `ctx.rpc.billing.svc.changeSubscription(...)`
- [ ] **Line 59** `apps/api-admin/src/app/modules/billing/billings-mutation.resolver.ts`: `ctx.rpc.billing.svc.cancelSubscription(...)`
- [ ] **Line 34** `apps/api-admin/src/app/modules/billing/billings.resolver.ts`: `ctx.rpc.billing.svc.readInvoice(...)`
- [ ] **Line 49** `apps/api-admin/src/app/modules/billing/billings.resolver.ts`: `ctx.rpc.billing.svc.findInvoices(...)`
- [ ] **Line 73** `apps/api-admin/src/app/modules/billing/billings.resolver.ts`: `ctx.rpc.billing.svc.readSubscription(...)`
- [ ] **Line 91** `apps/api-admin/src/app/modules/billing/billings.resolver.ts`: `ctx.rpc.billing.svc.findSubscriptions(...)`
- [ ] **Line 33** `apps/api-admin/src/app/modules/billing/cards.resolver.ts`: `ctx.rpc.billing.svc.readCard(...)`
- [ ] **Line 48** `apps/api-admin/src/app/modules/billing/cards.resolver.ts`: `ctx.rpc.billing.svc.findCards(...)`
- [ ] **Line 83** `apps/api-admin/src/app/modules/billing/cards.resolver.ts`: `ctx.rpc.billing.svc.createCard(...)`
- [ ] **Line 106** `apps/api-admin/src/app/modules/billing/cards.resolver.ts`: `ctx.rpc.billing.svc.deleteCard(...)`
- [ ] **Line 122** `apps/api-admin/src/app/modules/billing/cards.resolver.ts`: `ctx.rpc.billing.svc.setDefaultCard(...)`
- [ ] **Line 24** `apps/api-admin/src/app/modules/billing/plans.resolver.ts`: `ctx.rpc.billing.svc.readPlan(...)`
- [ ] **Line 30** `apps/api-admin/src/app/modules/billing/plans.resolver.ts`: `ctx.rpc.billing.svc.findPlans(...)`
- [ ] **Line 39** `apps/api-admin/src/app/modules/billing/plans.resolver.ts`: `ctx.rpc.billing.svc.findStripePlans(...)`
- [ ] **Line 32** `apps/api-admin/src/app/modules/tenant/tenant-members-mutation.resolver.ts`: `ctx.rpc.tenant.svc.inviteMember(...)`
- [ ] **Line 58** `apps/api-admin/src/app/modules/tenant/tenant-members-mutation.resolver.ts`: `ctx.rpc.tenant.svc.updateMember(...)`
- [ ] **Line 84** `apps/api-admin/src/app/modules/tenant/tenant-members-mutation.resolver.ts`: `ctx.rpc.tenant.svc.deleteMember(...)`
- [ ] **Line 39** `apps/api-admin/src/app/modules/tenant/tenant-members.resolver.ts`: `ctx.rpc.tenant.svc.readMember(...)`
- [ ] **Line 59** `apps/api-admin/src/app/modules/tenant/tenant-members.resolver.ts`: `ctx.rpc.tenant.svc.findMembers(...)`
- [ ] **Line 86** `apps/api-admin/src/app/modules/tenant/tenant-members.resolver.ts`: `ctx.rpc.account.svc.read(...)`
- [ ] **Line 36** `apps/api-admin/src/app/modules/tenant/tenants-mutation.resolver.ts`: `ctx.rpc.tenant.svc.createTenant(...)`
- [ ] **Line 55** `apps/api-admin/src/app/modules/tenant/tenants-mutation.resolver.ts`: `ctx.rpc.tenant.svc.updateTenant(...)`
- [ ] **Line 80** `apps/api-admin/src/app/modules/tenant/tenants-mutation.resolver.ts`: `ctx.rpc.tenant.svc.deleteTenant(...)`
- [ ] **Line 41** `apps/api-admin/src/app/modules/tenant/tenants.resolver.ts`: `ctx.rpc.tenant.svc.tenantAvailable(...)`
- [ ] **Line 64** `apps/api-admin/src/app/modules/tenant/tenants.resolver.ts`: `ctx.rpc.tenant.svc.readTenant(...)`
- [ ] **Line 84** `apps/api-admin/src/app/modules/tenant/tenants.resolver.ts`: `ctx.rpc.tenant.svc.findTenant(...)`
- [ ] **Line 102** `apps/api-admin/src/app/modules/tenant/tenants.resolver.ts`: `ctx.rpc.account.svc.read(...)`
- [ ] **Line 45** `apps/api-admin/src/app/modules/user/users.resolver.ts`: `ctx.rpc.role.svc.readUserRoles(...)`
- [ ] **Line 62** `apps/api-admin/src/app/modules/webhook/webhooks-mutation.resolver.ts`: `ctx.rpc.webhook.svc.createWebhook(...)`
- [ ] **Line 81** `apps/api-admin/src/app/modules/webhook/webhooks-mutation.resolver.ts`: `ctx.rpc.webhook.svc.updateWebhook(...)`
- [ ] **Line 106** `apps/api-admin/src/app/modules/webhook/webhooks-mutation.resolver.ts`: `ctx.rpc.webhook.svc.deleteWebhook(...)`
- [ ] **Line 14** `apps/api-admin/src/app/modules/webhook/webhooks.resolver.ts`: `ctx.rpc.webhook.svc.readWebhook(...)`
- [ ] **Line 31** `apps/api-admin/src/app/modules/webhook/webhooks.resolver.ts`: `ctx.rpc.webhook.svc.findWebhook(...)`

#### 2. Backend-to-Backend gRPC (7 calls)
- [ ] **Line 145** `apps/service-account/src/accounts/cqrs/commands/handlers/account/register-user.handler.ts`:  
  `this.roleClient.svc.addUserToRole({ domain: '*', userId: result.id.toString(), actor: 'user', role: 'customer' })`
- [ ] **Line 153** `apps/service-account/src/accounts/cqrs/commands/handlers/account/register-user.handler.ts`:  
  `this.billingClient.svc.createCustomer({ currency: '', number: '', name: `${result.firstname} ${result.lastname}`, email: ... })`
- [ ] **Line 105** `apps/service-tenant/src/tenants/cqrs/command/handlers/tenant/create-tenant.handler.ts`:  
  `this.billingService.svc.createSubscription({ planId: input.planId, tenantId: normalizedName, customerId: user.settings.stripeId, ... })`
- [ ] **Line 127** `apps/service-tenant/src/tenants/cqrs/command/handlers/tenant/create-tenant.handler.ts`:  
  `this.roleService.svc.addUserToRole({ role: 'owner', domain: tenant.normalizedName, actor: 'user', userId: user.id.toString() })`
- [ ] **Line 67** `apps/service-tenant/src/members/cqrs/command/handlers/member/accept-invitation.handler.ts`:  
  `this.roleService.svc.addUserToRole({ role: member.role, domain: tenant.normalizedName, actor: 'user', userId: user.id.toString() })`
- [ ] **Line 93** `apps/service-tenant/src/members/cqrs/command/handlers/member/remove-member.handler.ts`:  
  `this.roleService.svc.removeUserFromRole({ tenantId, userId: member.userId.toString() })`
- [ ] **Line 111** `apps/service-tenant/src/members/cqrs/command/handlers/member/invite-member.handler.ts`:  
  `this.roleService.svc.addUserToRole({ role: 'owner', domain: tenant.normalizedName, actor: 'user', userId: user.id.toString() })`

---

## ⚡ Automated Verification Command

You can run the deep evidence audit script anytime to programmatically verify that all 94 calls match the source lines:

```powershell
$env:PYTHONIOENCODING="utf-8"; uv run python "C:/Users/userk/.gemini/antigravity-cli/brain/59e7135e-98ba-44a5-b8c1-1f72948b4f8e/scratch/deep_audit.py"
```

*Expected result:* **AUDIT COMPLETE: 0 issues found across all 5 systems.**
