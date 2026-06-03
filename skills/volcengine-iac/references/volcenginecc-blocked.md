# Volcenginecc Blocked Verification Notes

This file records resources whose Terraform configuration reached `validate`/`plan` or an initial API call but could not be fully verified because the current account lacks service enablement, permissions, quota, or required external dependencies.

## KMS

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_kms_key_ring` | Blocked | `ServiceNotEnabled: KMS service not open yet` during create |
| `volcenginecc_kms_key` | Not applied | Depends on key ring |
| `volcenginecc_kms_secret` | Not applied | Depends on key TRN |

Minimal configuration validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`, but `apply` failed immediately on key ring creation. This was retried on 2026-05-30 and failed with the same service-not-enabled error:

```text
ServiceNotEnabled: KMS_ServiceNotOpen: KMS service not open yet, please open the service and try again later.
TypeName: Volcengine::KMS::KeyRing
Operation: CREATE
OperationStatus: FAILED
```

Latest retry evidence:

```text
EventTime: 2026-05-30T08:24:50+08:00
TaskID: task-1ffc9f7d-ef13-4590-be4d-2430f0b43faa
ServiceNotEnabled: KMS_ServiceNotOpen: KMS service not open yet, please open the service and try again later.
TypeName: Volcengine::KMS::KeyRing
Operation: CREATE
OperationStatus: FAILED
```

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-kms-current` used only `volcenginecc_kms_key_ring` to avoid putting secret values in state before the service is enabled. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded; apply failed with the same service boundary:

```text
EventTime: 2026-05-30T10:50:04+08:00
TaskID: task-b13684ba-4f37-475c-8529-71bbd8f88c19
ServiceNotEnabled: KMS_ServiceNotOpen: KMS service not open yet, please open the service and try again later.
TypeName: Volcengine::KMS::KeyRing
Operation: CREATE
OperationStatus: FAILED
```

Retried the same key-ring-only shape again on 2026-05-30 after other products had been verified. `terraform fmt`, `init -backend=false`, `validate`, and `plan` still succeeded; `apply` failed before creating any KMS resource:

```text
EventTime: 2026-05-30T12:24:07+08:00
TaskID: task-85c61cf3-f35d-465d-879e-d6903ed4d10d
ServiceNotEnabled: KMS_ServiceNotOpen: KMS service not open yet, please open the service and try again later.
TypeName: Volcengine::KMS::KeyRing
Operation: CREATE
OperationStatus: FAILED
```

Retried the same key-ring-only shape again on 2026-05-30 at 13:55 with the current account. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; `apply` still failed at service enablement before creating any KMS resource:

```text
EventTime: 2026-05-30T13:55:43+08:00
TaskID: task-a70d7af3-2c3a-4886-8228-bffc47008781
ServiceNotEnabled: KMS_ServiceNotOpen: KMS service not open yet, please open the service and try again later.
TypeName: Volcengine::KMS::KeyRing
Operation: CREATE
OperationStatus: FAILED
```

No KMS resources were created; Terraform state remained empty.

After KMS service permission was granted, a 2026-05-30 retry in `/tmp/volcenginecc-kms-retry-20260530150751` created keyring `cc-iac-kms-retry` (`02014a48-361a-4f62-85c0-948f59f1c41b`) and key `cc-iac-kms-retry-key` (`137517dd-b6e2-485b-a0a7-fef491277712`) successfully. Creating `volcenginecc_kms_secret` still failed because Credential Manager / Secrets Manager is not open:

```text
EventTime: 2026-05-30T15:08:48+08:00
TaskID: task-10a4a11d-f91c-4c62-b23b-402425ec8c62
AccessDenied: SecretsManagerServiceNotOpen: Secrets Manager service not open yet. Please open the service and try again later.
TypeName: Volcengine::KMS::Secret
Operation: CREATE
OperationStatus: FAILED
```

Destroy scheduled the key for deletion instead of physically removing it, then keyring deletion failed because the pending-deletion key still counts toward the keyring:

```text
EventTime: 2026-05-30T15:09:05+08:00
TaskID: task-97bec380-9ec8-4aca-8de9-12093615fb93
InvalidRequest: InvalidKeyringDeletion: Unable to delete keyring [cc-iac-kms-retry]. Please delete [1] keys in the keyring first.
TypeName: Volcengine::KMS::KeyRing
Operation: DELETE
OperationStatus: FAILED
```

Cloud-side check showed the key in `PendingDelete` with `ScheduleDeleteTime = "2026-06-06T15:09:03.374+08:00"` and the keyring still present with `KeyCount = 1`. Do not promote KMS to a clean verified example until `kms_key` destroy behavior and keyring cleanup are acceptable for shared examples. After the scheduled key deletion completes, delete keyring `02014a48-361a-4f62-85c0-948f59f1c41b` / `cc-iac-kms-retry` and remove the temporary Terraform state.

When KMS is enabled for the account, retry with this shape:

```hcl
resource "volcenginecc_kms_key_ring" "main" {
  keyring_name = "cc-iac-kms"
  keyring_type = "CustomKeyring"
  project_name = "default"
  description  = "volcenginecc KMS example keyring"
}

resource "volcenginecc_kms_key" "main" {
  keyring_name     = volcenginecc_kms_key_ring.main.keyring_name
  key_name         = "cc-iac-kms-key"
  key_spec         = "SYMMETRIC_256"
  key_usage        = "ENCRYPT_DECRYPT"
  protection_level = "SOFTWARE"
  origin           = "CloudKMS"
  multi_region     = false
}

resource "volcenginecc_kms_secret" "main" {
  secret_name    = "cc-iac-kms/generic"
  version_name   = "v1"
  project_name   = "default"
  secret_type    = "Generic"
  encryption_key = volcenginecc_kms_key.main.trn
  secret_value = jsonencode({
    example = "non-sensitive-verification-value"
  })
}
```

Do not store real AK/SK, passwords, or certificates in repository examples or temporary Terraform state during verification.

## Entry Traffic

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_clb_clb` | Verified | Private CLB create/destroy succeeded; see `volcenginecc-clb.md` |
| `volcenginecc_clb_certificate` | Verified | Server certificate with traditional RSA private key created/no-op/destroyed; see `volcenginecc-clb.md` |
| `volcenginecc_clb_acl` | Verified | Standalone CLB ACL create/no-op/destroy succeeded; see `volcenginecc-clb.md` |
| `volcenginecc_clb_server_group` | Blocked | `AccessDenied: Forbidden: You are not authorized to perform operations on the specified service` during create |
| `volcenginecc_clb_listener` | Not applied | Depends on CLB server group |
| `volcenginecc_clb_rule` | Not applied | Depends on CLB listener and server group |
| `volcenginecc_alb_health_check_template` | Verified | Create/destroy succeeded; see `volcenginecc-alb.md` |
| `volcenginecc_alb_acl` | Verified | Standalone ALB ACL create/no-op/destroy succeeded; see `volcenginecc-alb.md` |
| `volcenginecc_alb_customized_cfg` | Verified | Standalone ALB customized config create/no-op/destroy succeeded; see `volcenginecc-alb.md` |
| `volcenginecc_alb_load_balancer` | Verified | Private Basic ALB create/no-op/destroy succeeded; see `volcenginecc-alb.md` |
| `volcenginecc_alb_server_group` | Verified | Empty IP-type HTTP server group create/no-op/destroy succeeded; see `volcenginecc-alb.md` |
| `volcenginecc_alb_listener` | Verified | Disabled HTTP listener create/no-op/destroy succeeded; see `volcenginecc-alb.md` |
| `volcenginecc_alb_rule` | Verified | Basic host/path forwarding rule create/no-op/destroy succeeded; see `volcenginecc-alb.md` |
| `volcenginecc_alb_certificate` | Verified for Server | Server certificate with traditional RSA private key created/no-op/destroyed; CA certificate remains unverified |
| `volcenginecc_clb_nlb_security_policy` | Whitelist-blocked | Custom NLB TLS policy planned but create failed requesting whitelist key `nlb_tls_allow` |
| `volcenginecc_clb_nlb` | Lifecycle-only | Private NLB create/destroy succeeded, but the required server group has persistent no-op drift |
| `volcenginecc_clb_nlb_server_group` | Drift-blocked | Created/destroyed only after explicit session persistence settings; follow-up plans never converged |
| `volcenginecc_clb_nlb_listener` | Lifecycle-only | TCP listener created/destroyed, but depends on drift-blocked NLB server group |
| `volcenginecc_apig_gateway` | Verified | Private-only APIG gateway create/no-op/destroy succeeded; see `volcenginecc-apig.md` |
| `volcenginecc_apig_gateway_service` | Verified | Private HTTP gateway service create/no-op/destroy succeeded; see `volcenginecc-apig.md` |
| `volcenginecc_apig_upstream` | Whitelist-blocked | Domain upstream plan succeeded but create failed with `OperationDenied.AccountNotInWhitelist` |
| `volcenginecc_apig_upstream_source` | Dependency/whitelist-blocked | Requires APIG upstream capability plus a real VKE cluster or Nacos source; Nacos auth would store credentials |
| `volcenginecc_apig_custom_domain` | Dependency-blocked | Requires a real custom domain and certificate lifecycle |

CLB partial verification in `cn-beijing`: VPC, subnet, route table, and private CLB created successfully. Creating `clb_server_group` then failed with:

```text
AccessDenied: Forbidden: You are not authorized to perform operations on the specified service.
TypeName: Volcengine::CLB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

Latest CLB full-path retry in `cn-beijing`: VPC `vpc-3nqzotfd5g2rk931ebwxnb6a`, subnet `subnet-3nqzpif38t3i8931eb4qdwc4`, route table `vtb-3nqzrq5x7oxkw931eba51ryr`, and private CLB `clb-rrncm96jzgu8v0x57hsj4rw` created successfully. Creating an empty IP-type `volcenginecc_clb_server_group` failed with the same permission error before listener/rule creation:

```text
EventTime: 2026-05-30T09:47:16+08:00
TaskID: task-df977422-63ab-4b3f-8bd3-24f13f6f45a0
AccessDenied: Forbidden: You are not authorized to perform operations on the specified service.
TypeName: Volcengine::CLB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

The private CLB, route table, subnet, and VPC were destroyed successfully and final Terraform state was empty. Retry `clb_server_group`, `clb_listener`, and `clb_rule` after the account has CLB server group create permission.

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-clb-full-current` used a private CLB plus empty IP-type server group, disabled HTTP listener, and forwarding rule. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded for all seven resources. Apply created VPC `vpc-1joqambwuq22o1n7amqmd6hw9`, subnet `subnet-3pt6y91u9dxc06csxywfxhxgo`, route table `vtb-bu2m2luvc1s05h0b2uogd2lg`, and private CLB `clb-13f4n1lwlyvwg3n6nu5o4oogc`, then failed on `volcenginecc_clb_server_group` before listener/rule creation with the same permission boundary:

```text
EventTime: 2026-05-30T11:47:38+08:00
TaskID: task-a5a5beb5-3ec1-4d61-8d8a-c5db32fe5ad1
AccessDenied: Forbidden: You are not authorized to perform operations on the specified service.
TypeName: Volcengine::CLB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

Destroy removed the private CLB, route table, subnet, and VPC; final Terraform state was empty. `DescribeLoadBalancers --LoadBalancerName cc-iac-clb-full-clb` and `DescribeVpcs --VpcName cc-iac-clb-full-vpc` both returned `TotalCount: 0`.

After the user reported CLB permissions were added, a 2026-05-30 retry in `/tmp/volcenginecc-clb-retry-20260530151553` used the verified private CLB example plus empty IP-type `clb_server_group`, disabled HTTP listener, and forwarding rule. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded for all seven resources. Apply created VPC `vpc-1jofdkvmh3chs1n7amp8zgobf`, subnet `subnet-btwj0z1pg8ao5h0b2tooistd`, route table `vtb-3nri5k9phdtds931eb76g20v`, and private CLB `clb-mj3kjzm0nzeo5smt1bu6xglv`, then `clb_server_group` still failed before listener/rule creation:

```text
EventTime: 2026-05-30T15:17:10+08:00
TaskID: task-c070289a-f526-4327-94ba-051de99c346c
AccessDenied: Forbidden: You are not authorized to perform operations on the specified service.
TypeName: Volcengine::CLB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

Destroy removed the private CLB, route table, subnet, and VPC. Final Terraform state was empty, `ve clb DescribeLoadBalancers --body '{"LoadBalancerName":"cc-iac-clb-clb"}'` returned `TotalCount: 0`, and exact VPC-name matching for `cc-iac-clb-vpc` returned no rows. The missing permission is still the Cloud Control `Volcengine::CLB::ServerGroup` create path, not the base CLB instance path.

After another permission grant, a 2026-05-30 retry in `/tmp/volcenginecc-clb-retry-202605301716` used a private CLB, empty IP-type server group, disabled HTTP listener, and forwarding rule. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded for all seven resources. Apply created VPC `vpc-bt98xtvws6bk5h0b2u88a9ee`, subnet `subnet-iix49uzfbev474o8ctlv9nlv`, route table `vtb-iix5x9sxew3k74o8cttyknla`, and private CLB `clb-13f6mjnsonpxc3n6nu4l8x2b9`, then `clb_server_group` still failed before listener/rule creation:

```text
EventTime: 2026-05-30T17:22:32+08:00
TaskID: task-32122718-81fd-479b-aaf6-294fd8b9825f
AccessDenied: Forbidden: You are not authorized to perform operations on the specified service.
TypeName: Volcengine::CLB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

Destroy removed the private CLB, route table, subnet, and VPC. Final Terraform state was empty, `ve clb DescribeLoadBalancers --body '{"LoadBalancerName":"cc-iac-clb-1716-clb"}'` returned `TotalCount: 0`, exact VPC-name matching for `cc-iac-clb-1716-vpc` returned `TotalCount: 0`, and checking ENIs by the deleted VPC ID returned `InvalidVpc.NotFound`. The missing permission remains the Cloud Control `Volcengine::CLB::ServerGroup` create path.

APIG private gateway/service verification in `cn-beijing`: a one-subnet private standard gateway using `1c2g`, 2 replicas, and `enable_public_network = false` created successfully, followed by a private HTTP gateway service. The clean no-op shape omits `resource_spec.clb_spec_code` and `resource_spec.public_network_billing_type`; setting them while public network is disabled caused a replacement diff because the API read both back as empty strings. Gateway create took about 2 minutes, service create about 15 seconds, and the service returned a private default domain.

`volcenginecc_apig_upstream` with `source_type = "Domain"` and `example.com:80` planned successfully but failed on create:

```text
EventTime: 2026-05-30T10:56:42+08:00
TaskID: task-73d60fc0-0523-40a4-b40d-2e20692c2c1c
AccessDenied: OperationDenied.AccountNotInWhitelist: Operation is denied because the account is not in the whitelist.
TypeName: Volcengine::APIG::Upstream
Operation: CREATE
OperationStatus: FAILED
```

`volcenginecc_apig_upstream_source` was not applied after the account-level upstream whitelist failure. The resource is not a generic domain upstream: it imports a VKE/Kubernetes or Nacos source into APIG. A reusable example would require either a verified VKE cluster source or a real Nacos registry; the Nacos `basic.password` field would also be stored in Terraform state. Retry only after `apig_upstream` is allowed in the account, using a VKE source first to avoid registry credentials in shared examples.

APIG destroy caveat: service and gateway deletion succeeded, but subnet deletion initially failed with `InvalidSubnet.InUse` while service-managed ENIs were being released, and VPC deletion then failed on APIG-created security groups. Recovery was: wait until `ve vpc DescribeNetworkInterfaces --SubnetId <subnet_id>` returns empty, delete only the APIG-created `apig-sg-*` groups in the temporary VPC, rerun `terraform destroy`, and confirm final state is empty. `ListGateways`, `ListGatewayServices`, and VPC lookup confirmed no temporary APIG/VPC resources remained.

ALB partial verification in `cn-beijing`: health check template created successfully. A private Basic ALB and an IP-type empty ALB server group both planned successfully, then failed during apply:

```text
OperationFailed.QueryIAM: The request on the specified resource failed due to the query on IAM failed.
TypeName: Volcengine::ALB::LoadBalancer
Operation: CREATE
OperationStatus: FAILED
```

```text
OperationFailed.QueryIAM: The request on the specified resource failed due to the query on IAM failed.
TypeName: Volcengine::ALB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

Latest ALB full-path retry in `cn-beijing`: VPC `vpc-btgbikchi8745h0b2tl0oqg2`, two subnets, and two custom route tables created successfully. Creating both private Basic `volcenginecc_alb_load_balancer` and empty IP-type `volcenginecc_alb_server_group` still failed before listener/rule creation:

```text
EventTime: 2026-05-30T09:49:51+08:00
TaskID: task-3d426203-1e9f-47f3-b29f-4d0dc6148a10
GeneralServiceException: OperationFailed.QueryIAM: The request on the specified resource failed due to the query on IAM failed.
TypeName: Volcengine::ALB::LoadBalancer
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T09:49:12+08:00
TaskID: task-4d221f6a-1047-4795-98be-19312e2ab407
InvalidRequest: OperationFailed.QueryIAM: The request on the specified resource failed due to the query on IAM failed.
TypeName: Volcengine::ALB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

Destroy hit one transient `InvalidOperation.Conflict` on a route table, then a retry succeeded. All ALB retry dependencies were destroyed and final Terraform state was empty. Retry `alb_load_balancer`, `alb_server_group`, `alb_listener`, and `alb_rule` after the account/IAM path permits ALB create calls.

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-alb-full-current` used a private Basic ALB, empty IP-type HTTP server group, disabled HTTP listener, and path rule. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded after setting `alb_server_group.health_check.port = 0`; despite the docs marking the field optional, provider validation requires it even when health checks are disabled. Apply created VPC `vpc-1joqy4o8e0y681n7ampwc2o1p`, subnets `subnet-bu3d538nz85c5h0b2tulmndq` and `subnet-bu3c85f3a8zk5h0b2u21qkgy`, and route tables `vtb-bu3fljsjrsao5h0b2u0it3hh` and `vtb-bu3etrfvnytc5h0b2uf0dngc`, then ALB load balancer and server group failed with the same IAM query boundary:

```text
EventTime: 2026-05-30T11:51:47+08:00
TaskID: task-3a0c429a-3315-4855-a5c4-d593250af5ed
GeneralServiceException: OperationFailed.QueryIAM: The request on the specified resource failed due to the query on IAM failed.
TypeName: Volcengine::ALB::LoadBalancer
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T11:51:09+08:00
TaskID: task-e2367ab6-6400-49c3-bae2-868611c98bdd
InvalidRequest: OperationFailed.QueryIAM: The request on the specified resource failed due to the query on IAM failed.
TypeName: Volcengine::ALB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

Destroy removed both route tables, both subnets, and the VPC; final Terraform state was empty. `DescribeLoadBalancers --LoadBalancerName cc-iac-alb-full-alb` and `DescribeVpcs --VpcName cc-iac-alb-full-vpc` both returned `TotalCount: 0`.

After the user reported ALB permissions were added, a 2026-05-30 retry in `/tmp/volcenginecc-alb-retry-20260530151836` used a private Basic ALB, two subnets, empty IP-type HTTP server group, disabled HTTP listener, and forwarding rule. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply created VPC `vpc-1jofy4ick3ta81n7amp1sph42`, subnets `subnet-1jofzcqmi03cw1n7amqj9mhee` and `subnet-3psmciuxaoav46csxywektip1`, and route tables `vtb-iik3yfkbnshs74o8ctt6soz0` and `vtb-iik3hvozn7y874o8cti6f0v5`, then ALB load balancer and server group still failed:

```text
EventTime: 2026-05-30T15:20:02+08:00
TaskID: task-82bd2f77-5ae3-47ac-b34e-2e8d6143b0c8
GeneralServiceException: OperationFailed.QueryIAM: The request on the specified resource failed due to the query on IAM failed.
TypeName: Volcengine::ALB::LoadBalancer
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T15:19:23+08:00
TaskID: task-ccbab9a2-958c-4726-b9cd-bd19c8fdda45
InvalidRequest: OperationFailed.QueryIAM: The request on the specified resource failed due to the query on IAM failed.
TypeName: Volcengine::ALB::ServerGroup
Operation: CREATE
OperationStatus: FAILED
```

Destroy initially hit transient `InvalidOperation.Conflict` on one route table; a retry removed the remaining route table, subnet, and VPC. Final Terraform state was empty, `ve alb DescribeLoadBalancers --body '{"LoadBalancerName":"cc-iac-alb-retry-alb"}'` returned `TotalCount: 0`, and exact VPC-name matching for `cc-iac-alb-retry-vpc` returned no rows. The account/IAM path for ALB load balancer and server group create is still blocked.

