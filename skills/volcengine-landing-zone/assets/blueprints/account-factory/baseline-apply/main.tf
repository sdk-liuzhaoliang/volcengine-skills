terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = ">= 3.2.1"
    }
    volcenginecc = {
      source  = "volcengine/volcenginecc"
      version = ">= 0.0.41"
    }
  }
}

provider "volcenginecc" {
  region = var.region
}

locals {
  identity_payload  = jsondecode(var.identity_payload_json)
  config_payload    = jsondecode(var.config_payload_json)
  scp_payload       = jsondecode(var.scp_payload_json)
  custom_extensions = jsondecode(var.custom_extensions_json)
  config_rules      = try(local.config_payload.config_rules, [])
  scp_policies      = try(local.scp_payload.scp_policies, [])
  network_payload   = try(local.config_payload.network, {})
  network_enabled   = try(local.network_payload.enabled, false)

  workspace_root   = abspath(var.workspace_root)
  workspace_parent = abspath("${local.workspace_root}/..")
  blueprint_root   = abspath("${path.module}/..")
  runtime_root     = "${local.workspace_root}/account-factory/runs/${var.current_account_id}"
  config_summary   = "${local.runtime_root}/config/summary.json"
  scp_summary      = "${local.runtime_root}/scp/summary.json"
  network_run_dir  = "${local.runtime_root}/network-cross-account-connectivity"
  network_plan_txt = "${local.network_run_dir}/plan.txt"
  network_apply_sh = "${local.network_run_dir}/apply.sh"
  custom_runs_root = "${local.runtime_root}/custom-extensions"

  enabled_config_rules = [
    for rule in local.config_rules : rule
    if try(rule.enabled, true)
  ]

  enabled_scp_policies = [
    for policy in local.scp_policies : policy
    if try(policy.enabled, true)
  ]

  identity_users = {
    for user in try(local.identity_payload.users, []) :
    user.username => {
      username        = user.username
      display_name    = try(user.display_name, user.username)
      email           = try(user.email, null)
      description     = try(user.description, null)
      permission_sets = try(user.permission_sets, [])
    }
  }

  identity_groups = {
    for group in try(local.identity_payload.groups, []) :
    group.name => {
      name            = group.name
      display_name    = try(group.display_name, group.name)
      description     = try(group.description, null)
      join_type       = try(group.join_type, "Manual")
      permission_sets = try(group.permission_sets, [])
      members         = try(group.members, [])
    }
  }

  explicit_assignments = [
    for assignment in try(local.identity_payload.assignments, []) : {
      key            = "${assignment.principal_type}:${assignment.principal_name}:${assignment.permission_set}"
      principal_type = assignment.principal_type
      principal_name = assignment.principal_name
      permission_set = assignment.permission_set
      scope          = try(assignment.scope, "current_account")
    }
  ]

  derived_user_assignments = flatten([
    for username, user in local.identity_users : [
      for permission_set in user.permission_sets : {
        key            = "User:${username}:${permission_set}"
        principal_type = "User"
        principal_name = username
        permission_set = permission_set
        scope          = "current_account"
      }
    ]
  ])

  derived_group_assignments = flatten([
    for group_name, group in local.identity_groups : [
      for permission_set in group.permission_sets : {
        key            = "Group:${group_name}:${permission_set}"
        principal_type = "Group"
        principal_name = group_name
        permission_set = permission_set
        scope          = "current_account"
      }
    ]
  ])

  effective_assignments = {
    for assignment in concat(
      local.derived_user_assignments,
      local.derived_group_assignments,
      local.explicit_assignments
    ) :
    assignment.key => assignment
    if assignment.scope == "current_account"
  }

  permission_set_names = toset(distinct(concat(
    flatten([for _, user in local.identity_users : user.permission_sets]),
    flatten([for _, group in local.identity_groups : group.permission_sets]),
    [for _, assignment in local.effective_assignments : assignment.permission_set]
  )))

  permission_sets = {
    for name in local.permission_set_names :
    name => {
      name             = name
      description      = "Account Factory baseline managed permission set ${name}"
      session_duration = "PT4H"
      permission_policies = [{
        permission_policy_name     = name
        permission_policy_type     = "System"
        permission_policy_document = ""
      }]
    }
  }

  custom_extension_map = {
    for extension in local.custom_extensions :
    extension.name => {
      name   = extension.name
      type   = try(extension.type, "terraform")
      source = extension.source
      source_path = startswith(extension.source, "/") ? extension.source : (
        startswith(extension.source, "volcengine-landing-zone-workspace/")
        ? "${local.workspace_parent}/${extension.source}"
        : "${local.workspace_root}/${extension.source}"
      )
      description = try(extension.description, "")
      apply_after = try(extension.apply_after, [])
    }
  }

  custom_extension_runs = {
    for name, extension in local.custom_extension_map :
    name => {
      safe_name         = regexreplace(name, "[^0-9A-Za-z._-]", "-")
      runtime_dir       = "${local.custom_runs_root}/${regexreplace(name, "[^0-9A-Za-z._-]", "-")}"
      plan_summary_path = "${local.custom_runs_root}/${regexreplace(name, "[^0-9A-Za-z._-]", "-")}/plan.txt"
      apply_script_path = "${local.custom_runs_root}/${regexreplace(name, "[^0-9A-Za-z._-]", "-")}/apply.sh"
    }
  }
}


