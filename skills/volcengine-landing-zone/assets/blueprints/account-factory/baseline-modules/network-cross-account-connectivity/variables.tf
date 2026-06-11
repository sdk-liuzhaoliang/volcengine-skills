variable "network_account_id" {
  description = "统一网络账号 ID"
  type        = string
}

variable "current_account_id" {
  description = "当前新创建账号 ID，用于资源命名与输出关联"
  type        = string
}

variable "transit_router_id" {
  description = "统一网络中转路由器 ID"
  type        = string
}

variable "workload_vpc_cidr" {
  description = "业务账号 VPC CIDR"
  type        = string
}

variable "workload_subnet_cidr_az_a" {
  description = "业务账号可用区 A 子网 CIDR"
  type        = string
}

variable "workload_subnet_cidr_az_b" {
  description = "业务账号可用区 B 子网 CIDR"
  type        = string
}

variable "availability_zone_a" {
  description = "业务账号可用区 A"
  type        = string
  default     = "cn-beijing-a"
}

variable "availability_zone_b" {
  description = "业务账号可用区 B"
  type        = string
  default     = "cn-beijing-b"
}

variable "attach_to_shared_network" {
  description = "是否接入统一网络底座"
  type        = bool
  default     = true
}