After another permission grant, a 2026-05-30 retry in `/tmp/volcenginecc-alb-retry-202605301724` verified the full private Basic ALB path. The first apply created VPC `vpc-1a0rzey9a3eo08nvepk2xwrf0`, subnets `subnet-3pszlhz9fvk746csxyvz8ri0v` and `subnet-3nqxjaef1aiv4931ec7sx360`, route tables `vtb-btabgqpa08w05h0b2tfen2t1` and `vtb-iixl1qe8bk7474o8cu0inh61`, server group `rsp-1pf9tk34n89vk845wfadmo0m9`, private ALB `alb-1pf9tk72pgdts845wf9wsiyyj`, listener `lsn-1pf9tk91qkfsw845wfa7etpj5`, and rule `rule-1pf9tkkvx8rnk845wfayvebx8`.

The first follow-up plan showed server group health-check drift because the API reads disabled health checks back with defaults:

```text
~ http_code    = "http_2xx,http_3xx" -> "http_2xx"
~ http_version = "HTTP1.0" -> "HTTP1.1"
~ method       = "HEAD" -> "GET"
+ cross_zone_enabled = "on"
```

Aligning the configuration to the API defaults (`method = "HEAD"`, `http_version = "HTTP1.0"`, `http_code = "http_2xx,http_3xx"`) and omitting `cross_zone_enabled` produced a clean no-op plan. Destroy then removed rule, listener, server group, ALB, route tables, subnets, and VPC. Final Terraform state was empty, `ve alb DescribeLoadBalancers --body '{"LoadBalancerName":"cc-iac-alb-1724-alb"}'` returned `TotalCount: 0`, `ve alb DescribeServerGroups --body '{"ServerGroupName":"cc-iac-alb-1724-sg"}'` returned `TotalCount: 0`, exact VPC-name matching returned `TotalCount: 0`, and checking ENIs by the deleted VPC ID returned `InvalidVpc.NotFound`. The verified example now lives in `assets/examples/volcenginecc-alb`.

Formal verification of `assets/examples/volcenginecc-alb` in `/tmp/volcenginecc-alb-example-verify-202605301733` then created VPC `vpc-3nqz7ptxs0etc931ebqmyyo0`, server group `rsp-xoaavdcpzaww54ov5fdq8lgi`, private ALB `alb-bdgz9vls883k8dv40o8v1rkb`, listener `lsn-1pf9tl8kalfcw845wfafraq0l`, and rule `rule-bdgz9xktca2o8dv40obuj4s5`. A follow-up `terraform plan -detailed-exitcode` returned `No changes`. The first destroy hit one transient route-table `InvalidOperation.Conflict` after ALB/service ENI deletion; `DescribeNetworkInterfaces` showed no ENIs, and a second destroy removed the remaining route table, subnet, and VPC. Final Terraform state was empty, `ve alb DescribeLoadBalancers --body '{"LoadBalancerName":"cc-iac-alb-alb"}'` returned `TotalCount: 0`, `ve alb DescribeServerGroups --body '{"ServerGroupName":"cc-iac-alb-sg"}'` returned `TotalCount: 0`, exact VPC-name matching for `cc-iac-alb-vpc` returned `TotalCount: 0`, and checking ENIs by the deleted VPC ID returned `InvalidVpc.NotFound`.

ALB server certificate verification in `cn-beijing`: a self-signed `Server` certificate with a traditional RSA private key created successfully, had a clean no-op plan, and destroyed successfully. The created certificate ID was `cert-xoa99pcjymtc54ov5ehq2k2k`; final Terraform state was empty. A first server-certificate attempt with OpenSSL's default PKCS#8 private key failed with:

```text
InvalidPrivateKey.Malformed: The specified PrivateKey is malformed.
TypeName: Volcengine::ALB::Certificate
Operation: CREATE
OperationStatus: FAILED
```

The earlier ALB CA certificate attempt used a one-day self-signed CA certificate and failed with:

```text
InvalidCACertificate.Malformed: The specified CACertificate is malformed. The specified ca certificate's format is malformed.
TypeName: Volcengine::ALB::Certificate
Operation: CREATE
OperationStatus: FAILED
```

All temporary CLB/ALB resources were destroyed; final Terraform state was empty for both verification directories.

Standalone ALB/CLB ACL verification in `cn-beijing`: `volcenginecc_alb_acl` and `volcenginecc_clb_acl` both created with one TEST-NET CIDR entry, had a clean no-op plan, and destroyed successfully. Created IDs were `acl-1pf9s99tpguf4845wfatdciln` for ALB and `acl-mj0domhqg4xs5smt1al6e28u` for CLB. ACL creation took about 21s and deletion about 15s. These ACL examples verify policy group lifecycle only; listener attachment still depends on verified listener resources.

CLB server certificate verification in `cn-beijing`: a self-signed server certificate with a traditional RSA private key created successfully, had a clean no-op plan, and destroyed successfully. The created certificate ID was `cert-mj0pptquolxc5smt1b2ycpwb`; final Terraform state was empty. A first server-certificate attempt with OpenSSL's default PKCS#8 private key failed with:

```text
InvalidPrivateKey.Malformed: The specified PrivateKey is malformed.
TypeName: Volcengine::CLB::Certificate
Operation: CREATE
OperationStatus: FAILED
```

Standalone ALB customized config verification in `cn-beijing`: `volcenginecc_alb_customized_cfg` created with content `client_max_body_size 60M;\r\nkeepalive_timeout 77s;\r\n`, had a clean no-op plan, and destroyed successfully. Created ID was `ccfg-bdgxt19g2rcw8dv40nfok4lk`. Creation took about 15s and deletion about 6s. This verifies config-policy lifecycle only; listener association still depends on verified listener resources.

NLB TLS security policy retry in `cn-beijing`: `volcenginecc_clb_nlb_security_policy` validated and planned with `tls_versions = ["TLSv1.2"]` and common TLSv1.2 cipher suites, but create failed before any resource was created:

```text
RequestForbidden: Forbidden: You are not authorized to perform operations on the specified service; apply for the following whitelist key, 'nlb_tls_allow'.
TypeName: Volcengine::CLB::NLBSecurityPolicy
Operation: CREATE
TaskID: task-1e5a30a6-eab8-47d2-bf1d-4db51dfc95a4
EventTime: 2026-05-30T07:04:48+08:00
```

No NLB security policy resources were created; Terraform state remained empty. Retry after the `nlb_tls_allow` whitelist is granted.

NLB main path retry in `cn-beijing`: a private intranet NLB, IP-type empty TCP server group, and disabled TCP listener validated and planned successfully. NLB instance creation succeeded with ID `nlb-2wf9pvtq3gutcz9cqtob7oz4`; TCP listener creation succeeded with ID `lsn-2wf9pvzn6t0qoz9cquqgyaws`; all resources later destroyed successfully and final Terraform state was empty.

The first two server group create attempts failed because the provider/API sent an invalid session persistence timeout when session persistence was disabled or timeout was omitted:

```text
InvalidRequest: InvalidSessionPersistenceTimeout.Malformed: The specified SessionPersistenceTimeout is malformed.
TypeName: Volcengine::CLB::NLBServerGroup
Operation: CREATE
TaskID: task-d766a4e9-3a15-49b9-8e14-02619aa81bfc
EventTime: 2026-05-30T08:06:08+08:00
```

```text
InvalidRequest: InvalidSessionPersistenceTimeout.Malformed: The specified SessionPersistenceTimeout is malformed.
TypeName: Volcengine::CLB::NLBServerGroup
Operation: CREATE
TaskID: task-4e82e196-6159-4ec1-94d1-9d048bf63c4a
EventTime: 2026-05-30T08:07:16+08:00
```

Setting `session_persistence_enabled = true` and `session_persistence_timeout = 1000` allowed the server group to create with ID `rsp-11znzhiq70xz449iegfzg4u28`. However, every follow-up plan proposed an in-place update on Optional+Computed fields (`connection_drain_timeout`, `health_check` nested defaults, and `servers`) even after applying that update. `lifecycle.ignore_changes` on those fields, and even `ignore_changes = all`, did not suppress the provider-planned update. Do not add a verified NLB example until `volcenginecc_clb_nlb_server_group` can reach a clean no-op plan.

Minimal retry shape that created but drifted:

```hcl
resource "volcenginecc_clb_nlb_server_group" "app" {
  server_group_name           = "cc-iac-nlb-sg-app"
  project_name                = "default"
  vpc_id                      = volcenginecc_vpc_vpc.main.vpc_id
  protocol                    = "TCP"
  type                        = "ip"
  scheduler                   = "wrr"
  ip_address_version          = "ipv4"
  any_port_enabled            = false
  connection_drain_enabled    = false
  preserve_client_ip_enabled  = false
  session_persistence_enabled = true
  session_persistence_timeout = 1000
  proxy_protocol_type         = "off"
  timestamp_remove_enabled    = true

  health_check = {
    enabled             = false
    healthy_threshold   = 3
    interval            = 10
    method              = "GET"
    timeout             = 3
    type                = "TCP"
    unhealthy_threshold = 3
  }
}
```

## Network Interconnect

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_cen_cen` | Verified | CEN with same-account VPC attachment create/no-op/destroy succeeded; see `volcenginecc-cen.md` |
| `volcenginecc_cen_bandwidth_package` | Not applied | Depends on CEN permission and creates a billable bandwidth package |
| `volcenginecc_cen_inter_region_bandwidth` | Dependency-blocked | Requires CEN and CEN bandwidth package |
| `volcenginecc_cen_route_entry` | Dependency-blocked | Requires a created CEN attached to a network instance |
| `volcenginecc_cen_service_route_entry` | Dependency-blocked | Requires a created CEN and service VPC route target |
| `volcenginecc_cen_grant_instance` | Dependency/cross-account blocked | Requires another account's CEN ID and owner ID |
| `volcenginecc_directconnect_direct_connect_gateway` | Verified | Direct Connect gateway create/no-op/destroy succeeded; see `volcenginecc-directconnect.md` |
| `volcenginecc_directconnect_virtual_interface` | Dependency-blocked | Requires Direct Connect gateway and a real physical dedicated line ID |
| `volcenginecc_directconnect_gateway_route` | Dependency-blocked | Requires Direct Connect gateway and a VIF/CEN/TransitRouter next hop |
| `volcenginecc_transitrouter_transit_router` | Verified | TransitRouter create/no-op/destroy succeeded; see `volcenginecc-transitrouter.md` |
| `volcenginecc_transitrouter_transit_router_route_table` | Dependency-blocked | Requires a verified TransitRouter instance |
| `volcenginecc_transitrouter_vpc_attachment` | Dependency-blocked | Requires TransitRouter plus VPC/subnet attach points |
| `volcenginecc_transitrouter_vpn_attachment` | Dependency-blocked | Requires TransitRouter plus a VPN connection |
| `volcenginecc_transitrouter_peer_attachment` | Dependency/billable blocked | Requires two TransitRouter instances plus a bandwidth package |
| `volcenginecc_transitrouter_transit_router_route_entry` | Dependency-blocked | Requires a route table and valid attachment next hop |
| `volcenginecc_privatelink_endpoint_service` | Verified | Interface endpoint service backed by private CLB create/no-op/destroy succeeded; see `volcenginecc-privatelink.md` |
| `volcenginecc_privatelink_vpc_endpoint` | Verified | Same-account consumer endpoint create/no-op/destroy succeeded and reached `Connected`; see `volcenginecc-privatelink.md` |
| `volcenginecc_privatelink_vpc_endpoint_connection` | Advanced-path blocked | Auto-accepted baseline does not need explicit connection resource; verify separately only for manual connection/resource allocation workflows |

CEN minimal configuration validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`, using a temporary VPC attached through `instances`. VPC creation succeeded, then CEN creation failed:

```text
EventTime: 2026-05-30T11:14:35+08:00
TaskID: task-d9a02042-7e55-4f04-a5a9-6a7ce9f16a3d
AccessDenied: User is not authorized to perform: cen:CreateCen on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::CEN::CEN
Operation: CREATE
OperationStatus: FAILED
```

Recovery: `terraform destroy` removed the temporary VPC successfully. Final `terraform state list` returned empty, and `ve vpc DescribeVpcs --VpcName cc-iac-cen-vpc-current` returned `TotalCount: 0`.

After `cen:CreateCen` was granted, a 2026-05-30 retry in `/tmp/volcenginecc-cen-retry-202605301553` verified the CEN+single-VPC attachment lifecycle. CEN `cc-iac-cen-retry-cen` created with ID `cen-rrxduo4y1mo0v0x58jvanh7` and attached VPC `vpc-iindwi39pudc74o8cuxqgrn2`. `terraform plan -detailed-exitcode` returned `No changes`; destroy removed the CEN first, then the VPC. Final Terraform state was empty, `ve cen DescribeCens --body '{"CenName":"cc-iac-cen-retry-cen"}'` returned `TotalCount: 0`, and exact VPC-name matching for `cc-iac-cen-retry-vpc` returned no rows.

The verified example now lives in `assets/examples/volcenginecc-cen`; validation notes and pitfalls live in `references/volcenginecc-cen.md`. Start with the CEN+single-VPC attachment shape before trying bandwidth packages, inter-region bandwidth, published routes, or cross-account grants:

```hcl
resource "volcenginecc_cen_cen" "main" {
  cen_name     = "cc-iac-cen"
  description  = "volcenginecc CEN example"
  project_name = "default"

  instances = [
    {
      instance_id        = volcenginecc_vpc_vpc.main.vpc_id
      instance_owner_id  = var.account_id
      instance_region_id = "cn-beijing"
      instance_type      = "VPC"
    }
  ]
}
```

CEN bandwidth packages, inter-region bandwidth, published routes, and cross-account grants are still excluded from the default example because they add billable or external-account dependencies.

DirectConnect gateway retry in `cn-beijing`: the minimal gateway-only configuration used `enable_ipv_6 = false`, project `default`, and one tag. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply failed before a gateway ID was created:

```text
EventTime: 2026-05-30T13:32:58+08:00
TaskID: task-9431d2ba-2a4b-42bf-9952-2880ea6e93eb
AccessDenied: AccessDenied: User is not authorized to perform: directconnect:CreateDirectConnectGateway on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::DirectConnect::DirectConnectGateway
Operation: CREATE
OperationStatus: FAILED
```

No DirectConnect resources were created; Terraform state remained empty. Retry `directconnect_direct_connect_gateway` after the create permission is granted. Add `directconnect_virtual_interface` only with a real physical dedicated line ID, and add `directconnect_gateway_route` only after a valid VIF, CEN, or TransitRouter next hop exists.

After `directconnect:CreateDirectConnectGateway` was granted, a 2026-05-30 retry in `/tmp/volcenginecc-directconnect-retry-202605301556` verified the standalone Direct Connect gateway lifecycle. Gateway `cc-iac-dc-retry-gw` created with ID `dcg-aq8wpaltal8g17ng66bqjovt`. `terraform plan -detailed-exitcode` returned `No changes`; destroy removed the gateway, final Terraform state was empty, and `ve directconnect DescribeDirectConnectGateways --body '{"DirectConnectGatewayName":"cc-iac-dc-retry-gw"}'` returned `TotalCount: 0`. The verified example now lives in `assets/examples/volcenginecc-directconnect`; validation notes and pitfalls live in `references/volcenginecc-directconnect.md`.

TransitRouter retry in `cn-beijing`: the minimal router-only configuration used `asn = 64512`, `multicast_enabled = false`, project `default`, and one tag. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply failed before a TransitRouter ID was created:

```text
EventTime: 2026-05-30T13:35:09+08:00
TaskID: task-8f8d470c-8ee4-42c7-99af-2039e1a9e4a6
AccessDenied: AccessDenied: User is not authorized to perform: transitrouter:CreateTransitRouter on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::TransitRouter::TransitRouter
Operation: CREATE
OperationStatus: FAILED
```

No TransitRouter resources were created; Terraform state remained empty. Retry `transitrouter_transit_router` after the create permission is granted. Add route tables and VPC attachments only after the base router reaches clean no-op; peer attachments also need a bandwidth package and should be treated as billable inter-region resources.

After `transitrouter:CreateTransitRouter` was granted, a 2026-05-30 retry in `/tmp/volcenginecc-transitrouter-retry-202605301556` verified the standalone TransitRouter lifecycle. TransitRouter `cc-iac-tr-retry` created with ID `tr-mjpyegwsyeps5smt1a042pya`, `asn = 64512`, and `multicast_enabled = false`. `terraform plan -detailed-exitcode` returned `No changes`; destroy removed the router, final Terraform state was empty, and `ve transitrouter DescribeTransitRouters --body '{"TransitRouterName":"cc-iac-tr-retry"}'` returned `TotalCount: 0`. The verified example now lives in `assets/examples/volcenginecc-transitrouter`; validation notes and pitfalls live in `references/volcenginecc-transitrouter.md`.

PrivateLink CLB endpoint service configuration validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`. The retry used a temporary VPC, subnet, route table, private CLB, and an Interface endpoint service with private DNS disabled. VPC, subnet, route table, and CLB all created successfully, then endpoint service creation failed:

```text
EventTime: 2026-05-30T11:18:51+08:00
TaskID: task-4ca99cb4-83cf-45c6-b91c-cc77f95f824d
AccessDenied: User is not authorized to perform: privatelink:CreateVpcEndpointService on resource: trn:clb:cn-beijing:2109984414:clb/clb-rrnxl0iu0n40v0x58bp58rj,trn:iam::2109984414:project/default
TypeName: Volcengine::PrivateLink::EndpointService
Operation: CREATE
OperationStatus: FAILED
```

Recovery: `terraform destroy` removed the private CLB, route table, subnet, and VPC successfully. Final `terraform state list` returned empty; `ve clb DescribeLoadBalancers` for the temporary CLB returned `TotalCount: 0`; `ve vpc DescribeVpcs --VpcName cc-iac-pl-current-vpc` returned `TotalCount: 0`; `ve privatelink DescribeVpcEndpointServices --ServiceResourceType CLB --ServiceType Interface` returned `TotalCount: 0`.

After `privatelink:CreateVpcEndpointService` was granted, a 2026-05-30 retry in `/tmp/volcenginecc-privatelink-retry-202605301601` verified the full auto-accepted Interface PrivateLink path. The first apply created the service VPC/subnet/route table, private CLB `clb-mj3su951ld6o5smt1bkinzsv`, and endpoint service `epsvc-1mxfpfwqz9e681qigxqv417g5`. A follow-up plan returned `No changes`.

A second apply added a consumer VPC/subnet/route table/security group and endpoint `ep-1mxfpg2o2lk3k1qigxqfoigf8`. The first endpoint apply hit the common transient VPC security-group conflict, then a rerun succeeded:

```text
EventTime: 2026-05-30T16:04:43+08:00
TaskID: task-1323b43c-338c-45c4-b5ea-fbe48293f5ff
InvalidRequest: InvalidOperation.Conflict: The specified resource operation conflicts.
TypeName: Volcengine::VPC::SecurityGroup
Operation: CREATE
OperationStatus: FAILED
```

After the rerun, `ve privatelink DescribeVpcEndpoints --body '{"EndpointName":"cc-iac-pl-retry-endpoint"}'` showed the endpoint with `ConnectionStatus = "Connected"`, so no explicit `volcenginecc_privatelink_vpc_endpoint_connection` resource was needed for the baseline. The full stack then had a clean no-op plan.

Destroy removed endpoint, endpoint service, CLB, security group, route tables, subnets, and both VPCs. Final Terraform state was empty. `DescribeVpcEndpointServices` for service ID `epsvc-1mxfpfwqz9e681qigxqv417g5` returned `TotalCount: 0`, `DescribeVpcEndpoints` for endpoint ID `ep-1mxfpg2o2lk3k1qigxqfoigf8` no longer returned that endpoint, `ve clb DescribeLoadBalancers --body '{"LoadBalancerName":"cc-iac-pl-retry-clb"}'` returned `TotalCount: 0`, and exact VPC-name matching for both temporary VPCs returned no rows.

The verified example now lives in `assets/examples/volcenginecc-privatelink`; validation notes and pitfalls live in `references/volcenginecc-privatelink.md`. Keep `private_dns_enabled = false` for the baseline test; enabling Private DNS adds public domain verification.

## VKE Remaining Resources

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_vke_cluster` | Verified | No-node managed cluster create/no-op/destroy succeeded |
| `volcenginecc_vke_node_pool` | Verified | Zero-replica node pool create/no-op/destroy succeeded |
| `volcenginecc_vke_kubeconfig` | Verified | Private kubeconfig create/no-op/destroy succeeded |
| `volcenginecc_vke_addon` | Verified | Managed `pod-identity-webhook` addon create/no-op/destroy succeeded; see `volcenginecc-vke.md` |
| `volcenginecc_vke_default_node_pool` | Verified | Default node pool create/no-op/destroy succeeded on a zero-worker cluster; see `volcenginecc-vke.md` |
| `volcenginecc_vke_permission` | Dependency-bound | Requires a real cluster plus a deliberate IAM user/role/account grantee ID and authorization model |
| `volcenginecc_vke_node` | Dependency-blocked | Requires an existing ECS instance to attach as a worker node |

