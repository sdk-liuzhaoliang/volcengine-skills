terraform {
  required_providers {
    volcenginecc = {
      source  = "volcengine/volcenginecc"
      version = ">= 0.0.41"
    }
  }
}

locals {
  network_account_assume_role_trn = "trn:iam::${var.network_account_id}:role/OrganizationAccessControlRole"
}

# --- Provider: 主账号 (默认) ---
provider "volcenginecc" {
  region = var.region
}

# --- Provider: 网络账号 (通过 assume_role 跨账号) ---
provider "volcenginecc" {
  alias  = "network_account"
  region = var.region

  endpoints = {
    sts = "sts.volcengineapi.com"
  }

  assume_role = {
    assume_role_trn              = local.network_account_assume_role_trn
    assume_role_session_name     = "lz-network-setup"
    assume_role_duration_seconds = 3600
  }
}

# ---------------------------------------------------------------
# Part 1: 中转路由器 (Transit Router) — 在网络账号中创建
# ---------------------------------------------------------------
resource "volcenginecc_transitrouter_transit_router" "this" {
  provider = volcenginecc.network_account

  transit_router_name = "${var.prefix}-tr-${var.region}"
  description         = "Landing Zone Transit Router in network account for ${var.region}"
  project_name        = "default"

  tags = [
    {
      key   = "ManagedBy"
      value = "LandingZone"
    }
  ]
}

# ---------------------------------------------------------------
# Part 2: 网络底座 VPC — 在网络账号中创建
# ---------------------------------------------------------------
resource "volcenginecc_vpc_vpc" "network" {
  provider = volcenginecc.network_account

  cidr_block  = var.network_vpc_cidr
  vpc_name    = "${var.prefix}-network-vpc"
  description = "Network baseline VPC for Landing Zone"
}

resource "volcenginecc_vpc_subnet" "network_az_a" {
  provider = volcenginecc.network_account

  vpc_id      = volcenginecc_vpc_vpc.network.id
  zone_id     = "${var.region}-a"
  cidr_block  = var.network_subnet_cidr_az_a
  subnet_name = "${var.prefix}-network-subnet-a"
}

resource "volcenginecc_vpc_subnet" "network_az_b" {
  provider = volcenginecc.network_account

  vpc_id      = volcenginecc_vpc_vpc.network.id
  zone_id     = "${var.region}-b"
  cidr_block  = var.network_subnet_cidr_az_b
  subnet_name = "${var.prefix}-network-subnet-b"

  depends_on = [volcenginecc_vpc_subnet.network_az_a]
}

# ---------------------------------------------------------------
# Part 2.5: 确保网络账号已具备 Transit Router 服务关联角色
# 说明：
# - TR 在创建 VPC attachment 时需要网络账号内的 ServiceRoleForTransitRouter。
# - 当前通过 ve CLI 在 assume_role 到网络账号后进行幂等创建；若角色已存在则直接继续。
# ---------------------------------------------------------------
resource "null_resource" "network_account_transitrouter_service_linked_role" {
  triggers = {
    network_account_id = var.network_account_id
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu

      assume_role_output="$(ve sts AssumeRole \
        --RoleTrn "${local.network_account_assume_role_trn}" \
        --RoleSessionName "lz-network-slr")"

      temp_profile="lz-network-slr-$$"
      cleanup() {
        cleanup_status=$?
        if [ -n "$${temp_profile:-}" ]; then
          ve configure delete --profile "$temp_profile" >/dev/null 2>&1 || true
        fi
        exit "$cleanup_status"
      }
      trap cleanup EXIT INT TERM

      printf '%s' "$assume_role_output" | python3 - "$temp_profile" "${var.region}" <<'PY'
import json
import subprocess
import sys

profile = sys.argv[1]
region = sys.argv[2]
payload = json.load(sys.stdin)
credentials = payload.get("Result", {}).get("Credentials", {})

if (
    not credentials.get("AccessKeyId")
    or not credentials.get("SecretAccessKey")
    or not credentials.get("SessionToken")
):
    print("failed to assume network account role: credentials not found in AssumeRole response", file=sys.stderr)
    raise SystemExit(1)

subprocess.run(
    [
        "ve",
        "configure",
        "set",
        "--profile",
        profile,
        "--region",
        region,
        "--access-key",
        credentials["AccessKeyId"],
        "--secret-key",
        credentials["SecretAccessKey"],
        "--session-token",
        credentials["SessionToken"],
    ],
    check=True,
    stdout=subprocess.DEVNULL,
)
PY

      create_role_output="$(mktemp)"
      if ve iam CreateServiceLinkedRole --profile "$temp_profile" --ServiceName transitrouter >"$create_role_output" 2>&1; then
        rm -f "$create_role_output"
        exit 0
      fi

      if grep -q "RoleAlreadyExists" "$create_role_output"; then
        rm -f "$create_role_output"
        exit 0
      fi

      cat "$create_role_output" >&2
      rm -f "$create_role_output"
      exit 1
    EOT
  }
}

# ---------------------------------------------------------------
# Part 3: 将网络底座 VPC 连接到中转路由器
# ---------------------------------------------------------------
resource "volcenginecc_transitrouter_vpc_attachment" "network" {
  provider = volcenginecc.network_account

  transit_router_id              = volcenginecc_transitrouter_transit_router.this.id
  vpc_id                         = volcenginecc_vpc_vpc.network.id
  transit_router_attachment_name = "${var.prefix}-network-attach"
  description                    = "Network baseline VPC attachment"
  auto_publish_route_enabled     = true

  attach_points = [
    {
      subnet_id = volcenginecc_vpc_subnet.network_az_a.id
      zone_id   = "${var.region}-a"
    },
    {
      subnet_id = volcenginecc_vpc_subnet.network_az_b.id
      zone_id   = "${var.region}-b"
    }
  ]

  tags = [
    {
      key   = "ManagedBy"
      value = "LandingZone"
    }
  ]

  depends_on = [null_resource.network_account_transitrouter_service_linked_role]
}
