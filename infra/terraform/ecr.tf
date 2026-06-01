# Private image registries for the app's containers. The CI/CD epics (7-10) build
# each image once, push it here, and the host pulls the finished image instead of
# building on the box. One repository per service.
#
# Tags are immutable (CI tags by commit SHA, so a tag should never be reused), and
# images are scanned on push. A lifecycle policy expires untagged images so old
# build layers don't pile up and cost storage.

resource "aws_ecr_repository" "app" {
  for_each = toset(var.ecr_repositories)

  name                 = "linkshrink-${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name      = "linkshrink-${each.key}"
    Component = "registry"
  }
}

resource "aws_ecr_lifecycle_policy" "expire_untagged" {
  for_each   = toset(var.ecr_repositories)
  repository = aws_ecr_repository.app[each.key].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after ${var.ecr_untagged_expire_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.ecr_untagged_expire_days
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
