"""Persistent atomic storage manager for Passable Smart Chores Engine."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    ASSIGN_EACH,
    DEFAULT_DAILY_RESET_TIME,
    DEFAULT_NO_SCHOOL_KEYWORDS,
    DEFAULT_STREAK_MILESTONES,
    DEFAULT_UNDO_WINDOW_SECONDS,
    DEFAULT_WEEKLY_DUE_DAY,
    DEFAULT_WEEKLY_RESET_DAY,
    SCHEDULE_DAILY,
    SHARED_MODE_ANY_ACTIVE,
    STORAGE_KEY,
    STORAGE_VERSION,
    TARGET_MODE_SCREEN_TIME,
    TIER_REQUIRED,
    TIME_OF_DAY_OPTIONS,
    TRUST_HONOR,
    TRUST_INHERIT,
    UNLOCK_SCOPE_SHARED,
    VALID_ASSIGNMENT_MODES,
    VALID_GLOBAL_TRUST_MODES,
    VALID_REWARD_TYPES,
    VALID_SCHEDULE_TYPES,
    VALID_SHARED_MODES,
    VALID_TARGET_MODES,
    VALID_TIERS,
    VALID_TRUST_MODES,
    VALID_UNLOCK_SCOPES,
    VALID_ZERO_CHORES_BEHAVIORS,
    WEEKDAY_TO_INDEX,
    ZERO_CHORES_IGNORE,
)

_LOGGER = logging.getLogger(__name__)


def slugify_id(raw: str, prefix: str = "item") -> str:
    """Create a safe lowercase underscore identifier."""
    cleaned = re.sub(r"[^a-z0-9_]+", "_", str(raw or "").strip().lower()).strip("_")
    if not cleaned:
        return f"{prefix}_{secrets.token_hex(3)}"
    return cleaned


def normalize_hhmm(value: Any, fallback: str = DEFAULT_DAILY_RESET_TIME) -> str:
    """Validate and normalize an HH:MM string."""
    if not isinstance(value, str):
        return fallback
    parts = value.strip().split(":")
    if len(parts) < 2:
        return fallback
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    except (TypeError, ValueError):
        pass
    return fallback


def normalize_weekday(value: Any, fallback: str) -> str:
    """Validate and normalize a 3-letter weekday key."""
    val = str(value or "").strip().lower()[:3]
    if val in WEEKDAY_TO_INDEX:
        return val
    return fallback


def default_settings() -> dict[str, Any]:
    """Return default global integration settings."""
    return {
        "daily_reset_time": DEFAULT_DAILY_RESET_TIME,
        "weekly_reset_day": DEFAULT_WEEKLY_RESET_DAY,
        "weekly_due_day": DEFAULT_WEEKLY_DUE_DAY,
        "default_trust_mode": TRUST_HONOR,
        "undo_window_seconds": DEFAULT_UNDO_WINDOW_SECONDS,
        "no_school_calendars": [],
        "no_school_keywords": list(DEFAULT_NO_SCHOOL_KEYWORDS),
        "expand_weekends_on_no_school": True,
        "manual_no_school_date": None,
        "gamification_enabled": True,
        "points_enabled": True,
        "streaks_enabled": True,
        "rewards_enabled": True,
        "celebrations_enabled": True,
        "daily_all_done_bonus_points": 5,
        "parent_notify_services": [],
        "tts_entity": None,
        "streak_milestones": list(DEFAULT_STREAK_MILESTONES),
    }


def default_security() -> dict[str, Any]:
    """Return default security/PIN settings."""
    return {
        "pin_enabled": False,
        "pin_hash": None,
        "pin_salt": None,
        "require_pin_for_approvals": True,
        "require_pin_for_settings": True,
        "bypass_for_ha_admins": True,
    }


def hash_pin(pin: str, salt: str) -> str:
    """Hash a PIN with a per-user salt using SHA-256."""
    return hashlib.sha256(f"{salt}:{pin}".encode("utf-8")).hexdigest()


def normalize_kid(kid_id: str, data: dict[str, Any], default_order: int = 0) -> dict[str, Any]:
    """Normalize a kid profile dictionary."""
    raw = dict(data or {})
    trust = raw.get("trust_mode", TRUST_INHERIT)
    if trust not in VALID_TRUST_MODES:
        trust = TRUST_INHERIT
    return {
        "kid_id": kid_id,
        "name": str(raw.get("name") or kid_id.replace("_", " ").title()).strip(),
        "avatar": str(raw.get("avatar") or "🧒").strip(),
        "icon": str(raw.get("icon") or "mdi:account-child-circle").strip(),
        "accent_color": str(raw.get("accent_color") or "#039BE5").strip(),
        "enabled": bool(raw.get("enabled", True)),
        "trust_mode": trust,
        "points": max(0, int(raw.get("points", 0) or 0)),
        "lifetime_points": max(0, int(raw.get("lifetime_points", 0) or 0)),
        "streak_current": max(0, int(raw.get("streak_current", 0) or 0)),
        "streak_best": max(0, int(raw.get("streak_best", 0) or 0)),
        "last_streak_date": raw.get("last_streak_date"),
        "prev_streak_date": raw.get("prev_streak_date"),
        "streak_prev_before_today": max(0, int(raw.get("streak_prev_before_today", 0) or 0)),
        "daily_bonus_awarded_date": raw.get("daily_bonus_awarded_date"),
        "order": int(raw.get("order", default_order) or 0),
    }


def normalize_chore(
    chore_id: str,
    data: dict[str, Any],
    default_order: int = 0,
    default_week_key: str | None = None,
) -> dict[str, Any]:
    """Normalize a chore definition dictionary."""
    raw = dict(data or {})
    tier = raw.get("tier", TIER_REQUIRED)
    if tier not in VALID_TIERS:
        tier = TIER_REQUIRED

    sched = raw.get("schedule_type", SCHEDULE_DAILY)
    if sched not in VALID_SCHEDULE_TYPES:
        sched = SCHEDULE_DAILY

    assign = raw.get("assignment_mode", ASSIGN_EACH)
    if assign not in VALID_ASSIGNMENT_MODES:
        assign = ASSIGN_EACH

    trust = raw.get("trust_mode", TRUST_INHERIT)
    if trust not in VALID_TRUST_MODES:
        trust = TRUST_INHERIT

    time_of_day = raw.get("time_of_day", "anytime")
    if time_of_day not in TIME_OF_DAY_OPTIONS:
        time_of_day = "anytime"

    raw_custom_days = raw.get("custom_days") or []
    custom_days = [
        d for d in (str(x).lower()[:3] for x in raw_custom_days) if d in WEEKDAY_TO_INDEX
    ]

    assigned_kids = [
        str(k).strip() for k in (raw.get("assigned_kids") or []) if str(k).strip()
    ]

    weekly_due = raw.get("weekly_due_day")
    if weekly_due:
        weekly_due = normalize_weekday(weekly_due, DEFAULT_WEEKLY_DUE_DAY)
    else:
        weekly_due = None

    completions_raw = raw.get("completions")
    completions = dict(completions_raw) if isinstance(completions_raw, dict) else {}

    return {
        "chore_id": chore_id,
        "name": str(raw.get("name") or chore_id.replace("_", " ").title()).strip(),
        "emoji": str(raw.get("emoji") or "🧹").strip(),
        "image": raw.get("image") or None,
        "icon": str(raw.get("icon") or "mdi:check-circle-outline").strip(),
        "enabled": bool(raw.get("enabled", True)),
        "tier": tier,
        "schedule_type": sched,
        "custom_days": custom_days,
        "weekly_due_day": weekly_due,
        "weekly_flexible": bool(raw.get("weekly_flexible", True)),
        "assignment_mode": assign,
        "assigned_kids": assigned_kids,
        "rotation_offset": int(raw.get("rotation_offset", 0) or 0),
        "rotation_anchor_date": raw.get("rotation_anchor_date") or default_week_key,
        "points": max(0, int(raw.get("points", 5 if tier == TIER_REQUIRED else 15) or 0)),
        "trust_mode": trust,
        "time_of_day": time_of_day,
        "order": int(raw.get("order", default_order) or 0),
        "completions": completions,
    }


def normalize_reward(reward_id: str, data: dict[str, Any], default_order: int = 0) -> dict[str, Any]:
    """Normalize a reward definition dictionary."""
    raw = dict(data or {})
    rtype = raw.get("reward_type", "parent_fulfilled")
    if rtype not in VALID_REWARD_TYPES:
        rtype = "parent_fulfilled"
    default_auto = rtype == "smart_action"
    smart_action = raw.get("smart_action")
    if smart_action is not None and not isinstance(smart_action, dict):
        smart_action = None
    return {
        "reward_id": reward_id,
        "name": str(raw.get("name") or reward_id.replace("_", " ").title()).strip(),
        "emoji": str(raw.get("emoji") or "🎁").strip(),
        "icon": str(raw.get("icon") or "mdi:gift-outline").strip(),
        "cost": max(1, int(raw.get("cost", 25) or 25)),
        "reward_type": rtype,
        "auto_approve": bool(raw.get("auto_approve", default_auto)),
        "smart_action": smart_action,
        "enabled": bool(raw.get("enabled", True)),
        "order": int(raw.get("order", default_order) or 0),
    }


def normalize_unlock_rule(rule_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a device unlock rule dictionary."""
    raw = dict(data or {})
    scope = raw.get("scope", UNLOCK_SCOPE_SHARED)
    if scope not in VALID_UNLOCK_SCOPES:
        scope = UNLOCK_SCOPE_SHARED

    shared_mode = raw.get("shared_mode", SHARED_MODE_ANY_ACTIVE)
    if shared_mode not in VALID_SHARED_MODES:
        shared_mode = SHARED_MODE_ANY_ACTIVE

    target_mode = raw.get("target_mode", TARGET_MODE_SCREEN_TIME)
    if target_mode not in VALID_TARGET_MODES:
        target_mode = TARGET_MODE_SCREEN_TIME

    zero_beh = raw.get("zero_chores_behavior", ZERO_CHORES_IGNORE)
    if zero_beh not in VALID_ZERO_CHORES_BEHAVIORS:
        zero_beh = ZERO_CHORES_IGNORE

    return {
        "rule_id": rule_id,
        "name": str(raw.get("name") or rule_id.replace("_", " ").title()).strip(),
        "enabled": bool(raw.get("enabled", True)),
        "scope": scope,
        "kid_id": raw.get("kid_id") if scope == "personal" else None,
        "shared_mode": shared_mode,
        "target_mode": target_mode,
        "screen_time_device_id": raw.get("screen_time_device_id") or None,
        "target_entity": raw.get("target_entity") or None,
        "nintendo_bonus_minutes": max(5, int(raw.get("nintendo_bonus_minutes", 60) or 60)),
        "lock_on_reset": bool(raw.get("lock_on_reset", True)),
        "re_lock_if_uncompleted": bool(raw.get("re_lock_if_uncompleted", True)),
        "respect_screen_time_schedules": bool(raw.get("respect_screen_time_schedules", True)),
        "zero_chores_behavior": zero_beh,
        "unlocked_for_cycle_date": raw.get("unlocked_for_cycle_date"),
        "last_applied_locked": raw.get("last_applied_locked"),
    }


