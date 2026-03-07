"""Constants for the Better Stack Uptime integration."""

DOMAIN = "betterstack_uptime"

CONF_API_TOKEN = "api_token"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_POLL_INTERVAL = 60
MIN_POLL_INTERVAL = 15
MAX_POLL_INTERVAL = 3600

API_BASE_URL = "https://uptime.betterstack.com/api/v2"

# Supported Better Stack monitor statuses for enum sensor metadata
MONITOR_STATUS_OPTIONS = [
	"up",
	"down",
	"pending",
	"paused",
	"maintenance",
	"validating",
	"unknown",
]

# Statuses considered "up" for the binary sensor
STATUSES_UP = {"up", "validating"}
