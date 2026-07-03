Note that providing `api_id` will attach the authoriser to an API. If you wish to attach it yourself, you will do better to _not_ provide this, and instead use either the `lambda_invoke_arn` output in your own `aws_api_gateway_authorizer` resource, or the `constructed_lambda_invoke_arn` output in your full OpenAPI spec.

Note that you _should_ be able to use the `lambda_invoke_arn` output, but there seems to be a broken dependency bug in Terraform where this is not available until the module has run. This is being investigated.