`vke_node_pool` parameter narrowing during verification:

```text
MissingParameter.NodeConfig: The required parameter NodeConfig is missing.
MissingParameter.NodeConfig.Security.Login: The required parameter NodeConfig.Security.Login is missing.
InvalidParameter.AutoScaling.MaxReplicas: The specified parameter AutoScaling.MaxReplicas is invalid.
```

The verified zero-replica fix is: include real `node_config`, include `security.login`, and set `min_replicas = 0`, `desired_replicas = 0`, `max_replicas = 1`.

`vke_addon` was later verified with a deliberate on-demand managed addon:

```hcl
resource "volcenginecc_vke_addon" "pod_identity_webhook" {
  cluster_id  = volcenginecc_vke_cluster.main.cluster_id
  name        = "pod-identity-webhook"
  version     = "v0.1.1"
  deploy_mode = "Managed"
}
```

Creation took 5m26s and deletion took 5m17s. `ve vke ListAddons` showed the addon as `Running` before Terraform finished waiting, so allow several minutes for Cloud Control waiter convergence.

`vke_default_node_pool` was verified with only security login and cluster security groups:

```hcl
resource "volcenginecc_vke_default_node_pool" "default" {
  cluster_id = volcenginecc_vke_cluster.main.cluster_id

  node_config = {
    security = {
      login = {
        password = var.node_password_base64
      }
      security_group_ids = tolist(volcenginecc_vke_cluster.main.cluster_config.security_group_ids)
    }
  }
}
```

`vke_node` remains dependency-blocked because it attaches an existing ECS instance to a node pool:

```hcl
resource "volcenginecc_vke_node" "worker" {
  cluster_id         = volcenginecc_vke_cluster.main.cluster_id
  node_pool_id       = volcenginecc_vke_node_pool.zero.node_pool_id
  instance_id        = var.existing_ecs_instance_id
  keep_instance_name = true
}
```

Do not add a verified `vke_node` example until an ECS instance can be created or selected, attached, re-planned to no-op, detached/deleted, and the cleanup order is proven.

`vke_permission` remains dependency-bound because it grants RBAC to a real IAM principal on a real cluster:

```hcl
resource "volcenginecc_vke_permission" "visitor" {
  role_domain    = "namespace"
  cluster_id     = var.cluster_id
  namespace      = "kube-public"
  role_name      = "vke:visitor"
  is_custom_role = false
  grantee_id     = var.iam_user_id
  grantee_type   = "User"
}
```

Do not add a shared verified example until the target grantee is created/imported intentionally, the permission reaches `Success`, a no-op plan is clean, and revocation on destroy is proven. Avoid granting permissions to the caller account as a shortcut during verification.

## ECS Image

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_ecs_deployment_set` | Verified | Standalone placement set create/no-op/destroy succeeded; see `volcenginecc-ecs-extras.md` |
| `volcenginecc_ecs_hpc_cluster` | Verified | Standalone HPC cluster create/no-op/destroy succeeded; see `volcenginecc-ecs-extras.md` |
| `volcenginecc_ecs_launch_template_version` | Verified | Version 2 on a real launch template create/no-op/destroy succeeded; see `volcenginecc-ecs-launch-template-version.md` |
| `volcenginecc_ecs_image` | Dependency-bound | Requires a valid system disk snapshot, instance, snapshot group, or import image URL |

`ecs_image` is not part of the verified ECS examples because the low-cost EBS snapshot example creates a data disk snapshot, while ECS custom images require a system disk snapshot, whole-instance source, snapshot group, or imported image object:

```hcl
resource "volcenginecc_ecs_image" "from_system_snapshot" {
  image_name  = "cc-iac-image"
  snapshot_id = var.system_disk_snapshot_id
  project_name = "default"
}
```

Do not create an image from a data disk snapshot. Retry only after a throwaway ECS instance with a system disk snapshot is available, or after a test image object is staged in TOS for import. Verify create, no-op, and image deletion because custom images can keep snapshot references and block cleanup.

## IAM Federation and Access Keys

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_iam_user` | Verified | User create/no-op/destroy succeeded without login password or access key; see `volcenginecc-iam-users.md` |
| `volcenginecc_iam_group` | Verified | Group create/no-op/destroy succeeded with global read-only policy scope; see `volcenginecc-iam-users.md` |
| `volcenginecc_iam_oidc_provider` | Verified | Public issuer OIDC provider create/no-op/destroy succeeded; see `volcenginecc-iam-oidc-provider.md` |
| `volcenginecc_iam_saml_provider` | Verified | Role SSO SAML provider create/no-op/destroy succeeded; see `volcenginecc-iam-saml-provider.md` |
| `volcenginecc_iam_accesskey` | Sensitive-state blocked | Successful create would write `secret_access_key` into Terraform state |

Do not add `iam_accesskey` to reusable examples. The provider schema exposes `secret_access_key` as a read-only attribute, so a create writes the generated secret to Terraform state even if outputs are sensitive. If a deployment requires access keys, keep the state encrypted and access-controlled, rotate immediately, and never commit state or plans.

Do not use placeholder IdP URLs, fake thumbprints, or generated private keys in shared examples. Retry only with a disposable IdP metadata document whose certificate is public metadata, not a private key.

## CloudIdentity

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_cloudidentity_group` | Permission-blocked | `AccessDenied: User is not authorized to perform: cloudidentity:CreateGroup` during create |
| `volcenginecc_cloudidentity_permission_set` | Permission-blocked | `AccessDenied: User is not authorized to perform: cloudidentity:CreatePermissionSet` during create |
| `volcenginecc_cloudidentity_user` | Not applied | Requires CloudIdentity permission and writes initial password to Terraform state |
| `volcenginecc_cloudidentity_permission_set_assignment` | Dependency-blocked | Requires permission set plus real principal and target account IDs |
| `volcenginecc_cloudidentity_permission_set_provisioning` | Dependency-blocked | Requires permission set plus real target account ID |
| `volcenginecc_cloudidentity_user_provisioning` | Dependency-blocked | Requires real principal and target account IDs |

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-cloudidentity-current` used only a manual group and a system `ReadOnlyAccess` permission set, avoiding user password state and cross-account assignment/provisioning. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply failed before any resource IDs were created:

```text
EventTime: 2026-05-30T13:30:42+08:00
TaskID: task-2ab0edcc-530c-4d33-b9ee-a31f4d769cfa
AccessDenied: AccessDenied: User is not authorized to perform: cloudidentity:CreateGroup on resource:
TypeName: Volcengine::CloudIdentity::Group
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T13:30:42+08:00
TaskID: task-2fa24a9f-c5e8-4baf-b682-f1c06fca0c5a
AccessDenied: AccessDenied: User is not authorized to perform: cloudidentity:CreatePermissionSet on resource:
TypeName: Volcengine::CloudIdentity::PermissionSet
Operation: CREATE
OperationStatus: FAILED
```

No CloudIdentity resources were created; Terraform state remained empty. Retry group and permission set only after CloudIdentity create permissions are granted. Keep `cloudidentity_user` out of default examples unless the user explicitly accepts password-in-state risk, and add assignment/provisioning only with deliberate principal and target account IDs.

## Organization and Specialty Services

Resources not promoted to default cloud deployment examples:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_organization_organization` | Business-semantics blocked | Creates or manages the enterprise organization itself; requires a dedicated test organization and explicit owner approval |
| `volcenginecc_organization_unit` | Business-semantics blocked | Mutates enterprise organization structure; requires a known parent OU and cleanup policy |
| `volcenginecc_organization_account` | Business-semantics blocked | Creates or manages member accounts and may store account password/contact data in Terraform state |
| `volcenginecc_organization_service_control_policy` | Business-semantics blocked | Creates account/OU guardrail policies; a deny policy can break access if attached incorrectly |
| `volcenginecc_ark_endpoint` | Product/cost dependency blocked | Requires a real ModelArk foundation/custom model choice and creates a billable inference endpoint |
| `volcenginecc_escloud_instance` | Product/cost/sensitive-state blocked | Creates a billable search cluster and requires admin password stored in Terraform state |
| `volcenginecc_hbase_instance` | Product/cost blocked | Creates a billable HBase cluster with multi-node storage footprint |
| `volcenginecc_emr_cluster` | Product/cost/sensitive-state blocked | Creates a billable EMR cluster and can require ECS keypair/password/TOS/bootstrap dependencies |
| `volcenginecc_emr_node_group` | Dependency-blocked | Requires a running EMR cluster |
| `volcenginecc_emr_cluster_user` | Dependency/sensitive-state blocked | Requires a running EMR cluster and user credential lifecycle |
| `volcenginecc_emr_cluster_user_group` | Dependency-blocked | Requires a running EMR cluster and user/group model |
| `volcenginecc_gtm_pool` | Dependency-blocked | Requires an existing GTM instance ID; the provider exposes pool only, not GTM instance creation |
| `volcenginecc_fwcenter_dns_control_policy` | Dependency/business-policy blocked | Requires an existing Internet Firewall instance ID and creates a domain denylist policy |

These resources were inspected against provider docs but not applied in the shared cloud deployment baseline because they either alter organization-level business state, create high-cost specialty service instances, require an existing product instance that the provider cannot create, or would store credentials/private operational data in Terraform state. Do not add default examples for them without an explicit product-specific goal, cost approval, and a disposable test account or instance.

## RDS MySQL Extras

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_rdsmysql_endpoint` | Drift-blocked for default example | Custom direct endpoint create/delete succeeded, but no-op plan tried to update `addresses.domain_prefix` and failed because the domain prefix already exists |
| `volcenginecc_rdsmysql_backup` | API-blocked | `backup_method = "Physical"` and `backup_method = "Logical"` both failed with `InvalidParameter: 参数BackupMethod值无效` |

The custom endpoint retry used a verified MySQL instance in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`:

```hcl
resource "volcenginecc_rdsmysql_endpoint" "custom" {
  instance_id         = volcenginecc_rdsmysql_instance.main.instance_id
  endpoint_name       = "${local.prefix}-custom"
  endpoint_type       = "Custom"
  connection_mode     = "Direct"
  nodes               = "Primary"
  read_write_mode     = "ReadWrite"
  read_write_spliting = false

  addresses = [
    {
      domain_prefix  = "cciacmysql"
      dns_visibility = false
      port           = "3306"
    }
  ]
}
```

Creation succeeded and returned endpoint ID `mysql-ae90e8397914-custom-058a`, and later destroy deleted it successfully. The first follow-up plan was not clean because readback dropped `addresses.domain_prefix`; reapply attempted to update the already-created address and failed:

```text
OperationDenied_Common: domain prefix already exists
TypeName: Volcengine::RDSMySQL::Endpoint
Operation: UPDATE
OperationStatus: FAILED
```

Do not include `rdsmysql_endpoint` in generated examples until a shape produces create, no-op plan, and destroy without suppressing meaningful drift.

Manual backup creation was tested with both documented method values. The `Physical` attempt failed:

```text
InvalidParameter: 参数BackupMethod值无效
TypeName: Volcengine::RDSMySQL::Backup
Operation: CREATE
OperationStatus: FAILED
```

The `Logical` attempt with `backup_type = "Full"` and database-level `backup_meta` failed with the same invalid backup method error. Keep `rdsmysql_backup` out of generated examples until a working API enum or provider fix is verified.

During this retry, dependent database/account creation initially failed with `InstanceIsNotRunning` immediately after the instance became visible. Waiting about 90 seconds and re-running apply succeeded. A later destroy attempt hit the same status window while deleting the account; after retry, database/account, instance, allowlist, endpoint, VPC, subnet, and route table were all destroyed and final Terraform state was empty.

## veFaaS Remaining Resources

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_vefaas_function` | Verified | Function create/no-op/destroy succeeded with a valid Python ZIP containing root-level `index.py`; see `volcenginecc-vefaas.md` |
| `volcenginecc_vefaas_release` | Partially verified | Successful release create/no-op succeeded; delete is not supported after final `finished` status |
| `volcenginecc_vefaas_timer` | Verified | Disabled timer trigger create/no-op/destroy succeeded after release |
| `volcenginecc_vefaas_sandbox` | Lifecycle-only/drift-blocked | Native/image function, release, sandbox create/destroy succeeded with a pre-cached public sandbox image, but follow-up plans drift on `volcenginecc_vefaas_release` computed fields. |
| `volcenginecc_vefaas_kafka_trigger` | Dependency-blocked | Requires Kafka instance/topic and SASL credentials; current Kafka instance create still fails with Cloud Control `ServiceInternalError` |

The initial empty-ZIP function create succeeded, but release failed with:

```text
revision_build_failed: function failed to build revision source: failed to download and validate source: failed to validate entry file for runtime: python3.9/v1, err: Unable to find function entry (index.py). Please make sure the root directory contains function entry.
```

Updating that existing function from an empty ZIP to a valid ZIP failed server-side:

```text
ServiceInternalError: InternalServiceError: Internal error occurred: panic: [happened in biz handler, method=VeFaaSServiceV2.UpdateFunction, please check the panic at the server side] runtime error: slice bounds out of range [:-1].
TypeName: Volcengine::VEFAAS::Function
Operation: UPDATE
OperationStatus: FAILED
```

The verified path creates the function with valid ZIP source from the start.

Creating a timer before a successful release failed with:

```text
InvalidRequest: InvalidOperation: function has not been fully released yet, please release it first
TypeName: Volcengine::VEFAAS::Timer
Operation: CREATE
OperationStatus: FAILED
```

Deleting a successful release failed with:

```text
AccessDenied: InvalidOperation: This operation is not supported., release already in final status: finished
TypeName: Volcengine::VEFAAS::Release
Operation: DELETE
OperationStatus: FAILED
```

For cleanup after a successful release, run `terraform state rm volcenginecc_vefaas_release.main`, then destroy the timer/function resources.

Creating a sandbox for the verified Python function failed with:

```text
AccessDenied: InvalidOperation: fn is not webserver sandbox function, not support to create sandbox instance
TypeName: Volcengine::VEFAAS::Sandbox
Operation: CREATE
OperationStatus: FAILED
```

A later native/image sandbox retry used `runtime = "native/v1"`, `source_type = "image"`, `source = "nginx:1.25-alpine"`, `command = "nginx -g 'daemon off;'"`, `port = 80`, and `cpu_strategy = "always"` on the function, release, and sandbox path. `fmt`, `init`, `validate`, and `plan` passed, but apply failed on function create:

```text
NotFound: ResourceNotFound: Sandbox image not found in pre cache sandbox image list, you need to precache your sandbox image first
TypeName: Volcengine::VEFAAS::Function
Operation: CREATE
TaskID: task-ada9f3fc-e2a4-4d18-9edf-e0bb4700ce5d
EventTime: 2026-05-30T06:46:56+08:00
```

No resources were created by the native/image retry; Terraform state remained empty. Do not add a verified `vefaas_sandbox` example until a pre-cached sandbox image is available and function create, release, sandbox create, no-op plan, and destroy all succeed.

Current-account sandbox retries on 2026-05-30 found usable pre-cached sandbox images via `ve vefaas ListSandboxImages --body '{"ImageType":"public","PageNumber":1,"PageSize":5}'` and `--body '{"ImageType":"private","PageNumber":1,"PageSize":5}'`. `ImageType` must be lowercase; uppercase values were rejected as invalid. The public All-in-one image group was available, and the account had four successful historical pre-cache tickets.

Two pre-cached-image shapes still failed at sandbox startup:

```text
EventTime: 2026-05-30T12:08:19+08:00
TaskID: task-513c24a4-8820-4d03-b57b-d70ed7985092
InvalidOperation: error_code: "function_exited", error_message "function exited unexpectedly(exit status 127) ... bash: ./run.sh: No such file or directory"
TypeName: Volcengine::VEFAAS::Sandbox
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T12:09:44+08:00
TaskID: task-0ee19f79-96c6-46f0-a8b8-eb6f2dc72e78
InvalidOperation: error_code: "function_exited", error_message "function exited unexpectedly(exit status 1) ... /etc/sudoers.d/: Is a directory"
TypeName: Volcengine::VEFAAS::Sandbox
Operation: CREATE
OperationStatus: FAILED
```

The working lifecycle shape used public image `enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:1.9.3`, `image_id = "kwdxncbgsn"`, and command `python3 -m http.server 8080 --bind 0.0.0.0`. Function, release, and sandbox created successfully; sandbox reached `Ready`. Follow-up plan was not clean because `volcenginecc_vefaas_release` proposed an in-place update on computed fields. Cleanup removed the finished release from Terraform state, then destroyed sandbox and function. Sandbox destroy took about 66s; final Terraform state was empty.

## RDS SQL Server

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_rdsmssql_allow_list` | Lifecycle-verified | Create/no-op/delete succeeded after permissions were granted; deletion may need to wait for association count to drop to 0 |
| `volcenginecc_rdsmssql_instance` | Destroy-caveat | Basic SQL Server 2019 Standard create and no-op succeeded; VPC cleanup can remain blocked by delayed RDS service-managed security group release |

Minimal configuration validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`. The first apply created only the network dependencies, then failed on allowlist creation:

```text
AccessDenied: User is not authorized to perform: rds_mssql:CreateAllowList on resource: trn:iam::2109984414:project/default,trn:vpc:cn-beijing:2109984414:securitygroup/*
TypeName: Volcengine::RDSMsSQL::AllowList
Operation: CREATE
OperationStatus: FAILED
```

A second apply without the allowlist dependency was used only to test the instance API and failed with:

```text
AccessDenied: User is not authorized to perform: rds_mssql:CreateDBInstance on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::RDSMsSQL::Instance
Operation: CREATE
OperationStatus: FAILED
```

Temporary VPC, subnet, and route table resources were destroyed successfully; final Terraform state was empty.

Latest allowlist-only retry in `cn-beijing`: a standalone `volcenginecc_rdsmssql_allow_list` validated and planned successfully, then failed with the same permission denial before any resources were created:

```text
EventTime: 2026-05-30T09:53:23+08:00
TaskID: task-61f39a52-4f2b-45be-9eb3-8aa66e603def
AccessDenied: User is not authorized to perform: rds_mssql:CreateAllowList on resource: trn:iam::2109984414:project/default,trn:vpc:cn-beijing:2109984414:securitygroup/*
TypeName: Volcengine::RDSMsSQL::AllowList
Operation: CREATE
OperationStatus: FAILED
```

Retried the standalone allowlist shape again on 2026-05-30 at 13:59 with allow list name `cc-iac-mssql-allow-retry`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; apply still failed before creating any resource:

```text
EventTime: 2026-05-30T13:59:24+08:00
TaskID: task-56cba346-4b98-4ee3-a470-3736c56b671d
AccessDenied: User is not authorized to perform: rds_mssql:CreateAllowList on resource: trn:iam::2109984414:project/default,trn:vpc:cn-beijing:2109984414:securitygroup/*
TypeName: Volcengine::RDSMsSQL::AllowList
Operation: CREATE
OperationStatus: FAILED
```

Terraform state remained empty. This permission boundary was resolved by later grants; the remaining issue is destroy-time backend cleanup.

After the user reported MSSQL permissions were added, a 2026-05-30 retry in `/tmp/volcenginecc-rdsmssql-retry-20260530152214` used a standalone allowlist plus minimal Basic SQL Server 2019 Standard instance, VPC, subnet, and route table. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded. The allowlist created successfully with ID `acl-3b64796c92ed45eb9d375ca193bc60a8`, proving `rds_mssql:CreateAllowList` was granted. The instance failed three times, including after 90s and 180s waits, because RDS MSSQL could not see the Terraform-created VPC even though `ve vpc DescribeVpcs` returned it as `Available`:

```text
EventTime: 2026-05-30T15:23:26+08:00
TaskID: task-8e6cf6eb-29ed-4b89-bd28-8485d695e9ed
NotFound: VpcIDNotFound: The specified VpcID does not exist.
TypeName: Volcengine::RDSMsSQL::Instance
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T15:25:23+08:00
TaskID: task-823b9378-9b34-4ac3-b308-41c348298ec4
NotFound: VpcIDNotFound: The specified VpcID does not exist.
TypeName: Volcengine::RDSMsSQL::Instance
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T15:29:12+08:00
TaskID: task-19721463-7c7e-48a1-ab29-94c8ae786d8e
NotFound: VpcIDNotFound: The specified VpcID does not exist.
TypeName: Volcengine::RDSMsSQL::Instance
Operation: CREATE
OperationStatus: FAILED
```

