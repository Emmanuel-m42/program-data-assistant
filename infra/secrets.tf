# Secret containers only. Values are added by hand with `gcloud secrets versions add` (README), so
# they never appear in this repo or in Terraform state.

locals {
  secrets = merge(
    {
      # postgresql://postgres:<password>@/pda?host=/cloudsql/<connection name>, for pda-load only.
      db_admin_url = "${var.name}-db-admin-url"
      # postgresql://pda_reader:<password>@/pda?host=/cloudsql/<connection name>, for the API.
      # pda-load also reads it and sets that password on the read-only role.
      db_reader_url = "${var.name}-db-reader-url"
    },
    var.model_provider == "anthropic" ? { anthropic_api_key = "${var.name}-anthropic-api-key" } : {},
  )
}

resource "google_secret_manager_secret" "s" {
  for_each = local.secrets

  secret_id = each.value
  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}
