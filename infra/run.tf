# Cloud Run: the API service, the web service and the one-off load job. All three are created only
# when deploy_services is true, after the images are pushed and the secrets have values.

locals {
  model_env = merge(
    { PDA_PROVIDER = var.model_provider },
    var.model_provider == "ollama" ? {
      OLLAMA_HOST      = var.ollama_host
      PDA_OLLAMA_MODEL = var.ollama_model
      PDA_OLLAMA_CTX   = tostring(var.ollama_num_ctx)
    } : {},
    var.model_provider == "anthropic" ? { PDA_ANTHROPIC_MODEL = var.anthropic_model } : {},
    var.model_provider == "vertex" ? {
      PDA_VERTEX_PROJECT = var.project_id
      PDA_VERTEX_REGION  = var.vertex_region
      PDA_VERTEX_MODEL   = var.vertex_model
    } : {},
  )

  api_secret_env = merge(
    { PDA_READER_URL = "db_reader_url" },
    var.model_provider == "anthropic" ? { ANTHROPIC_API_KEY = "anthropic_api_key" } : {},
  )

  # The browser's Origin is whichever run.app address it loaded the web app from, plus any custom domain.
  cors_origins = var.deploy_services ? join(",", concat(google_cloud_run_v2_service.web[0].urls, var.extra_cors_origins)) : ""
}

resource "google_cloud_run_v2_service" "web" {
  count = var.deploy_services ? 1 : 0

  name                = "${var.name}-web"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.web.email

    scaling {
      min_instance_count = 0
      max_instance_count = var.web_max_instances
    }

    containers {
      image = local.web_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
        cpu_idle = true
      }
    }
  }

  depends_on = [google_project_service.enabled]
}

resource "google_cloud_run_v2_service" "api" {
  count = var.deploy_services ? 1 : 0

  lifecycle {
    precondition {
      condition     = var.model_provider != "ollama" || var.ollama_host != ""
      error_message = "Set ollama_host to the self-hosted Ollama URL, or pick another model_provider."
    }
  }

  name                = "${var.name}-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.api.email
    # Answers from a large local model can take a minute or more.
    timeout                          = "300s"
    max_instance_request_concurrency = 8

    scaling {
      min_instance_count = 0
      max_instance_count = var.api_max_instances
    }

    dynamic "vpc_access" {
      for_each = var.vpc_network == null ? [] : [1]
      content {
        network_interfaces {
          network    = var.vpc_network
          subnetwork = var.vpc_subnetwork
        }
        # Only private ranges (the model server) go through the VPC; the rest goes out directly.
        egress = "PRIVATE_RANGES_ONLY"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.db.connection_name]
      }
    }

    containers {
      image = local.api_image

      ports {
        container_port = 8080
      }

      resources {
        # The embedding model runs in the container (onnxruntime), which wants about 1 GB.
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "PDA_CORS_ORIGINS"
        value = local.cors_origins
      }

      dynamic "env" {
        for_each = local.model_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.api_secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.s[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }
  }

  depends_on = [
    google_project_service.enabled,
    google_project_iam_member.sql_client,
    google_project_iam_member.api_vertex,
    google_secret_manager_secret_iam_member.readers,
  ]
}

# Creates the schema, loads the demo CSVs and embeds the documents. Run it once after the first
# deploy, and again whenever the data or schema changes (it drops and recreates both schemas):
#   gcloud run jobs execute pda-load --region us-central1 --wait
resource "google_cloud_run_v2_job" "load" {
  count = var.deploy_services ? 1 : 0

  name                = "${var.name}-load"
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1

    template {
      service_account = google_service_account.loader.email
      max_retries     = 1
      timeout         = "900s"

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.db.connection_name]
        }
      }

      containers {
        image   = local.api_image
        command = ["pda-load"]

        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi"
          }
        }

        env {
          name = "PDA_DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.s["db_admin_url"].secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "PDA_READER_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.s["db_reader_url"].secret_id
              version = "latest"
            }
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }

  depends_on = [
    google_project_service.enabled,
    google_project_iam_member.sql_client,
    google_secret_manager_secret_iam_member.readers,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  for_each = var.public && var.deploy_services ? { api = google_cloud_run_v2_service.api[0].name, web = google_cloud_run_v2_service.web[0].name } : {}

  name     = each.value
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
