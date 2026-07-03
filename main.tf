data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "invocation_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "invocation_role" {
  name               = "${var.name}_api_gateway_auth_invocation"
  path               = "/"
  assume_role_policy = data.aws_iam_policy_document.invocation_assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "invocation_policy" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.this.arn]
  }
}

resource "aws_iam_role_policy" "invocation_policy" {
  name   = "${var.name}-authorizer"
  role   = aws_iam_role.invocation_role.id
  policy = data.aws_iam_policy_document.invocation_policy.json
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name}-authorizer"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "read_secrets" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetResourcePolicy",
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:ListSecretVersionIds"
    ]
    resources = ["arn:aws:secretsmanager:*:*:secret:${var.secret_name}*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetRandomPassword",
      "secretsmanager:ListSecrets"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "read_secrets" {
  name        = "${var.name}-authorizer"
  description = "Used for the ${var.name} custom Lambda API authorizer"
  policy      = data.aws_iam_policy_document.read_secrets.json
  tags        = var.tags
}

resource "aws_iam_role_policy_attachment" "read_secrets" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.read_secrets.arn
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "archive_file" "this" {
  type        = "zip"
  source_dir  = "${path.module}/functions/"
  excludes    = ["${path.module}/terraform"]
  output_path = "${path.module}/authorizers.zip"
}

resource "aws_lambda_function" "this" {
  depends_on = [data.archive_file.this]

  filename         = "${path.module}/authorizers.zip"
  function_name    = "common-${var.name}-api-authorizer"
  role             = aws_iam_role.lambda.arn
  handler          = "authorizer.lambda_handler"
  runtime          = "python3.8"
  source_code_hash = data.archive_file.this.output_base64sha256
  tags             = var.tags

  environment {
    variables = {
      secret_name = var.secret_name
    }
  }
}

resource "aws_lambda_permission" "api_gateway" {
  count = var.api_id != null ? 1 : 0

  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:${var.api_id}/*/*"
}

resource "aws_api_gateway_authorizer" "common" {
  count = var.attach_to_api == true ? 1 : 0

  name                   = "${var.name}-common"
  rest_api_id            = var.api_id
  authorizer_uri         = aws_lambda_function.this.invoke_arn
  authorizer_credentials = aws_iam_role.invocation_role.arn
}
