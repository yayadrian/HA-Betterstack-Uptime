"""Constants for the Better Stack Uptime integration."""

DOMAIN = "betterstack_uptime"

CONF_API_TOKEN = "api_token"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_POLL_INTERVAL = 60
MIN_POLL_INTERVAL = 15
MAX_POLL_INTERVAL = 3600

API_BASE_URL = "https://uptime.betterstack.com/api/v2"
API_TOKEN_URL = "https://betterstack.com/settings/global-api-tokens"

# Supported Better Stack check statuses for enum sensor metadata.
# Anything else is reported as HA's own unknown state.
CHECK_STATUS_OPTIONS = [
    "up",
    "down",
    "pending",
    "paused",
    "maintenance",
    "validating",
]

# Statuses considered "up" for the binary sensor
STATUSES_UP = {"up", "validating"}

# Heartbeat IDs can collide with monitor IDs, so heartbeat keys, unique IDs
# and device identifiers carry this prefix (see docs/adr/0001)
HEARTBEAT_ID_PREFIX = "heartbeat-"
