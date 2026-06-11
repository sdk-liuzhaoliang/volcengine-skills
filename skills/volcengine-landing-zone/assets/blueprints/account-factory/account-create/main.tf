terraform {
  required_providers {
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
  account_tags_cli_args = join(" ", flatten([
    for idx, tag in var.account_tags : [
      format("--Tags.%d.Key %s", idx + 1, jsonencode(tag.key)),
      format("--Tags.%d.Value %s", idx + 1, jsonencode(tag.value))
    ]
  ]))

  account_tag_validation_pairs = join("\n", [
    for tag in var.account_tags : "${tag.key}\t${tag.value}"
  ])
}

resource "volcenginecc_organization_account" "account" {
  account_name = var.account_name
  show_name    = var.show_name
  org_unit_id  = var.target_ou_id
}

resource "null_resource" "financial_relation" {
  triggers = {
    account_id                       = volcenginecc_organization_account.account.account_id
    financial_relation_type          = var.financial_relation_type
    financial_relation_auth_list_str = var.financial_relation_auth_list_str
    financial_relation_account_alias = var.financial_relation_account_alias
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu

      relation_name="${var.financial_relation_type}"
      case "$relation_name" in
        Financial_Hosting)
          relation_code="1"
          ;;
        Financial_Association)
          relation_code="4"
          ;;
        *)
          echo "Unsupported financial relation type: $relation_name" >&2
          exit 1
          ;;
      esac

      sub_account_id="${volcenginecc_organization_account.account.account_id}"
      auth_list_str="${var.financial_relation_auth_list_str}"
      requested_account_alias="${var.financial_relation_account_alias}"
      account_alias="$requested_account_alias"
      account_alias_source="user"
      if [ -z "$account_alias" ]; then
        account_alias="${var.account_name}"
        account_alias_source="auto"
      fi
      fallback_account_alias="${var.account_name}-$sub_account_id"

      list_body=$(printf '{"AccountIDSearchList":["%s"],"Relation":["%s"]}' "$sub_account_id" "$relation_code")
      list_output=$(ve billing ListFinancialRelation --body "$list_body" 2>&1) || {
        echo "Failed to list financial relation for account $sub_account_id" >&2
        echo "$list_output" >&2
        exit 1
      }

      if printf '%s' "$list_output" | grep -Eq "\"SubAccountI[dD]\"[[:space:]]*:[[:space:]]*\"?$sub_account_id\"?" &&
         printf '%s' "$list_output" | grep -Eq "\"Relation\"[[:space:]]*:[[:space:]]*(\\[)?\"?$relation_code\"?(\\])?"; then
        echo "Financial relation already exists for account $sub_account_id, skip"
        exit 0
      fi

      # CreateFinancialRelation binds the master account from the current caller context.
      build_create_body() {
        create_account_alias="$1"
        if [ -n "$auth_list_str" ] && [ -n "$create_account_alias" ]; then
          printf '{"SubAccountID":%s,"Relation":%s,"AuthListStr":"%s","AccountAlias":"%s"}' "$sub_account_id" "$relation_code" "$auth_list_str" "$create_account_alias"
        elif [ -n "$auth_list_str" ]; then
          printf '{"SubAccountID":%s,"Relation":%s,"AuthListStr":"%s"}' "$sub_account_id" "$relation_code" "$auth_list_str"
        elif [ -n "$create_account_alias" ]; then
          printf '{"SubAccountID":%s,"Relation":%s,"AccountAlias":"%s"}' "$sub_account_id" "$relation_code" "$create_account_alias"
        else
          printf '{"SubAccountID":%s,"Relation":%s}' "$sub_account_id" "$relation_code"
        fi
      }

      create_output=""
      create_body="$(build_create_body "$account_alias")"
      if create_output=$(ve billing CreateFinancialRelation --body "$create_body" 2>&1); then
        :
      elif printf '%s' "$create_output" | grep -Eqi 'OperationDenied\.AccountAliasExist|AccountAliasExist'; then
        if [ "$account_alias_source" = "user" ]; then
          echo "Financial relation alias conflict for account $sub_account_id: explicit AccountAlias '$account_alias' already exists" >&2
          echo "$create_output" >&2
          exit 1
        fi

        if [ "$fallback_account_alias" = "$account_alias" ]; then
          echo "Financial relation alias conflict for account $sub_account_id and no alternate alias is available" >&2
          echo "$create_output" >&2
          exit 1
        fi

        account_alias="$fallback_account_alias"
        create_body="$(build_create_body "$account_alias")"
        if create_output=$(ve billing CreateFinancialRelation --body "$create_body" 2>&1); then
          :
        elif ! printf '%s' "$create_output" | grep -Eqi 'already exists|duplicate|重复|已存在'; then
          echo "Failed to create financial relation for account $sub_account_id" >&2
          echo "$create_output" >&2
          exit 1
        fi
      elif ! printf '%s' "$create_output" | grep -Eqi 'already exists|duplicate|重复|已存在'; then
        echo "Failed to create financial relation for account $sub_account_id" >&2
        echo "$create_output" >&2
        exit 1
      fi

      verify_output=$(ve billing ListFinancialRelation --body "$list_body" 2>&1) || {
        echo "Failed to verify financial relation for account $sub_account_id" >&2
        echo "$verify_output" >&2
        exit 1
      }

      if ! printf '%s' "$verify_output" | grep -Eq "\"SubAccountI[dD]\"[[:space:]]*:[[:space:]]*\"?$sub_account_id\"?" ||
         ! printf '%s' "$verify_output" | grep -Eq "\"Relation\"[[:space:]]*:[[:space:]]*(\\[)?\"?$relation_code\"?(\\])?"; then
        echo "Financial relation verification failed for account $sub_account_id" >&2
        echo "$verify_output" >&2
        exit 1
      fi

      echo "$create_output"
    EOT
  }

  depends_on = [volcenginecc_organization_account.account]
}

resource "null_resource" "account_tags" {
  count = length(var.account_tags) > 0 ? 1 : 0

  triggers = {
    account_id   = volcenginecc_organization_account.account.account_id
    account_tags = jsonencode(var.account_tags)
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu

      account_id="${volcenginecc_organization_account.account.account_id}"

      tag_output=$(ve organization TagResources \
        --ResourceIds.1 "$account_id" \
        --ResourceType "account" \
        ${local.account_tags_cli_args} 2>&1) || {
        echo "Failed to tag account $account_id" >&2
        echo "$tag_output" >&2
        exit 1
      }

      verify_output=$(ve organization ListTagResources \
        --ResourceIds.1 "$account_id" \
        --ResourceType "account" 2>&1) || {
        echo "Failed to verify account tags for $account_id" >&2
        echo "$verify_output" >&2
        exit 1
      }

      while IFS="$(printf '\t')" read -r expected_key expected_value; do
        [ -n "$expected_key" ] || continue

        if ! printf '%s' "$verify_output" | grep -Eq "\"(TagKey|Key)\"[[:space:]]*:[[:space:]]*\"$expected_key\"" ||
           ! printf '%s' "$verify_output" | grep -Eq "\"(TagValue|Value)\"[[:space:]]*:[[:space:]]*\"$expected_value\""; then
          echo "Account tag verification failed for $account_id: $expected_key=$expected_value" >&2
          echo "$verify_output" >&2
          exit 1
        fi
      done <<'EOF'
${local.account_tag_validation_pairs}
EOF

      echo "$tag_output"
    EOT
  }

  depends_on = [volcenginecc_organization_account.account]
}
