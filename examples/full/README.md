This example is written to run against [MiniStack](https://github.com/ministackorg/ministack), which emulates AWS locally. CI (the terrappy reusable workflows) starts MiniStack as a service and runs `terraform plan` on pull requests and `terraform apply` on pushes to `acc`.

## Requirements

The example has no provider configuration of its own. It relies on these environment variables, which CI/CD always sets and which you must set yourself when running the example locally:

```sh
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=eu-central-1
```

Without `AWS_ENDPOINT_URL`, the example would run against whichever real AWS account your credentials point to.

## Running locally

```sh
docker run -d --name ministack -p 4566:4566 ministackorg/ministack:1.5.31
terraform init
terraform apply
docker rm -f ministack # MiniStack keeps everything in the container, so this clears it
```

## Notes

Note that providing `api_id` will attach the authoriser to an API. If you wish to attach it yourself, you will do better to _not_ provide this, and instead use either the `lambda_invoke_arn` output in your own `aws_api_gateway_authorizer` resource, or the `constructed_lambda_invoke_arn` output in your full OpenAPI spec.

Note that you _should_ be able to use the `lambda_invoke_arn` output, but there seems to be a broken dependency bug in Terraform where this is not available until the module has run. This is being investigated.

`api_id` is a static string rather than an API created alongside the example, because the module uses it in a `count`, which has to be known at plan time.
