terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }

  # Remote state in a GCS bucket you create once by hand (versioning on). Left commented so
  # `terraform init -backend=false` and local experiments work without a bucket:
  #
  #   gcloud storage buckets create gs://<project>-tfstate --location=us-central1 \
  #     --uniform-bucket-level-access --public-access-prevention
  #   gcloud storage buckets update gs://<project>-tfstate --versioning
  #
  # then uncomment and run `terraform init -backend-config="bucket=<project>-tfstate"`.
  #
  # backend "gcs" {
  #   prefix = "program-data-assistant"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