# Cloud Identity resources in this module are generated dynamically from the
# merged baseline payload. Terraform cannot safely express a per-instance
# serial chain for these dynamic resources, so callers should run this module
# with `terraform plan/apply -parallelism=1` to avoid Volcengine control-plane
# ConcurrentException responses during identity writes.

resource "volcenginecc_cloudidentity_permission_set" "baseline" {

  for_each = local.permission_sets

  name             = each.value.name
  description      = each.value.description
  session_duration = each.value.session_duration
  permission_policies = [
    for policy in each.value.permission_policies : {
      permission_policy_name     = policy.permission_policy_name
      permission_policy_type     = policy.permission_policy_type
      permission_policy_document = policy.permission_policy_document
    }
  ]
}

resource "volcenginecc_cloudidentity_user" "baseline" {
  for_each = local.identity_users

  user_name    = each.value.username
  display_name = each.value.display_name
  description  = each.value.description
  email        = each.value.email
}

resource "volcenginecc_cloudidentity_group" "baseline" {
  for_each = local.identity_groups

  group_name   = each.value.name
  display_name = each.value.display_name
  description  = each.value.description
  join_type    = each.value.join_type
  members = [
    for member_name in each.value.members : {
      user_id = volcenginecc_cloudidentity_user.baseline[member_name].user_id
    }
  ]
}

resource "volcenginecc_cloudidentity_permission_set_assignment" "baseline" {
  for_each = local.effective_assignments

  permission_set_id = volcenginecc_cloudidentity_permission_set.baseline[each.value.permission_set].permission_set_id
  principal_type    = each.value.principal_type
  principal_id = (
    each.value.principal_type == "Group"
    ? volcenginecc_cloudidentity_group.baseline[each.value.principal_name].group_id
    : volcenginecc_cloudidentity_user.baseline[each.value.principal_name].user_id
  )
  target_id = var.current_account_id
}

resource "volcenginecc_cloudidentity_permission_set_provisioning" "baseline" {
  for_each = {
    for permission_set_name in toset([
      for _, assignment in local.effective_assignments : assignment.permission_set
    ]) :
    permission_set_name => permission_set_name
  }

  permission_set_id = volcenginecc_cloudidentity_permission_set.baseline[each.key].permission_set_id
  target_id         = var.current_account_id

  depends_on = [volcenginecc_cloudidentity_permission_set_assignment.baseline]
}

resource "null_resource" "identity_stage" {
  triggers = {
    current_account_id   = var.current_account_id
    user_count           = tostring(length(local.identity_users))
    group_count          = tostring(length(local.identity_groups))
    assignment_count     = tostring(length(local.effective_assignments))
    permission_set_count = tostring(length(local.permission_sets))
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu
      echo "Identity stage completed for account ${var.current_account_id}"
      echo "Users: ${length(local.identity_users)}"
      echo "Groups: ${length(local.identity_groups)}"
      echo "Assignments: ${length(local.effective_assignments)}"
      echo "Permission sets: ${length(local.permission_sets)}"
    EOT
  }

  depends_on = [
    volcenginecc_cloudidentity_permission_set.baseline,
    volcenginecc_cloudidentity_user.baseline,
    volcenginecc_cloudidentity_group.baseline,
    volcenginecc_cloudidentity_permission_set_assignment.baseline,
    volcenginecc_cloudidentity_permission_set_provisioning.baseline,
  ]
}

