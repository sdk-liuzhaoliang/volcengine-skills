output "workload_vpc_id" {
  description = "业务账号 VPC ID"
  value       = volcenginecc_vpc_vpc.workload.id
}

output "workload_subnet_az_a_id" {
  description = "业务账号可用区 A 子网 ID"
  value       = volcenginecc_vpc_subnet.workload_az_a.id
}

output "workload_subnet_az_b_id" {
  description = "业务账号可用区 B 子网 ID"
  value       = volcenginecc_vpc_subnet.workload_az_b.id
}

output "workload_vpc_attachment_id" {
  description = "业务账号 VPC 接入统一网络的 attachment ID"
  value       = try(volcenginecc_transitrouter_vpc_attachment.workload[0].id, null)
}
