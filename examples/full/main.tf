module "authorizer" {
  source = "../../"

  name   = "app-x"
  api_id = "c882c433o3" # See README for why you may not want this
  tags   = { app = "module-test-app" }
}
