# Postgres 16 for the program tables and the pgvector document chunks.
#
# Connection: Cloud Run's built-in Cloud SQL connection (the Auth Proxy, as a unix socket under
# /cloudsql). The instance has a public IP but no authorized networks, so nothing can reach it
# except through the proxy, which checks the caller's IAM role (cloudsql.client) and encrypts the
# connection. That avoids a VPC, private services access and a VPC connector just for the
# database. Private IP is the step up if the project already has a VPC for the model server.
#
# pgvector: Cloud SQL ships the `vector` extension. `pda-load` creates it from the app's schema
# (CREATE EXTENSION IF NOT EXISTS vector), along with the read-only role, so Terraform doesn't.
#
# Users: Cloud SQL creates the `postgres` user with the instance. Its password, and the reader's,
# are set outside Terraform (see README) so neither ends up in Terraform state.

resource "google_sql_database_instance" "db" {
  #checkov:skip=CKV_GCP_60:Public IP with no authorized networks; reachable only through the IAM-checked Cloud SQL connection (see above)
  #checkov:skip=CKV_GCP_79:Postgres 16 is the version the app is built and tested against
  #checkov:skip=CKV_GCP_108:Hostname logging adds a reverse lookup per connection; connections come from Cloud Run only
  #checkov:skip=CKV_GCP_109:Default log level kept for a demo database
  #checkov:skip=CKV_GCP_110:pgAudit left off for a demo with made-up data
  #checkov:skip=CKV_GCP_111:Statement logging left off; the API logs each question and the SQL tool's queries are returned to the caller
  #checkov:skip=CKV2_GCP_13:Duration logging left off; Query Insights covers slow queries
  name             = "${var.name}-db"
  region           = var.region
  database_version = "POSTGRES_16"

  deletion_protection = var.db_deletion_protection

  settings {
    # Shared-core tiers (db-f1-micro, db-g1-small) need the Enterprise edition.
    edition                     = "ENTERPRISE"
    tier                        = var.db_tier
    availability_type           = "ZONAL"
    disk_type                   = "PD_SSD"
    disk_size                   = var.db_disk_gb
    disk_autoresize             = true
    deletion_protection_enabled = var.db_deletion_protection

    ip_configuration {
      ipv4_enabled = true
      # The Cloud SQL connection presents a short-lived client certificate, so plain TLS clients
      # (and anything without one) are refused.
      ssl_mode = "TRUSTED_CLIENT_CERTIFICATE_REQUIRED"
      # No authorized_networks: only the Cloud SQL connection can reach the instance.
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }
    database_flags {
      name  = "log_lock_waits"
      value = "on"
    }

    backup_configuration {
      enabled    = true
      start_time = "09:00" # UTC
      backup_retention_settings {
        retained_backups = 7
      }
    }

    maintenance_window {
      day  = 7 # Sunday
      hour = 10
    }

    insights_config {
      query_insights_enabled = true
    }
  }

  depends_on = [google_project_service.enabled]
}

resource "google_sql_database" "pda" {
  name     = "pda"
  instance = google_sql_database_instance.db.name
}

locals {
  db_socket = "/cloudsql/${google_sql_database_instance.db.connection_name}"
}
