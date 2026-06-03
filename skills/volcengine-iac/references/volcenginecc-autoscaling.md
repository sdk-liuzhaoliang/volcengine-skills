# Volcenginecc Auto Scaling Example

Lifecycle-verified example path:

```text
assets/examples/volcenginecc-autoscaling/main.tf
```

Use this example when a deployment needs the Auto Scaling control plane for ECS capacity management. It verifies a disabled zero-capacity scaling group, a launch-template-backed scaling configuration, and a lifecycle hook without creating scaled ECS instances.

This is not a clean no-op verified example with provider `volcengine/volcenginecc ~> 0.0.46`. It creates and cleans up successfully, but follow-up plans can show provider readback pseudo-diffs and default Terraform destroy ordering is wrong for an active scaling configuration. Read the pitfalls before applying or destroying it.

## Covered resources

| Resource | Deployment use |
|---|---|
| `volcenginecc_autoscaling_scaling_group` | Scaling boundary for ECS instances, subnets, cooldown, min/max/desired counts, and launch template binding |
| `volcenginecc_autoscaling_scaling_configuration` | ECS instance shape used by the scaling group |
| `volcenginecc_autoscaling_scaling_lifecycle_hook` | Hook for scale-out lifecycle actions |
| `volcenginecc_ecs_launch_template` | Required by the Cloud Control scaling group create path even though generated docs mark it optional |
| `volcenginecc_ecs_keypair`, `volcenginecc_vpc_vpc`, `volcenginecc_vpc_subnet`, `volcenginecc_vpc_route_table`, `volcenginecc_vpc_security_group` | Minimal dependencies for launch template and scaling configuration |

`volcenginecc_autoscaling_scaling_policy` is intentionally excluded because scheduled policy creation failed with the documented time shapes during verification. See `volcenginecc-blocked.md` before adding it.

## Verified command sequence

The example was verified in `cn-beijing` with provider `volcengine/volcenginecc ~> 0.0.46`, zone `cn-beijing-a`, image `image-z0dpqndnmy8rpzcad9rz`, and instance type `ecs.g4i.large`:

```bash
cd assets/examples/volcenginecc-autoscaling
export VOLCENGINE_ACCESS_KEY=...
export VOLCENGINE_SECRET_KEY=...
export VOLCENGINE_REGION=cn-beijing
terraform fmt -check
terraform init -backend=false -input=false
terraform validate
terraform plan -out=tfplan.binary -input=false
terraform apply -input=false tfplan.binary
terraform plan -detailed-exitcode -input=false
```

Observed successful create path:

```text
VPC: vpc-1jobdu53eq2v41n7ampvk5swq
Subnet: subnet-1jobf29fae8zk1n7ampo9my6n
Route table: vtb-iiv2o48a4u0w74o8cucdso2m
Security group: sg-btklgai29edc5h0b2ucplytb
Keypair: cc-iac-as-key
Launch template: lt-yenb7gkazegln4lcig9d
Scaling group: scg-yenb7gl9ihfv0hfqhula
Scaling configuration: scc-yenb7j74kci1qnmuk05a
Lifecycle hook: sgh-yenb7j7sow9ht5yj9vf5
```

The first full create/destroy run removed all nine resources with `Destroy complete! Resources: 9 destroyed.` and final Terraform state was empty.

A later policy retry created another group/config/hook set and confirmed cleanup behavior. Group `scg-yenb7wby5nfv0gjg6syk` and configuration `scc-yenb7yvoud9ht4efbcr9` were deleted, `ve autoscaling DescribeScalingGroups --ScalingGroupIds.1 scg-yenb7wby5nfv0gjg6syk` returned `TotalCount: 0`, `ve autoscaling DescribeScalingConfigurations --ScalingConfigurationIds.1 scc-yenb7yvoud9ht4efbcr9` returned `TotalCount: 0`, and final Terraform state was empty.

## Pitfalls found during verification

1. `launch_template_id` is effectively required for `volcenginecc_autoscaling_scaling_group` in the current Cloud Control path. Creating a scaling group without it failed even though generated docs mark it optional:

   ```text
   EventTime: 2026-05-30T10:14:57+08:00
   TaskID: task-2169963f-6192-43bd-a5f8-5f47bc72e6ae
   MissingParameter.LaunchTemplateId
   TypeName: Volcengine::AutoScaling::ScalingGroup
   Operation: CREATE
   OperationStatus: FAILED
   ```

