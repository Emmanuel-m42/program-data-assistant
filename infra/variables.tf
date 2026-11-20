variable "project_id" {
  description = "GCP project to deploy into."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run, Cloud SQL and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "name" {
  description = "Prefix for resource names (services, instance, secrets, service accounts)."
  type        = string
  default     = "pda"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,14}$", var.name))
    error_message = "Use 2 to 15 lowercase letters, digits or dashes, starting with a letter."
  }
}

variable "deploy_services" {
  description = "Create the Cloud Run services and the load job. Leave false on the first apply, before images and secret values exist."
  type        = bool
  default     = false
}

variable "api_image_tag" {
  description = "Tag of the API image in Artifact Registry (for example a git commit SHA)."
  type        = string
  default     = "latest"
}

variable "web_image_tag" {
  description = "Tag of the web image in Artifact Registry."
  type        = string
  default     = "latest"
}

# ---------- model ----------

variable "model_provider" {
  description = "ollama (self-hosted open model), anthropic (Claude, API key in Secret Manager) or vertex (Claude on Vertex AI, no key)."
  type        = string
  default     = "ollama"

  validation {
    condition     = contains(["ollama", "anthropic", "vertex"], var.model_provider)
    error_message = "model_provider must be ollama, anthropic or vertex."
  }
}

variable "ollama_host" {
  description = "URL of the self-hosted Ollama server, for example http://10.20.0.5:11434 over a VPN. Required when model_provider is ollama. Ollama has no authentication of its own, so keep it on a private network."
  type        = string
  default     = ""

  validation {
    condition     = var.ollama_host == "" || can(regex("^https?://", var.ollama_host))
    error_message = "ollama_host must start with http:// or https://."
  }
}

variable "ollama_model" {
  description = "Model name on the Ollama server."
  type        = string
  default     = "qwen3.5:9b"
}

variable "ollama_num_ctx" {
  description = "Context window sent to Ollama. 16384 avoids the overflow seen on long second turns."
  type        = number
  default     = 16384
}

variable "anthropic_model" {
  description = "Model ID for the Anthropic API."
  type        = string
  default     = "claude-sonnet-5-5"
}

variable "vertex_region" {
  description = "Vertex AI region for Claude (for example global or us-east5)."
  type        = string
  default     = "global"
}

variable "vertex_model" {
  description = "Claude model ID as Vertex AI names it."
  type        = string
  default     = "claude-sonnet-5-5"
}

# ---------- network ----------

variable "vpc_network" {
  description = "Optional VPC network for Direct VPC egress from the API, when the Ollama server is reached over a VPN or interconnect into that VPC. null for none."
  type        = string
  default     = null
}

variable "vpc_subnetwork" {
  description = "Subnetwork in vpc_network for Direct VPC egress. Needed with vpc_network."
  type        = string
  default     = null
}

# ---------- database ----------

variable "db_tier" {
  description = "Cloud SQL machine tier. db-f1-micro is the cheapest (shared core, no SLA); db-custom-1-3840 is the smallest dedicated core."
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_gb" {
  description = "Cloud SQL disk size in GB. The demo data is a few MB."
  type        = number
  default     = 10
}

variable "db_deletion_protection" {
  description = "Block deleting the database instance from Terraform and from the console."
  type        = bool
  default     = true
}

# ---------- web and access ----------

variable "public" {
  description = "Let anyone on the internet call both services. The browser calls the API directly, so the API must be public when the web app is."
  type        = bool
  default     = true
}

variable "extra_cors_origins" {
  description = "More origins the API accepts, such as a custom domain for the web app. The web service's own run.app URLs are always included."
  type        = list(string)
  default     = []
}

variable "api_max_instances" {
  description = "Upper bound on API containers, a cost ceiling."
  type        = number
  default     = 2
}

variable "web_max_instances" {
  description = "Upper bound on web containers."
  type        = number
  default     = 2
}