Discovery confirmed `cn-beijing-a` supports `SQLServer_2019_Std` Basic and spec `rds.mssql.3il.x8.medium.s1`, so this is not an obvious zone/spec mismatch. Destroy removed the allowlist, route table, subnet, and VPC; final Terraform state was empty. `ve rdsmssql DescribeAllowLists` for `cc-iac-mssql-retry-allow` returned an empty list, `ve rdsmssql DescribeDBInstances` for `cc-iac-mssql-retry-instance` returned `Total: 0`, and exact VPC-name matching for `cc-iac-mssql-retry-vpc` returned no rows. Retry the instance with an older, pre-existing disposable VPC/subnet or after the RDS MSSQL VPC visibility path is confirmed.

After another permission grant, a 2026-05-30 retry in `/tmp/volcenginecc-rdsmssql-retry-202605301743` created the full minimal SQL Server path successfully. The configuration used VPC `vpc-btcto3qrmvb45h0b2u52k12s`, subnet `subnet-3pt1kgmjawoow6csxywfwxwl9`, route table `vtb-1jp3m05rryfpc1n7amp7sqooh`, allowlist `acl-158fda4205e5461da6b089629737e11f`, and Basic SQL Server 2019 Standard instance `mssql-07cef429b3c4` with spec `rds.mssql.3il.x8.medium.s1`. Create took about 4m37s and a follow-up `terraform plan -detailed-exitcode` returned `No changes`, so the earlier `VpcIDNotFound` no longer reproduces.

RDS SQL Server is promoted only as a lifecycle/destroy-caveat example, not as a clean verified example, because destroy did not fully converge in the same run. The instance delete returned success after about 10s, and later `DescribeDBInstances` returned `Total: 0`. However, subnet deletion initially failed while two RDS service-managed ENIs were still attached; after about 60s, `DescribeNetworkInterfaces --SubnetId subnet-3pt1kgmjawoow6csxywfwxwl9` returned `TotalCount: 0` and the allowlist `AssociatedInstanceNum` dropped to `0`. A second destroy removed the allowlist and subnet, but VPC deletion remained blocked by the RDS service-managed security group `sg-ij00cwlytvk074o8ctvy0oul`:

```text
EventTime: 2026-05-30T17:51:50+08:00
TaskID: task-3cc04316-3f9f-4063-b644-97760ee23017
InvalidRequest: InvalidVpc.InUse: The specified VPC has dependent resource of a security group.
TypeName: Volcengine::VPC::VPC
Operation: DELETE
OperationStatus: FAILED
```

Manual deletion of `sg-ij00cwlytvk074o8ctvy0oul` failed because it is service-managed:

```text
Forbidden: You are not authorized to perform operations on the specified security group.
The specified security group is a service-managed security group.
```

After another 3 minutes, `DescribeDBInstances` still returned `Total: 0` and `DescribeNetworkInterfaces --VpcId vpc-btcto3qrmvb45h0b2u52k12s` still returned `TotalCount: 0`, but `DescribeSecurityGroups --VpcId vpc-btcto3qrmvb45h0b2u52k12s` still showed the service-managed security group plus the default security group. After another 5 minutes, the service-managed security group was still present, and a final `terraform destroy` failed with the same VPC dependency:

```text
EventTime: 2026-05-30T18:04:52+08:00
TaskID: task-9b75ebb2-e898-4f59-a3c2-aab9481aa060
InvalidRequest: InvalidVpc.InUse: The specified VPC has dependent resource of a security group.
TypeName: Volcengine::VPC::VPC
Operation: DELETE
OperationStatus: FAILED
```

Current residue after the retry: Terraform state in `/tmp/volcenginecc-rdsmssql-retry-202605301743` contains only `volcenginecc_vpc_vpc.main` for VPC `vpc-btcto3qrmvb45h0b2u52k12s`; the temporary binary `tfplan` was deleted because it may contain sensitive variables. Cloud-side residue is VPC `vpc-btcto3qrmvb45h0b2u52k12s` plus service-managed security group `sg-ij00cwlytvk074o8ctvy0oul` (`Mssql Managed Security Group`) and its default security group. Instance `mssql-07cef429b3c4`, allowlist `acl-158fda4205e5461da6b089629737e11f`, RDS ENIs, route table, and subnet were deleted or no longer visible. Continue cleanup by waiting for the RDS service-managed security group to disappear, then rerun `terraform destroy` to remove the VPC. Keep MSSQL out of the clean verified count until this cleanup behavior is understood.

After the user successfully created and released a separate RDS MySQL instance, a 2026-05-31 retry in `/tmp/volcenginecc-rdsmssql-cleanretry-20260531023059` used the shared `assets/examples/volcenginecc-rdsmssql` shape with prefix `cc-iac-mssql-0531`, CIDR `10.118.0.0/16`, and the 60s `time_sleep` create/destroy delay. Apply succeeded: VPC `vpc-ijd4bbvlew3k74o8cuk7m3e9`, subnet `subnet-1a11bcepqxips8nvepldtwmnj`, route table `vtb-btmyu76jr7r45h0b2u5kvw61`, allowlist `acl-9ca58061348c442380285e16d3c8870e`, and SQL Server instance `mssql-e2b854194c05` were created successfully. Instance creation took 4m45s and a follow-up plan returned `No changes`.

Destroy order was correct with the updated dependency graph: SQL Server instance deleted first in 12s, then `time_sleep` waited 60s, then the allowlist, route table, and subnet all deleted successfully. VPC deletion still failed because the RDS service-managed security group remained:

```text
EventTime: 2026-05-31T02:40:06+08:00
TaskID: task-6ba1dc41-9c93-433c-9020-496808bf4584
InvalidRequest: InvalidVpc.InUse: The specified VPC has dependent resource of a security group.
TypeName: Volcengine::VPC::VPC
Operation: DELETE
OperationStatus: FAILED
```

Cloud-side checks after the failed destroy showed `DescribeDBInstances` `Total: 0`, `DescribeAllowLists` empty, and `DescribeNetworkInterfaces --VpcId vpc-ijd4bbvlew3k74o8cuk7m3e9` `TotalCount: 0`, but `DescribeSecurityGroups --VpcId vpc-ijd4bbvlew3k74o8cuk7m3e9` still returned default security group `sg-ijd4bhsor20w74o8cv2crync` and service-managed MSSQL security group `sg-ijdv4ls74um874o8cullvbdk`. `DescribeVpcs --VpcIds ["vpc-ijd4bbvlew3k74o8cuk7m3e9"]` returned `TotalCount: 0`, so the VPC and security-group views are inconsistent. An additional 60s wait followed by another `terraform destroy` failed with the same VPC security-group dependency:

```text
EventTime: 2026-05-31T02:42:03+08:00
TaskID: task-044b65e3-3492-42cb-bc3e-8a6edcf1d54c
InvalidRequest: InvalidVpc.InUse: The specified VPC has dependent resource of a security group.
TypeName: Volcengine::VPC::VPC
Operation: DELETE
OperationStatus: FAILED
```

Current residue from the 2026-05-31 retry: Terraform state in `/tmp/volcenginecc-rdsmssql-cleanretry-20260531023059` contains only `volcenginecc_vpc_vpc.main` for VPC `vpc-ijd4bbvlew3k74o8cuk7m3e9`; cloud-side residue is the VPC/security-group index entry plus service-managed MSSQL security group `sg-ijdv4ls74um874o8cullvbdk` and default security group `sg-ijd4bhsor20w74o8cv2crync`. Keep this example lifecycle-verified only. The 60s sleep fixes Terraform ordering and the short allowlist/subnet release window, but does not fix this service-managed SG cleanup issue.

The shared lifecycle example uses this shape:

```hcl
resource "volcenginecc_rdsmssql_allow_list" "app" {
  project_name    = "default"
  allow_list_name = "cc-iac-mssql-allow"
  allow_list_type = "IPv4"
  user_allow_list = "10.96.0.0/16"
}

resource "volcenginecc_rdsmssql_instance" "main" {
  node_spec              = "rds.mssql.3il.x8.medium.s1"
  zone_id                = "cn-beijing-a"
  subnet_id              = volcenginecc_vpc_subnet.main.subnet_id
  db_engine_version      = "SQLServer_2019_Std"
  instance_type          = "Basic"
  storage_space          = 20
  vpc_id                 = volcenginecc_vpc_vpc.main.vpc_id
  instance_name          = "cc-iac-mssql-instance"
  super_account_password = var.mssql_password
  server_collation       = "Chinese_PRC_CI_AS"
  time_zone              = "China Standard Time"
  project_name           = "default"
  maintenance_time       = "18:00Z-21:59Z"
  allow_list_ids         = [volcenginecc_rdsmssql_allow_list.app.allow_list_id]

  charge_info = {
    charge_type = "PostPaid"
  }
}
```

`assets/examples/volcenginecc-rdsmssql` exists as a lifecycle/destroy-caveat example only. It adds a `time_sleep` 60s create/destroy delay between network readiness and SQL Server lifecycle, but operators should still poll `DescribeDBInstances`, `DescribeNetworkInterfaces`, `DescribeAllowLists`, and `DescribeSecurityGroups` every 60s before rerunning destroy if the VPC is blocked. `super_account_password` is sensitive in plan output but will still be stored in Terraform state.

## MongoDB

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_mongodb_allow_list` | Permission-blocked | `AccessDenied: User is not authorized to perform: mongodb:CreateAllowList` during create |
| `volcenginecc_mongodb_instance` | Dependency/permission-blocked | Requires MongoDB allowlist permission and creates a billable instance; not applied after allowlist permission failed |
| `volcenginecc_mongodb_ssl_state` | Dependency-blocked | Requires a successfully created MongoDB instance |

Read-only discovery in `cn-beijing` succeeded: `ve mongodb DescribeAvailabilityZones --body '{"RegionId":"cn-beijing"}'` returned normal zones `cn-beijing-a` through `cn-beijing-d`; `ve mongodb DescribeNodeSpecs --body '{"RegionId":"cn-beijing"}'` returned a minimal ReplicaSet node spec `mongo.1c2g` with `MinStorage = 20`.

Standalone MongoDB allowlist verification in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`: `terraform fmt`, `init`, `validate`, and `plan` succeeded, then apply failed before any resource was created:

```text
EventTime: 2026-05-30T10:35:52+08:00
TaskID: task-5b14fa52-e44d-432f-a704-738ac3de09a3
AccessDenied: User is not authorized to perform: mongodb:CreateAllowList on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::MongoDB::AllowList
Operation: CREATE
OperationStatus: FAILED
```

`terraform state list` was empty after the failed apply. `ve mongodb DescribeAllowLists --body '{"RegionId":"cn-beijing","ProjectName":"default","AllowListName":"cc-iac-mongodb-allow"}'` returned `Total: 0`, confirming no allowlist was created.

Retry MongoDB only after `mongodb:CreateAllowList` and `mongodb:CreateDBInstance` are granted. Use the discovered minimal ReplicaSet shape to reduce cost:

```hcl
resource "volcenginecc_mongodb_allow_list" "app" {
  allow_list_name     = "cc-iac-mongodb-allow"
  allow_list_type     = "IPv4"
  allow_list_category = "Ordinary"
  allow_list_desc     = "volcenginecc MongoDB allowlist example"
  project_name        = "default"
  allow_list          = ["10.0.0.0/8"]
}

resource "volcenginecc_mongodb_instance" "main" {
  zone_id                = "cn-beijing-a"
  vpc_id                 = volcenginecc_vpc_vpc.main.vpc_id
  subnet_id              = volcenginecc_vpc_subnet.main.subnet_id
  db_engine              = "MongoDB"
  db_engine_version      = "MongoDB_7_0"
  instance_type          = "ReplicaSet"
  node_spec              = "mongo.1c2g"
  node_number            = 3
  storage_space_gb       = 20
  super_account_name     = "root"
  super_account_password = var.mongodb_password
  instance_name          = "cc-iac-mongodb"
  instance_count         = 1
  charge_type            = "PostPaid"
  project_name           = "default"
  allow_list_ids         = [volcenginecc_mongodb_allow_list.app.allow_list_id]
}
```

Do not add an `assets/examples/volcenginecc-mongodb` verified example until allowlist, instance, optional SSL state, no-op plan, and destroy all succeed. `super_account_password` is sensitive in plan output but will still be stored in Terraform state.

## veDB MySQL

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_vedbm_allow_list` | Permission-blocked | `AccessDenied: User is not authorized to perform: vedbm:CreateAllowList` during create |
| `volcenginecc_vedbm_instance` | Dependency/permission-blocked | Requires veDBM allowlist permission and creates a billable instance with a password stored in state |
| `volcenginecc_vedbm_account` | Dependency-blocked | Requires a running veDBM instance; account password is stored in Terraform state |
| `volcenginecc_vedbm_database` | Dependency-blocked | Requires a running veDBM instance and optional account grants |
| `volcenginecc_vedbm_endpoint` | Dependency-blocked | Requires a running veDBM instance and node selection |
| `volcenginecc_vedbm_backup` | Dependency-blocked | Requires a running veDBM instance |

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-vedbm-current` used only a standalone IPv4 allowlist to avoid creating a billable database instance or storing database passwords. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply failed before an allowlist ID was created:

```text
EventTime: 2026-05-30T13:29:27+08:00
TaskID: task-8ece5813-c6ba-4e1c-b53f-46c4a1cc1fc2
AccessDenied: AccessDenied: User is not authorized to perform: vedbm:CreateAllowList on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::VEDBM::AllowList
Operation: CREATE
OperationStatus: FAILED
```

No veDBM resources were created; Terraform state remained empty. After `vedbm:CreateAllowList` and `vedbm:CreateDBInstance` are granted, retry the standalone allowlist first. Add `vedbm_instance` only with a sensitive password variable and a disposable VPC/subnet, then add account, database, endpoint, and backup in later applies after the instance reaches a stable running state.

## Kafka

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_kafka_allow_list` | Verified | Standalone allowlist create/no-op/destroy succeeded; see example `volcenginecc-kafka-allow-list` |
| `volcenginecc_kafka_instance` | Service-blocked | Both full and minimal instance create attempts failed with Cloud Control `ServiceInternalError: InternalError` |
| `volcenginecc_kafka_topic` | Dependency-blocked | Requires a successfully created Kafka instance |

The initial configuration validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`. It included VPC, subnet, route table, Kafka allowlist, Kafka instance, SASL user settings, and one topic. Apply created the network and allowlist resources, then Kafka instance creation failed:

```text
ServiceInternalError: InternalError: The request failed due to some unknown error, exception or failure.
TypeName: Volcengine::Kafka::Instance
Operation: CREATE
OperationStatus: FAILED
```

A second minimized retry removed SASL user settings, topic creation, custom parameters, and explicit storage type. It kept only `compute_spec = "kafka.20xrate.hw"`, `version = "2.8.2"`, `partition_number = 350`, `storage_space = 100`, VPC/subnet, and the verified allowlist. That attempt failed with the same Cloud Control error:

```text
ServiceInternalError: InternalError: The request failed due to some unknown error, exception or failure.
TypeName: Volcengine::Kafka::Instance
Operation: CREATE
OperationStatus: FAILED
```

Temporary VPC, subnet, route table, and Kafka allowlist resources were destroyed successfully; final Terraform state was empty.

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-kafka-current` used the same minimized Kafka shape: VPC, subnet, custom route table, verified allowlist, and a single pay-as-you-go `volcenginecc_kafka_instance` with `compute_spec = "kafka.20xrate.hw"`, `version = "2.8.2"`, `partition_number = 350`, and `storage_space = 100`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply created VPC `vpc-bu1k7r8cjnr45h0b2uchh31y`, subnet `subnet-1jopkfmx9eark1n7amqc04rhn`, route table `vtb-3nqh7jkkl4c1s931ebvpps73`, and allowlist `acl-7829e720baf2499ab10bcde584883f85`, then Kafka instance creation failed with the same service-side error:

```text
EventTime: 2026-05-30T11:42:26+08:00
TaskID: task-bce68173-fc18-4bab-9927-b8f42b2e3190
ServiceInternalError: InternalError: The request failed due to some unknown error, exception or failure.
TypeName: Volcengine::Kafka::Instance
Operation: CREATE
OperationStatus: FAILED
```

Retried the same minimized Kafka shape again on 2026-05-30 at 14:24. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded. Apply created VPC `vpc-3nr8kolqd1clc931ebvtvo9v`, subnet `subnet-btmtuqzfh14w5h0b2ui8d5fd`, route table `vtb-btmvnh6xhtz45h0b2tqddvri`, and allowlist `acl-800ac25596ea49149401bd6dc4ad85c9`, then Kafka instance creation still failed with the same service-side error:

```text
EventTime: 2026-05-30T14:24:15+08:00
TaskID: task-641c0f5d-e26b-426d-8cab-bc52806ba87c
ServiceInternalError: InternalError: The request failed due to some unknown error, exception or failure.
TypeName: Volcengine::Kafka::Instance
Operation: CREATE
OperationStatus: FAILED
```

Destroy removed the allowlist, route table, subnet, and VPC; final Terraform state was empty. `DescribeVpcs --VpcName cc-iac-kafka-vpc` returned `TotalCount: 0` in the earlier retry, and exact VPC-name matching for `cc-iac-kafka-retry-vpc` returned no rows in the 14:24 retry. `ve kafka DescribeAllowLists` returned a service-side `InternalError` 500 during residue checking, so the reliable cleanup evidence for the Kafka allowlist is Terraform destroy completion plus empty state. Because Kafka instance creation still fails, `volcenginecc_kafka_topic` and `volcenginecc_vefaas_kafka_trigger` remain dependency-blocked and must not be generated with placeholder instance IDs or SASL credentials.

Standalone Kafka allowlist verification in `cn-beijing`: `volcenginecc_kafka_allow_list` created with `allow_list = "10.97.0.0/16"`, had a clean no-op plan, and destroyed successfully. Created ID was `acl-917f65a4315948cdb08720d2cb58f3f6`. Creation took about 22s and deletion about 15s. The generated docs/example use the wrong resource name `volcenginecc_kafka_allowlist`; the actual Terraform resource type is `volcenginecc_kafka_allow_list`.

When the Kafka instance API is usable, retry with this minimal shape first:

```hcl
resource "volcenginecc_kafka_allow_list" "app" {
  allow_list      = "10.97.0.0/16"
  allow_list_name = "cc-iac-kafka-allow"
}

resource "volcenginecc_kafka_instance" "main" {
  compute_spec         = "kafka.20xrate.hw"
  instance_description = "volcenginecc Kafka example instance"
  instance_name        = "cc-iac-kafka-instance"
  subnet_id            = volcenginecc_vpc_subnet.main.subnet_id
  ip_white_list        = [volcenginecc_kafka_allow_list.app.allow_list_id]
  partition_number     = 350
  storage_space        = 100
  version              = "2.8.2"
  vpc_id               = volcenginecc_vpc_vpc.main.vpc_id
  zone_id              = "cn-beijing-a"
  project_name         = "default"

  charge_info = {
    charge_type = "PostPaid"
    auto_renew  = false
  }
}
```

After instance creation succeeds, add `volcenginecc_kafka_topic` in a second apply. The provider docs/example have a resource naming pitfall: docs show `volcenginecc_kafka_allowlist`, but the actual Terraform resource name is `volcenginecc_kafka_allow_list`.

## RabbitMQ

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_rabbitmq_allow_list` | Dependency-only verified | Create/destroy succeeded after permission grant, but instance path is still blocked |
| `volcenginecc_rabbitmq_instance` | Service-internal blocked | `ServiceInternalError: InternalError` during create |
| `volcenginecc_rabbitmq_public_address` | Dependency-blocked | Requires a successfully created RabbitMQ instance and EIP |
| `volcenginecc_rabbitmq_instance_plugin` | Dependency-blocked | Requires a successfully created RabbitMQ instance and a deliberate plugin choice |

