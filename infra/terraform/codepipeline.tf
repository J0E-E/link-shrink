# The CI/CD pipeline: Source (GitHub) -> Build (test+push) -> Deploy (SSM).
# Fully hands-off — a push to the tracked branch flows straight through with no
# approval action. Also holds the artifact bucket and the GitHub connection.

# ---------------------------------------------------------------------------
# Artifact store
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "artifacts" {
  bucket = "linkshrink-codepipeline-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name      = "linkshrink-codepipeline-artifacts"
    Component = "cicd"
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Build artifacts are disposable — expire them so storage stays bounded.
resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "expire-artifacts"
    status = "Enabled"

    filter {}

    expiration {
      days = var.artifact_expire_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.artifact_expire_days
    }
  }
}

# ---------------------------------------------------------------------------
# GitHub connection (created PENDING — authorize once in the console)
# ---------------------------------------------------------------------------

resource "aws_codestarconnections_connection" "github" {
  name          = "linkshrink-github"
  provider_type = "GitHub"

  tags = {
    Name      = "linkshrink-github"
    Component = "cicd"
  }
}

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

resource "aws_codepipeline" "main" {
  name     = "linkshrink"
  role_arn = aws_iam_role.pipeline.arn

  artifact_store {
    type     = "S3"
    location = aws_s3_bucket.artifacts.bucket
  }

  stage {
    name = "Source"
    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source"]

      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github.arn
        FullRepositoryId = var.github_repository
        BranchName       = var.github_branch
      }
    }
  }

  stage {
    name = "Build"
    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      version          = "1"
      input_artifacts  = ["source"]
      output_artifacts = ["build_out"]
      namespace        = "BuildVars"

      configuration = {
        ProjectName = aws_codebuild_project.build.name
      }
    }
  }

  stage {
    name = "Deploy"
    action {
      name            = "Deploy"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = "1"
      input_artifacts = ["source"]

      configuration = {
        ProjectName = aws_codebuild_project.deploy.name
        EnvironmentVariables = jsonencode([
          {
            name  = "IMAGE_TAG"
            type  = "PLAINTEXT"
            value = "#{BuildVars.IMAGE_TAG}"
          }
        ])
      }
    }
  }

  tags = {
    Name      = "linkshrink"
    Component = "cicd"
  }
}
