variable "endpoint" {
  description = "Emulator endpoint. http://floci:4566 inside compose, http://localhost:5766 from the host."
  type        = string
  default     = "http://localhost:5766"
}

variable "name_prefix" {
  description = "Must match KMS_KEY_ID (alias/<name_prefix>) in deploy/compose/compose.floci.yaml."
  type        = string
  default     = "agenteval-local"
}
