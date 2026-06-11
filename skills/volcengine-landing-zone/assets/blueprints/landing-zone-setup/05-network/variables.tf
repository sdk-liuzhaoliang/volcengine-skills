variable "region" {
  description = "火山引擎主 Region"
  type        = string
  default     = "cn-beijing"
}

variable "prefix" {
  description = "企业名称前缀"
  type        = string
}

variable "network_account_id" {
  description = "网络账号 ID（来自阶段 1 输出）"
  type        = string
}

variable "network_vpc_cidr" {
  description = "网络底座 VPC CIDR"
  type        = string
  default     = "10.0.0.0/16"
}

variable "network_subnet_cidr_az_a" {
  description = "网络底座子网 CIDR (可用区 A)"
  type        = string
  default     = "10.0.1.0/24"
}

variable "network_subnet_cidr_az_b" {
  description = "网络底座子网 CIDR (可用区 B)"
  type        = string
  default     = "10.0.2.0/24"
}
