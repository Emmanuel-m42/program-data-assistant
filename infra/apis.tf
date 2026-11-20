locals {
  services = concat(
    [
      "artifactregistry.googleapis.com",
      "iam.googleapis.com",
      "run.googleapis.com",
      "secretmanager.googleapis.com",
      "sqladmin.googleapis.com", # the Cloud SQL connection Cloud Run mounts goes through this API
    ],
    var.vpc_network == null ? [] : ["compute.googleapis.com"],
    var.model_provider == "vertex" ? ["aiplatform.googleapis.com"] : [],
  )
}

resource "google_project_service" "enabled" {
  for_each = toset(local.services)

  service = each.value
  # Turning an API off on destroy can break other things in the project.
  disable_on_destroy = false
}
