output "baseline_names" {
  description = "本次应用的 baseline 文件名列表"
  value       = var.baseline_names
}

output "identity_stage_status" {
  description = "identity 段状态（当前第一交付切片已真实落地）"
  value       = "implemented"
}

output "config_stage_status" {
  description = "config 段状态（当前仅输出待应用规则摘要，尚未真实下发）"
  value       = "dry_run_only"
}

output "scp_stage_status" {
  description = "scp 段状态（当前仅输出待应用策略摘要，尚未真实下发）"
  value       = "dry_run_only"
}

output "network_stage_status" {
  description = "network 模块段状态（当前生成独立 plan 与 apply 脚本，需用户确认后执行）"
  value       = local.network_enabled ? "plan_prepared" : "skipped"
}

output "custom_extensions_stage_status" {
  description = "custom terraform extensions 段状态（当前生成独立 plan 与 apply 脚本，需用户确认后执行）"
  value       = length(local.custom_extension_map) > 0 ? "plan_prepared" : "not_requested"
}

output "baseline_execution_mode" {
  description = "baseline 执行模式说明"
  value       = "plan_prepared_requires_user_confirmation"
}

output "runtime_root" {
  description = "baseline 本次运行的本地运行态目录"
  value       = local.runtime_root
}

output "config_summary_path" {
  description = "config 段摘要文件路径"
  value       = local.config_summary
}

output "scp_summary_path" {
  description = "scp 段摘要文件路径"
  value       = local.scp_summary
}

output "network_plan_summary_path" {
  description = "network 模块 plan 摘要文件路径"
  value       = local.network_plan_txt
}

output "network_apply_script_path" {
  description = "network 模块 apply 脚本路径"
  value       = local.network_enabled ? local.network_apply_sh : null
}

output "custom_extension_plan_summary_paths" {
  description = "custom terraform extensions 的 plan 摘要文件路径映射"
  value = {
    for name, run in local.custom_extension_runs :
    name => run.plan_summary_path
  }
}

output "custom_extension_apply_script_paths" {
  description = "custom terraform extensions 的 apply 脚本路径映射"
  value = {
    for name, run in local.custom_extension_runs :
    name => run.apply_script_path
  }
}

output "identity_usernames" {
  description = "identity 阶段解析并管理的用户名列表"
  value       = sort(keys(local.identity_users))
}

output "identity_group_names" {
  description = "identity 阶段解析并管理的组名列表"
  value       = sort(keys(local.identity_groups))
}

output "identity_permission_set_names" {
  description = "identity 阶段解析并管理的权限集列表"
  value       = sort(keys(local.permission_sets))
}

output "custom_extension_names" {
  description = "custom terraform extensions 阶段解析出的扩展名称列表"
  value       = sort(keys(local.custom_extension_map))
}

output "identity_user_ids" {
  description = "identity 阶段创建的用户 ID 映射"
  value = {
    for username, resource in volcenginecc_cloudidentity_user.baseline :
    username => resource.user_id
  }
}

output "identity_group_ids" {
  description = "identity 阶段创建的组 ID 映射"
  value = {
    for group_name, resource in volcenginecc_cloudidentity_group.baseline :
    group_name => resource.group_id
  }
}