Minimal private-network configuration validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`. The first apply created only the network dependencies, then failed on allowlist creation:

```text
AccessDenied: User is not authorized to perform: rabbitmq:CreateAllowList on resource:
TypeName: Volcengine::RabbitMQ::AllowList
Operation: CREATE
OperationStatus: FAILED
```

A standalone allowlist retry without network or instance dependencies still failed with the same permission denial; no resources were created and Terraform state remained empty:

```text
AccessDenied: User is not authorized to perform: rabbitmq:CreateAllowList on resource:
TypeName: Volcengine::RabbitMQ::AllowList
Operation: CREATE
TaskID: task-6c07a9b7-9c72-4bdb-a010-aa4ec94ea3ef
EventTime: 2026-05-30T08:20:50+08:00
```

Latest standalone allowlist retry still failed before any resource was created; Terraform state remained empty:

```text
EventTime: 2026-05-30T09:54:29+08:00
TaskID: task-d1bc9ed5-e940-440e-89f2-8e07738914a0
AccessDenied: User is not authorized to perform: rabbitmq:CreateAllowList
TypeName: Volcengine::RabbitMQ::AllowList
Operation: CREATE
OperationStatus: FAILED
```

Retried the standalone allowlist shape again on 2026-05-30 at 13:59 with allow list name `cc-iac-rabbit-allow-retry`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; apply still failed before creating any resource:

```text
EventTime: 2026-05-30T13:59:43+08:00
TaskID: task-92d6b7a5-db08-4d54-b7aa-1eab5d2a61cf
AccessDenied: User is not authorized to perform: rabbitmq:CreateAllowList on resource:
TypeName: Volcengine::RabbitMQ::AllowList
Operation: CREATE
OperationStatus: FAILED
```

A second apply without the allowlist dependency was used only to test the instance API and failed with:

```text
AccessDenied: User is not authorized to perform: rabbitmq:CreateInstance on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::RabbitMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

Temporary VPC, subnet, and route table resources were destroyed successfully; final Terraform state was empty.

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-rabbitmq-current` used VPC, subnet, route table, `volcenginecc_rabbitmq_allow_list`, and `volcenginecc_rabbitmq_instance`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply created VPC `vpc-bu4dhufolgjk5h0b2ugt8nea`, subnet `subnet-1a126yhc3e03k8nvepkni52jg`, and route table `vtb-3nqjplo73xou8931eblw679i`, then both RabbitMQ resources failed with the same IAM permission boundary:

```text
EventTime: 2026-05-30T11:56:52+08:00
TaskID: task-aa6f3eaa-57ec-4c30-b59e-79dec5b9c4ea
AccessDenied: User is not authorized to perform: rabbitmq:CreateAllowList
TypeName: Volcengine::RabbitMQ::AllowList
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T11:57:33+08:00
TaskID: task-859ae916-3ba2-4d7f-b385-5b1ccff129ce
AccessDenied: User is not authorized to perform: rabbitmq:CreateInstance on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::RabbitMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

Destroy removed the route table, subnet, and VPC; final Terraform state was empty. `DescribeVpcs --VpcName cc-iac-rabbit-current-vpc` returned `TotalCount: 0`, and `DescribeInstances --InstanceName cc-iac-rabbit-current-instance` returned no RabbitMQ instances.

After RabbitMQ permissions were granted, a 2026-05-30 retry in `/tmp/volcenginecc-rabbitmq-retry-20260530153035` created allowlist `acl-06da2274763d40b4adddf896edf22a0f` plus VPC dependencies successfully. Creating the RabbitMQ instance then failed in the service backend:

```text
EventTime: 2026-05-30T15:33:46+08:00
TaskID: task-8e262631-64a9-4686-8e9e-429bb125c479
ServiceInternalError: InternalError: The request failed due to some unknown error, exception or failure.
TypeName: Volcengine::RabbitMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

Cleanup destroyed the allowlist, route table, subnet, and VPC. Final Terraform state was empty; `ve rabbitmq DescribeAllowLists --body '{"RegionId":"cn-beijing","AllowListName":"cc-iac-rabbit-retry-allow"}'` returned an empty `AllowLists` array, `DescribeInstances` returned `Total: 0`, and exact VPC-name matching for `cc-iac-rabbit-retry-vpc` returned no rows.

After another permission grant, a 2026-05-30 retry in `/tmp/volcenginecc-rabbitmq-retry-202605301631` created allowlist `acl-71df21f00ea84383a61c3e77b0a5b5a3` plus VPC dependencies successfully. Creating the RabbitMQ instance still failed in the service backend:

```text
EventTime: 2026-05-30T16:32:29+08:00
TaskID: task-9d25fc0d-7229-487a-8830-00b0268ce35e
ServiceInternalError: InternalError: The request failed due to some unknown error, exception or failure.
TypeName: Volcengine::RabbitMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

Cleanup destroyed the allowlist, route table, subnet, and VPC. Final Terraform state was empty; `ve rabbitmq DescribeAllowLists --body '{"RegionId":"cn-beijing","AllowListName":"cc-iac-rabbit-1631-allow"}'` returned an empty `AllowLists` array, `DescribeInstances --InstanceName cc-iac-rabbit-1631-instance` returned `Total: 0`, and exact VPC-name matching for `cc-iac-rabbit-1631-vpc` returned no rows.

When the RabbitMQ service backend issue is resolved, retry with this shape:

```hcl
resource "volcenginecc_rabbitmq_allow_list" "app" {
  allow_list_type = "IPv4"
  allow_list      = "10.98.0.0/16"
  allow_list_name = "cc-iac-rabbit-allow"
}

resource "volcenginecc_rabbitmq_instance" "main" {
  zone_id              = "cn-beijing-a"
  user_name            = "appadmin"
  user_password        = var.rabbitmq_password
  compute_spec         = "rabbitmq.n1.x4.small"
  version              = "3.12"
  storage_space        = 100
  instance_description = "volcenginecc RabbitMQ example instance"
  instance_name        = "cc-iac-rabbit-instance"
  vpc_id               = volcenginecc_vpc_vpc.main.vpc_id
  subnet_id            = volcenginecc_vpc_subnet.main.subnet_id
  project_name         = "default"

  charge_detail = {
    charge_type = "PostPaid"
  }
}
```

Do not add an `assets/examples/volcenginecc-rabbitmq` verified example until apply, no-op plan, and destroy all succeed. The provider docs/example have a resource naming pitfall: docs show `volcenginecc_rabbitmq_allowlist`, but the actual Terraform resource name is `volcenginecc_rabbitmq_allow_list`. `user_password` is sensitive in plan output but will still be stored in Terraform state.

## RocketMQ

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_rocketmq_allow_list` | Dependency-only verified | Create/destroy succeeded after permission grant, but instance path is still blocked |
| `volcenginecc_rocketmq_instance` | Parameter/network blocked | `StorageSpace`, `VpcIdOrSubnetId`, and `ComputeSpec` validation failures during create |
| `volcenginecc_rocketmq_topic` | Dependency-blocked | Requires a successfully created RocketMQ instance |
| `volcenginecc_rocketmq_group` | Dependency-blocked | Requires a successfully created RocketMQ instance |

Minimal private-network configuration validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`. It used RocketMQ `4.8` rather than `5.x`, because the docs say `5.x` requires whitelist application. The first apply created only the network dependencies, then failed on allowlist creation:

```text
AccessDenied: User is not authorized to perform: rocketmq:CreateAllowList on resource: trn:RocketMQ:cn-beijing:2109984414:instance/cc-iac-rocket-allow
TypeName: Volcengine::RocketMQ::AllowList
Operation: CREATE
OperationStatus: FAILED
```

A standalone allowlist retry without network or instance dependencies still failed with the same permission denial; no resources were created and Terraform state remained empty:

```text
AccessDenied: User is not authorized to perform: rocketmq:CreateAllowList on resource: trn:RocketMQ:cn-beijing:2109984414:instance/cc-iac-rocket-allow-05300830
TypeName: Volcengine::RocketMQ::AllowList
Operation: CREATE
TaskID: task-1f1066ed-8ab5-42b8-9777-2b5d2fc82036
EventTime: 2026-05-30T08:20:50+08:00
```

Latest standalone allowlist retry still failed before any resource was created; Terraform state remained empty:

```text
EventTime: 2026-05-30T09:54:29+08:00
TaskID: task-812b4b46-ddcc-4ae1-8364-9afecd834ba6
AccessDenied: User is not authorized to perform: rocketmq:CreateAllowList
TypeName: Volcengine::RocketMQ::AllowList
Operation: CREATE
OperationStatus: FAILED
```

Retried the standalone allowlist shape again on 2026-05-30 at 14:01 with allow list name `cc-iac-rocket-allow-retry`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; apply still failed before creating any resource:

```text
EventTime: 2026-05-30T14:01:24+08:00
TaskID: task-c3a64a2c-d84c-4fe2-b144-6dbcd867db3f
AccessDenied: User is not authorized to perform: rocketmq:CreateAllowList on resource: trn:RocketMQ:cn-beijing:2109984414:instance/cc-iac-rocket-allow-retry
TypeName: Volcengine::RocketMQ::AllowList
Operation: CREATE
OperationStatus: FAILED
```

A second apply without the allowlist dependency was used only to test the instance API and failed with:

```text
AccessDenied: User is not authorized to perform: rocketmq:CreateInstance on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::RocketMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

Temporary VPC, subnet, and route table resources were destroyed successfully; final Terraform state was empty.

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-rocketmq-current` used VPC, subnet, route table, `volcenginecc_rocketmq_allow_list`, and a private RocketMQ 4.8 instance shape. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply created VPC `vpc-1a12g96xu93b48nvepko7zwop`, subnet `subnet-3nqk0gw1pxclc931ebyw1dfq`, and route table `vtb-1a12i7s9nbri88nvepkg6zpvj`, then failed on allowlist creation before the instance dependency could start:

```text
EventTime: 2026-05-30T11:59:15+08:00
TaskID: task-dfc6bd42-e8de-4655-8412-500a2d54bada
AccessDenied: User is not authorized to perform: rocketmq:CreateAllowList on resource: trn:RocketMQ:cn-beijing:2109984414:instance/cc-iac-rocket-current-allow
TypeName: Volcengine::RocketMQ::AllowList
Operation: CREATE
OperationStatus: FAILED
```

Destroy removed the route table, subnet, and VPC; final Terraform state was empty. `DescribeVpcs --VpcName cc-iac-rocket-current-vpc` returned `TotalCount: 0`. `ve rocketmq DescribeInstances --InstanceName ...` was not usable as a residue check because the CLI rejected the filter shape with `InvalidParameter: The specified parameter PageSizeOrPageNumber is not valid`; the RocketMQ instance create call had not started because it depended on the failed allowlist.

After RocketMQ permissions were granted, a 2026-05-30 retry in `/tmp/volcenginecc-rocketmq-retry-202605301536` created allowlist `acl-ad61375b1da6493590be31f9d41d5e1a` plus VPC dependencies successfully, proving the allowlist permission is now usable. Instance creation then exposed API-side shape constraints:

```text
EventTime: 2026-05-30T15:38:49+08:00
TaskID: task-fed42caf-1c1a-466d-8e13-c76b1bf93171
InvalidRequest: InvalidParameter: The specified parameter StorageSpace is not valid.
```

Changing `storage_space` from `100` to the docs' `300` moved validation forward, but the otherwise same `rocketmq.n1.x2.micro` private-network shape failed on the VPC/subnet pair:

```text
EventTime: 2026-05-30T15:39:13+08:00
TaskID: task-8bf7adff-a928-495d-ac09-6c33b34023f3
InvalidRequest: InvalidParameter: The specified parameter VpcIdOrSubnetId is not valid.
```

Trying the docs example compute spec `rocketmq.x2.2k` with `storage_space = 300` failed compute spec validation in the current API path:

```text
EventTime: 2026-05-30T15:40:19+08:00
TaskID: task-5afe9e6d-c124-47bb-a67d-f5fdda650b6c
InvalidRequest: InvalidParameter: The specified parameter ComputeSpec is not valid.
```

Cleanup destroyed the allowlist, route table, subnet, and VPC. Final Terraform state was empty; `ve rocketmq DescribeAllowLists --RegionId cn-beijing --AllowListName cc-iac-rocket-retry-allow` returned `AllowLists: null`, and exact VPC-name matching for `cc-iac-rocket-retry-vpc` returned no rows. `ve rocketmq DescribeAvailabilityZones` shows `cn-beijing-a/b/c/d` are normal, but the CLI does not expose a product/specification list action, so the exact valid spec/subnet matrix still needs product-side confirmation.

After another permission grant, a 2026-05-30 retry in `/tmp/volcenginecc-rocketmq-retry-202605301705` created allowlist `acl-30cbca2fcb5e4c5faa275aec2a38f03b`, VPC `vpc-iiv1ud15pam874o8ctzoc3ka`, subnet `subnet-3nqtc2caj94ow931ebzocopq`, and route table `vtb-3nqteoa5ib6dc931ecitufx9`. Three instance shapes were tested against those dependencies:

```text
version = "5.x"
zone_id = "cn-beijing-a,cn-beijing-c,cn-beijing-d"
compute_spec = "rocketmq.x2.2k"
storage_space = 300
TaskID: task-bcdf0985-b0e4-4618-ab85-03c71a332c69
InvalidRequest: InvalidParameter: The specified parameter StorageSpace is not valid.
```

```text
version = "5.x"
zone_id = "cn-beijing-a,cn-beijing-c,cn-beijing-d"
compute_spec = "rocketmq.x2.2k"
storage_space = 500
TaskID: task-c1e5cfcc-4fed-46eb-b045-521a487addeb
InvalidRequest: InvalidParameter: The specified parameter StorageSpace is not valid.
```

```text
version = "4.8"
zone_id = "cn-beijing-a"
compute_spec = "rocketmq.n3.x2.medium"
storage_space = 300
TaskID: task-a46f9e35-5d61-424e-98ed-9969e83aac25
InvalidRequest: InvalidParameter: The specified parameter StorageSpace is not valid.
```

The docs page and provider schema still do not expose a reliable compute/storage matrix, and `ve rocketmq` has no list-specifications action. Do not continue blind storage enumeration; get the valid `ComputeSpec` plus `StorageSpace` matrix from RocketMQ product support or an API that exposes product specifications. Cleanup destroyed the allowlist, route table, subnet, and VPC. Final Terraform state was empty; `ve rocketmq DescribeInstances` returned `Total: 0`, `DescribeAllowLists --AllowListName cc-iac-rocket-1705-allow` returned `AllowLists: null`, and `ve vpc DescribeVpcs --VpcName cc-iac-rocket-1705-vpc` returned `TotalCount: 0`.

When the RocketMQ spec/subnet matrix is known, retry with this adjusted shape before adding topic/group:

```hcl
resource "volcenginecc_rocketmq_allow_list" "app" {
  allow_list_name = "cc-iac-rocket-allow"
  allow_list_type = "IPv4"
  allow_list      = "10.99.0.0/16"
}

resource "volcenginecc_rocketmq_instance" "main" {
  allow_list_ids       = [volcenginecc_rocketmq_allow_list.app.allow_list_id]
  ip_version_type      = "IPv4"
  enable_ssl           = false
  version              = "4.8"
  zone_id              = "cn-beijing-a"
  compute_spec         = "rocketmq.n1.x2.micro"
  storage_space        = 300
  vpc_id               = volcenginecc_vpc_vpc.main.vpc_id
  subnet_id            = volcenginecc_vpc_subnet.main.subnet_id
  file_reserved_time   = 24
  instance_name        = "cc-iac-rocket-instance"
  network_types        = "PrivateNetwork"
  project_name         = "default"
  instance_description = "volcenginecc RocketMQ example instance"

  charge_detail = {
    charge_type = "PostPaid"
  }
}
```

Do not add an `assets/examples/volcenginecc-rocketmq` verified example until apply, no-op plan, and destroy all succeed. After the instance is verified, add `volcenginecc_rocketmq_topic` and `volcenginecc_rocketmq_group` in a second apply.

## BMQ

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_bmq_instance` | Service-role blocked | `RoleNotExist: Role 'trn:iam::2109984414:role/ServiceRoleForBmq' does not exist` during create |
| `volcenginecc_bmq_group` | Dependency-blocked | Requires a successfully created BMQ instance |

BMQ API discovery succeeded in `cn-beijing`: `ve bmq ListSpecifications` returned `bmq.standard` as available and `ve bmq DescribeAvailableZones` showed `cn-beijing-a`, `cn-beijing-c`, and `cn-beijing-d` not sold out. The Terraform configuration validated and planned successfully with provider `volcengine/volcenginecc ~> 0.0.46`, using VPC, subnet, route table, security group, `bmq.standard`, and a private overlay endpoint. Apply created only the network dependencies, then failed on BMQ instance creation:

```text
AccessDenied: User is not authorized to perform: bmq:CreateInstance on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::BMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

Temporary VPC, subnet, route table, and security group resources were destroyed successfully; final Terraform state was empty.

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-bmq-current` used VPC, subnet, route table, security group, and a private overlay `volcenginecc_bmq_instance`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. A first apply created VPC `vpc-bu5awtl1tslc5h0b2tutud18`, subnet `subnet-1a12sg5cdcjk08nvepk29ls70`, and route table `vtb-ij609sqc42rk74o8ctgttvhi`, but the security group create hit a transient VPC control-plane conflict:

```text
EventTime: 2026-05-30T12:01:40+08:00
TaskID: task-e80a987f-6a15-4b13-a4b1-77a549cea80b
InvalidOperation.Conflict: The specified resource operation conflicts.
TypeName: Volcengine::VPC::SecurityGroup
Operation: CREATE
OperationStatus: FAILED
```

Rerunning apply after the VPC settled created security group `sg-3nqkl4awxplog931ebp2lgms`, then the BMQ instance failed at the service permission boundary:

```text
EventTime: 2026-05-30T12:02:28+08:00
TaskID: task-3b027337-c698-4f29-9879-ab106bc3ab6a
AccessDenied: User is not authorized to perform: bmq:CreateInstance on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::BMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

Destroy removed the security group, route table, subnet, and VPC; final Terraform state was empty. `DescribeVpcs --VpcName cc-iac-bmq-current-vpc` returned `TotalCount: 0`. `ve bmq ListInstances --Region ...` was not usable as a residue check because that CLI command rejected `--Region`; no BMQ instance ID was created because `CreateInstance` failed before resource creation.

After BMQ create permission was granted, a 2026-05-30 retry in `/tmp/volcenginecc-bmq-retry-202605301542` again hit the transient VPC security-group conflict on the first apply, then succeeded on a second apply after the VPC settled. BMQ instance creation then moved past the earlier IAM permission boundary and failed because the service-linked role is missing:

