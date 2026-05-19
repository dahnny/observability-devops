resource "null_resource" "observability_stack" {
  triggers = {
    project       = var.project_name
    compose_files = join(",", var.compose_files)
  }

  provisioner "local-exec" {
    command     = "docker compose ${join(" ", [for file in var.compose_files : "-f ../${file}"])} up -d --build"
    working_dir = path.module
  }
}
