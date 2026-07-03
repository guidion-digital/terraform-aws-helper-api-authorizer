Creates a simple (dumb) API Gateway authorizer Lambda.

# Usage

See [examples folder](./examples).

There are a few ways you could implement the resulting authoriser Lambda:

## Pre-Created by Cinfra

1. Cinfra creates the resources for you, and passes the following variables to the application workspaces that wish to make use of it:
   1. `authorizer_function_name`
   1. `authorizer_lambda_invoke_arn`
1. You can then create the following resource (replacing `app-x` with the name you gave to the module when you defined it):

      ```hcl
      resource "aws_lambda_permission" "authorizer" {
        statement_id  = "AllowExecutionFromAPIGateway"
        action        = "lambda:InvokeFunction"
        function_name = var.authorizer_function_name
        principal     = "apigateway.amazonaws.com"
        source_arn    = "arn:aws:execute-api:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:${module.app-x.api_id}/*/*"
      }
      ```

1. At the same time, you can fill in the values in the [API Lambdas module](https://github.com/GuidionOps/terraform-aws-app-api-lambda/) you're using:

- `authorizers.custom{}`
- `lambdas{}.endpoints{}.{method}.security`

with the new authoriser, and start using it.

## From the Same Location as the Application Module

1. Define a _separate_ module block instance of the [authorizer module](app.terraform.io/guidion/helper-api-authorizer/aws), and run Terraform
1. Add a `authorizers.custom` block in the API module, defining the name of the authoriser
1. Now you can use the authorizer in a Lambdas `lambdas{}.endpoints.{verb}.security` list

## Within the API Module

There is a way in which you can get the application module to create all the resources for you, by passing values to `authorizers.create_custom{}`. This is not recommended however, since it results in cyclic dependencies when you try to implement it in the most useful way.

# Rationale

Sometimes, some people want to see the word 'Bearer'.

This authorizer checks the `authorizationToken` against all the values in a Secrets Manager secret (which must be a dict of {client: token}). If a match is found, it generates an allow policy which permits access to all methods.

# Caveats and Gotchyas

The generated allow policy is probably too permissive. It allows all methods for the calling API. In order to refine this though, configuration would need to be added into the mix, which the Lambda could pick up to see which client is allowed which methods.
