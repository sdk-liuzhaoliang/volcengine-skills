terraform {
  required_providers {
    volcenginecc = {
      source  = "volcengine/volcenginecc"
      version = ">= 0.0.41"
    }
  }
}

resource "volcenginecc_vpc_vpc" "workload" {
  cidr_block  = var.workload_vpc_cidr
  vpc_name    = "${var.current_account_id}-workload-vpc"
  description = "Account Factory workload VPC attached to shared transit router"
}

resource "volcenginecc_vpc_subnet" "workload_az_a" {
  vpc_id      = volcenginecc_vpc_vpc.workload.id
  zone_id     = var.availability_zone_a
  cidr_block  = var.workload_subnet_cidr_az_a
  subnet_name = "${var.current_account_id}-workload-subnet-a"
}

resource "volcenginecc_vpc_subnet" "workload_az_b" {
  vpc_id      = volcenginecc_vpc_vpc.workload.id
  zone_id     = var.availability_zone_b
  cidr_block  = var.workload_subnet_cidr_az_b
  subnet_name = "${var.current_account_id}-workload-subnet-b"

  depends_on = [volcenginecc_vpc_subnet.workload_az_a]
}

resource "null_resource" "workload_transitrouter_service_linked_role" {
  count = var.attach_to_shared_network ? 1 : 0

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu

      create_role_output="$(mktemp)"
      if ve iam CreateServiceLinkedRole --ServiceName transitrouter >"$create_role_output" 2>&1; then
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

resource "volcenginecc_transitrouter_vpc_attachment" "workload" {
  count = var.attach_to_shared_network ? 1 : 0

  transit_router_id              = var.transit_router_id
  vpc_id                         = volcenginecc_vpc_vpc.workload.id
  transit_router_attachment_name = "${var.current_account_id}-workload-attach"
  description                    = "Account Factory workload VPC attachment"
  auto_publish_route_enabled     = true

  attach_points = [
    {
      subnet_id = volcenginecc_vpc_subnet.workload_az_a.id
      zone_id   = var.availability_zone_a
    },
    {
      subnet_id = volcenginecc_vpc_subnet.workload_az_b.id
      zone_id   = var.availability_zone_b
    }
  ]

  depends_on = [null_resource.workload_transitrouter_service_linked_role]
}
