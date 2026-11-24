# Agent Extraction Validation Report

## 1. Aggregate Summary
- **Systems Evaluated**: 15
- **Schema & Partition Conformance**: 15/15 (100.0%)
- **Macro Interface Identification F1**: `0.9799` (Signature F1: `0.6975`)
- **Macro Inter-Service Class Edge F1 (SM)**: `0.9016`
- **Macro Inter-Service Interface Call F1 (IFN)**: `0.9936`

## 2. Per-System Breakdown

| System | Schema | GT Ifaces | Pred Ifaces | Iface F1 | Class Edge F1 | Iface Call F1 | ΔCHD | ΔCHM | ΔIFN | ΔSM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MS001` | PASS | 13 | 13 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS004` | PASS | 56 | 48 | `0.9231` | `1.0000` | `1.0000` | 0.0418 | 0.0957 | 0.0000 | 0.0000 |
| `MS010` | PASS | 7 | 7 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS016` | PASS | 18 | 18 | `1.0000` | `0.7907` | `0.9811` | 0.0000 | 0.0000 | 0.1111 | 0.0000 |
| `MS017` | PASS | 4 | 4 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS020` | PASS | 11 | 11 | `1.0000` | `0.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS021` | PASS | 58 | 58 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0005 | 0.0000 | 0.0000 |
| `MS031` | PASS | 16 | 16 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS032` | PASS | 11 | 11 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0278 | 0.0000 | 0.0000 |
| `MS039` | PASS | 27 | 22 | `0.8571` | `0.9333` | `0.9524` | 0.0063 | 0.0152 | 0.0000 | 0.0000 |
| `MS047` | PASS | 28 | 28 | `1.0000` | `0.8333` | `1.0000` | 0.0072 | 0.0363 | 0.0000 | 0.0000 |
| `MS070` | PASS | 125 | 127 | `0.9921` | `1.0000` | `0.9801` | 0.0335 | 0.0000 | 0.1176 | 0.0000 |
| `MS078` | PASS | 6 | 6 | `1.0000` | `1.0000` | `1.0000` | 0.0009 | 0.0000 | 0.0000 | 0.0000 |
| `MS098` | PASS | 128 | 119 | `0.9636` | `0.9667` | `0.9905` | 0.0200 | 0.0014 | 0.1111 | 0.0000 |
| `MS106` | PASS | 28 | 26 | `0.9630` | `1.0000` | `1.0000` | 0.0046 | 0.0045 | 0.0000 | 0.0000 |

## 3. Diagnostic Error Analysis (False Positives & False Negatives)

### `MS001`: Perfect Match (0 Errors)

### `MS004`
- **Interface False Negatives (8)**:
  - `('ftgo-order-service', 'ordercommandhandlers', 'approveOrder')`
  - `('ftgo-order-service', 'ordercommandhandlers', 'beginCancel')`
  - `('ftgo-order-service', 'ordercommandhandlers', 'beginReviseOrder')`
  - `('ftgo-order-service', 'ordercommandhandlers', 'confirmCancel')`
  - `('ftgo-order-service', 'ordercommandhandlers', 'confirmRevision')`
  - `('ftgo-order-service', 'ordercommandhandlers', 'rejectOrder')`
  - `('ftgo-order-service', 'ordercommandhandlers', 'undoCancel')`
  - `('ftgo-order-service', 'ordercommandhandlers', 'undoPendingRevision')`

### `MS010`: Perfect Match (0 Errors)

### `MS016`
- **Inter-Service Call False Positives (1)**:
  - `('WebApp', 'WorkshopManagementAPI', 'refdatacontroller.getcustomers')`

### `MS017`: Perfect Match (0 Errors)

### `MS020`: Perfect Match (0 Errors)

### `MS021`: Perfect Match (0 Errors)

### `MS031`: Perfect Match (0 Errors)

### `MS032`: Perfect Match (0 Errors)

### `MS039`
- **Interface False Positives (1)**:
  - `('paymentservice', 'hipstershopserver', 'ChargeServiceHandler')`
- **Interface False Negatives (6)**:
  - `('frontend', 'frontendserver', 'assistantHandler')`
  - `('frontend', 'frontendserver', 'homeHandler')`
  - `('frontend', 'frontendserver', 'logoutHandler')`
  - `('frontend', 'frontendserver', 'productHandler')`
  - `('frontend', 'frontendserver', 'viewCartHandler')`
  - `('paymentservice', 'server', 'ChargeServiceHandler')`
- **Inter-Service Call False Positives (1)**:
  - `('checkoutservice', 'paymentservice', 'hipstershopserver.chargeservicehandler')`
- **Inter-Service Call False Negatives (1)**:
  - `('checkoutservice', 'paymentservice', 'server.chargeservicehandler')`

### `MS047`: Perfect Match (0 Errors)

### `MS070`
- **Interface False Positives (2)**:
  - `('sfe', 'selfservicefrontendimpl', 'submitOverrideRequestHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'validateOverrideFieldHandler')`
- **Inter-Service Call False Negatives (3)**:
  - `('ca', 'sa', 'sqlstorageauthority.keyblocked')`
  - `('ra', 'sa', 'sqlstorageauthority.keyblocked')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.keyblocked')`

### `MS078`: Perfect Match (0 Errors)

### `MS098`
- **Interface False Negatives (9)**:
  - `('api-admin', 'accountscontroller', 'facebookAuth')`
  - `('api-admin', 'accountscontroller', 'githubAuth')`
  - `('api-admin', 'accountscontroller', 'googleAuth')`
  - `('api-admin', 'accountsmutationresolver', 'changePassword')`
  - `('api-admin', 'accountsmutationresolver', 'refreshTokens')`
  - `('api-admin', 'accountsmutationresolver', 'verifyExpireToken')`
  - `('api-admin', 'rolesresolver', 'role')`
  - `('api-admin', 'rolesresolver', 'roles')`
  - `('api-admin', 'usersmutationresolver', 'update')`
- **Inter-Service Call False Positives (1)**:
  - `('api-admin', 'service-role', 'rolescontroller.addpolicy')`

### `MS106`
- **Interface False Negatives (2)**:
  - `('newsletter_with_frontend', 'views', 'editor')`
  - `('newsletter_with_frontend', 'views', 'snippets')`
