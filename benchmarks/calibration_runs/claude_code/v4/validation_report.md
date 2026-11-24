# Agent Extraction Validation Report

## 1. Aggregate Summary
- **Systems Evaluated**: 15
- **Schema & Partition Conformance**: 15/15 (100.0%)
- **Macro Interface Identification F1**: `0.9869` (Signature F1: `0.8803`)
- **Macro Inter-Service Class Edge F1 (SM)**: `0.9055`
- **Macro Inter-Service Interface Call F1 (IFN)**: `0.9955`

## 2. Per-System Breakdown

| System | Schema | GT Ifaces | Pred Ifaces | Iface F1 | Class Edge F1 | Iface Call F1 | ΔCHD | ΔCHM | ΔIFN | ΔSM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MS001` | PASS | 13 | 13 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS004` | PASS | 56 | 56 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS010` | PASS | 7 | 7 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS016` | PASS | 18 | 18 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS017` | PASS | 4 | 4 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS020` | PASS | 11 | 11 | `1.0000` | `0.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS021` | PASS | 58 | 57 | `0.9913` | `1.0000` | `1.0000` | 0.0007 | 0.0121 | 0.0000 | 0.0000 |
| `MS031` | PASS | 16 | 16 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS032` | PASS | 11 | 11 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS039` | PASS | 27 | 27 | `0.9630` | `0.9333` | `0.9524` | 0.0012 | 0.0402 | 0.0000 | 0.0000 |
| `MS047` | PASS | 28 | 28 | `1.0000` | `0.6667` | `1.0000` | 0.0508 | 0.0036 | 0.0000 | 0.0000 |
| `MS070` | PASS | 125 | 133 | `0.9690` | `1.0000` | `0.9801` | 0.0480 | 0.0880 | 0.1176 | 0.0000 |
| `MS078` | PASS | 6 | 6 | `1.0000` | `1.0000` | `1.0000` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `MS098` | PASS | 128 | 128 | `1.0000` | `0.9831` | `1.0000` | 0.0011 | 0.0003 | 0.0000 | 0.0000 |
| `MS106` | PASS | 28 | 22 | `0.8800` | `1.0000` | `1.0000` | 0.2489 | 0.3256 | 0.0000 | 0.0000 |

## 3. Diagnostic Error Analysis (False Positives & False Negatives)

### `MS001`: Perfect Match (0 Errors)

### `MS004`: Perfect Match (0 Errors)

### `MS010`: Perfect Match (0 Errors)

### `MS016`: Perfect Match (0 Errors)

### `MS017`: Perfect Match (0 Errors)

### `MS020`: Perfect Match (0 Errors)

### `MS021`
- **Interface False Negatives (1)**:
  - `('services/tools.descartes.teastore.image', 'imageproviderendpoint', 'getState')`

### `MS031`: Perfect Match (0 Errors)

### `MS032`: Perfect Match (0 Errors)

### `MS039`
- **Interface False Positives (1)**:
  - `('paymentservice', 'hipstershopserver', 'ChargeServiceHandler')`
- **Interface False Negatives (1)**:
  - `('paymentservice', 'server', 'ChargeServiceHandler')`
- **Inter-Service Call False Positives (1)**:
  - `('checkoutservice', 'paymentservice', 'hipstershopserver.chargeservicehandler')`
- **Inter-Service Call False Negatives (1)**:
  - `('checkoutservice', 'paymentservice', 'server.chargeservicehandler')`

### `MS047`: Perfect Match (0 Errors)

### `MS070`
- **Interface False Positives (8)**:
  - `('sfe', 'selfservicefrontendimpl', 'UnpauseForm')`
  - `('sfe', 'selfservicefrontendimpl', 'UnpauseStatus')`
  - `('sfe', 'selfservicefrontendimpl', 'UnpauseSubmit')`
  - `('sfe', 'selfservicefrontendimpl', 'makeOverrideRequestFormHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'overrideAutoApprovedSuccessHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'overrideRequestSubmittedSuccessHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'submitOverrideRequestHandler')`
  - `('sfe', 'selfservicefrontendimpl', 'validateOverrideFieldHandler')`
- **Inter-Service Call False Negatives (3)**:
  - `('ca', 'sa', 'sqlstorageauthority.keyblocked')`
  - `('ra', 'sa', 'sqlstorageauthority.keyblocked')`
  - `('wfe2', 'sa', 'sqlstorageauthorityro.keyblocked')`

### `MS078`: Perfect Match (0 Errors)

### `MS098`: Perfect Match (0 Errors)

### `MS106`
- **Interface False Negatives (6)**:
  - `('awsmail', 'tasks', 'send_aws_mail_attachment')`
  - `('confirmation', 'tasks', 'send_mail')`
  - `('invitation', 'tasks', 'send_mail')`
  - `('newsletter', 'tasks', 'send_mail')`
  - `('registration', 'tasks', 'send_mail')`
  - `('send_certificate', 'tasks', 'send_mail')`
