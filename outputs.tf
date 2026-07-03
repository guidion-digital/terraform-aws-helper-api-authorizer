output "lambda_arn" {
  description = "ARN of the Lambda authoriser"
  value       = aws_lambda_function.this.arn
}

output "lambda_invoke_arn" {
  description = "Readymade ARN that can be used to attach this authoriser. Can be used for the value of authorizer_uri in a aws_api_gateway_authorizer resource"
  value       = aws_lambda_function.this.invoke_arn
}

output "constructed_lambda_invoke_arn" {
  description = "Constructed ARN that can be used to attach this authoriser"
  value       = "arn:aws:apigateway:${data.aws_region.current.id}:lambda:path/2015-03-31/functions/arn:aws:lambda:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:function:${aws_lambda_function.this.function_name}/invocations"
}

output "lambda_name" {
  description = "Name of the Lambda authoriser"
  value       = aws_lambda_function.this.function_name
}

output "invocation_role_arn" {
  description = "ARN of role allowing invocation by API Gateway. Can be used for the authorizer_credentials value of a aws_api_gateway_authorizer resource"
  value       = aws_iam_role.invocation_role.arn
}