resource "null_resource" "config_stage" {
  triggers = {
    current_account_id = var.current_account_id
    config_rule_count  = tostring(length(local.enabled_config_rules))
    config_payload     = var.config_payload_json
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command = <<-EOT
      set -eu

      summary_file="${local.config_summary}"
      mkdir -p "$(dirname "$summary_file")"

      printf '%s\n' '${jsonencode({
    stage              = "config"
    status             = "dry_run_only"
    current_account_id = var.current_account_id
    enabled_rule_count = length(local.enabled_config_rules)
    enabled_rules      = local.enabled_config_rules
})}' > "$summary_file"

      echo "Config stage prepared dry-run summary for account ${var.current_account_id}"
      echo "Enabled config rules: ${length(local.enabled_config_rules)}"
      echo "Summary file: $summary_file"
    EOT
}

depends_on = [null_resource.identity_stage]
}

resource "null_resource" "scp_stage" {
  triggers = {
    current_account_id = var.current_account_id
    scp_policy_count   = tostring(length(local.enabled_scp_policies))
    scp_payload        = var.scp_payload_json
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command = <<-EOT
      set -eu

      summary_file="${local.scp_summary}"
      mkdir -p "$(dirname "$summary_file")"

      printf '%s\n' '${jsonencode({
    stage                = "scp"
    status               = "dry_run_only"
    current_account_id   = var.current_account_id
    enabled_policy_count = length(local.enabled_scp_policies)
    enabled_policies     = local.enabled_scp_policies
})}' > "$summary_file"

      echo "SCP stage prepared dry-run summary for account ${var.current_account_id}"
      echo "Enabled SCP policies: ${length(local.enabled_scp_policies)}"
      echo "Summary file: $summary_file"
    EOT
}

depends_on = [null_resource.config_stage]
}

resource "null_resource" "network_module_stage" {
  triggers = {
    current_account_id = var.current_account_id
    network_enabled    = tostring(local.network_enabled)
    network_payload    = jsonencode(local.network_payload)
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command = <<-EOT
      set -eu

      run_dir="${local.network_run_dir}"
      summary_file="${local.network_plan_txt}"
      apply_script="${local.network_apply_sh}"
      module_dir="${local.blueprint_root}/baseline-modules/network-cross-account-connectivity"

      mkdir -p "${local.runtime_root}"

      if [ "${tostring(local.network_enabled)}" != "true" ]; then
        mkdir -p "$run_dir"
        printf '%s\n' '${jsonencode({
    stage              = "network"
    status             = "skipped"
    current_account_id = var.current_account_id
    enabled            = false
})}' > "$summary_file"
        rm -f "$apply_script"
        echo "Network module not enabled for this baseline"
        exit 0
      fi

      if [ ! -d "$module_dir" ]; then
        echo "Network module directory does not exist: $module_dir" >&2
        exit 1
      fi

      if [ ! -f "$module_dir/main.tf" ]; then
        echo "Network module directory missing main.tf: $module_dir" >&2
        exit 1
      fi

      rm -rf "$run_dir"
      mkdir -p "$run_dir"
      cp -R "$module_dir"/. "$run_dir"/
      rm -rf "$run_dir/.terraform"
      rm -f "$run_dir/terraform.tfstate" "$run_dir/terraform.tfstate.backup" "$run_dir/tfplan"

      workload_vpc_cidr='${try(local.network_payload.workload_vpc_cidr, "")}'
      workload_subnet_cidr_az_a='${try(local.network_payload.workload_subnet_cidr_az_a, "")}'
      workload_subnet_cidr_az_b='${try(local.network_payload.workload_subnet_cidr_az_b, "")}'

      if [ -z "$workload_vpc_cidr" ] || [ -z "$workload_subnet_cidr_az_a" ] || [ -z "$workload_subnet_cidr_az_b" ]; then
        echo "network baseline requires workload_vpc_cidr, workload_subnet_cidr_az_a, and workload_subnet_cidr_az_b" >&2
        exit 1
      fi

      terraform -chdir="$run_dir" init -backend=false
      terraform -chdir="$run_dir" plan -out=tfplan \
        -var "current_account_id=${var.current_account_id}" \
        -var "network_account_id=${try(local.network_payload.network_account_id, "")}" \
        -var "transit_router_id=${try(local.network_payload.transit_router_id, "")}" \
        -var "workload_vpc_cidr=$workload_vpc_cidr" \
        -var "workload_subnet_cidr_az_a=$workload_subnet_cidr_az_a" \
        -var "workload_subnet_cidr_az_b=$workload_subnet_cidr_az_b" \
        -var "availability_zone_a=${try(local.network_payload.availability_zone_a, "cn-beijing-a")}" \
        -var "availability_zone_b=${try(local.network_payload.availability_zone_b, "cn-beijing-b")}" \
        -var "attach_to_shared_network=${tostring(try(local.network_payload.attach_to_shared_network, true))}"
      terraform -chdir="$run_dir" show -no-color tfplan > "$summary_file"

      cat > "$apply_script" <<'EOF'
