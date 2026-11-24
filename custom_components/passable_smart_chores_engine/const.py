"""Constants for Passable Smart Chores Engine."""

from __future__ import annotations

DOMAIN = "passable_smart_chores_engine"
VERSION = "1.0.0"
STORAGE_KEY = "passable_smart_chores_engine"
STORAGE_VERSION = 1

FRONTEND_URL_PATH = "/passable_chores_frontend/passable-chores-card.js"

# Days & scheduling
DAYS_OF_WEEK = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
WEEKDAY_TO_INDEX: dict[str, int] = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

SCHEDULE_DAILY = "daily"
SCHEDULE_SCHOOL_DAYS = "school_days"
SCHEDULE_WEEKENDS = "weekends"
SCHEDULE_WEEKLY = "weekly"
SCHEDULE_CUSTOM_DAYS = "custom_days"
VALID_SCHEDULE_TYPES = (
    SCHEDULE_DAILY,
    SCHEDULE_SCHOOL_DAYS,
    SCHEDULE_WEEKENDS,
    SCHEDULE_WEEKLY,
    SCHEDULE_CUSTOM_DAYS,
)

ASSIGN_EACH = "each"
ASSIGN_ROTATE_WEEKLY = "rotate_weekly"
ASSIGN_UP_FOR_GRABS = "up_for_grabs"
VALID_ASSIGNMENT_MODES = (
    ASSIGN_EACH,
    ASSIGN_ROTATE_WEEKLY,
    ASSIGN_UP_FOR_GRABS,
)

TIER_REQUIRED = "required"
TIER_BONUS = "bonus"
VALID_TIERS = (TIER_REQUIRED, TIER_BONUS)

STATUS_PENDING = "pending"
STATUS_WAITING_APPROVAL = "waiting_approval"
STATUS_COMPLETED = "completed"
VALID_STATUSES = (
    STATUS_PENDING,
    STATUS_WAITING_APPROVAL,
    STATUS_COMPLETED,
)

TRUST_INHERIT = "inherit"
TRUST_HONOR = "honor_system"
TRUST_APPROVAL = "parent_approval"
VALID_TRUST_MODES = (
    TRUST_INHERIT,
    TRUST_HONOR,
    TRUST_APPROVAL,
)
VALID_GLOBAL_TRUST_MODES = (TRUST_HONOR, TRUST_APPROVAL)

TIME_OF_DAY_OPTIONS = ("anytime", "morning", "afternoon", "evening")

# Unlock rules
UNLOCK_SCOPE_PERSONAL = "personal"
UNLOCK_SCOPE_SHARED = "shared"
VALID_UNLOCK_SCOPES = (UNLOCK_SCOPE_PERSONAL, UNLOCK_SCOPE_SHARED)

SHARED_MODE_ANY_ACTIVE = "any_active_kid"
SHARED_MODE_ALL_ACTIVE = "all_active_kids"
VALID_SHARED_MODES = (SHARED_MODE_ANY_ACTIVE, SHARED_MODE_ALL_ACTIVE)

TARGET_MODE_SCREEN_TIME = "passable_screen_time"
TARGET_MODE_LOCKOUT_SWITCH = "lockout_switch"
TARGET_MODE_POWER_SWITCH = "power_switch"
TARGET_MODE_NINTENDO = "nintendo_switch"
VALID_TARGET_MODES = (
    TARGET_MODE_SCREEN_TIME,
    TARGET_MODE_LOCKOUT_SWITCH,
    TARGET_MODE_POWER_SWITCH,
    TARGET_MODE_NINTENDO,
)

ZERO_CHORES_IGNORE = "ignore"
ZERO_CHORES_UNLOCK = "unlock"
VALID_ZERO_CHORES_BEHAVIORS = (ZERO_CHORES_IGNORE, ZERO_CHORES_UNLOCK)

# Rewards
REWARD_SMART_ACTION = "smart_action"
REWARD_PARENT_FULFILLED = "parent_fulfilled"
VALID_REWARD_TYPES = (REWARD_SMART_ACTION, REWARD_PARENT_FULFILLED)

SMART_ACTION_SCREEN_TIME_TIMER = "screen_time_timer"
SMART_ACTION_SCREEN_TIME_BONUS = "screen_time_bonus"
SMART_ACTION_NINTENDO_BONUS = "nintendo_bonus"
SMART_ACTION_HA_SERVICE = "ha_service"
VALID_SMART_ACTION_KINDS = (
    SMART_ACTION_SCREEN_TIME_TIMER,
    SMART_ACTION_SCREEN_TIME_BONUS,
    SMART_ACTION_NINTENDO_BONUS,
    SMART_ACTION_HA_SERVICE,
)

REDEMPTION_PENDING = "pending"
REDEMPTION_APPROVED = "approved"
REDEMPTION_DENIED = "denied"

# Defaults
DEFAULT_DAILY_RESET_TIME = "05:00"
DEFAULT_WEEKLY_RESET_DAY = "mon"
DEFAULT_WEEKLY_DUE_DAY = "sat"
DEFAULT_UNDO_WINDOW_SECONDS = 15
DEFAULT_STREAK_MILESTONES = [3, 7, 14, 30, 60, 100]
DEFAULT_NO_SCHOOL_KEYWORDS = [
    "no school",
    "holiday",
    "break",
    "teacher",
    "inservice",
    "in-service",
    "vacation",
    "day off",
    "closed",
    "professional development",
]

# Dispatcher signals
SIGNAL_KID_ADDED = "passable_chores_kid_added"
SIGNAL_KID_UPDATED = "passable_chores_kid_updated"
SIGNAL_KID_REMOVED = "passable_chores_kid_removed"
SIGNAL_ENGINE_UPDATED = "passable_chores_engine_updated"
SIGNAL_STORAGE_UPDATED = "passable_chores_storage_updated"

# Event bus events
EVENT_CHORE_COMPLETED = f"{DOMAIN}_chore_completed"
EVENT_CHORE_APPROVED = f"{DOMAIN}_chore_approved"
EVENT_CHORE_REJECTED = f"{DOMAIN}_chore_rejected"
EVENT_KID_ALL_COMPLETED = f"{DOMAIN}_kid_all_completed"
EVENT_STREAK_MILESTONE = f"{DOMAIN}_streak_milestone"
EVENT_REWARD_REDEEMED = f"{DOMAIN}_reward_redeemed"
EVENT_DEVICE_UNLOCKED = f"{DOMAIN}_device_unlocked"

# Mobile push actionable notification prefixes
ACTION_APPROVE_CHORE_PREFIX = "PASSABLE_CHORES_APPROVE_"
ACTION_REJECT_CHORE_PREFIX = "PASSABLE_CHORES_REJECT_"
ACTION_APPROVE_REWARD_PREFIX = "PASSABLE_CHORES_RWD_OK_"
ACTION_DENY_REWARD_PREFIX = "PASSABLE_CHORES_RWD_NO_"

# Config keys
CONF_DAILY_RESET_TIME = "daily_reset_time"
CONF_WEEKLY_RESET_DAY = "weekly_reset_day"
CONF_WEEKLY_DUE_DAY = "weekly_due_day"
CONF_DEFAULT_TRUST_MODE = "default_trust_mode"
CONF_NO_SCHOOL_CALENDARS = "no_school_calendars"
CONF_GAMIFICATION_ENABLED = "gamification_enabled"
CONF_SEED_STARTER_TEMPLATES = "seed_starter_templates"
