# ALB Service Notes

## Flat Parameter Mode

ALB create APIs use flat CLI parameters, not JSON body mode. Nested arrays use indexed dot notation such as `--ZoneMappings.1.ZoneId`.

For private ALB smoke tests, keep all EIP/public address fields unset unless public exposure is explicitly under test:

```bash
ve alb CreateLoadBalancer \
  --RegionId cn-beijing \
  --LoadBalancerName cli-skill-test-alb \
  --Type private \
  --VpcId vpc-xxxx \
  --SubnetId subnet-xxxx \
  --ZoneMappings.1.ZoneId cn-beijing-b \
  --ZoneMappings.1.SubnetId subnet-xxxx \
  --LoadBalancerBillingType 2 \
  --LoadBalancerEdition Basic
```

Observed in `cn-beijing`: ALB zones were readable and load balancers, listeners, server groups, certificates, and health-check templates all returned empty lists. No lifecycle test was run because ALB is billable and depends on real VPC/subnet choices.