#!/bin/sh
set -eu
terraform -chdir="${local.network_run_dir}" apply tfplan
EOF
      chmod +x "$apply_script"

      echo "Network module plan prepared for account ${var.current_account_id}"
      echo "Plan summary: $summary_file"
      echo "Apply script: $apply_script"
    EOT
}

depends_on = [null_resource.scp_stage]
}

resource "null_resource" "custom_terraform_extension" {
  for_each = local.custom_extension_map

  triggers = {
    current_account_id = var.current_account_id
    extension_name     = each.value.name
    extension_type     = each.value.type
    extension_source   = each.value.source
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu

      extension_source="${each.value.source}"
      extension_dir="${each.value.source_path}"
      run_dir="${local.custom_extension_runs[each.key].runtime_dir}"
      summary_file="${local.custom_extension_runs[each.key].plan_summary_path}"
      apply_script="${local.custom_extension_runs[each.key].apply_script_path}"

      echo "Preparing custom terraform extension ${each.value.name} for account ${var.current_account_id}"
      echo "Resolved directory: $extension_dir"

      if [ "${each.value.type}" != "terraform" ]; then
        echo "Unsupported custom extension type: ${each.value.type}" >&2
        exit 1
      fi

      if [ ! -d "$extension_dir" ]; then
        echo "Custom extension directory does not exist: $extension_dir" >&2
        exit 1
      fi

      if [ ! -f "$extension_dir/main.tf" ]; then
        echo "Custom extension directory missing main.tf: $extension_dir" >&2
        exit 1
      fi

      rm -rf "$run_dir"
      mkdir -p "$run_dir"
      cp -R "$extension_dir"/. "$run_dir"/
      rm -rf "$run_dir/.terraform"
      rm -f "$run_dir/terraform.tfstate" "$run_dir/terraform.tfstate.backup" "$run_dir/tfplan"

      terraform -chdir="$run_dir" init -backend=false
      terraform -chdir="$run_dir" plan -out=tfplan
      terraform -chdir="$run_dir" show -no-color tfplan > "$summary_file"

      cat > "$apply_script" <<'EOF'
#!/bin/sh
set -eu
terraform -chdir="${local.custom_extension_runs[each.key].runtime_dir}" apply tfplan
EOF
      chmod +x "$apply_script"

      echo "Plan summary: $summary_file"
      echo "Apply script: $apply_script"
    EOT
  }

  depends_on = [null_resource.network_module_stage]
}

resource "null_resource" "custom_terraform_extensions_stage" {
  triggers = {
    current_account_id = var.current_account_id
    extension_count    = tostring(length(local.custom_extension_map))
    extension_names    = join(",", sort(keys(local.custom_extension_map)))
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu
      echo "Custom Terraform extensions plans prepared for account ${var.current_account_id}"
      echo "Extensions: ${join(", ", sort(keys(local.custom_extension_map)))}"
    EOT
  }

  depends_on = [null_resource.custom_terraform_extension]
}