class PassableChoresStorage:
    """Manages persistent atomic storage for kids, chores, rewards, unlock rules, and logs."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize atomic storage."""
        self.hass = hass
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = {
            "settings": default_settings(),
            "security": default_security(),
            "kids": {},
            "chores": {},
            "rewards": {},
            "redemptions": [],
            "unlock_rules": {},
            "activity_log": [],
            "cycle_state": {
                "last_cycle_date": None,
                "last_week_key": None,
                "had_required_due": {},
            },
        }

    async def async_load(self) -> dict[str, Any]:
        """Load persisted data from disk and normalize schema defaults."""
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            self.data = stored

        modified = False
        # Settings
        if not isinstance(self.data.get("settings"), dict):
            self.data["settings"] = default_settings()
            modified = True
        else:
            s_def = default_settings()
            for k, v in s_def.items():
                if k not in self.data["settings"]:
                    self.data["settings"][k] = v
                    modified = True
            self.data["settings"]["daily_reset_time"] = normalize_hhmm(
                self.data["settings"].get("daily_reset_time"), DEFAULT_DAILY_RESET_TIME
            )
            self.data["settings"]["weekly_reset_day"] = normalize_weekday(
                self.data["settings"].get("weekly_reset_day"), DEFAULT_WEEKLY_RESET_DAY
            )
            self.data["settings"]["weekly_due_day"] = normalize_weekday(
                self.data["settings"].get("weekly_due_day"), DEFAULT_WEEKLY_DUE_DAY
            )
            if self.data["settings"].get("default_trust_mode") not in VALID_GLOBAL_TRUST_MODES:
                self.data["settings"]["default_trust_mode"] = TRUST_HONOR
                modified = True

        # Security
        if not isinstance(self.data.get("security"), dict):
            self.data["security"] = default_security()
            modified = True
        else:
            sec_def = default_security()
            for k, v in sec_def.items():
                if k not in self.data["security"]:
                    self.data["security"][k] = v
                    modified = True

        # Collections
        for key, default_val in (
            ("kids", {}),
            ("chores", {}),
            ("rewards", {}),
            ("unlock_rules", {}),
        ):
            if not isinstance(self.data.get(key), dict):
                self.data[key] = default_val
                modified = True

        for key in ("redemptions", "activity_log"):
            if not isinstance(self.data.get(key), list):
                self.data[key] = []
                modified = True

        if not isinstance(self.data.get("cycle_state"), dict):
            self.data["cycle_state"] = {
                "last_cycle_date": None,
                "last_week_key": None,
                "had_required_due": {},
            }
            modified = True
        else:
            self.data["cycle_state"].setdefault("last_cycle_date", None)
            self.data["cycle_state"].setdefault("last_week_key", None)
            if not isinstance(self.data["cycle_state"].get("had_required_due"), dict):
                self.data["cycle_state"]["had_required_due"] = {}
                modified = True

        # Normalize entries
        for idx, (kid_id, kid_raw) in enumerate(list(self.data["kids"].items())):
            norm = normalize_kid(kid_id, kid_raw, default_order=idx)
            if norm != kid_raw:
                self.data["kids"][kid_id] = norm
                modified = True

        for idx, (chore_id, chore_raw) in enumerate(list(self.data["chores"].items())):
            norm = normalize_chore(chore_id, chore_raw, default_order=idx)
            if norm != chore_raw:
                self.data["chores"][chore_id] = norm
                modified = True

        for idx, (reward_id, reward_raw) in enumerate(list(self.data["rewards"].items())):
            norm = normalize_reward(reward_id, reward_raw, default_order=idx)
            if norm != reward_raw:
                self.data["rewards"][reward_id] = norm
                modified = True

        for rule_id, rule_raw in list(self.data["unlock_rules"].items()):
            norm = normalize_unlock_rule(rule_id, rule_raw)
            if norm != rule_raw:
                self.data["unlock_rules"][rule_id] = norm
                modified = True

        if modified:
            await self.async_save()

        _LOGGER.info(
            "Loaded Passable Chores storage: %s kids, %s chores, %s rewards, %s unlock rules",
            len(self.data["kids"]),
            len(self.data["chores"]),
            len(self.data["rewards"]),
            len(self.data["unlock_rules"]),
        )
        return self.data

    async def async_save(self) -> None:
        """Persist storage atomically."""
        await self._store.async_save(self.data)

    # Accessors
    def get_settings(self) -> dict[str, Any]:
        return self.data.setdefault("settings", default_settings())

    def get_security(self) -> dict[str, Any]:
        return self.data.setdefault("security", default_security())

    def get_public_security(self) -> dict[str, Any]:
        sec = self.get_security()
        return {
            "pin_enabled": bool(sec.get("pin_enabled", False) and sec.get("pin_hash")),
            "require_pin_for_approvals": bool(sec.get("require_pin_for_approvals", True)),
            "require_pin_for_settings": bool(sec.get("require_pin_for_settings", True)),
            "bypass_for_ha_admins": bool(sec.get("bypass_for_ha_admins", True)),
        }

    def verify_pin(self, candidate: str) -> bool:
        sec = self.get_security()
        pin_hash = sec.get("pin_hash")
        pin_salt = sec.get("pin_salt")
        if not pin_hash or not pin_salt:
            return False
        return hmac.compare_digest(hash_pin(str(candidate or ""), pin_salt), pin_hash)

    def set_pin(self, new_pin: str) -> None:
        salt = secrets.token_hex(16)
        sec = self.get_security()
        sec["pin_salt"] = salt
        sec["pin_hash"] = hash_pin(str(new_pin), salt)
        sec["pin_enabled"] = True

    def clear_pin(self) -> None:
        sec = self.get_security()
        sec["pin_salt"] = None
        sec["pin_hash"] = None
        sec["pin_enabled"] = False

    def get_kids(self) -> dict[str, dict[str, Any]]:
        return self.data.setdefault("kids", {})

    def get_chores(self) -> dict[str, dict[str, Any]]:
        return self.data.setdefault("chores", {})

    def get_rewards(self) -> dict[str, dict[str, Any]]:
        return self.data.setdefault("rewards", {})

    def get_redemptions(self) -> list[dict[str, Any]]:
        return self.data.setdefault("redemptions", [])

    def get_unlock_rules(self) -> dict[str, dict[str, Any]]:
        return self.data.setdefault("unlock_rules", {})

    def get_activity_log(self) -> list[dict[str, Any]]:
        return self.data.setdefault("activity_log", [])

    def get_cycle_state(self) -> dict[str, Any]:
        return self.data.setdefault(
            "cycle_state",
            {"last_cycle_date": None, "last_week_key": None, "had_required_due": {}},
        )

    def append_activity(self, entry: dict[str, Any], limit: int = 80) -> None:
        log = self.get_activity_log()
        log.insert(0, entry)
        if len(log) > limit:
            del log[limit:]

    def append_redemption(self, entry: dict[str, Any], limit: int = 50) -> None:
        items = self.get_redemptions()
        items.insert(0, entry)
        if len(items) > limit:
            del items[limit:]