```text
EventTime: 2026-05-30T15:44:07+08:00
TaskID: task-afaabafa-8576-4c58-a28d-97eaf21ac118
NotFound: RoleNotExist: Role 'trn:iam::2109984414:role/ServiceRoleForBmq' does not exist.
TypeName: Volcengine::BMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

Cleanup destroyed the security group, route table, subnet, and VPC. Final Terraform state was empty; exact VPC-name matching for `cc-iac-bmq-retry-vpc` returned no rows, and `ve bmq SearchInstances` returned `TotalCount: 0`.

After another permission grant, a 2026-05-30 retry in `/tmp/volcenginecc-bmq-retry-202605301636` used the same private overlay shape and created VPC `vpc-iisbde5ugq9s74o8cujmdrpu`, subnet `subnet-iisbzjabywao74o8cuovyal0`, route table `vtb-3nqp6pn3amrk0931ec352wqa`, and security group `sg-1josnjckpz7r41n7ampwasl6p`. The BMQ instance request then ran for about 16 minutes. Terraform reported the Cloud Control task as failed:

```text
EventTime: 2026-05-30T16:53:19+08:00
TaskID: task-ba1c091a-7f54-44f4-8e37-fc92b9a1ed13
InvalidRequest: InvalidParameter: parameter is invalid, pls check parameters
TypeName: Volcengine::BMQ::Instance
Operation: CREATE
OperationStatus: FAILED
```

However, `ve bmq SearchInstances --body '{"SearchKey":"cc-iac-bmq-1636"}'` immediately showed the instance was actually created and `RUNNING` as `bmq-5er8frdjem3gbtqwargy`. Because Terraform did not put the instance in state after the failed task, import was required before cleanup:

```text
terraform import volcenginecc_bmq_instance.main bmq-5er8frdjem3gbtqwargy
```

The imported instance still did not converge to a clean no-op plan. Terraform planned updates for `endpoints`, computed `tags`, and the security group had an extra default egress rule (`description = "放通全部流量"`, `priority = 100`) in addition to the configured egress rule. This means the shape is not suitable for a verified example even though the cloud instance can be created.

Destroy deleted the BMQ instance, then the first network cleanup attempt failed because BMQ-managed VCI ENIs were still attached to the security group:

```text
EventTime: 2026-05-30T16:55:34+08:00
TaskID: task-1a9c03fe-8da9-43c7-8b95-fd2bd05381c4
AccessDenied: Forbidden: You are not authorized to perform operations on the specified elastic network interface. The specified elastic network interface is a service-managed elastic network interface.
TypeName: Volcengine::VPC::SecurityGroup
Operation: DELETE
OperationStatus: FAILED
```

After `ve vpc DescribeNetworkInterfaces --VpcId vpc-iisbde5ugq9s74o8cujmdrpu` and `--SubnetId subnet-iisbzjabywao74o8cuovyal0` returned no rows, rerunning `terraform destroy` removed the security group, route table, subnet, and VPC. Final Terraform state was empty; `ve bmq SearchInstances` returned `TotalCount: 0`, `ve vpc DescribeVpcs --VpcName cc-iac-bmq-1636-vpc` returned `TotalCount: 0`, and checking ENIs by the deleted VPC ID returned `InvalidVpc.NotFound`.

When `ServiceRoleForBmq` exists and BMQ can assume it, retry with this shape:

```hcl
resource "volcenginecc_bmq_instance" "main" {
  name                   = "cc-iac-bmq"
  billing_type           = "POST"
  project_name           = "default"
  specification          = "bmq.standard"
  vpc_id                 = volcenginecc_vpc_vpc.main.vpc_id
  message_retention      = 1
  security_group_id_list = [volcenginecc_vpc_security_group.app.security_group_id]
  subnet_id_list         = [volcenginecc_vpc_subnet.main.subnet_id]
  zone_id_list           = ["cn-beijing-a"]

  endpoints = {
    overlay = {
      vpc_ids = [volcenginecc_vpc_vpc.main.vpc_id]
    }
  }
}
```

Do not add an `assets/examples/volcenginecc-bmq` verified example until apply, no-op plan, and destroy all succeed. The provider exposes `volcenginecc_bmq_instance` and `volcenginecc_bmq_group`, but no `volcenginecc_bmq_topic`; BMQ topics still need the `ve bmq CreateTopic` API or another tool path.

## File Storage

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_filenas_instance` | Verified | FileNAS `Extreme/NFS/Standard` create/no-op/destroy succeeded; see `volcenginecc-filenas.md` |
| `volcenginecc_filenas_snapshot` | Drift-blocked for default example | Create/delete succeeded, but no-op plan repeatedly showed `retention_days = -1 -> 2147483647` |
| `volcenginecc_filenas_mount_point` | Dependency-blocked | Requires `permission_group_id`; provider `0.0.46` has no FileNAS permission group resource |
| `volcenginecc_efs_file_system` | Verified | EFS `Premium/Premium_125` create/no-op/destroy succeeded; see `volcenginecc-efs.md` |
| `volcenginecc_vepfs_instance` | Service-internal blocked | `ServiceInternalError: InternalError: Service has some internal Error` during create |
| `volcenginecc_vepfs_mount_service` | Dependency/service-catalog blocked | Requires vePFS instance; `ve vepfs DescribeMountServiceNodeTypes` returned empty node type lists in Beijing |

EFS minimal configuration validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`, using `cn-beijing-a`, `Premium`, `Premium_125`, and provisioned bandwidth `300`. Apply failed immediately with:

```text
AccessDenied: AccessDenied: User is not authorized to perform: efs:CreateFileSystem on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::EFS::FileSystem
Operation: CREATE
OperationStatus: FAILED
```

No EFS resources were created; Terraform state remained empty.

Current-account retry on 2026-05-30 used the same minimal shape in `/tmp/volcenginecc-efs-current`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded; apply failed with the same permission boundary:

```text
EventTime: 2026-05-30T10:45:47+08:00
TaskID: task-a8ba57f6-309e-455d-9fff-4f161ef85f34
AccessDenied: User is not authorized to perform: efs:CreateFileSystem
```

Retried the same standalone EFS file system shape again on 2026-05-30 at 14:04 with file system name `cc-iac-efs-retry`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; apply still failed before creating any resource:

```text
EventTime: 2026-05-30T14:04:03+08:00
TaskID: task-ad3f7a23-dcb9-4c63-84c4-44fadb51f6c8
AccessDenied: User is not authorized to perform: efs:CreateFileSystem on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::EFS::FileSystem
Operation: CREATE
OperationStatus: FAILED
```

Post-failure checks: `terraform state list` returned empty in the earlier retry, and `ve efs DescribeFileSystems` with `FileSystemName=cc-iac-efs-current` returned `TotalCount: 0`. The 14:04 retry returned `Identifier: null`; a cloud-side `ve efs DescribeFileSystems` check with `FileSystemName=cc-iac-efs-retry` returned `TotalCount: 0`.

After `efs:CreateFileSystem` was granted, a 2026-05-30 retry in `/tmp/volcenginecc-efs-retry-202605301545` verified the EFS file system lifecycle. The initial tagged shape created successfully but a follow-up plan showed a tag drift because `type = "Custom"` read back without `type`. Removing the `tags` block produced a clean no-op plan. The verified EFS file system `cc-iac-efs-retry` created with ID `efs-cnbja3a96f8f938a6`, `terraform plan -detailed-exitcode` returned `No changes`, destroy removed the file system, final Terraform state was empty, and `ve efs DescribeFileSystems --body '{"FileSystemName":"cc-iac-efs-retry"}'` returned `TotalCount: 0`.

The verified example now lives in `assets/examples/volcenginecc-efs`; validation notes and pitfalls live in `references/volcenginecc-efs.md`. Use this shape:

```hcl
resource "volcenginecc_efs_file_system" "main" {
  file_system_name    = "cc-iac-efs-fs"
  description         = "volcenginecc EFS example file system"
  charge_type         = "PayAsYouGo"
  zone_id             = "cn-beijing-a"
  instance_type       = "Premium"
  performance_density = "Premium_125"
  project_name        = "default"

  performance = {
    bandwidth_mode        = "Provisioned"
    provisioned_bandwidth = 300
  }
}
```

FileNAS `volcenginecc_filenas_snapshot` was deliberately excluded from the verified default example even though create and delete both succeeded. The persistent no-op drift is caused by generated provider schema: `retention_days` is read-only/computed but also has default `2147483647`, while the API reads back `-1`.

```text
~ retention_days = -1 -> 2147483647
```

Do not use `ignore_changes = [retention_days]`; Terraform warns that the attribute is provider-decided and the ignore rule is redundant. If snapshots are needed anyway, document this residual drift in the plan review.

FileNAS mount points need an existing permission group:

```hcl
resource "volcenginecc_filenas_mount_point" "app" {
  file_system_id      = volcenginecc_filenas_instance.main.file_system_id
  mount_point_name    = "cc-iac-filenas-mount"
  permission_group_id = var.filenas_permission_group_id
  subnet_id           = var.subnet_id
  vpc_id              = var.vpc_id
}
```

The `ve filenas CreatePermissionGroup` API exists, but the provider does not expose a matching `volcenginecc_filenas_permission_group` resource in `0.0.46`, so a from-scratch Terraform-only example would hide an unmanaged prerequisite.

vePFS sale discovery succeeded in `cn-beijing`: `ve vepfs DescribeZones` returned `OnSale` for `Advance_100` and `Performance` in `cn-beijing-a/b/c/d/e`. The Terraform configuration validated and planned successfully with VPC, subnet, route table, and `volcenginecc_vepfs_instance`, then failed on instance creation:

```text
AccessDenied: AccessDenied: User is not authorized to perform: vepfs:CreateFileSystem on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::VEPFS::Instance
Operation: CREATE
OperationStatus: FAILED
```

Temporary VPC, subnet, and route table resources were destroyed successfully; final Terraform state was empty.

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-vepfs-current` confirmed the same boundary. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. The temporary VPC/subnet/route table were created, then `volcenginecc_vepfs_instance` failed:

```text
EventTime: 2026-05-30T10:46:51+08:00
TaskID: task-8faaddbe-dd15-4d88-8b6c-10788b212628
AccessDenied: User is not authorized to perform: vepfs:CreateFileSystem
```

Retried the same VPC/subnet/route-table-backed shape again on 2026-05-30 at 14:05 with file system name `cc-iac-vepfs-retry-fs`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded. The temporary VPC `vpc-3nr4zqxilyubk931ecl4efyg`, subnet `subnet-3psehxdoa8ykg6csxyw9kxuif`, and route table `vtb-1jpc0q51mi03k1n7amp6tsw0r` were created, then `volcenginecc_vepfs_instance` failed:

```text
EventTime: 2026-05-30T14:05:53+08:00
TaskID: task-c5a777fb-370f-4096-8eac-4330ac46d376
AccessDenied: User is not authorized to perform: vepfs:CreateFileSystem on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::VEPFS::Instance
Operation: CREATE
OperationStatus: FAILED
```

Recovery: `terraform destroy` removed 3 temporary network resources. Final `terraform state list` returned empty, `ve vepfs DescribeFileSystems` with `FileSystemName=cc-iac-vepfs-current` returned `TotalCount: 0`, and the temporary VPC ID no longer appeared in `DescribeVpcs`. The 14:05 retry also ended with empty Terraform state, `ve vepfs DescribeFileSystems` for `cc-iac-vepfs-retry-fs` returned `TotalCount: 0`, and exact VPC-name matching for `cc-iac-vepfs-retry-vpc` returned no rows.

After `vepfs:CreateFileSystem` was granted, a 2026-05-30 retry in `/tmp/volcenginecc-vepfs-retry-202605301550` created the temporary VPC, subnet, and route table successfully, then vePFS instance creation failed in the service backend:

```text
EventTime: 2026-05-30T15:51:47+08:00
TaskID: task-4b0a4469-9e6f-44ad-8550-5f306ea06fba
ServiceInternalError: InternalError: Service has some internal Error. Pls Contact With Admin.
TypeName: Volcengine::VEPFS::Instance
Operation: CREATE
OperationStatus: FAILED
```

Cleanup destroyed the route table, subnet, and VPC. Final Terraform state was empty, `ve vepfs DescribeFileSystems --body '{"FileSystemName":"cc-iac-vepfs-retry-fs"}'` returned `TotalCount: 0`, and exact VPC-name matching for `cc-iac-vepfs-retry-vpc` returned no rows. `ve vepfs DescribeMountServiceNodeTypes --body '{"ZoneId":"cn-beijing-a"}'` still returned `NodeTypeInfos: []`, so mount service remains blocked even after instance creation is fixed.

After another permission grant, a 2026-05-30 retry in `/tmp/volcenginecc-vepfs-retry-202605301707` used the same VPC/subnet/route-table-backed vePFS shape after confirming `ve vepfs DescribeZones` reports `Advance_100` and `Performance` as `OnSale` in Beijing zones. The temporary VPC `vpc-1joxfsgv4uiv41n7ampzp4z39`, subnet `subnet-3psxsbno1yzuo6csxyw8ul7qr`, and route table `vtb-3nqudnfptzchs931ec1syj9f` created successfully, then vePFS instance creation still failed in the service backend:

```text
EventTime: 2026-05-30T17:08:14+08:00
TaskID: task-c714d023-22d5-432e-a114-f419f55d136b
ServiceInternalError: InternalError: Service has some internal Error. Pls Contact With Admin.
TypeName: Volcengine::VEPFS::Instance
Operation: CREATE
OperationStatus: FAILED
```

Cleanup destroyed the route table, subnet, and VPC. Final `terraform state list` returned empty, `ve vepfs DescribeFileSystems --body '{"Filters":[{"Key":"FileSystemName","Value":"cc-iac-vepfs-1707-fs"}],"PageNumber":1,"PageSize":10}'` returned `TotalCount: 0`, exact VPC-name matching for `cc-iac-vepfs-1707-vpc` returned `TotalCount: 0`, and checking ENIs by the deleted VPC ID returned `InvalidVpc.NotFound`.

When the vePFS service internal error is resolved, retry with this shape:

```hcl
resource "volcenginecc_vepfs_instance" "main" {
  file_system_name = "cc-iac-vepfs-fs"
  description      = "volcenginecc vePFS example file system"
  zone_id          = "cn-beijing-a"
  charge_type      = "PayAsYouGo"
  file_system_type = "VePFS"
  store_type       = "Advance_100"
  protocol_type    = "VePFS"
  project_name     = "default"
  capacity         = 8
  vpc_id           = volcenginecc_vpc_vpc.main.vpc_id
  subnet_id        = volcenginecc_vpc_subnet.main.subnet_id
  version_number   = "1.4.0"
  enable_restripe  = false
}
```

Do not add `volcenginecc_vepfs_mount_service` until a vePFS instance is verified and `ve vepfs DescribeMountServiceNodeTypes` returns a usable `node_type`; it returned empty `NodeTypeInfos` for `cn-beijing-a`, `b`, `c`, `d`, and `e` in this account. The 2026-05-30 retry still returned `NodeTypeInfos: []` for `cn-beijing-a`.

## Logs and Monitoring

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_tls_project` | Verified | Project create/no-op/destroy succeeded; see `volcenginecc-tls.md` |
| `volcenginecc_tls_topic` | Verified | Topic create/no-op/destroy succeeded; see `volcenginecc-tls.md` |
| `volcenginecc_tls_index` | Verified | Index create/no-op/destroy succeeded; see `volcenginecc-tls.md` |
| `volcenginecc_tls_rule` | Verified | Minimal host file rule create/no-op/destroy succeeded without `host_group_infos`; see `volcenginecc-tls.md` |
| `volcenginecc_tls_consumer_group` | Verified | Consumer group create/no-op/destroy succeeded with `allow_consume = true` topic; see `volcenginecc-tls.md` |
| `volcenginecc_tls_schedule_sql_task` | Verified | Disabled bounded scheduled SQL task create/no-op/destroy succeeded with indexed source/destination topics; see `volcenginecc-tls.md` |
| `volcenginecc_tls_shipper` | Drift-blocked for default example | TOS shipper create/delete worked, but no-op drifted `status = true -> false`; TOS bucket cleanup hit long Cloud Control waiter |
| `volcenginecc_tls_alarm_notify_group` | Provider-shape blocked | Empty group rejected; both GeneralWebhook `receivers` and `notice_rules.receiver_infos` groups created but provider returned inconsistent nested sets after apply |
| `volcenginecc_tls_alarm` | Dependency-blocked | Requires a stable alarm notification group ID |
| `volcenginecc_cloudmonitor_rule` | Verified | Disabled ECS CPU rule create/no-op/destroy succeeded after permission grant; see `volcenginecc-cloudmonitor.md` |

`tls_rule` was re-verified in `cn-beijing` with a minimal host-file collection rule. The first retry omitted `paths` and failed after project/topic/index creation:

```text
InvalidRequest: InvalidArgument: Invalid argument key Paths, value <nil>, please check argument.
TypeName: Volcengine::TLS::Rule
Operation: CREATE
TaskID: task-83a27070-a352-447e-9a5e-80b622396c01
EventTime: 2026-05-30T06:52:57+08:00
```

Adding `input_type = 0`, `log_type = "minimalist_log"`, and `paths = ["/var/log/messages"]` created rule ID `9d0941ac-4c7e-4aa8-8bc3-166b1d54213a`. Setting `pause = 1` caused readback drift (`pause = 0 -> 1` on the next plan), so the verified example omits `pause`. With `pause` omitted, the follow-up plan returned `No changes`, and destroy removed the rule, index, topic, and project successfully. Final Terraform state was empty.

`tls_consumer_group` was verified in `cn-beijing` with a project, a topic configured with `allow_consume = true`, and:

```hcl
resource "volcenginecc_tls_consumer_group" "app" {
  project_id          = volcenginecc_tls_project.main.project_id
  topic_id_list       = [volcenginecc_tls_topic.app.topic_id]
  consumer_group_name = "cc-iac-tls-cg-group"
  heartbeat_ttl       = 10
  ordered_consume     = false
}
```

Creation returned ID `1a5b5fcc-9932-4548-b70c-74bca345c838|cc-iac-tls-cg-group`. The topic read back `consume_topic = "out-e12b9976-6a9b-4793-ad5b-46f4f1739226"`, but the follow-up plan returned `No changes`. Destroy removed consumer group, topic, and project successfully, and final Terraform state was empty.

`tls_shipper` to TOS was retried in `cn-beijing` with a temporary TLS project/topic and TOS bucket. The first TOS bucket shape used `enable_version_status = "Disabled"` and failed provider validation because the accepted values are only `Enabled` and `Suspended`. A second shape used `Suspended`, passed validation, then failed create after the API had partially created the bucket:

```text
GeneralServiceException: InvalidBody: The bucket multi-version is not enabled.
TypeName: Volcengine::TOS::Bucket
Operation: CREATE
TaskID: task-f2c6efe3-2173-410a-9c3f-2da4557e6198
EventTime: 2026-05-30T07:11:30+08:00
```

The next create returned `AlreadyExists` for bucket `cc-iac-tls-shipper-05300712`, so the bucket was imported into the temporary state and updated to `enable_version_status = "Enabled"`. After that, a disabled TOS shipper created successfully:

```hcl
resource "volcenginecc_tls_shipper" "tos" {
  topic_id     = volcenginecc_tls_topic.app.topic_id
  shipper_name = "cc-iac-tls-shipper-tos"
  shipper_type = "tos"
  status       = false

  content_info = {
    format = "json"
    json_info = {
      enable = true
      escape = true
      keys   = ["__content__", "__source__", "__path__", "__time__"]
    }
  }

  tos_shipper_info = {
    bucket           = volcenginecc_tos_bucket.logs.name
    compress         = "none"
    interval         = 300
    max_size         = 5
    partition_format = "%Y/%m/%d/%H/%M"
    prefix           = "tls"
  }
}
```

Created shipper ID was `ac905b0f-7c83-4288-a76f-d478ccb2fb05`, but the follow-up plan was not clean:

```text
~ status = true -> false
```

Do not add `tls_shipper` to the verified TLS example until a shape produces create, no-op plan, and destroy without suppressing meaningful drift. During cleanup, shipper/topic/project deleted successfully. The TOS bucket delete entered the known long Cloud Control waiter; `tosutil stat tos://cc-iac-tls-shipper-05300712 -e=tos-cn-beijing.volces.com -re=cn-beijing` returned 404, then the stale temporary state entry was removed. Final temporary Terraform state was empty.

`tls_schedule_sql_task` was verified in `cn-beijing` with source and destination topics, each with a TLS index, plus `status = 0` and a bounded process window. The first retry without indexes failed:

```text
GeneralServiceException: IndexNotExists: Index does not exist.
TypeName: Volcengine::TLS::ScheduleSqlTask
Operation: CREATE
TaskID: task-2bb13df3-3007-4add-afb6-423866fb4cb7
EventTime: 2026-05-30T07:41:18+08:00
```

Adding indexes for both topics allowed create to succeed. Created task ID was `b266af30-f819-4eef-81a8-c9890f4d7ff7`; the follow-up plan returned `No changes`, and destroy removed the task, indexes, topics, and project successfully. Final Terraform state was empty.

`tls_alarm_notify_group` empty-group retry validated and planned, then failed during create:

```text
InvalidRequest: InvalidArgument: Invalid argument key NotifyType, value [], please check argument.
TypeName: Volcengine::TLS::AlarmNotifyGroup
Operation: CREATE
OperationStatus: FAILED
```

A second retry with `notify_type = ["Trigger", "Recovery"]` and a GeneralWebhook receiver created the notification group, but Terraform failed the apply because the provider could not correlate the planned `receivers` set with the actual returned set:

```text
Provider produced inconsistent result after apply
When applying changes to volcenginecc_tls_alarm_notify_group.webhook,
provider "registry.terraform.io/volcengine/volcenginecc" produced an unexpected new value:
.receivers: planned set element ... does not correlate with any element in actual.
```

A third retry used `notice_rules.receiver_infos` instead of top-level `notify_type`/`receivers` and also planned successfully. It created the notification group, but failed after apply with the same provider set correlation class:

```text
Provider produced inconsistent result after apply
When applying changes to volcenginecc_tls_alarm_notify_group.webhook_rule,
provider "registry.terraform.io/volcengine/volcenginecc" produced an unexpected new value:
.notice_rules: planned set element ... does not correlate with any element in actual.
```

The `notice_rules` retry used this minimal shape:

```hcl
resource "volcenginecc_tls_alarm_notify_group" "webhook_rule" {
  alarm_notify_group_name = "cc-iac-tls-notify"
  iam_project_name        = "default"

  notice_rules = [
    {
      rule_node = jsonencode({
        Type  = "Condition"
        Value = ["Severity", "in", "[\"notice\",\"warning\",\"critical\"]"]
      })
      has_next     = false
      has_end_node = true

      receiver_infos = [
        {
          receiver_type     = "User"
          receiver_names    = []
          receiver_channels = ["GeneralWebhook"]
          start_time        = "00:00:00"
          end_time          = "23:59:59"

          general_webhook_url    = "https://example.com/tls-alarm"
          general_webhook_method = "POST"
          general_webhook_headers = [
            {
              key   = "Content-Type"
              value = "application/json"
            }
          ]
          general_webhook_body = "{\"alarm\":\"cc-iac-tls\"}"
        }
      ]
    }
  ]
}
```

