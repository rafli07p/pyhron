resource "google_compute_network" "pyhron_vpc" {
  name                    = "pyhron-vpc-${var.environment}"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "pyhron_subnet" {
  name          = "pyhron-subnet-${var.environment}"
  ip_cidr_range = "10.0.0.0/20"
  region        = var.region
  network       = google_compute_network.pyhron_vpc.id

  private_ip_google_access = true
}

resource "google_vpc_access_connector" "pyhron" {
  name          = "pyhron-vpc-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.pyhron_vpc.name
}
