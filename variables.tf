variable "name" {
  description = "Name to use as part of resource name"
  type        = string
}

variable "api_id" {
  description = "ID of the API to add the athorizer to"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "secret_name" {
  description = "The name of the Secrets Manager secret containing the 'bearer tokens'"
  type        = string
  default     = "api-bearer-tokens"
}

variable "attach_to_api" {
  description = "Whether to attach the authorizer to var.api_id"
  type        = bool
  default     = false
}
