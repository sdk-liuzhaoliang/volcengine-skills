output "transit_router_id" {
  description = "中转路由器 (TR) ID"
  value       = volcenginecc_transitrouter_transit_router.this.id
}

output "network_vpc_id" {
  description = "网络底座 VPC ID"
  value       = volcenginecc_vpc_vpc.network.id
}

output "network_subnet_az_a_id" {
  description = "网络底座子网 ID (可用区 A)"
  value       = volcenginecc_vpc_subnet.network_az_a.id
}

output "network_subnet_az_b_id" {
  description = "网络底座子网 ID (可用区 B)"
  value       = volcenginecc_vpc_subnet.network_az_b.id
}

output "network_vpc_attachment_id" {
  description = "网络底座 VPC 与 TR 的连接 ID"
  value       = volcenginecc_transitrouter_vpc_attachment.network.id
}
