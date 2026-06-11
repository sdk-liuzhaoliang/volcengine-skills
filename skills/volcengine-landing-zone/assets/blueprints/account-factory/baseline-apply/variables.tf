variable "region" {
  description = "火山引擎主 Region"
  type        = string
  default     = "cn-beijing"
}

variable "workspace_root" {
  description = "运行根目录绝对路径，对应 ./volcengine-landing-zone-workspace"
  type        = string
}

variable "current_account_id" {
  description = "当前新创建账号 ID，baseline 将应用到该账号"
  type        = string
}

variable "baseline_names" {
  description = "由 agent 读取并确认后的 baseline 名称列表；用于结果摘要与回显"
  type        = list(string)
  default     = []
}

variable "identity_payload_json" {
  description = "由 agent 基于 baseline 模块与变量结果归一化后的 identity 段 JSON；当前消费 users、groups、assignments"
  type        = string
  default     = "{}"
}

variable "config_payload_json" {
  description = "由 agent 基于 baseline 模块与变量结果归一化后的 config 段 JSON；当前消费 config_rules 与 network"
  type        = string
  default     = "{}"
}

variable "scp_payload_json" {
  description = "由 agent 基于 baseline 模块与变量结果归一化后的 scp 段 JSON；当前只输出启用 SCP 策略摘要，不直接下发"
  type        = string
  default     = "{}"
}

variable "custom_extensions_json" {
  description = "由 agent 基于 baseline 模块与变量结果归一化后的 custom extensions JSON；当前按扩展目录准备独立 plan 与 apply 脚本"
  type        = string
  default     = "[]"
}
