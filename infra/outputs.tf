output "registry" {
  description = "Docker repository to push images to."
  value       = local.registry
}

output "db_connection_name" {
  description = "Cloud SQL connection name, used in the socket path of the database URLs."
  value       = google_sql_database_instance.db.connection_name
}

output "db_url_templates" {
  description = "Values for the URL secrets, with the passwords left to fill in."
  value = {
    admin  = "postgresql://postgres:<password>@/${google_sql_database.pda.name}?host=${local.db_socket}"
    reader = "postgresql://pda_reader:<password>@/${google_sql_database.pda.name}?host=${local.db_socket}"
  }
}

output "secrets" {
  description = "Secret Manager secret IDs that need a value before deploy_services = true."
  value       = { for k, s in google_secret_manager_secret.s : k => s.secret_id }
}

output "api_url" {
  description = "API address. Build the web image with PUBLIC_API_URL set to this."
  value       = var.deploy_services ? google_cloud_run_v2_service.api[0].uri : null
}

output "web_url" {
  description = "Web app address."
  value       = var.deploy_services ? google_cloud_run_v2_service.web[0].uri : null
}

output "load_job" {
  description = "Name of the Cloud Run job that loads the schema and data."
  value       = var.deploy_services ? google_cloud_run_v2_job.load[0].name : null
}