The partially created notification groups were present in state and were destroyed successfully with Terraform. Temporary TLS project, topic, index, and notification group resources were destroyed; final Terraform state was empty.

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-tls-notify-current` used the smallest top-level `notify_type` + one GeneralWebhook `receivers` shape, without TLS project/topic dependencies. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. The service created notification group `43e9387f-6191-42bc-8947-27704ef9bce3`, but Terraform failed the apply with the same provider nested-set correlation bug:

```text
Provider produced inconsistent result after apply
When applying changes to volcenginecc_tls_alarm_notify_group.webhook,
provider "registry.terraform.io/volcengine/volcenginecc" produced an unexpected new value:
.receivers: planned set element ... does not correlate with any element in actual.
```

The created notification group was present in Terraform state and destroyed successfully; final Terraform state was empty. Because even the smallest receiver shape cannot complete apply cleanly, `volcenginecc_tls_alarm` remains dependency-blocked for generated examples.

Retried the same smallest top-level `notify_type` + one GeneralWebhook `receivers` shape again on 2026-05-30 at 14:20 with group name `cc-iac-tls-notify-retry`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded. The service created notification group `bacc9b55-3961-4d1c-8103-d8a3650217a6`, then Terraform failed with the same provider nested-set correlation bug:

```text
Provider produced inconsistent result after apply
When applying changes to volcenginecc_tls_alarm_notify_group.webhook,
provider "provider[\"registry.terraform.io/volcengine/volcenginecc\"]" produced an unexpected new value:
.receivers: planned set element ... does not correlate with any element in actual.
```

The created notification group was present in Terraform state as a tainted resource and was destroyed successfully; final Terraform state was empty.

Current-account notification group discovery on 2026-05-30 used the read-only `volcenginecc_tls_alarm_notify_groups` data source. It returned an empty ID set:

```text
data.volcenginecc_tls_alarm_notify_groups.all: Read complete after 1s [id="cn-beijing"]
alarm_notify_group_ids = toset([])
```

Do not add a verified `tls_alarm_notify_group` or `tls_alarm` example until a notification group can apply, re-plan to no-op, and destroy cleanly. If an existing notification group is imported for a real deployment, prove a no-op plan before referencing it from `volcenginecc_tls_alarm`.

`cloudmonitor_rule` minimal disabled ECS CPU rule validated and planned successfully in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`, using `namespace = "VCM_ECS"`, `sub_namespace = "Instance"`, `enable_state = "disable"`, `CpuTotal`, and no contact group IDs. Create failed, and a 2026-05-30 retry failed with the same permission denial:

```text
AccessDenied: AccessDenied: User is not authorized to perform: cloudmonitor:CreateRule on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::CloudMonitor::Rule
Operation: CREATE
OperationStatus: FAILED
```

Latest retry evidence:

```text
EventTime: 2026-05-30T08:23:16+08:00
TaskID: task-9cb3a58e-7e64-43b7-8d3f-1d83c1fad671
AccessDenied: User is not authorized to perform: cloudmonitor:CreateRule on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::CloudMonitor::Rule
Operation: CREATE
OperationStatus: FAILED
```

Latest current-AK retry evidence:

```text
EventTime: 2026-05-30T10:38:58+08:00
TaskID: task-e68f2d6f-6237-49da-bf5f-02aa398ed231
AccessDenied: User is not authorized to perform: cloudmonitor:CreateRule on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::CloudMonitor::Rule
Operation: CREATE
OperationStatus: FAILED
```

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-cloudmonitor-current` used the same disabled ECS CPU rule shape with rule name `cc-iac-cm-ecs-cpu-current`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded; apply failed before creating any resource:

```text
EventTime: 2026-05-30T12:20:27+08:00
TaskID: task-f6f51d03-1020-4ead-ad50-da3ad229f04e
AccessDenied: User is not authorized to perform: cloudmonitor:CreateRule on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::CloudMonitor::Rule
Operation: CREATE
OperationStatus: FAILED
```

Retried the same disabled ECS CPU rule shape again on 2026-05-30 at 13:57 with rule name `cc-iac-cm-ecs-cpu-retry`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; apply still failed before creating any resource:

```text
EventTime: 2026-05-30T13:57:30+08:00
TaskID: task-d79cd50f-1c2e-4830-abfb-5119264baa32
AccessDenied: User is not authorized to perform: cloudmonitor:CreateRule on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::CloudMonitor::Rule
Operation: CREATE
OperationStatus: FAILED
```

No CloudMonitor resources were created in those retries; Terraform state remained empty. The latest `ve cloudmonitor ListRules --body '{"PageNumber":1,"PageSize":10,"RuleName":"cc-iac-cm-ecs-cpu-current"}'` returned an empty `Data` list. The account has a default CloudMonitor contact group (`2060456752737312768`) but it contains no contacts.

After `cloudmonitor:CreateRule` was granted, a 2026-05-30 retry in `/tmp/volcenginecc-cloudmonitor-retry-20260530151009` verified `volcenginecc_cloudmonitor_rule`. The first post-permission create without a concrete notification route failed with:

```text
EventTime: 2026-05-30T15:10:31+08:00
TaskID: task-c53f8582-58f6-4489-926e-937e8261252c
InvalidRequest: InvalidParam.Notification: 通知渠道和回调不能同时为空
TypeName: Volcengine::CloudMonitor::Rule
Operation: CREATE
OperationStatus: FAILED
```

Binding the default contact group then failed because it had no members:

```text
EventTime: 2026-05-30T15:11:04+08:00
TaskID: task-34a7edf5-5851-4c66-aa3c-004d4d7e18f1
InvalidRequest: ContactGroupMemberEmpty: 联系组 默认告警联系组 2060456752737312768 的联系人为空，请选择非空联系组
TypeName: Volcengine::CloudMonitor::Rule
Operation: CREATE
OperationStatus: FAILED
```

Using Webhook notification moved validation to the metric period field. `period = "1m"` and `period = "60s"` both failed with `InvalidParam.Period`; `period = "60"` succeeded. The verified disabled ECS CPU rule created ID `2060620425061621760`, follow-up `terraform plan -detailed-exitcode` returned `No changes`, `terraform destroy` removed the rule, final Terraform state was empty, and `ve cloudmonitor ListRules --body '{"PageNumber":1,"PageSize":10,"RuleName":"cc-iac-cm-ecs-cpu-retry2"}'` returned an empty `Data` list.

Retry shape:

```hcl
resource "volcenginecc_cloudmonitor_rule" "ecs_cpu" {
  rule_name        = "cc-iac-cm-ecs-cpu"
  description      = "volcenginecc CloudMonitor example disabled ECS CPU rule"
  rule_type        = "static"
  namespace        = "VCM_ECS"
  sub_namespace    = "Instance"
  level            = "warning"
  evaluation_count = 1
  enable_state     = "disable"
  regions          = ["cn-beijing"]
  project_name     = "default"

  original_dimensions = {
    key    = "ResourceID"
    values = ["*"]
  }

  multiple_conditions = false
  condition_operator  = "&&"

  conditions = [
    {
      metric_name         = "CpuTotal"
      statistics          = "avg"
      comparison_operator = ">"
      threshold           = "95"
      period              = "1m"
      metric_unit         = "Percent"
    }
  ]

  no_data = {
    enable           = false
    evaluation_count = 3
  }

  recovery_notify = {
    enable = false
  }

  silence_time    = 5
  alert_methods   = ["Email"]
  effect_start_at = "00:00"
  effect_end_at   = "23:59"
}
```

## VPC Extended Resources

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_vpc_prefix_list` | Verified | Prefix list create/no-op/destroy succeeded; see `volcenginecc-vpc-extras.md` |
| `volcenginecc_vpc_network_acl` | Verified | Subnet ACL create/no-op/destroy succeeded; see `volcenginecc-vpc-extras.md` |
| `volcenginecc_vpc_eni` | Verified | Standalone secondary ENI create/no-op/destroy succeeded; see `volcenginecc-vpc-extras.md` |
| `volcenginecc_vpc_ha_vip` | Verified | Unbound HAVIP create/no-op/destroy succeeded; see `volcenginecc-vpc-extras.md` |
| `volcenginecc_vpc_bandwidth_package` | Verified | Empty IPv4 BGP shared bandwidth package create/no-op/destroy succeeded; see `volcenginecc-vpc-extras.md` |
| `volcenginecc_vpc_ipv6_gateway` | Dependency-blocked | VPC creation with `enable_ipv_6 = true` failed before gateway create |
| `volcenginecc_vpc_ipv6_address_bandwidth` | Dependency-blocked | Requires a VPC/subnet/ENI IPv6 address; VPC IPv6 create is unsupported in current API path |
| `volcenginecc_vpc_flow_log` | Permission-blocked | `InvalidOperation.NoPermission` during create |
| `volcenginecc_vpc_traffic_mirror_filter` | Verified | Standalone filter create/no-op/destroy succeeded; see `volcenginecc-vpc-traffic-mirror-filter.md` |
| `volcenginecc_vpc_traffic_mirror_filter_rule` | Verified | Ingress TCP rule create/no-op/destroy succeeded; see `volcenginecc-vpc-traffic-mirror-filter.md` |
| `volcenginecc_vpc_traffic_mirror_target` | Verified | Private CLB target create/no-op/destroy succeeded; see `volcenginecc-vpc-traffic-mirror-target.md` |
| `volcenginecc_vpc_traffic_mirror_session` | Spec-blocked | Attached ECS ENI from `ecs.g4i.large` rejected because the instance spec does not support traffic mirror |

IPv6 retry in `cn-beijing`: a VPC with `enable_ipv_6 = true`, IPv6 subnet, IPv6 gateway, and IPv6-enabled ENI validated and planned successfully, but VPC create failed before any resource was created:

```text
EventTime: 2026-05-30T08:37:36+08:00
TaskID: task-547630d7-8255-4ccb-a9c7-b7044e0b2577
InvalidRequest: InvalidParameter.EnableIpv6: The EnableIpv6 parameter is currently not supported.
TypeName: Volcengine::VPC::VPC
Operation: CREATE
OperationStatus: FAILED
```

No IPv6 resources were created; Terraform state remained empty. Retry `volcenginecc_vpc_ipv6_gateway` and `volcenginecc_vpc_ipv6_address_bandwidth` only after the Cloud Control VPC create path accepts `enable_ipv_6 = true`, or by importing an existing IPv6-enabled VPC/subnet/IPv6 address.

Flow log retry in `cn-beijing`: a VPC plus TLS project/topic target validated and planned successfully. TLS project/topic and the VPC created, then `volcenginecc_vpc_flow_log` failed:

```text
EventTime: 2026-05-30T08:41:37+08:00
TaskID: task-71fc48d1-53d6-4ba1-b49a-982e87c04834
AccessDenied: InvalidOperation.NoPermission: The current service is not allowed to do this operation.
TypeName: Volcengine::VPC::FlowLog
Operation: CREATE
OperationStatus: FAILED
```

The TLS project, TLS topic, and VPC dependencies were destroyed and Terraform state was empty afterward. Retry after the account has permission to create VPC flow logs.

Traffic mirror filter retry in `cn-beijing`: standalone filter `tmf-3pst38p3t0jcw6csxyvwz4zbl` and ingress TCP filter rule `tmr-3pst47jzgnfnk6csxyw7yh4ip` created successfully, returned a clean no-op plan, then destroyed successfully with final Terraform state empty. See `volcenginecc-vpc-traffic-mirror-filter.md` for the verified example.

Full traffic mirror target/session retry in `cn-beijing`: filter, ingress TCP filter rule, VPC, subnet, route table, security group, and two standalone ENIs created successfully. Creating a mirror target from the standalone target ENI failed:

```text
EventTime: 2026-05-30T08:40:22+08:00
TaskID: task-dcdf7dc8-1619-4bf6-b9d5-4927e3c3dd08
InvalidRequest: InvalidEni.InstanceMismatch: The specified elastic network interface is not attached to the specified instance.
TypeName: Volcengine::VPC::TrafficMirrorTarget
Operation: CREATE
OperationStatus: FAILED
```

All created dependencies were destroyed and Terraform state was empty afterward. Retry the full target/session path with two ECS-attached ENIs, or a CLB instance as the target, instead of standalone ENIs.

Second full traffic mirror target/session retry in `cn-beijing`: a temporary ECS instance `i-yenb54ta0wwh2yosws0r` with attached primary ENI `eni-1jo66i9dxfe9s1n7amp3p3r8p` and a private CLB `clb-mj1i8xbze0w05smt1aesjjg0` were created successfully. A CLB mirror target `tmt-3nqye2tsbjksg931ecgdajy6`, filter `tmf-3nqye2a20f11c931ec3b3h8z`, and rule `tmr-3nqyfm0ofytxc931ecepx6n3` also created successfully. A later standalone CLB mirror target example returned a clean no-op plan and is now verified in `volcenginecc-vpc-traffic-mirror-target.md`. Creating the mirror session then failed:

```text
EventTime: 2026-05-30T09:41:03+08:00
TaskID: task-f0f925f4-1ad8-48e3-ad0d-32806da050ef
InvalidRequest: InvalidInstanceSpecification.Malformed: The specified instance does not currently support traffic mirror.
TypeName: Volcengine::VPC::TrafficMirrorSession
Operation: CREATE
OperationStatus: FAILED
```

The mirror target/filter/rule, private CLB, ECS instance, keypair, security group, route table, subnet, and VPC were all destroyed successfully. Final Terraform state was empty in both temporary verification directories. Retry `volcenginecc_vpc_traffic_mirror_session` only after selecting an ECS instance family that explicitly supports traffic mirroring.

## VPN Remaining Resources

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_vpn_vpn_gateway` | Verified | IPsec and SSL gateway shapes both create/no-op/destroy; see `volcenginecc-vpn.md` and `volcenginecc-vpn-ssl.md` |
| `volcenginecc_vpn_customer_gateway` | Verified | Customer gateway create/no-op/destroy succeeded in the IPsec example |
| `volcenginecc_vpn_vpn_connection` | Verified | IPsec connection create/no-op/destroy succeeded with sensitive PSK variable |
| `volcenginecc_vpn_vpn_gateway_route` | Verified | Static VPN gateway route create/no-op/destroy succeeded |
| `volcenginecc_vpn_ssl_vpn_server` | Verified | SSL VPN server create/no-op/destroy succeeded; see `volcenginecc-vpn-ssl.md` |
| `volcenginecc_vpn_ssl_vpn_client_cert` | Sensitive-state blocked | Resource returns `client_key`, client certificate, CA certificate, and OpenVPN config into Terraform state |

SSL VPN server retry in `cn-beijing`: VPC, subnet, route table, SSL-enabled VPN gateway, and SSL VPN server created successfully. The first SSL server attempt failed because `client_ip_pool = "172.30.200.0/26"` overlapped `local_subnets = ["172.30.0.0/16"]`:

```text
EventTime: 2026-05-30T13:41:39+08:00
TaskID: task-74e7b4b9-a036-4170-afaf-7ab2fc368424
InvalidRequest: InvalidSslVpnClientIpPool.Conflict: The specified ClientIpPool conflicts with that of local subnets.
TypeName: Volcengine::VPN::SslVpnServer
Operation: CREATE
OperationStatus: FAILED
```

Changing `client_ip_pool` to `10.250.0.0/26` fixed the shape. The successful run created VPN gateway `vgw-3nr16uvy3e1og931eb9v4m8n` and SSL VPN server `vss-ijh95fubdqm874o8cv2fkow7`; a follow-up plan returned `No changes`. Destroy removed the SSL server, gateway, route table, subnet, and VPC; final Terraform state was empty. `DescribeVpnGateways --VpnGatewayName cc-iac-vpn-ssl-current-gateway` and `DescribeVpcs --VpcName cc-iac-vpn-ssl-current-vpc` both returned `TotalCount: 0`.

Do not add `vpn_ssl_vpn_client_cert` to shared examples unless the user explicitly accepts that generated client private key material will be stored in Terraform state.

## TOS Extended Resources

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_tos_bucket` | Verified | Bucket create/no-op/destroy succeeded; see `volcenginecc-tos.md` |
| `volcenginecc_tos_bucket_cors` | Verified | CORS create/no-op/destroy succeeded; see `volcenginecc-tos.md` |
| `volcenginecc_tos_bucket_encryption` | Verified | AES256 encryption create/no-op/destroy succeeded; see `volcenginecc-tos.md` |
| `volcenginecc_tos_bucket_inventory` | Assume-role blocked | Terraform-created IAM role/policy still failed `InvalidRole: assume role fail` |
| `volcenginecc_tos_bucket_notification` | Verified | veFaaS target notification create/no-op/destroy succeeded; see `volcenginecc-tos-notification.md` |
| `volcenginecc_tos_bucket_realtime_log` | External role blocked | `InvalidRole: Role must exist` using default-looking role name |

TOS extended retry in `cn-beijing`: bucket `cc-iac-tos-extra-05300844` created successfully, then all three extended resources failed:

```text
EventTime: 2026-05-30T08:46:43+08:00
TaskID: task-dd356d04-ab97-4ea3-9a18-6737378dcd5f
GeneralServiceException: InvalidRole: Role must exist.
TypeName: Volcengine::TOS::BucketInventory
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T08:46:43+08:00
TaskID: task-7661e202-e19e-403d-8554-bc0973f7e463
NotFound: NotificationRule not found
TypeName: Volcengine::TOS::BucketNotification
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T08:46:43+08:00
TaskID: task-2229e424-fc40-4d28-92d0-323d9dee3d8e
GeneralServiceException: InvalidRole: Role must exist.
TypeName: Volcengine::TOS::BucketRealtimeLog
Operation: CREATE
OperationStatus: FAILED
```

The bucket was deleted; `tosutil stat tos://cc-iac-tos-extra-05300844 -e=tos-cn-beijing.volces.com -re=cn-beijing` returned 404. The Cloud Control delete waiter kept running after cloud-side deletion, so the temporary state entry was removed only after the 404 and Terraform refresh warning confirmed the resource was gone.

Retry inventory and realtime log only after creating the required IAM roles and granting TOS service access. Retry notification with a real Kafka, RocketMQ, or veFaaS destination; do not use `notification_rules = []` as a create-time baseline.

TOS bucket inventory was retried again in the current account with Terraform-created IAM role and policy prerequisites. The role trust policy allowed `Principal.Service = ["tos.volcengine.com"]` to call `sts:AssumeRole`, and the custom policy allowed `tos:Get*`, `tos:List*`, and `tos:PutObject` on the inventory bucket. IAM role `cc-iac-tos-role-current-role`, IAM policy `cc-iac-tos-role-current-policy|Custom`, and bucket `cc-iac-tos-inv-current` all created successfully, but inventory create still failed:

```text
EventTime: 2026-05-30T13:18:49+08:00
TaskID: task-c65ae5ed-6bf0-4eaa-8a8f-bc513d39c3fa
GeneralServiceException: InvalidRole: assume role fail, please check role.
TypeName: Volcengine::TOS::BucketInventory
Operation: CREATE
OperationStatus: FAILED
```

Do not add a verified `tos_bucket_inventory` example until the exact service principal, role path/name requirement, or account-side trust requirement is confirmed. Cleanup note: after the failure, IAM policy and role destroyed cleanly. The TOS bucket was cloud-side deleted (`tosutil stat` returned 404), but Cloud Control kept waiting on delete, so the stale bucket state entry was removed only after confirming the 404. Final temporary Terraform state was empty.

TOS bucket notification was later verified with a released veFaaS function destination. The first attempt with only `volcenginecc_vefaas_function` failed because TOS requires the function to be fully released:

```text
EventTime: 2026-05-30T12:44:12+08:00
TaskID: task-be420bf3-78d8-4052-b8e1-04fbee0fa470
InvalidRequest: InvalidArgument: faas function has not been fully released yet, please release it first
TypeName: Volcengine::TOS::BucketNotification
Operation: CREATE
OperationStatus: FAILED
```

Adding `volcenginecc_vefaas_release` and an explicit `depends_on` from the notification to the release fixed the dependency. Bucket `cc-iac-tos-noti-current`, function `4cjgrs2l`, release record `ybfg6a9met7gd111`, and notification `cc-iac-tos-noti-current` created successfully, and a follow-up plan returned `No changes`. See [`volcenginecc-tos-notification.md`](./volcenginecc-tos-notification.md) for cleanup caveats: TOS bucket deletion can leave a stuck Cloud Control waiter after TOS returns 404, and finished veFaaS release records may need `terraform state rm`.

