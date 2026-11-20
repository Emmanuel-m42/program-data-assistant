# One service account per workload, each with only what it uses.
#
#   api     connects to Cloud SQL, reads the reader URL (and the Anthropic key, or calls Vertex AI)
#   loader  connects to Cloud SQL, reads the admin URL and the reader URL (it sets the reader password)
#   web     nothing: it serves static files

resource "google_service_account" "api" {
  account_id   = "${var.name}-api"
  display_name = "Program data assistant API"
}

resource "google_service_account" "loader" {
  account_id   = "${var.name}-loader"
  display_name = "Program data assistant schema and data load job"
}

resource "google_service_account" "web" {
  account_id   = "${var.name}-web"
  display_name = "Program data assistant web app"
}

# cloudsql.client can only be granted on the project. The project is meant to hold this app's
# instance alone; in a shared project, add an IAM condition on the instance name.
resource "google_project_iam_member" "sql_client" {
  for_each = {
    api    = google_service_account.api.member
    loader = google_service_account.loader.member
  }

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = each.value
}

resource "google_project_iam_member" "api_vertex" {
  count = var.model_provider == "vertex" ? 1 : 0

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.api.member
}

locals {
  secret_readers = merge(
    {
      "api-db_reader_url"    = { secret = "db_reader_url", member = google_service_account.api.member }
      "loader-db_admin_url"  = { secret = "db_admin_url", member = google_service_account.loader.member }
      "loader-db_reader_url" = { secret = "db_reader_url", member = google_service_account.loader.member }
    },
    var.model_provider == "anthropic" ? {
      "api-anthropic_api_key" = { secret = "anthropic_api_key", member = google_service_account.api.member }
    } : {},
  )
}

resource "google_secret_manager_secret_iam_member" "readers" {
  for_each = local.secret_readers

  secret_id = google_secret_manager_secret.s[each.value.secret].id
  role      = "roles/secretmanager.secretAccessor"
  member    = each.value.member
}
