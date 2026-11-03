# Read README.md before running this: it lists the AWS_* environment variables this example
# expects, which point every AWS call at MiniStack. CI sets them for you

module "authorizer" {
  source = "../../"

  name   = "app-x"
  api_id = "abc1234567" # See README for why you may not want this
  tags   = { app = "module-test-app" }
}
