module "authorizer" {
  source = "../../"

  name   = "app-x"
  api_id = "abc1234567" # See README for why you may not want this
  tags   = { app = "module-test-app" }
}