2. The launch template used by Auto Scaling must include `launch_template_version.volumes`. Omitting it failed with:

   ```text
   EventTime: 2026-05-30T10:15:37+08:00
   TaskID: task-fbbc455e-15e8-4ef4-9ae4-db83e37b85c8
   MissingParameter.LaunchTemplateVolumes
   TypeName: Volcengine::ECS::LaunchTemplate
   Operation: CREATE
   OperationStatus: FAILED
   ```

3. `volcenginecc_autoscaling_scaling_policy` scheduled rules failed with `InvalidScheduledPolicyLaunchTime.Malformed` for all tested future time formats, including the docs-style minute timestamp and an RFC3339 seconds timestamp:

   ```text
   launch_time = "2030-01-01T00:00Z"
   TaskID: task-24652433-23b8-4289-a2ed-5ca6a9fdf837
   EventTime: 2026-05-30T10:17:14+08:00
   InvalidScheduledPolicyLaunchTime.Malformed
   ```

   ```text
   launch_time = "2030-01-01T00:00+08:00"
   TaskID: task-0ad97fc0-80de-43a4-ae17-9b2efbf59733
   EventTime: 2026-05-30T10:17:50+08:00
   InvalidScheduledPolicyLaunchTime.Malformed
   ```

   ```text
   launch_time = "2030-01-01T00:00:00Z"
   TaskID: task-2dc0f91d-f29b-41f8-8f3e-48b736d14e7c
   EventTime: 2026-05-30T10:23:55+08:00
   InvalidScheduledPolicyLaunchTime.Malformed
   ```

4. A follow-up plan after create can show pseudo-diffs. Observed diffs included `volcenginecc_autoscaling_scaling_configuration` computed `eip`/`password`, `volcenginecc_autoscaling_scaling_group` readback of `launch_template_id = ""` and `launch_template_version = ""`, and an extra default egress rule on `volcenginecc_vpc_security_group`. Do not auto-apply these diffs without inspecting them.

5. Default Terraform destroy ordering can fail after `volcenginecc_autoscaling_scaling_configuration` becomes the group's active scaling configuration. Terraform tries to delete the configuration before the group, and the API rejects it:

   ```text
   EventTime: 2026-05-30T10:24:48+08:00
   TaskID: task-e25ed6b5-6314-4d93-b662-96097f69e41f
   InvalidScalingConfiguration.InUse: The specified ScalingConfiguration [scc-yenb7yvoud9ht4efbcr9] is in use.
   TypeName: Volcengine::AutoScaling::ScalingConfiguration
   Operation: DELETE
   OperationStatus: FAILED
   ```

   Recovery sequence used during verification:

   ```bash
   terraform state rm volcenginecc_autoscaling_scaling_configuration.app
   terraform destroy -target=volcenginecc_autoscaling_scaling_group.app -auto-approve -input=false
   ve autoscaling DescribeScalingConfigurations --ScalingConfigurationIds.1 <scaling_configuration_id>
   terraform destroy -auto-approve -input=false
   terraform state list
   ```

   Deleting the scaling group cascaded the active scaling configuration in the verified run. Confirm with `DescribeScalingConfigurations` before removing the rest of the stack.

6. Keep `min_instance_number = 0`, `max_instance_number = 0`, `desire_instance_number = 0`, and `is_enable_scaling_group = false` for low-cost validation. Raising desired capacity will create ECS instances and needs additional cleanup and health checks.

## Import IDs

```bash
terraform import volcenginecc_autoscaling_scaling_group.example scg-xxxxxxxx
terraform import volcenginecc_autoscaling_scaling_configuration.example scc-xxxxxxxx
terraform import volcenginecc_autoscaling_scaling_lifecycle_hook.example "scg-xxxxxxxx|sgh-xxxxxxxx"
terraform import volcenginecc_autoscaling_scaling_policy.example "scg-xxxxxxxx|sp-xxxxxxxx"
```
