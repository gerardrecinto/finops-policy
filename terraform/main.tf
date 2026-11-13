terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    google  = { source = "hashicorp/google", version = "~> 6.0" }
  }
}

variable "subscription_id" { type = string }
variable "billing_account" { type = string }
variable "alert_emails" { type = list(string) }
variable "monthly_budget" {
  type    = number
  default = 10000
}

resource "azurerm_consumption_budget_subscription" "monthly" {
  name            = "monthly"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = var.monthly_budget
  time_grain      = "Monthly"

  time_period {
    start_date = "2027-01-01T00:00:00Z"
  }

  # Warn at 80 percent of actual spend, then at 100 percent of the forecast.
  notification {
    operator       = "GreaterThan"
    threshold      = 80
    threshold_type = "Actual"
    contact_emails = var.alert_emails
  }

  notification {
    operator       = "GreaterThan"
    threshold      = 100
    threshold_type = "Forecasted"
    contact_emails = var.alert_emails
  }
}

resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account
  display_name    = "monthly"

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget)
    }
  }

  threshold_rules {
    threshold_percent = 0.8
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }
}
