resource "google_artifact_registry_repository" "images" {
  #checkov:skip=CKV_GCP_84:Google-managed encryption; the images hold code and made-up demo data only
  repository_id = var.name
  location      = var.region
  format        = "DOCKER"
  description   = "Images for the program data assistant (api, web)."

  # Keep the ten most recent versions of each image; drop untagged layers after two weeks.
  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "1209600s"
    }
  }

  depends_on = [google_project_service.enabled]
}

locals {
  registry  = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
  api_image = "${local.registry}/api:${var.api_image_tag}"
  web_image = "${local.registry}/web:${var.web_image_tag}"
}