## EBS Extended Resources

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_storageebs_volume` | Verified | Standalone data disk create/no-op/destroy succeeded; see `volcenginecc-ecs.md` and `volcenginecc-ebs-snapshot.md` |
| `volcenginecc_storageebs_snapshot` | Verified | Manual snapshot create/no-op/destroy succeeded; see `volcenginecc-ebs-snapshot.md` |
| `volcenginecc_storageebs_snapshot_group` | Lifecycle verified with parent drift | Snapshot group create/destroy succeeded from an ECS system volume; fresh no-op drift came from parent ECS/security-group Optional+Computed fields, not the snapshot group |

Manual snapshot verification in `cn-beijing`: a 10 GiB `ESSD_PL0` postpaid data disk in `cn-beijing-a` created successfully, snapshot `snap-3x4l1lwpj94i4t7woexd` created in about 2m6s, a follow-up plan returned `No changes`, and destroy removed the snapshot and disk. Final Terraform state was empty.

Snapshot group retry in `cn-beijing`: an ECS-backed system volume path validated, planned, applied, and destroyed successfully. First create failed only because `description` was set on the snapshot group:

```text
EventTime: 2026-05-30T10:00:58+08:00
TaskID: task-b2e1aefd-5c81-4f9c-8d61-8c5d828b1398
InvalidRequest: InvalidParameter.Description: The specified description is invalid.
TypeName: Volcengine::StorageEBS::SnapshotGroup
Operation: CREATE
OperationStatus: FAILED
```

After omitting `description`, snapshot group `sg-3x4l645av94i4t7xb043` created from ECS instance `i-yenb6ggdfkxjd1u6a5gq` and system volume `vol-3x4l625l4h42xlzbc9tb`, returned a clean follow-up plan, and destroyed successfully. A fresh run from empty state also created snapshot group `sg-3x4l6dnynl42xlzbet12` from ECS instance `i-yenb6rc9vkxjd1utivbg` and system volume `vol-3x4l6d2w4x42xlzbepss`; the snapshot group itself had no drift, but the follow-up plan showed parent `volcenginecc_ecs_instance` and `volcenginecc_vpc_security_group` Optional+Computed pseudo-diffs. Destroy removed all seven resources and final Terraform state was empty.

Use [`volcenginecc-ebs-snapshot-group.md`](./volcenginecc-ebs-snapshot-group.md) for the verified lifecycle example. Do not use standalone unattached disks for snapshot groups.

## Auto Scaling

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_autoscaling_scaling_group` | Lifecycle verified with drift/destroy caveat | Create/destroy succeeded only with a launch template; follow-up plan showed provider readback pseudo-diffs |
| `volcenginecc_autoscaling_scaling_configuration` | Lifecycle verified with destroy caveat | Create succeeded and was cascaded by scaling group deletion; direct Terraform destroy can fail while it is the active configuration |
| `volcenginecc_autoscaling_scaling_lifecycle_hook` | Lifecycle verified | Scale-out hook create/delete succeeded |
| `volcenginecc_autoscaling_scaling_policy` | API/provider-shape blocked | Scheduled policy launch times from docs and RFC3339 variants all failed as malformed |

Auto Scaling retry in `cn-beijing`: VPC, subnet, route table, security group, keypair, ECS launch template, scaling group, scaling configuration, and lifecycle hook validated, planned, applied, and destroyed. A successful run created launch template `lt-yenb7gkazegln4lcig9d`, scaling group `scg-yenb7gl9ihfv0hfqhula`, scaling configuration `scc-yenb7j74kci1qnmuk05a`, and lifecycle hook `sgh-yenb7j7sow9ht5yj9vf5`; destroy removed all nine resources and final Terraform state was empty.

Creating the scaling group without `launch_template_id` failed even though generated docs mark it optional:

```text
EventTime: 2026-05-30T10:14:57+08:00
TaskID: task-2169963f-6192-43bd-a5f8-5f47bc72e6ae
MissingParameter.LaunchTemplateId
TypeName: Volcengine::AutoScaling::ScalingGroup
Operation: CREATE
OperationStatus: FAILED
```

Creating the required launch template without `launch_template_version.volumes` failed:

```text
EventTime: 2026-05-30T10:15:37+08:00
TaskID: task-fbbc455e-15e8-4ef4-9ae4-db83e37b85c8
MissingParameter.LaunchTemplateVolumes
TypeName: Volcengine::ECS::LaunchTemplate
Operation: CREATE
OperationStatus: FAILED
```

Scheduled scaling policies failed for multiple future time formats, including `2030-01-01T00:00Z`, `2030-01-01T00:00+08:00`, and `2030-01-01T00:00:00Z`:

```text
EventTime: 2026-05-30T10:23:55+08:00
TaskID: task-2dc0f91d-f29b-41f8-8f3e-48b736d14e7c
InvalidRequest: InvalidScheduledPolicyLaunchTime.Malformed: The specified ScheduledPolicy LaunchTime is malformed.
TypeName: Volcengine::AutoScaling::ScalingPolicy
Operation: CREATE
OperationStatus: FAILED
```

One cleanup run exposed Terraform destroy ordering drift: deleting the active scaling configuration before the scaling group failed with `InvalidScalingConfiguration.InUse`. Recovery removed the configuration from state, destroyed the scaling group first, confirmed both group and configuration were gone with `ve autoscaling DescribeScalingGroups --ScalingGroupIds.1 scg-yenb7wby5nfv0gjg6syk` and `ve autoscaling DescribeScalingConfigurations --ScalingConfigurationIds.1 scc-yenb7yvoud9ht4efbcr9`, then destroyed the remaining launch template/network dependencies. Final Terraform state was empty.

Use [`volcenginecc-autoscaling.md`](./volcenginecc-autoscaling.md) for the verified lifecycle example. Do not add `autoscaling_scaling_policy` to shared examples until a scheduled or alarm policy shape reaches create, no-op, and destroy without manual recovery.

## CBR

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_cbr_vault` | Permission-blocked | `AccessDenied: User is not authorized to perform: cbr:CreateVault` during create |
| `volcenginecc_cbr_backup_policy` | Permission-blocked | `AccessDenied: User is not authorized to perform: cbr:CreateBackupPolicy` during create |
| `volcenginecc_cbr_backup_resource` | Dependency-blocked | Requires permission plus a real ECS or vePFS backup source |
| `volcenginecc_cbr_backup_plan` | Dependency-blocked | Requires a backup policy and backup resource |

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-cbr-current` used a minimal independent shape: one backup vault and one disabled full backup policy. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply failed before any resource IDs were created:

```text
EventTime: 2026-05-30T13:26:06+08:00
TaskID: task-ac67bd68-813a-4438-b5aa-cc06d0f162db
AccessDenied: AccessDenied: User is not authorized to perform: cbr:CreateVault on resource: trn:iam::2109984414:project/default
TypeName: Volcengine::CBR::Vault
Operation: CREATE
OperationStatus: FAILED
```

```text
EventTime: 2026-05-30T13:26:06+08:00
TaskID: task-5db8277c-6060-4250-9e80-17a3b35a1b81
AccessDenied: AccessDenied: User is not authorized to perform: cbr:CreateBackupPolicy on resource:
TypeName: Volcengine::CBR::BackupPolicy
Operation: CREATE
OperationStatus: FAILED
```

No CBR resources were created; Terraform state remained empty. The provider docs have a resource naming pitfall: the backup policy example uses `volcenginecc_cbr_backuppolicy`, but the registered Terraform resource type is `volcenginecc_cbr_backup_policy`. After `cbr:CreateVault` and `cbr:CreateBackupPolicy` are granted, retry the minimal vault plus disabled policy first. Add `cbr_backup_resource` and `cbr_backup_plan` only after selecting a disposable ECS or vePFS source and proving create, no-op plan, destroy, and empty final state.

## VMP

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_vmp_workspace` | Service-disabled blocked | `ProductUnsubscribed: You are not subscribed to VMP` during create |
| `volcenginecc_vmp_alerting_rule` | Dependency-blocked | Requires a working VMP workspace; notification policies are optional only after create is proven |

Current-account retry on 2026-05-30 in `/tmp/volcenginecc-vmp-current` used a minimal workspace without custom credentials: `auth_type = "None"`, `public_access_enabled = false`, `delete_protection_enabled = false`, and `instance_type_id = "vmp.standard.15d"`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded. Apply failed before a workspace ID was created:

```text
EventTime: 2026-05-30T13:27:55+08:00
TaskID: task-ea6aafc3-19e5-4f76-add2-5f698cb3fd13
ServiceNotEnabled: ProductUnsubscribed: You are not subscribed to VMP. Please go to the VMP console web page to subscribe to the service.
TypeName: Volcengine::VMP::Workspace
Operation: CREATE
OperationStatus: FAILED
```

No VMP resources were created; Terraform state remained empty. Do not add a verified `volcenginecc-vmp` example until the VMP service is subscribed. After subscription, retry the private workspace first; only add `vmp_alerting_rule` after the workspace reaches no-op, using `status = "Disabled"` and no notification policy IDs to test whether rules can be staged before notification routing exists.

## DNS, PrivateZone, CDN, and WAF Remaining Resources

Attempted resources:

| Resource | Status | Evidence |
|---|---|---|
| `volcenginecc_dns_zone` | Verified | Public zone create/no-op/destroy succeeded; see `volcenginecc-dns.md` |
| `volcenginecc_privatezone_private_zone` | Verified | Private zone create/no-op/destroy succeeded; see `volcenginecc-privatezone.md` |
| `volcenginecc_privatezone_record` | Verified | Private A record create/no-op/destroy succeeded; see `volcenginecc-privatezone.md` |
| `volcenginecc_privatezone_resolver_endpoint` | Service-linked-role blocked | `ErrServiceNotTrusted: ServiceLinkedRole of private_zone is not trusted` during create |
| `volcenginecc_privatezone_resolver_rule` | Dependency-blocked | Requires a working resolver endpoint ID |
| `volcenginecc_privatezone_user_vpc_authorization` | External dependency blocked | Self-account validation rejected; requires a real target account/verification flow |
| `volcenginecc_cdn_domain` | Service-disabled blocked | `ServiceNotEnabled: OperationDenied.ServiceStopped` during create |
| `volcenginecc_cdn_share_config` | Service-disabled blocked | Minimal shared referer config planned, but CDN service is stopped for the account |
| `volcenginecc_waf_domain` | Domain dependency blocked | Unregistered test domain failed DNICP validation |

PrivateZone resolver endpoint validated and planned successfully with a two-AZ VPC/subnet shape, then failed during create:

```text
InvalidRequest: ErrServiceNotTrusted: ServiceLinkedRole of private_zone is not trusted
TypeName: Volcengine::PrivateZone::ResolverEndpoint
Operation: CREATE
OperationStatus: FAILED
```

Latest retry evidence:

```text
EventTime: 2026-05-30T08:28:34+08:00
TaskID: task-90f74600-270e-40d6-9c50-a2dc242bd12f
InvalidRequest: ErrServiceNotTrusted: ServiceLinkedRole of private_zone is not trusted
TypeName: Volcengine::PrivateZone::ResolverEndpoint
Operation: CREATE
OperationStatus: FAILED
```

Retried the same two-AZ VPC/subnet shape again on 2026-05-30 at 14:14, with `volcenginecc_privatezone_resolver_rule` in the same plan depending on the endpoint. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded. Apply created temporary VPC `vpc-1jo4zz1kwfy801n7amqmtj8za`, subnets `subnet-1jo518l7l1jpc1n7ampvkwdgq` and `subnet-3nr6mwzbrfaps931eb0tqvtt`, and route table `vtb-btl6x31q9dkw5h0b2tt8bzzk`; endpoint creation still failed before the resolver rule dependency could run:

```text
EventTime: 2026-05-30T14:14:22+08:00
TaskID: task-4c3c562b-acf3-46c9-8f97-44fae2967cb7
InvalidRequest: ErrServiceNotTrusted: ServiceLinkedRole of private_zone is not trusted
TypeName: Volcengine::PrivateZone::ResolverEndpoint
Operation: CREATE
OperationStatus: FAILED
```

The failed retries created only temporary VPC/subnet/route-table dependencies. Recovery destroyed all temporary network resources; final Terraform state was empty, and exact VPC-name matching for `cc-iac-pzone-resolver-retry-vpc` returned no rows.

Because the resolver endpoint never created, `volcenginecc_privatezone_resolver_rule` was not applied. When the PrivateZone service-linked role is trusted, retry with this shape:

```hcl
resource "volcenginecc_privatezone_resolver_endpoint" "outbound" {
  name          = "cc-iac-pzone-endpoint"
  vpc_id        = volcenginecc_vpc_vpc.main.vpc_id
  vpc_region    = "cn-beijing"
  direction     = "OUTBOUND"
  endpoint_type = "IPv4"
  project_name  = "default"

  ip_configs = [
    {
      az_id     = "cn-beijing-a"
      subnet_id = volcenginecc_vpc_subnet.primary.subnet_id
    },
    {
      az_id     = "cn-beijing-b"
      subnet_id = volcenginecc_vpc_subnet.secondary.subnet_id
    }
  ]
}

resource "volcenginecc_privatezone_resolver_rule" "outbound" {
  name        = "cc-iac-pzone-rule"
  type        = "OUTBOUND"
  endpoint_id = tonumber(volcenginecc_privatezone_resolver_endpoint.outbound.endpoint_id)
  zone_name   = "corp.internal"

  forward_i_ps = [
    {
      ip   = "100.96.0.10"
      port = 53
    }
  ]

  vp_cs = [
    {
      region = "cn-beijing"
      vpc_id = volcenginecc_vpc_vpc.main.vpc_id
    }
  ]
}
```

`volcenginecc_privatezone_user_vpc_authorization` validated and planned with the current account ID and `auth_type = 0`, then failed as expected:

```text
InvalidRequest: ErrAccountSelfValidationNotAllowed: account self-validation not allowed
TypeName: Volcengine::PrivateZone::UserVPCAuthorization
Operation: CREATE
OperationStatus: FAILED
```

Retried the same current-account `auth_type = 0` shape on 2026-05-30 at 14:17. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; apply still failed at the self-account validation boundary before creating any authorization:

```text
EventTime: 2026-05-30T14:17:17+08:00
TaskID: task-713d0927-c425-490e-8c0f-0fabbddf0ece
InvalidRequest: ErrAccountSelfValidationNotAllowed: account self-validation not allowed
TypeName: Volcengine::PrivateZone::UserVPCAuthorization
Identifier: 2109984414
Operation: CREATE
OperationStatus: FAILED
```

Terraform state remained empty.

Do not add this as a generic verified example. It needs either an enterprise-organization target account (`auth_type = 0`) or an out-of-band verification code (`auth_type = 1`) for a real cross-account VPC authorization.

`volcenginecc_cdn_domain` minimal IP-origin configuration validated and planned successfully, then create failed because CDN is stopped for the account:

```text
ServiceNotEnabled: OperationDenied.ServiceStopped: 服务处于停用状态，不支持该操作。
TypeName: Volcengine::CDN::Domain
Operation: CREATE
OperationStatus: FAILED
```

Current-account retry on 2026-05-30 used the same minimal IP-origin shape in `/tmp/volcenginecc-cdn-current`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded; apply failed before creating a CDN domain:

```text
EventTime: 2026-05-30T12:27:35+08:00
TaskID: task-7f06dc07-70c2-4600-8127-5e0a83415f68
ServiceNotEnabled: OperationDenied.ServiceStopped: 服务处于停用状态，不支持该操作。
TypeName: Volcengine::CDN::Domain
Operation: CREATE
OperationStatus: FAILED
```

Retried the same minimal IP-origin shape again on 2026-05-30 at 14:09 with domain `cdn.example.com`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; apply still failed at the CDN service-state boundary:

```text
EventTime: 2026-05-30T14:09:21+08:00
TaskID: task-22c5431f-3067-4312-aa7d-b8244f102e7a
ServiceNotEnabled: OperationDenied.ServiceStopped: 服务处于停用状态，不支持该操作。
TypeName: Volcengine::CDN::Domain
Identifier: cdn.example.com
Operation: CREATE
OperationStatus: FAILED
```

Terraform state remained empty. A cloud-side `ve cdn DescribeCdnConfig` check for `cdn.example.com` was also blocked by `OperationDenied.ServiceStopped`, so CDN must be enabled before any domain residue can be queried directly.

`volcenginecc_cdn_share_config` minimal shared referer allowlist configuration also validated and planned successfully, then failed with the same service-stopped status:

```text
ServiceNotEnabled: OperationDenied.ServiceStopped: 服务处于停用状态，不支持该操作。
TypeName: Volcengine::CDN::ShareConfig
Operation: CREATE
TaskID: task-11a70a5f-4b96-4d93-900e-b90453e2cbcc
EventTime: 2026-05-30T07:07:48+08:00
```

Current-account retry on 2026-05-30 used the same minimal shared referer allowlist shape in `/tmp/volcenginecc-cdn-share-current`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded; apply failed before creating a shared config:

```text
EventTime: 2026-05-30T12:27:35+08:00
TaskID: task-d4d3920c-736f-4da7-a7f1-36fd527ba370
ServiceNotEnabled: OperationDenied.ServiceStopped: 服务处于停用状态，不支持该操作。
TypeName: Volcengine::CDN::ShareConfig
Operation: CREATE
OperationStatus: FAILED
```

No CDN shared config resources were created; Terraform state remained empty. Retry both CDN resources only after CDN is enabled for the account.

Retry shape after CDN is enabled:

```hcl
resource "volcenginecc_cdn_domain" "main" {
  domain         = "cdn.example.com"
  service_type   = "web"
  service_region = "outside_chinese_mainland"
  project        = "default"

  origin = [
    {
      origin_action = {
        origin_lines = [
          {
            address               = "1.1.1.1"
            http_port             = "80"
            https_port            = "443"
            instance_type         = "ip"
            origin_host           = "cdn.example.com"
            origin_type           = "primary"
            private_bucket_access = false
            weight                = "1"
          }
        ]
      }
    }
  ]
}
```

`volcenginecc_waf_domain` minimal CNAME HTTP configuration validated and planned successfully, then create failed because the throwaway domain was not registered with DNICP:

```text
InvalidRequest: InvalidParameter: Domain(cc-iac-waf-0530043107.com) The domain name is not registered with DNICP
TypeName: Volcengine::WAF::Domain
Operation: CREATE
OperationStatus: FAILED
```

Current-account retry on 2026-05-30 used the same CNAME HTTP shape in `/tmp/volcenginecc-waf-current`, with a public IP origin and `protocols = ["HTTP"]`. `terraform fmt`, `init -backend=false`, `validate`, and `plan` succeeded; apply failed before creating a WAF domain because the test domain was not registered with DNICP:

```text
EventTime: 2026-05-30T12:28:51+08:00
TaskID: task-f1f680d7-6b13-4469-9828-367a3a7ea4ce
InvalidRequest: InvalidParameter: Domain(cc-iac-waf-current.example.com) The domain name is not registered with DNICP
TypeName: Volcengine::WAF::Domain
Operation: CREATE
OperationStatus: FAILED
```

Retried the same CNAME HTTP shape again on 2026-05-30 at 14:10 with domain `cc-iac-waf-retry.example.com`. `terraform fmt -check`, `init -backend=false`, `validate`, and `plan` succeeded; apply was still rejected by DNICP registration validation before creating a WAF domain:

```text
EventTime: 2026-05-30T14:10:59+08:00
TaskID: task-79ee70f4-3ebc-493e-841d-7a1d2129d3cd
InvalidRequest: InvalidParameter: Domain(cc-iac-waf-retry.example.com) The domain name is not registered with DNICP
TypeName: Volcengine::WAF::Domain
Identifier: cc-iac-waf-retry.example.com
Operation: CREATE
OperationStatus: FAILED
```

Terraform state remained empty. A generic WAF example cannot be cleanly verified with a throwaway domain; use a real registered domain and an origin that can safely receive WAF probes.

Retry with a real registered domain and reachable origin:

```hcl
resource "volcenginecc_waf_domain" "main" {
  access_mode        = 10
  domain             = "www.example.com"
  lb_algorithm       = "wrr"
  public_real_server = 1
  project_name       = "default"
  vpc_id             = ""
  protocols          = ["HTTP"]

  protocol_ports = {
    http = [80]
  }

  backend_groups = [
    {
      access_port = [80]
      name        = "default"
      backends = [
        {
          protocol = "HTTP"
          port     = 80
          ip       = "1.1.1.1"
          weight   = 50
        }
      ]
    }
  ]
}
```
