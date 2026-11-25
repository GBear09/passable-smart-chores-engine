"""Core scheduling, rotation, approval, rewards, and device unlock engine."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
import logging
import secrets
from typing import Any, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_time_change,
    async_track_time_interval,
)
import homeassistant.util.dt as dt_util

from .const import (
    ACTION_APPROVE_CHORE_PREFIX,
    ACTION_APPROVE_REWARD_PREFIX,
    ACTION_DENY_REWARD_PREFIX,
    ACTION_REJECT_CHORE_PREFIX,
    ASSIGN_EACH,
    ASSIGN_ROTATE_WEEKLY,
    ASSIGN_UP_FOR_GRABS,
    DEFAULT_DAILY_RESET_TIME,
    DEFAULT_NO_SCHOOL_KEYWORDS,
    DEFAULT_UNDO_WINDOW_SECONDS,
    DEFAULT_WEEKLY_DUE_DAY,
    DEFAULT_WEEKLY_RESET_DAY,
    DOMAIN,
    EVENT_CHORE_APPROVED,
    EVENT_CHORE_COMPLETED,
    EVENT_CHORE_REJECTED,
    EVENT_DEVICE_UNLOCKED,
    EVENT_KID_ALL_COMPLETED,
    EVENT_REWARD_REDEEMED,
    EVENT_STREAK_MILESTONE,
    REDEMPTION_APPROVED,
    REDEMPTION_DENIED,
    REDEMPTION_PENDING,
    REWARD_PARENT_FULFILLED,
    REWARD_SMART_ACTION,
    SCHEDULE_CUSTOM_DAYS,
    SCHEDULE_DAILY,
    SCHEDULE_SCHOOL_DAYS,
    SCHEDULE_WEEKLY,
    SCHEDULE_WEEKENDS,
    SHARED_MODE_ALL_ACTIVE,
    SHARED_MODE_ANY_ACTIVE,
    SIGNAL_ENGINE_UPDATED,
    SIGNAL_KID_ADDED,
    SIGNAL_KID_REMOVED,
    SIGNAL_KID_UPDATED,
    SIGNAL_STORAGE_UPDATED,
    SMART_ACTION_HA_SERVICE,
    SMART_ACTION_NINTENDO_BONUS,
    SMART_ACTION_SCREEN_TIME_BONUS,
    SMART_ACTION_SCREEN_TIME_TIMER,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_WAITING_APPROVAL,
    TARGET_MODE_LOCKOUT_SWITCH,
    TARGET_MODE_NINTENDO,
    TARGET_MODE_POWER_SWITCH,
    TARGET_MODE_SCREEN_TIME,
    TIER_BONUS,
    TIER_REQUIRED,
    TRUST_APPROVAL,
    TRUST_HONOR,
    TRUST_INHERIT,
    UNLOCK_SCOPE_PERSONAL,
    UNLOCK_SCOPE_SHARED,
    WEEKDAY_TO_INDEX,
    ZERO_CHORES_UNLOCK,
)
from .storage import (
    PassableChoresStorage,
    normalize_chore,
    normalize_hhmm,
    normalize_kid,
    normalize_reward,
    normalize_unlock_rule,
    normalize_weekday,
    slugify_id,
)

_LOGGER = logging.getLogger(__name__)

INDEX_TO_WEEKDAY = {v: k for k, v in WEEKDAY_TO_INDEX.items()}


def compute_cycle_date(
    now_local: datetime, daily_reset_time: str = DEFAULT_DAILY_RESET_TIME
) -> date:
    """Return the active chore cycle date accounting for daily_reset_time (e.g. 05:00)."""
    norm = normalize_hhmm(daily_reset_time, DEFAULT_DAILY_RESET_TIME)
    hour, minute = (int(p) for p in norm.split(":"))
    if (now_local.hour, now_local.minute) < (hour, minute):
        return (now_local - timedelta(days=1)).date()
    return now_local.date()


def compute_week_start_date(
    cycle_date: date, weekly_reset_day: str = DEFAULT_WEEKLY_RESET_DAY
) -> date:
    """Return the start date of the current chore week for the given weekly_reset_day."""
    reset_slug = normalize_weekday(weekly_reset_day, DEFAULT_WEEKLY_RESET_DAY)
    reset_idx = WEEKDAY_TO_INDEX[reset_slug]
    days_since_reset = (cycle_date.weekday() - reset_idx) % 7
    return cycle_date - timedelta(days=days_since_reset)


def is_no_school_day(
    cycle_date: date,
    settings: dict[str, Any],
    calendar_holiday_dates: set[str] | None = None,
) -> bool:
    """Return True if cycle_date is flagged as a No-School day via override or calendar."""
    iso = cycle_date.isoformat()
    if settings.get("manual_no_school_date") == iso:
        return True
    if calendar_holiday_dates and iso in calendar_holiday_dates:
        return True
    return False


def is_effective_school_day(
    cycle_date: date,
    settings: dict[str, Any],
    calendar_holiday_dates: set[str] | None = None,
) -> bool:
    """Return True if cycle_date is Mon-Fri and NOT a No-School/holiday day."""
    if cycle_date.weekday() >= 5:
        return False
    return not is_no_school_day(cycle_date, settings, calendar_holiday_dates)


def resolve_effective_trust_mode(
    chore: dict[str, Any], kid: dict[str, Any], settings: dict[str, Any]
) -> str:
    """Resolve effective trust mode: chore -> kid -> global default."""
    chore_trust = chore.get("trust_mode", TRUST_INHERIT)
    if chore_trust in (TRUST_HONOR, TRUST_APPROVAL):
        return chore_trust
    kid_trust = kid.get("trust_mode", TRUST_INHERIT)
    if kid_trust in (TRUST_HONOR, TRUST_APPROVAL):
        return kid_trust
    global_trust = settings.get("default_trust_mode", TRUST_HONOR)
    return global_trust if global_trust in (TRUST_HONOR, TRUST_APPROVAL) else TRUST_HONOR


def resolve_weekly_assignee(
    chore: dict[str, Any],
    kids: dict[str, dict[str, Any]],
    current_week_start: date,
    weekly_reset_day: str,
) -> str | None:
    """Return the active kid_id responsible for a rotate_weekly chore during current_week_start."""
    assigned = [
        kid_id
        for kid_id in (chore.get("assigned_kids") or [])
        if kid_id in kids and kids[kid_id].get("enabled", True)
    ]
    if not assigned:
        return None
    anchor_str = chore.get("rotation_anchor_date")
    try:
        anchor_date = (
            date.fromisoformat(anchor_str)
            if anchor_str
            else current_week_start
        )
    except ValueError:
        anchor_date = current_week_start
    anchor_week_start = compute_week_start_date(anchor_date, weekly_reset_day)
    weeks_elapsed = max(0, (current_week_start - anchor_week_start).days // 7)
    offset = int(chore.get("rotation_offset", 0) or 0)
    idx = (weeks_elapsed + offset) % len(assigned)
    return assigned[idx]


def get_chore_cycle_key(chore: dict[str, Any], cycle_date_str: str, week_key: str) -> str:
    """Return the storage cycle_key ('YYYY-MM-DD' for daily-family or week_key for weekly)."""
    if chore.get("schedule_type") == SCHEDULE_WEEKLY:
        return week_key
    return cycle_date_str


def evaluate_chore_schedule_for_kid(
    chore: dict[str, Any],
    kid_id: str,
    kids: dict[str, dict[str, Any]],
    cycle_date: date,
    settings: dict[str, Any],
    calendar_holiday_dates: set[str] | None = None,
) -> dict[str, Any]:
    """Evaluate visibility, assignment, and unlock-gating for (chore, kid) on cycle_date."""
    if not chore.get("enabled", True):
        return {"visible": False, "is_due_today_for_unlock": False, "is_rotation_turn": False}

    weekly_reset_day = settings.get("weekly_reset_day", DEFAULT_WEEKLY_RESET_DAY)
    week_start = compute_week_start_date(cycle_date, weekly_reset_day)
    assign_mode = chore.get("assignment_mode", ASSIGN_EACH)

    is_rotation_turn = False
    if assign_mode == ASSIGN_UP_FOR_GRABS:
        # Visible in bounty pool; if assigned_kids is non-empty, restrict eligibility to them
        assigned = chore.get("assigned_kids") or []
        if assigned and kid_id not in assigned:
            return {"visible": False, "is_due_today_for_unlock": False, "is_rotation_turn": False}
    elif assign_mode == ASSIGN_ROTATE_WEEKLY:
        assignee = resolve_weekly_assignee(chore, kids, week_start, weekly_reset_day)
        if assignee != kid_id:
            return {"visible": False, "is_due_today_for_unlock": False, "is_rotation_turn": False}
        is_rotation_turn = True
    else:
        if kid_id not in (chore.get("assigned_kids") or []):
            return {"visible": False, "is_due_today_for_unlock": False, "is_rotation_turn": False}

    sched = chore.get("schedule_type", SCHEDULE_DAILY)
    tier = chore.get("tier", TIER_REQUIRED)
    day_slug = INDEX_TO_WEEKDAY[cycle_date.weekday()]
    no_school = is_no_school_day(cycle_date, settings, calendar_holiday_dates)
    expand_weekends = bool(settings.get("expand_weekends_on_no_school", True))

    visible = False
    is_due_today_for_unlock = False
    due_label: str | None = None

    if sched == SCHEDULE_DAILY:
        visible = True
        is_due_today_for_unlock = tier == TIER_REQUIRED
    elif sched == SCHEDULE_SCHOOL_DAYS:
        visible = is_effective_school_day(cycle_date, settings, calendar_holiday_dates)
        is_due_today_for_unlock = visible and (tier == TIER_REQUIRED)
    elif sched == SCHEDULE_WEEKENDS:
        visible = (cycle_date.weekday() >= 5) or (expand_weekends and no_school)
        is_due_today_for_unlock = visible and (tier == TIER_REQUIRED)
    elif sched == SCHEDULE_CUSTOM_DAYS:
        visible = day_slug in (chore.get("custom_days") or [])
        is_due_today_for_unlock = visible and (tier == TIER_REQUIRED)
    elif sched == SCHEDULE_WEEKLY:
        due_day = normalize_weekday(
            chore.get("weekly_due_day") or settings.get("weekly_due_day"),
            DEFAULT_WEEKLY_DUE_DAY,
        )
        reset_idx = WEEKDAY_TO_INDEX[normalize_weekday(weekly_reset_day, DEFAULT_WEEKLY_RESET_DAY)]
        due_idx = WEEKDAY_TO_INDEX[due_day]
        current_offset = (cycle_date - week_start).days
        due_offset = (due_idx - reset_idx) % 7
        flexible = bool(chore.get("weekly_flexible", True))
        due_label = f"Due {due_day.title()}"

        if flexible:
            visible = 0 <= current_offset <= 6
            # On or after the weekly due day (e.g. Saturday/Sunday), promote to required today
            is_due_today_for_unlock = (
                visible and (tier == TIER_REQUIRED) and (current_offset >= due_offset)
            )
        else:
            visible = current_offset >= due_offset
            is_due_today_for_unlock = visible and (tier == TIER_REQUIRED)

    return {
        "visible": visible,
        "is_due_today_for_unlock": is_due_today_for_unlock,
        "is_rotation_turn": is_rotation_turn,
        "due_label": due_label,
    }


def evaluate_kid_boards(
    storage: PassableChoresStorage,
    now_local: datetime,
    calendar_holiday_dates: set[str] | None = None,
) -> dict[str, Any]:
    """Pure computation of today's cycle info, per-kid boards, bounties, and pending approvals."""
    settings = storage.get_settings()
    kids = storage.get_kids()
    chores = storage.get_chores()

    cycle_date = compute_cycle_date(
        now_local, settings.get("daily_reset_time", DEFAULT_DAILY_RESET_TIME)
    )
    cycle_date_str = cycle_date.isoformat()
    weekly_reset_day = settings.get("weekly_reset_day", DEFAULT_WEEKLY_RESET_DAY)
    week_start = compute_week_start_date(cycle_date, weekly_reset_day)
    week_key = week_start.isoformat()
    no_school = is_no_school_day(cycle_date, settings, calendar_holiday_dates)
    school_day = is_effective_school_day(cycle_date, settings, calendar_holiday_dates)

    sorted_kids = sorted(
        kids.values(), key=lambda k: (int(k.get("order", 0)), k.get("name", "").lower())
    )
    sorted_chores = sorted(
        chores.values(), key=lambda c: (int(c.get("order", 0)), c.get("name", "").lower())
    )

    kid_boards: dict[str, dict[str, Any]] = {}
    pending_approvals: list[dict[str, Any]] = []
    bonus_chores: list[dict[str, Any]] = []

    # Pre-scan up_for_grabs claims in the active cycle
    bounty_claims: dict[str, list[str]] = {}
    for cid, chore in chores.items():
        if chore.get("assignment_mode") != ASSIGN_UP_FOR_GRABS:
            continue
        ckey = get_chore_cycle_key(chore, cycle_date_str, week_key)
        claims: list[str] = []
        for k_id, rec in (chore.get("completions") or {}).items():
            if isinstance(rec, dict) and rec.get("cycle_key") == ckey:
                if rec.get("status") in (STATUS_COMPLETED, STATUS_WAITING_APPROVAL):
                    claims.append(k_id)
        bounty_claims[cid] = claims

    for kid in sorted_kids:
        kid_id = kid["kid_id"]
        board_items: list[dict[str, Any]] = []
        required_due_total = 0
        required_due_completed = 0
        required_due_waiting = 0
        visible_total = 0
        visible_completed = 0

        for chore in sorted_chores:
            if chore.get("assignment_mode") == ASSIGN_UP_FOR_GRABS:
                continue
            eval_res = evaluate_chore_schedule_for_kid(
                chore, kid_id, kids, cycle_date, settings, calendar_holiday_dates
            )
            if not eval_res["visible"]:
                continue

            ckey = get_chore_cycle_key(chore, cycle_date_str, week_key)
            rec = (chore.get("completions") or {}).get(kid_id)
            if not isinstance(rec, dict) or rec.get("cycle_key") != ckey:
                status = STATUS_PENDING
                completed_at = None
                undo_expires_at = None
            else:
                status = rec.get("status", STATUS_PENDING)
                if status not in (STATUS_PENDING, STATUS_WAITING_APPROVAL, STATUS_COMPLETED):
                    status = STATUS_PENDING
                completed_at = rec.get("completed_at")
                undo_expires_at = rec.get("undo_expires_at")

            is_due_today = bool(eval_res["is_due_today_for_unlock"])
            visible_total += 1
            if status == STATUS_COMPLETED:
                visible_completed += 1

            if is_due_today:
                required_due_total += 1
                if status == STATUS_COMPLETED:
                    required_due_completed += 1
                elif status == STATUS_WAITING_APPROVAL:
                    required_due_waiting += 1

            eff_trust = resolve_effective_trust_mode(chore, kid, settings)
            item = {
                "chore_id": chore["chore_id"],
                "kid_id": kid_id,
                "name": chore["name"],
                "emoji": chore.get("emoji", "🧹"),
                "image": chore.get("image"),
                "icon": chore.get("icon", "mdi:check-circle-outline"),
                "tier": chore.get("tier", TIER_REQUIRED),
                "schedule_type": chore.get("schedule_type", SCHEDULE_DAILY),
                "assignment_mode": chore.get("assignment_mode", ASSIGN_EACH),
                "is_rotation_turn": eval_res["is_rotation_turn"],
                "due_label": eval_res.get("due_label"),
                "is_due_today_for_unlock": is_due_today,
                "points": int(chore.get("points", 0) or 0),
                "trust_mode": eff_trust,
                "time_of_day": chore.get("time_of_day", "anytime"),
                "status": status,
                "completed_at": completed_at,
                "undo_expires_at": undo_expires_at,
                "cycle_key": ckey,
            }
            board_items.append(item)

            if status == STATUS_WAITING_APPROVAL:
                pending_approvals.append(
                    {
                        "kind": "chore",
                        "chore_id": chore["chore_id"],
                        "kid_id": kid_id,
                        "kid_name": kid["name"],
                        "kid_avatar": kid.get("avatar", "🧒"),
                        "title": chore["name"],
                        "emoji": chore.get("emoji", "🧹"),
                        "points": int(chore.get("points", 0) or 0),
                        "requested_at": completed_at,
                    }
                )

        is_active_today = bool(kid.get("enabled", True)) and required_due_total > 0
        is_all_done_today = is_active_today and required_due_completed >= required_due_total
        progress_pct = (
            round((required_due_completed / required_due_total) * 100)
            if required_due_total > 0
            else (100 if visible_total > 0 and visible_completed >= visible_total else 0)
        )

        kid_trust = kid.get("trust_mode", TRUST_INHERIT)
        eff_kid_trust = (
            kid_trust
            if kid_trust in (TRUST_HONOR, TRUST_APPROVAL)
            else settings.get("default_trust_mode", TRUST_HONOR)
        )

        kid_boards[kid_id] = {
            **kid,
            "effective_trust_mode": eff_kid_trust,
            "board": board_items,
            "visible_total": visible_total,
            "visible_completed": visible_completed,
            "required_due_total": required_due_total,
            "required_due_completed": required_due_completed,
            "required_due_waiting": required_due_waiting,
            "progress_pct": progress_pct,
            "is_active_kid_today": is_active_today,
            "is_all_done_today": is_all_done_today,
        }

    # Build Up-for-Grabs Bonus Chores list
    for chore in sorted_chores:
        if not chore.get("enabled", True):
            continue
        if chore.get("assignment_mode") != ASSIGN_UP_FOR_GRABS:
            continue
        # Check schedule active using first dummy evaluation
        sched = chore.get("schedule_type", SCHEDULE_DAILY)
        day_slug = INDEX_TO_WEEKDAY[cycle_date.weekday()]
        expand_weekends = bool(settings.get("expand_weekends_on_no_school", True))
        sched_active = True
        if sched == SCHEDULE_SCHOOL_DAYS:
            sched_active = school_day
        elif sched == SCHEDULE_WEEKENDS:
            sched_active = (cycle_date.weekday() >= 5) or (expand_weekends and no_school)
        elif sched == SCHEDULE_CUSTOM_DAYS:
            sched_active = day_slug in (chore.get("custom_days") or [])
        if not sched_active:
            continue

        cid = chore["chore_id"]
        ckey = get_chore_cycle_key(chore, cycle_date_str, week_key)
        claims = bounty_claims.get(cid, [])
        claimed_by = claims[0] if claims else None
        claimed_status = None
        if claimed_by:
            rec = (chore.get("completions") or {}).get(claimed_by, {})
            claimed_status = rec.get("status")
            if claimed_status == STATUS_WAITING_APPROVAL and claimed_by in kids:
                kid_obj = kids[claimed_by]
                pending_approvals.append(
                    {
                        "kind": "chore",
                        "chore_id": cid,
                        "kid_id": claimed_by,
                        "kid_name": kid_obj["name"],
                        "kid_avatar": kid_obj.get("avatar", "🧒"),
                        "title": chore["name"],
                        "emoji": chore.get("emoji", "⭐"),
                        "points": int(chore.get("points", 0) or 0),
                        "requested_at": rec.get("completed_at"),
                    }
                )

        bonus_chores.append(
            {
                "chore_id": cid,
                "name": chore["name"],
                "emoji": chore.get("emoji", "⭐"),
                "image": chore.get("image"),
                "points": int(chore.get("points", 0) or 0),
                "schedule_type": sched,
                "assigned_kids": chore.get("assigned_kids") or [],
                "claimed_by_kid_id": claimed_by,
                "claimed_by_name": kids[claimed_by]["name"] if claimed_by in kids else None,
                "claimed_status": claimed_status,
                "cycle_key": ckey,
            }
        )

    # Pending reward redemptions
    for rdm in storage.get_redemptions():
        if rdm.get("status") == REDEMPTION_PENDING:
            pending_approvals.append(
                {
                    "kind": "reward",
                    "redemption_id": rdm["redemption_id"],
                    "kid_id": rdm["kid_id"],
                    "kid_name": rdm.get("kid_name", rdm["kid_id"]),
                    "kid_avatar": kids.get(rdm["kid_id"], {}).get("avatar", "🧒"),
                    "title": rdm.get("reward_name", "Reward"),
                    "emoji": rdm.get("emoji", "🎁"),
                    "cost": int(rdm.get("cost", 0) or 0),
                    "requested_at": rdm.get("requested_at"),
                }
            )

    return {
        "cycle": {
            "cycle_date": cycle_date_str,
            "week_key": week_key,
            "is_school_day": school_day,
            "is_no_school_override": no_school,
            "manual_no_school_active": settings.get("manual_no_school_date") == cycle_date_str,
            "daily_reset_time": settings.get("daily_reset_time", DEFAULT_DAILY_RESET_TIME),
            "weekly_reset_day": weekly_reset_day,
            "weekly_due_day": settings.get("weekly_due_day", DEFAULT_WEEKLY_DUE_DAY),
        },
        "kids": kid_boards,
        "bonus_chores": bonus_chores,
        "pending_approvals": pending_approvals,
    }


def evaluate_unlock_rule_satisfied(
    rule: dict[str, Any],
    kid_boards: dict[str, dict[str, Any]],
) -> tuple[bool | None, str]:
    """Return (satisfied_or_None_if_skip, reason_text) for an unlock rule."""
    if not rule.get("enabled", True):
        return None, "disabled"

    zero_beh = rule.get("zero_chores_behavior", ZERO_CHORES_UNLOCK if False else "ignore")
    scope = rule.get("scope", UNLOCK_SCOPE_SHARED)

    if scope == UNLOCK_SCOPE_PERSONAL:
        kid_id = rule.get("kid_id")
        kid = kid_boards.get(kid_id or "")
        if not kid or not kid.get("enabled", True):
            return None, "kid_missing_or_disabled"
        if not kid.get("is_active_kid_today"):
            if zero_beh == ZERO_CHORES_UNLOCK:
                return True, "zero_chores_unlock"
            return None, "zero_chores_ignored"
        if kid.get("is_all_done_today"):
            return True, f"{kid['name']} completed all required chores"
        return False, f"{kid['name']} has remaining chores ({kid['required_due_completed']}/{kid['required_due_total']})"

    # Shared device rule: exclude disabled kids and 0-chore kids
    active_kids = [
        k for k in kid_boards.values() if k.get("enabled", True) and k.get("is_active_kid_today")
    ]
    if not active_kids:
        if zero_beh == ZERO_CHORES_UNLOCK:
            return True, "no_active_kids_unlock"
        return None, "no_active_kids_ignored"

    shared_mode = rule.get("shared_mode", SHARED_MODE_ANY_ACTIVE)
    if shared_mode == SHARED_MODE_ALL_ACTIVE:
        if all(k.get("is_all_done_today") for k in active_kids):
            return True, "all active kids completed chores"
        done_names = [k["name"] for k in active_kids if k.get("is_all_done_today")]
        return False, f"waiting for all active kids ({len(done_names)}/{len(active_kids)} done)"

    # Default: any_active_kid
    done_kids = [k["name"] for k in active_kids if k.get("is_all_done_today")]
    if done_kids:
        return True, f"{done_kids[0]} completed chores"
    return False, "waiting for any active kid to finish"


class PassableChoresEngine:
    """Async coordinator engine for Passable Smart Chores."""

    def __init__(
        self,
        hass: HomeAssistant,
        storage: PassableChoresStorage,
        entry_id: str,
    ) -> None:
        self.hass = hass
        self.storage = storage
        self.entry_id = entry_id
        self._unsubs: list[Callable[[], None]] = []
        self._reset_unsub: Callable[[], None] | None = None
        self._calendar_holiday_dates: set[str] = set()
        self._last_holiday_refresh_date: str | None = None
        self._pending_action_tokens: dict[str, tuple[str, str, str]] = {}
        self._eval_lock = asyncio.Lock()

    async def async_setup(self) -> None:
        """Load storage, check cycle rollover, refresh calendars, and register timers."""
        await self.storage.async_load()
        await self.async_refresh_calendar_holidays()
        await self.async_check_cycle_rollover(evaluate_unlocks=True)

        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_periodic_tick,
                timedelta(seconds=60),
            )
        )
        self._schedule_daily_reset_listener()

        # Listen for Home Assistant mobile_app actionable notification taps
        self._unsubs.append(
            self.hass.bus.async_listen(
                "mobile_app_notification_action",
                self._async_handle_mobile_notification_action,
            )
        )

    async def async_unload(self) -> None:
        """Tear down timers and listeners."""
        if self._reset_unsub is not None:
            self._reset_unsub()
            self._reset_unsub = None
        for unsub in self._unsubs:
            try:
                unsub()
            except Exception:
                pass
        self._unsubs.clear()

    def _schedule_daily_reset_listener(self) -> None:
        """Register exact time-of-day callback for daily_reset_time."""
        if self._reset_unsub is not None:
            self._reset_unsub()
            self._reset_unsub = None
        reset_hhmm = normalize_hhmm(
            self.storage.get_settings().get("daily_reset_time"), DEFAULT_DAILY_RESET_TIME
        )
        hour, minute = (int(p) for p in reset_hhmm.split(":"))

        @callback
        def _on_reset_time(_now: datetime) -> None:
            self.hass.async_create_task(self.async_check_cycle_rollover(evaluate_unlocks=True))

        self._reset_unsub = async_track_time_change(
            self.hass, _on_reset_time, hour=hour, minute=minute, second=5
        )

    async def _async_periodic_tick(self, _now: datetime) -> None:
        """Periodic 60s check for cycle rollover, holiday calendar refresh, and deferred unlocks."""
        await self.async_check_cycle_rollover(evaluate_unlocks=True)

    async def async_refresh_calendar_holidays(self) -> None:
        """Inspect configured No-School / Holiday calendars for the active cycle date."""
        settings = self.storage.get_settings()
        calendars = settings.get("no_school_calendars") or []
        now_local = dt_util.now()
        cycle_date = compute_cycle_date(
            now_local, settings.get("daily_reset_time", DEFAULT_DAILY_RESET_TIME)
        )
        iso = cycle_date.isoformat()
        self._last_holiday_refresh_date = iso

        if not calendars:
            self._calendar_holiday_dates.discard(iso)
            return

        keywords = [
            str(k).strip().lower()
            for k in (settings.get("no_school_keywords") or DEFAULT_NO_SCHOOL_KEYWORDS)
            if str(k).strip()
        ]
        start_dt = datetime.combine(cycle_date, time(0, 0, 0), tzinfo=now_local.tzinfo)
        end_dt = datetime.combine(cycle_date, time(23, 59, 59), tzinfo=now_local.tzinfo)
        found_no_school = False

        for cal_id in calendars:
            if not cal_id or not isinstance(cal_id, str):
                continue
            is_holiday_cal = "holiday" in cal_id.lower()
            matched_service = False
            try:
                if self.hass.services.has_service("calendar", "get_events"):
                    resp = await self.hass.services.async_call(
                        "calendar",
                        "get_events",
                        {
                            "entity_id": cal_id,
                            "start_date_time": start_dt.isoformat(),
                            "end_date_time": end_dt.isoformat(),
                        },
                        blocking=True,
                        return_response=True,
                    )
                    events = []
                    if isinstance(resp, dict):
                        cal_block = resp.get(cal_id, {})
                        if isinstance(cal_block, dict):
                            events = cal_block.get("events") or []
                    for ev in events:
                        summary = str(ev.get("summary") or "").lower()
                        desc = str(ev.get("description") or "").lower()
                        if is_holiday_cal or any(kw in summary or kw in desc for kw in keywords):
                            found_no_school = True
                            matched_service = True
                            break
            except Exception as err:
                _LOGGER.debug("Calendar get_events failed for %s: %s", cal_id, err)

            if not matched_service:
                st = self.hass.states.get(cal_id)
                if st and st.state == "on":
                    msg = str(st.attributes.get("message") or "").lower()
                    desc = str(st.attributes.get("description") or "").lower()
                    if is_holiday_cal or any(kw in msg or kw in desc for kw in keywords):
                        found_no_school = True

            if found_no_school:
                break

        if found_no_school:
            self._calendar_holiday_dates.add(iso)
        else:
            self._calendar_holiday_dates.discard(iso)

    def get_snapshot_evaluation(self, now_local: datetime | None = None) -> dict[str, Any]:
        """Return evaluated boards for the given local timestamp."""
        return evaluate_kid_boards(
            self.storage,
            now_local or dt_util.now(),
            self._calendar_holiday_dates,
        )

    async def async_check_cycle_rollover(
        self,
        now_local: datetime | None = None,
        evaluate_unlocks: bool = True,
    ) -> bool:
        """Detect day/week rollover, enforce streak continuity, prune stale states, and evaluate unlocks."""
        now_local = now_local or dt_util.now()
        settings = self.storage.get_settings()
        cycle_date = compute_cycle_date(
            now_local, settings.get("daily_reset_time", DEFAULT_DAILY_RESET_TIME)
        )
        cycle_date_str = cycle_date.isoformat()
        week_start = compute_week_start_date(
            cycle_date, settings.get("weekly_reset_day", DEFAULT_WEEKLY_RESET_DAY)
        )
        week_key = week_start.isoformat()

        if self._last_holiday_refresh_date != cycle_date_str:
            await self.async_refresh_calendar_holidays()

        cycle_state = self.storage.get_cycle_state()
        last_cycle = cycle_state.get("last_cycle_date")
        last_week = cycle_state.get("last_week_key")
        rolled_over = False

        if last_cycle != cycle_date_str:
            rolled_over = True
            # Clear expired manual no-school override
            if settings.get("manual_no_school_date") and settings["manual_no_school_date"] != cycle_date_str:
                settings["manual_no_school_date"] = None

            # Update streak continuity for kids who had required chores on last_cycle
            if last_cycle:
                had_req = cycle_state.get("had_required_due") or {}
                for kid_id, kid in self.storage.get_kids().items():
                    if not kid.get("enabled", True):
                        continue
                    if had_req.get(kid_id, False) and kid.get("last_streak_date") != last_cycle:
                        kid["streak_current"] = 0

            # Prune stale completions
            week_changed = last_week != week_key
            for chore in self.storage.get_chores().values():
                comps = chore.get("completions")
                if not isinstance(comps, dict):
                    continue
                valid_key = week_key if chore.get("schedule_type") == SCHEDULE_WEEKLY else cycle_date_str
                for kid_id in list(comps.keys()):
                    rec = comps.get(kid_id)
                    if not isinstance(rec, dict) or rec.get("cycle_key") != valid_key:
                        if chore.get("schedule_type") != SCHEDULE_WEEKLY or week_changed:
                            del comps[kid_id]

            cycle_state["last_cycle_date"] = cycle_date_str
            cycle_state["last_week_key"] = week_key
            cycle_state["had_required_due"] = {}

        # Record today's had_required_due flags so tomorrow's rollover knows who had chores today
        eval_data = self.get_snapshot_evaluation(now_local)
        had_req_today = cycle_state.setdefault("had_required_due", {})
        changed_flags = False
        for kid_id, kdata in eval_data["kids"].items():
            has_req = kdata["required_due_total"] > 0
            if had_req_today.get(kid_id) != has_req:
                had_req_today[kid_id] = has_req
                changed_flags = True

        if rolled_over or changed_flags:
            await self.storage.async_save()

        if evaluate_unlocks:
            await self.async_evaluate_unlock_rules(
                is_cycle_reset=rolled_over, now_local=now_local
            )

        if rolled_over:
            async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return rolled_over

    # =========================================================================
    # CHORE COMPLETION, UNDO & APPROVAL WORKFLOW
    # =========================================================================

    async def async_complete_chore(
        self,
        chore_id: str,
        kid_id: str,
        by_parent: bool = False,
        parent_name: str | None = None,
        now_local: datetime | None = None,
    ) -> dict[str, Any]:
        """Complete a chore for a kid (honor system, parent override, or request approval)."""
        now_local = now_local or dt_util.now()
        chores = self.storage.get_chores()
        kids = self.storage.get_kids()
        settings = self.storage.get_settings()

        chore = chores.get(chore_id)
        kid = kids.get(kid_id)
        if not chore or not kid:
            raise ValueError("Chore or kid not found")

        eval_before = self.get_snapshot_evaluation(now_local)
        cycle_date_str = eval_before["cycle"]["cycle_date"]
        week_key = eval_before["cycle"]["week_key"]
        ckey = get_chore_cycle_key(chore, cycle_date_str, week_key)

        # Prevent duplicate claim on up_for_grabs
        if chore.get("assignment_mode") == ASSIGN_UP_FOR_GRABS:
            for other_kid, rec in (chore.get("completions") or {}).items():
                if (
                    other_kid != kid_id
                    and isinstance(rec, dict)
                    and rec.get("cycle_key") == ckey
                    and rec.get("status") in (STATUS_COMPLETED, STATUS_WAITING_APPROVAL)
                ):
                    raise ValueError("Bonus chore has already been claimed this cycle")

        existing = (chore.get("completions") or {}).get(kid_id)
        if isinstance(existing, dict) and existing.get("cycle_key") == ckey:
            if existing.get("status") == STATUS_COMPLETED:
                return {"status": STATUS_COMPLETED, "already_completed": True}
            if existing.get("status") == STATUS_WAITING_APPROVAL and not by_parent:
                return {"status": STATUS_WAITING_APPROVAL, "already_waiting": True}

        eff_trust = resolve_effective_trust_mode(chore, kid, settings)
        undo_secs = max(0, int(settings.get("undo_window_seconds", DEFAULT_UNDO_WINDOW_SECONDS)))
        now_utc = dt_util.utcnow()
        undo_until = (now_utc + timedelta(seconds=undo_secs)).isoformat() if undo_secs > 0 else None

        if by_parent or eff_trust == TRUST_HONOR:
            awarded_pts = self._award_chore_points(chore, kid, settings)
            chore.setdefault("completions", {})[kid_id] = {
                "cycle_key": ckey,
                "status": STATUS_COMPLETED,
                "completed_at": now_utc.isoformat(),
                "approved_by": parent_name or ("Parent" if by_parent else "Honor System"),
                "points_awarded": awarded_pts,
                "undo_expires_at": undo_until,
            }
            self.storage.append_activity(
                {
                    "timestamp": now_utc.isoformat(),
                    "type": "chore_completed",
                    "kid_id": kid_id,
                    "kid_name": kid["name"],
                    "title": chore["name"],
                    "emoji": chore.get("emoji", "🧹"),
                    "points_delta": awarded_pts,
                }
            )
            self.hass.bus.async_fire(
                EVENT_CHORE_COMPLETED,
                {
                    "chore_id": chore_id,
                    "kid_id": kid_id,
                    "points_awarded": awarded_pts,
                    "by_parent": by_parent,
                },
            )
            await self._async_handle_post_completion_updates(kid_id, now_local)
            await self.storage.async_save()
            await self.async_evaluate_unlock_rules(now_local=now_local)
            async_dispatcher_send(self.hass, SIGNAL_KID_UPDATED, kid_id)
            async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
            return {"status": STATUS_COMPLETED, "points_awarded": awarded_pts}

        # Parent approval required
        chore.setdefault("completions", {})[kid_id] = {
            "cycle_key": ckey,
            "status": STATUS_WAITING_APPROVAL,
            "completed_at": now_utc.isoformat(),
            "approved_by": None,
            "points_awarded": 0,
            "undo_expires_at": undo_until,
        }
        self.storage.append_activity(
            {
                "timestamp": now_utc.isoformat(),
                "type": "chore_waiting_approval",
                "kid_id": kid_id,
                "kid_name": kid["name"],
                "title": chore["name"],
                "emoji": chore.get("emoji", "🧹"),
                "points_delta": 0,
            }
        )
        await self.storage.async_save()
        await self._async_send_approval_notification(chore, kid)
        async_dispatcher_send(self.hass, SIGNAL_KID_UPDATED, kid_id)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return {"status": STATUS_WAITING_APPROVAL, "points_awarded": 0}

    def _award_chore_points(
        self, chore: dict[str, Any], kid: dict[str, Any], settings: dict[str, Any]
    ) -> int:
        if not (settings.get("gamification_enabled", True) and settings.get("points_enabled", True)):
            return 0
        pts = max(0, int(chore.get("points", 0) or 0))
        if pts > 0:
            kid["points"] = int(kid.get("points", 0) or 0) + pts
            kid["lifetime_points"] = int(kid.get("lifetime_points", 0) or 0) + pts
        return pts

    async def _async_handle_post_completion_updates(
        self, kid_id: str, now_local: datetime
    ) -> None:
        """Check if kid just reached 100% of required chores today and update streak/bonus."""
        eval_after = self.get_snapshot_evaluation(now_local)
        kid = self.storage.get_kids().get(kid_id)
        kboard = eval_after["kids"].get(kid_id)
        if not kid or not kboard:
            return
        cycle_date_str = eval_after["cycle"]["cycle_date"]
        settings = self.storage.get_settings()

        if not kboard["is_all_done_today"]:
            return

        # Streak increment (idempotent per cycle_date_str)
        if (
            settings.get("gamification_enabled", True)
            and settings.get("streaks_enabled", True)
            and kid.get("last_streak_date") != cycle_date_str
        ):
            kid["prev_streak_date"] = kid.get("last_streak_date")
            kid["streak_prev_before_today"] = int(kid.get("streak_current", 0) or 0)
            kid["streak_current"] = kid["streak_prev_before_today"] + 1
            kid["streak_best"] = max(int(kid.get("streak_best", 0) or 0), kid["streak_current"])
            kid["last_streak_date"] = cycle_date_str

            milestones = settings.get("streak_milestones") or []
            if kid["streak_current"] in milestones:
                self.hass.bus.async_fire(
                    EVENT_STREAK_MILESTONE,
                    {"kid_id": kid_id, "kid_name": kid["name"], "streak": kid["streak_current"]},
                )

        # Daily all-done bonus points (idempotent per cycle_date_str)
        if (
            settings.get("gamification_enabled", True)
            and settings.get("points_enabled", True)
            and kid.get("daily_bonus_awarded_date") != cycle_date_str
        ):
            bonus_pts = max(0, int(settings.get("daily_all_done_bonus_points", 0) or 0))
            if bonus_pts > 0:
                kid["points"] = int(kid.get("points", 0) or 0) + bonus_pts
                kid["lifetime_points"] = int(kid.get("lifetime_points", 0) or 0) + bonus_pts
                kid["daily_bonus_awarded_date"] = cycle_date_str
                self.storage.append_activity(
                    {
                        "timestamp": dt_util.utcnow().isoformat(),
                        "type": "daily_bonus",
                        "kid_id": kid_id,
                        "kid_name": kid["name"],
                        "title": "All Chores Done Bonus!",
                        "emoji": "🎉",
                        "points_delta": bonus_pts,
                    }
                )

        self.hass.bus.async_fire(
            EVENT_KID_ALL_COMPLETED,
            {
                "kid_id": kid_id,
                "kid_name": kid["name"],
                "streak": kid.get("streak_current", 0),
                "cycle_date": cycle_date_str,
            },
        )

        # Optional TTS shoutout
        tts_entity = settings.get("tts_entity")
        if tts_entity and self.hass.states.get(tts_entity):
            try:
                await self.hass.services.async_call(
                    "tts",
                    "speak",
                    {
                        "entity_id": tts_entity,
                        "message": f"Awesome job {kid['name']}! All your chores are done!",
                    },
                    blocking=False,
                )
            except Exception as err:
                _LOGGER.debug("TTS shoutout skipped: %s", err)

    async def async_uncomplete_chore(
        self,
        chore_id: str,
        kid_id: str,
        now_local: datetime | None = None,
    ) -> dict[str, Any]:
        """Revert a chore completion (or pending approval) back to pending."""
        now_local = now_local or dt_util.now()
        chore = self.storage.get_chores().get(chore_id)
        kid = self.storage.get_kids().get(kid_id)
        if not chore or not kid:
            raise ValueError("Chore or kid not found")

        eval_before = self.get_snapshot_evaluation(now_local)
        cycle_date_str = eval_before["cycle"]["cycle_date"]
        week_key = eval_before["cycle"]["week_key"]
        ckey = get_chore_cycle_key(chore, cycle_date_str, week_key)

        comps = chore.get("completions") or {}
        rec = comps.get(kid_id)
        if not isinstance(rec, dict) or rec.get("cycle_key") != ckey:
            return {"status": STATUS_PENDING}

        awarded_pts = int(rec.get("points_awarded", 0) or 0)
        if awarded_pts > 0:
            kid["points"] = max(0, int(kid.get("points", 0) or 0) - awarded_pts)
            kid["lifetime_points"] = max(0, int(kid.get("lifetime_points", 0) or 0) - awarded_pts)

        del comps[kid_id]

        # Re-evaluate board to check if streak/daily bonus for today must be rolled back
        eval_after = self.get_snapshot_evaluation(now_local)
        kboard = eval_after["kids"].get(kid_id)
        if kboard and not kboard["is_all_done_today"]:
            if kid.get("last_streak_date") == cycle_date_str:
                kid["streak_current"] = int(kid.get("streak_prev_before_today", 0) or 0)
                kid["last_streak_date"] = kid.get("prev_streak_date")
            if kid.get("daily_bonus_awarded_date") == cycle_date_str:
                bonus_pts = max(
                    0, int(self.storage.get_settings().get("daily_all_done_bonus_points", 0) or 0)
                )
                if bonus_pts > 0:
                    kid["points"] = max(0, int(kid.get("points", 0) or 0) - bonus_pts)
                    kid["lifetime_points"] = max(
                        0, int(kid.get("lifetime_points", 0) or 0) - bonus_pts
                    )
                kid["daily_bonus_awarded_date"] = None

        await self.storage.async_save()
        await self.async_evaluate_unlock_rules(now_local=now_local)
        async_dispatcher_send(self.hass, SIGNAL_KID_UPDATED, kid_id)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return {"status": STATUS_PENDING}

    async def async_approve_chore(
        self,
        chore_id: str,
        kid_id: str,
        parent_name: str | None = None,
        now_local: datetime | None = None,
    ) -> dict[str, Any]:
        """Approve a chore waiting for parent approval."""
        now_local = now_local or dt_util.now()
        chore = self.storage.get_chores().get(chore_id)
        kid = self.storage.get_kids().get(kid_id)
        if not chore or not kid:
            raise ValueError("Chore or kid not found")
        res = await self.async_complete_chore(
            chore_id,
            kid_id,
            by_parent=True,
            parent_name=parent_name or "Parent",
            now_local=now_local,
        )
        self.hass.bus.async_fire(
            EVENT_CHORE_APPROVED,
            {"chore_id": chore_id, "kid_id": kid_id, "parent_name": parent_name or "Parent"},
        )
        return res

    async def async_reject_chore(
        self,
        chore_id: str,
        kid_id: str,
        note: str | None = None,
        now_local: datetime | None = None,
    ) -> dict[str, Any]:
        """Reject a waiting-approval chore back to pending ('Try Again')."""
        res = await self.async_uncomplete_chore(chore_id, kid_id, now_local=now_local)
        chore = self.storage.get_chores().get(chore_id)
        kid = self.storage.get_kids().get(kid_id)
        if chore and kid:
            self.storage.append_activity(
                {
                    "timestamp": dt_util.utcnow().isoformat(),
                    "type": "chore_rejected",
                    "kid_id": kid_id,
                    "kid_name": kid["name"],
                    "title": f"{chore['name']} (Try Again)",
                    "emoji": "🔄",
                    "points_delta": 0,
                }
            )
            await self.storage.async_save()
            self.hass.bus.async_fire(
                EVENT_CHORE_REJECTED,
                {"chore_id": chore_id, "kid_id": kid_id, "note": note},
            )
            async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return res

    async def async_approve_all_pending(
        self, kid_id: str | None = None, parent_name: str | None = None
    ) -> int:
        """Approve all pending chores (optionally filtered by kid_id)."""
        eval_data = self.get_snapshot_evaluation()
        count = 0
        for item in eval_data["pending_approvals"]:
            if kid_id and item.get("kid_id") != kid_id:
                continue
            if item["kind"] == "chore":
                await self.async_approve_chore(
                    item["chore_id"], item["kid_id"], parent_name=parent_name
                )
                count += 1
        return count

    async def async_rotate_chore(self, chore_id: str, steps: int = 1) -> dict[str, Any]:
        """Manually advance or rewind a rotating chore's turn."""
        chore = self.storage.get_chores().get(chore_id)
        if not chore:
            raise ValueError("Chore not found")
        chore["rotation_offset"] = int(chore.get("rotation_offset", 0) or 0) + int(steps)
        await self.storage.async_save()
        await self.async_evaluate_unlock_rules()
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return chore

    async def async_reset_chores(
        self, scope: str = "daily", kid_id: str | None = None
    ) -> int:
        """Manually reset daily or weekly/all chore completions."""
        cleared = 0
        for chore in self.storage.get_chores().values():
            is_weekly = chore.get("schedule_type") == SCHEDULE_WEEKLY
            if scope == "daily" and is_weekly:
                continue
            if scope == "weekly" and not is_weekly:
                continue
            comps = chore.get("completions") or {}
            if kid_id:
                if kid_id in comps:
                    del comps[kid_id]
                    cleared += 1
            else:
                if comps:
                    cleared += len(comps)
                    chore["completions"] = {}

        # Reset today's unlock latches when resetting chores
        for rule in self.storage.get_unlock_rules().values():
            if not kid_id or rule.get("kid_id") == kid_id or rule.get("scope") == UNLOCK_SCOPE_SHARED:
                rule["unlocked_for_cycle_date"] = None

        await self.storage.async_save()
        await self.async_evaluate_unlock_rules(is_cycle_reset=True)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return cleared

    # =========================================================================
    # MOBILE ACTIONABLE NOTIFICATIONS
    # =========================================================================

    async def _async_send_approval_notification(
        self, chore: dict[str, Any], kid: dict[str, Any]
    ) -> None:
        services = self.storage.get_settings().get("parent_notify_services") or []
        if not services:
            return
        token = secrets.token_hex(4)
        self._pending_action_tokens[token] = ("chore", chore["chore_id"], kid["kid_id"])
        approve_action = f"{ACTION_APPROVE_CHORE_PREFIX}{token}"
        reject_action = f"{ACTION_REJECT_CHORE_PREFIX}{token}"
        payload = {
            "title": f"Chore Approval: {kid['name']}",
            "message": f"{kid.get('avatar', '🧒')} {kid['name']} finished {chore.get('emoji', '🧹')} {chore['name']}.",
            "data": {
                "tag": f"passable_chore_{chore['chore_id']}_{kid['kid_id']}",
                "actions": [
                    {"action": approve_action, "title": "Approve"},
                    {"action": reject_action, "title": "Try Again"},
                ],
            },
        }
        await self._async_dispatch_notify(services, payload)

    async def _async_send_reward_notification(
        self, redemption: dict[str, Any]
    ) -> None:
        services = self.storage.get_settings().get("parent_notify_services") or []
        if not services:
            return
        token = secrets.token_hex(4)
        self._pending_action_tokens[token] = ("reward", redemption["redemption_id"], redemption["kid_id"])
        ok_action = f"{ACTION_APPROVE_REWARD_PREFIX}{token}"
        no_action = f"{ACTION_DENY_REWARD_PREFIX}{token}"
        payload = {
            "title": f"Reward Request: {redemption['kid_name']}",
            "message": f"{redemption['kid_name']} wants to redeem {redemption.get('emoji', '🎁')} {redemption['reward_name']} ({redemption['cost']} ⭐).",
            "data": {
                "tag": f"passable_reward_{redemption['redemption_id']}",
                "actions": [
                    {"action": ok_action, "title": "Approve"},
                    {"action": no_action, "title": "Refund"},
                ],
            },
        }
        await self._async_dispatch_notify(services, payload)

    async def _async_dispatch_notify(
        self, services: list[str], payload: dict[str, Any]
    ) -> None:
        for svc in services:
            if not svc or "." not in svc:
                continue
            domain, service_name = svc.split(".", 1)
            try:
                await self.hass.services.async_call(
                    domain, service_name, payload, blocking=False
                )
            except Exception as err:
                _LOGGER.debug("Notify service %s failed: %s", svc, err)

    @callback
    def _async_handle_mobile_notification_action(self, event: Event) -> None:
        action = str((event.data or {}).get("action") or "")
        if not action:
            return
        if action.startswith(ACTION_APPROVE_CHORE_PREFIX):
            token = action[len(ACTION_APPROVE_CHORE_PREFIX):]
            meta = self._pending_action_tokens.pop(token, None)
            if meta and meta[0] == "chore":
                self.hass.async_create_task(
                    self.async_approve_chore(meta[1], meta[2], parent_name="Mobile Push")
                )
        elif action.startswith(ACTION_REJECT_CHORE_PREFIX):
            token = action[len(ACTION_REJECT_CHORE_PREFIX):]
            meta = self._pending_action_tokens.pop(token, None)
            if meta and meta[0] == "chore":
                self.hass.async_create_task(self.async_reject_chore(meta[1], meta[2]))
        elif action.startswith(ACTION_APPROVE_REWARD_PREFIX):
            token = action[len(ACTION_APPROVE_REWARD_PREFIX):]
            meta = self._pending_action_tokens.pop(token, None)
            if meta and meta[0] == "reward":
                self.hass.async_create_task(
                    self.async_resolve_redemption(meta[1], approved=True, resolved_by="Mobile Push")
                )
        elif action.startswith(ACTION_DENY_REWARD_PREFIX):
            token = action[len(ACTION_DENY_REWARD_PREFIX):]
            meta = self._pending_action_tokens.pop(token, None)
            if meta and meta[0] == "reward":
                self.hass.async_create_task(
                    self.async_resolve_redemption(meta[1], approved=False, resolved_by="Mobile Push")
                )

    # =========================================================================
    # REWARDS & POINTS BANK
    # =========================================================================

    async def async_adjust_points(
        self, kid_id: str, delta: int, reason: str = "Parent Adjustment"
    ) -> int:
        """Add or deduct star points for a kid."""
        kid = self.storage.get_kids().get(kid_id)
        if not kid:
            raise ValueError("Kid not found")
        current = int(kid.get("points", 0) or 0)
        next_val = max(0, current + int(delta))
        kid["points"] = next_val
        if delta > 0:
            kid["lifetime_points"] = int(kid.get("lifetime_points", 0) or 0) + int(delta)
        self.storage.append_activity(
            {
                "timestamp": dt_util.utcnow().isoformat(),
                "type": "points_adjusted",
                "kid_id": kid_id,
                "kid_name": kid["name"],
                "title": reason,
                "emoji": "⭐",
                "points_delta": int(delta),
            }
        )
        await self.storage.async_save()
        async_dispatcher_send(self.hass, SIGNAL_KID_UPDATED, kid_id)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return next_val

    async def async_redeem_reward(
        self, reward_id: str, kid_id: str
    ) -> dict[str, Any]:
        """Redeem a reward for a kid (auto-executes smart rewards or queues parent fulfillment)."""
        reward = self.storage.get_rewards().get(reward_id)
        kid = self.storage.get_kids().get(kid_id)
        if not reward or not kid:
            raise ValueError("Reward or kid not found")
        if not reward.get("enabled", True):
            raise ValueError("Reward is currently disabled")

        cost = max(1, int(reward.get("cost", 25) or 25))
        balance = int(kid.get("points", 0) or 0)
        if balance < cost:
            raise ValueError(f"{kid['name']} needs {cost} stars (has {balance})")

        kid["points"] = balance - cost
        auto_approve = bool(
            reward.get("auto_approve", reward.get("reward_type") == REWARD_SMART_ACTION)
        )
        now_iso = dt_util.utcnow().isoformat()
        redemption = {
            "redemption_id": f"rdm_{secrets.token_hex(4)}",
            "reward_id": reward_id,
            "reward_name": reward["name"],
            "emoji": reward.get("emoji", "🎁"),
            "kid_id": kid_id,
            "kid_name": kid["name"],
            "cost": cost,
            "status": REDEMPTION_APPROVED if auto_approve else REDEMPTION_PENDING,
            "requested_at": now_iso,
            "resolved_at": now_iso if auto_approve else None,
            "resolved_by": "Auto" if auto_approve else None,
        }
        self.storage.append_redemption(redemption)

        if auto_approve:
            await self._async_execute_reward_action(reward, kid)
            self.storage.append_activity(
                {
                    "timestamp": now_iso,
                    "type": "reward_redeemed",
                    "kid_id": kid_id,
                    "kid_name": kid["name"],
                    "title": f"Redeemed: {reward['name']}",
                    "emoji": reward.get("emoji", "🎁"),
                    "points_delta": -cost,
                }
            )
            self.hass.bus.async_fire(
                EVENT_REWARD_REDEEMED,
                {"reward_id": reward_id, "kid_id": kid_id, "cost": cost, "auto_approved": True},
            )
        else:
            self.storage.append_activity(
                {
                    "timestamp": now_iso,
                    "type": "reward_requested",
                    "kid_id": kid_id,
                    "kid_name": kid["name"],
                    "title": f"Requested: {reward['name']}",
                    "emoji": reward.get("emoji", "🎁"),
                    "points_delta": -cost,
                }
            )
            await self._async_send_reward_notification(redemption)

        await self.storage.async_save()
        async_dispatcher_send(self.hass, SIGNAL_KID_UPDATED, kid_id)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return redemption

    async def async_resolve_redemption(
        self,
        redemption_id: str,
        approved: bool,
        resolved_by: str = "Parent",
    ) -> dict[str, Any]:
        """Approve or deny (with full star refund) a pending reward redemption."""
        target = None
        for rdm in self.storage.get_redemptions():
            if rdm.get("redemption_id") == redemption_id:
                target = rdm
                break
        if not target:
            raise ValueError("Redemption request not found")
        if target.get("status") != REDEMPTION_PENDING:
            return target

        kid = self.storage.get_kids().get(target["kid_id"])
        reward = self.storage.get_rewards().get(target["reward_id"])
        now_iso = dt_util.utcnow().isoformat()
        target["resolved_at"] = now_iso
        target["resolved_by"] = resolved_by

        if approved:
            target["status"] = REDEMPTION_APPROVED
            if reward and kid:
                await self._async_execute_reward_action(reward, kid)
            self.storage.append_activity(
                {
                    "timestamp": now_iso,
                    "type": "reward_approved",
                    "kid_id": target["kid_id"],
                    "kid_name": target.get("kid_name", target["kid_id"]),
                    "title": f"Approved: {target['reward_name']}",
                    "emoji": target.get("emoji", "🎁"),
                    "points_delta": 0,
                }
            )
            self.hass.bus.async_fire(
                EVENT_REWARD_REDEEMED,
                {
                    "reward_id": target["reward_id"],
                    "kid_id": target["kid_id"],
                    "cost": target["cost"],
                    "auto_approved": False,
                },
            )
        else:
            target["status"] = REDEMPTION_DENIED
            if kid:
                kid["points"] = int(kid.get("points", 0) or 0) + int(target.get("cost", 0) or 0)
            self.storage.append_activity(
                {
                    "timestamp": now_iso,
                    "type": "reward_denied",
                    "kid_id": target["kid_id"],
                    "kid_name": target.get("kid_name", target["kid_id"]),
                    "title": f"Refunded: {target['reward_name']}",
                    "emoji": "↩️",
                    "points_delta": int(target.get("cost", 0) or 0),
                }
            )

        await self.storage.async_save()
        if kid:
            async_dispatcher_send(self.hass, SIGNAL_KID_UPDATED, kid["kid_id"])
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return target

    async def _async_execute_reward_action(
        self, reward: dict[str, Any], kid: dict[str, Any]
    ) -> None:
        """Execute automated smart-home action attached to a reward."""
        if reward.get("reward_type") != REWARD_SMART_ACTION:
            return
        sa = reward.get("smart_action") or {}
        kind = sa.get("action_kind")
        try:
            if kind == SMART_ACTION_SCREEN_TIME_TIMER:
                dev_id = sa.get("device_id") or "all"
                mins = max(1, int(sa.get("duration_minutes", 20) or 20))
                await self.hass.services.async_call(
                    "passable_smart_screen_time_engine",
                    "start_timer",
                    {
                        "device_id": dev_id,
                        "mode": "unlock",
                        "duration": mins,
                        "unit": "minutes",
                        "power_on": False,
                    },
                    blocking=False,
                )
            elif kind == SMART_ACTION_SCREEN_TIME_BONUS:
                dev_id = sa.get("device_id") or "all"
                mins = max(1, int(sa.get("duration_minutes", 15) or 15))
                await self.hass.services.async_call(
                    "passable_smart_screen_time_engine",
                    "adjust_bonus_time",
                    {"device_id": dev_id, "delta_minutes": mins, "reset": False},
                    blocking=False,
                )
            elif kind == SMART_ACTION_NINTENDO_BONUS:
                ent = sa.get("entity_id")
                mins = max(1, int(sa.get("duration_minutes", 15) or 15))
                if ent:
                    st = self.hass.states.get(ent)
                    try:
                        cur = float(st.state) if st and st.state not in ("unknown", "unavailable") else 0.0
                    except (TypeError, ValueError):
                        cur = 0.0
                    await self.hass.services.async_call(
                        "number",
                        "set_value",
                        {"entity_id": ent, "value": cur + mins},
                        blocking=False,
                    )
            elif kind == SMART_ACTION_HA_SERVICE:
                svc = str(sa.get("service") or "").strip()
                if "." in svc:
                    dom, sname = svc.split(".", 1)
                    sdata = dict(sa.get("service_data") or {})
                    if sa.get("entity_id") and "entity_id" not in sdata:
                        sdata["entity_id"] = sa["entity_id"]
                    await self.hass.services.async_call(dom, sname, sdata, blocking=False)
        except Exception as err:
            _LOGGER.warning(
                "Smart reward execution failed for %s (%s): %s",
                reward.get("name"),
                kid.get("name"),
                err,
            )

    # =========================================================================
    # DEVICE UNLOCK INTEGRATION (PASSABLE SCREEN TIME / SWITCHES / NINTENDO)
    # =========================================================================

    def _is_screen_time_schedule_blocking(self, dev_id: str) -> bool:
        """Check whether Passable Smart Screen Time Engine is currently holding device in downtime or restriction."""
        st_data = self.hass.data.get("passable_smart_screen_time_engine", {})
        for key, st_engine in st_data.items():
            if key in ("frontend_registered", "websocket_registered"):
                continue
            storage = getattr(st_engine, "storage", None)
            if not storage:
                continue
            dev = storage.get_device(dev_id) if hasattr(storage, "get_device") else None
            if dev and dev.get("locked"):
                reason = dev.get("locked_reason")
                if reason in ("schedule", "restriction", "rest_of_day"):
                    return True
            if getattr(st_engine, "_active_restrictions", None):
                return True
        return False

    async def async_evaluate_unlock_rules(
        self,
        is_cycle_reset: bool = False,
        now_local: datetime | None = None,
    ) -> None:
        """Evaluate and apply all enabled personal/shared device unlock rules."""
        async with self._eval_lock:
            now_local = now_local or dt_util.now()
            eval_data = self.get_snapshot_evaluation(now_local)
            cycle_date_str = eval_data["cycle"]["cycle_date"]
            kid_boards = eval_data["kids"]
            changed = False

            for rule_id, rule in self.storage.get_unlock_rules().items():
                satisfied, reason = evaluate_unlock_rule_satisfied(rule, kid_boards)
                if satisfied is None:
                    continue

                target_mode = rule.get("target_mode", TARGET_MODE_SCREEN_TIME)
                st_dev_id = rule.get("screen_time_device_id")
                target_entity = rule.get("target_entity")

                if satisfied:
                    if rule.get("unlocked_for_cycle_date") == cycle_date_str:
                        continue
                    if (
                        rule.get("respect_screen_time_schedules", True)
                        and target_mode == TARGET_MODE_SCREEN_TIME
                        and st_dev_id
                        and self._is_screen_time_schedule_blocking(st_dev_id)
                    ):
                        _LOGGER.debug(
                            "Unlock rule %s satisfied (%s) but waiting for Screen Time downtime window on %s",
                            rule_id,
                            reason,
                            st_dev_id,
                        )
                        continue

                    ok = await self._async_actuate_unlock(rule, locked=False)
                    if ok:
                        rule["unlocked_for_cycle_date"] = cycle_date_str
                        rule["last_applied_locked"] = False
                        changed = True
                        self.hass.bus.async_fire(
                            EVENT_DEVICE_UNLOCKED,
                            {
                                "rule_id": rule_id,
                                "name": rule.get("name"),
                                "reason": reason,
                            },
                        )
                else:
                    should_lock = (
                        (is_cycle_reset and rule.get("lock_on_reset", True))
                        or (
                            rule.get("last_applied_locked") is None
                            and rule.get("lock_on_reset", True)
                        )
                        or (
                            rule.get("unlocked_for_cycle_date") == cycle_date_str
                            and rule.get("re_lock_if_uncompleted", True)
                        )
                    )
                    if should_lock:
                        ok = await self._async_actuate_unlock(rule, locked=True)
                        if ok:
                            rule["unlocked_for_cycle_date"] = None
                            rule["last_applied_locked"] = True
                            changed = True

            if changed:
                await self.storage.async_save()

    async def _async_actuate_unlock(self, rule: dict[str, Any], locked: bool) -> bool:
        """Execute hardware/integration lock or unlock for a rule."""
        mode = rule.get("target_mode", TARGET_MODE_SCREEN_TIME)
        st_dev_id = rule.get("screen_time_device_id")
        target_entity = rule.get("target_entity")

        try:
            if mode == TARGET_MODE_SCREEN_TIME:
                if not st_dev_id:
                    return False
                if not self.hass.services.has_service("passable_smart_screen_time_engine", "set_lockout"):
                    _LOGGER.debug("passable_smart_screen_time_engine.set_lockout service not available")
                    return False
                await self.hass.services.async_call(
                    "passable_smart_screen_time_engine",
                    "set_lockout",
                    {
                        "device_id": st_dev_id,
                        "locked": bool(locked),
                        "power_on": False,
                        "rest_of_day": False,
                    },
                    blocking=False,
                )
                return True

            if mode == TARGET_MODE_LOCKOUT_SWITCH:
                if not target_entity:
                    return False
                await self.hass.services.async_call(
                    "switch",
                    "turn_on" if locked else "turn_off",
                    {"entity_id": target_entity},
                    blocking=False,
                )
                return True

            if mode == TARGET_MODE_POWER_SWITCH:
                if not target_entity:
                    return False
                domain = target_entity.split(".", 1)[0] if "." in target_entity else "switch"
                svc_domain = domain if domain in ("switch", "media_player", "homeassistant") else "homeassistant"
                await self.hass.services.async_call(
                    svc_domain,
                    "turn_off" if locked else "turn_on",
                    {"entity_id": target_entity},
                    blocking=False,
                )
                return True

            if mode == TARGET_MODE_NINTENDO:
                if not target_entity:
                    return False
                val = 0 if locked else max(5, int(rule.get("nintendo_bonus_minutes", 60) or 60))
                await self.hass.services.async_call(
                    "number",
                    "set_value",
                    {"entity_id": target_entity, "value": val},
                    blocking=False,
                )
                return True
        except Exception as err:
            _LOGGER.warning("Failed to actuate unlock rule %s: %s", rule.get("rule_id"), err)
        return False

    # =========================================================================
    # CRUD & STARTER TEMPLATES
    # =========================================================================

    async def async_save_kid(self, payload: dict[str, Any]) -> dict[str, Any]:
        kids = self.storage.get_kids()
        raw_id = str(payload.get("kid_id") or "").strip()
        is_new = not raw_id or raw_id not in kids
        kid_id = raw_id if raw_id else slugify_id(payload.get("name", "kid"), prefix="kid")
        if is_new and kid_id in kids:
            kid_id = f"{kid_id}_{secrets.token_hex(2)}"

        existing = kids.get(kid_id, {})
        merged = {**existing, **payload, "kid_id": kid_id}
        if "order" not in merged:
            merged["order"] = len(kids)
        kid = normalize_kid(kid_id, merged, default_order=len(kids))
        kids[kid_id] = kid
        await self.storage.async_save()
        if is_new:
            async_dispatcher_send(self.hass, SIGNAL_KID_ADDED, kid_id)
        else:
            async_dispatcher_send(self.hass, SIGNAL_KID_UPDATED, kid_id)
        async_dispatcher_send(self.hass, SIGNAL_STORAGE_UPDATED)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return kid

    async def async_delete_kid(self, kid_id: str) -> None:
        kids = self.storage.get_kids()
        if kid_id in kids:
            del kids[kid_id]
        for chore in self.storage.get_chores().values():
            if kid_id in (chore.get("assigned_kids") or []):
                chore["assigned_kids"] = [k for k in chore["assigned_kids"] if k != kid_id]
            if isinstance(chore.get("completions"), dict) and kid_id in chore["completions"]:
                del chore["completions"][kid_id]
        for rule_id, rule in list(self.storage.get_unlock_rules().items()):
            if rule.get("kid_id") == kid_id:
                del self.storage.get_unlock_rules()[rule_id]
        await self.storage.async_save()
        await self.async_evaluate_unlock_rules()
        async_dispatcher_send(self.hass, SIGNAL_KID_REMOVED, kid_id)
        async_dispatcher_send(self.hass, SIGNAL_STORAGE_UPDATED)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)

    async def async_reorder_kids(self, kid_ids: list[str]) -> None:
        kids = self.storage.get_kids()
        for idx, kid_id in enumerate(kid_ids):
            if kid_id in kids:
                kids[kid_id]["order"] = idx
        await self.storage.async_save()
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)

    async def async_save_chore(self, payload: dict[str, Any]) -> dict[str, Any]:
        chores = self.storage.get_chores()
        raw_id = str(payload.get("chore_id") or "").strip()
        is_new = not raw_id or raw_id not in chores
        chore_id = raw_id if raw_id else slugify_id(payload.get("name", "chore"), prefix="chore")
        if is_new and chore_id in chores:
            chore_id = f"{chore_id}_{secrets.token_hex(2)}"

        eval_data = self.get_snapshot_evaluation()
        week_key = eval_data["cycle"]["week_key"]
        existing = chores.get(chore_id, {})
        merged = {**existing, **payload, "chore_id": chore_id}
        if "order" not in merged:
            merged["order"] = len(chores)
        chore = normalize_chore(
            chore_id, merged, default_order=len(chores), default_week_key=week_key
        )
        chores[chore_id] = chore
        await self.storage.async_save()
        await self.async_evaluate_unlock_rules()
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return chore

    async def async_delete_chore(self, chore_id: str) -> None:
        chores = self.storage.get_chores()
        if chore_id in chores:
            del chores[chore_id]
            await self.storage.async_save()
            await self.async_evaluate_unlock_rules()
            async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)

    async def async_save_reward(self, payload: dict[str, Any]) -> dict[str, Any]:
        rewards = self.storage.get_rewards()
        raw_id = str(payload.get("reward_id") or "").strip()
        is_new = not raw_id or raw_id not in rewards
        reward_id = raw_id if raw_id else slugify_id(payload.get("name", "reward"), prefix="reward")
        if is_new and reward_id in rewards:
            reward_id = f"{reward_id}_{secrets.token_hex(2)}"
        existing = rewards.get(reward_id, {})
        merged = {**existing, **payload, "reward_id": reward_id}
        if "order" not in merged:
            merged["order"] = len(rewards)
        reward = normalize_reward(reward_id, merged, default_order=len(rewards))
        rewards[reward_id] = reward
        await self.storage.async_save()
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return reward

    async def async_delete_reward(self, reward_id: str) -> None:
        rewards = self.storage.get_rewards()
        if reward_id in rewards:
            del rewards[reward_id]
            await self.storage.async_save()
            async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)

    async def async_save_unlock_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        rules = self.storage.get_unlock_rules()
        raw_id = str(payload.get("rule_id") or "").strip()
        is_new = not raw_id or raw_id not in rules
        rule_id = raw_id if raw_id else slugify_id(payload.get("name", "unlock_rule"), prefix="rule")
        if is_new and rule_id in rules:
            rule_id = f"{rule_id}_{secrets.token_hex(2)}"
        existing = rules.get(rule_id, {})
        merged = {**existing, **payload, "rule_id": rule_id}
        rule = normalize_unlock_rule(rule_id, merged)
        binding_keys = (
            "scope",
            "kid_id",
            "shared_mode",
            "target_mode",
            "screen_time_device_id",
            "target_entity",
        )
        if is_new or any(existing.get(k) != rule.get(k) for k in binding_keys):
            rule["last_applied_locked"] = None
            rule["unlocked_for_cycle_date"] = None
        rules[rule_id] = rule
        await self.storage.async_save()
        await self.async_evaluate_unlock_rules()
        async_dispatcher_send(self.hass, SIGNAL_STORAGE_UPDATED)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return rule

    async def async_delete_unlock_rule(self, rule_id: str) -> None:
        rules = self.storage.get_unlock_rules()
        if rule_id in rules:
            del rules[rule_id]
            await self.storage.async_save()
            async_dispatcher_send(self.hass, SIGNAL_STORAGE_UPDATED)
            async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)

    async def async_save_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        settings = self.storage.get_settings()
        reset_time_changed = (
            "daily_reset_time" in updates
            and normalize_hhmm(updates["daily_reset_time"], settings["daily_reset_time"])
            != settings["daily_reset_time"]
        )
        calendars_changed = "no_school_calendars" in updates

        for k, v in updates.items():
            if k == "daily_reset_time":
                settings[k] = normalize_hhmm(v, settings.get(k, DEFAULT_DAILY_RESET_TIME))
            elif k in ("weekly_reset_day", "weekly_due_day"):
                settings[k] = normalize_weekday(v, settings.get(k, DEFAULT_WEEKLY_RESET_DAY))
            elif k == "toggle_manual_no_school":
                cur_cycle = compute_cycle_date(
                    dt_util.now(), settings.get("daily_reset_time", DEFAULT_DAILY_RESET_TIME)
                ).isoformat()
                settings["manual_no_school_date"] = cur_cycle if v else None
            elif k in settings:
                settings[k] = v

        if reset_time_changed:
            self._schedule_daily_reset_listener()
        if calendars_changed:
            await self.async_refresh_calendar_holidays()

        await self.storage.async_save()
        await self.async_check_cycle_rollover(evaluate_unlocks=True)
        async_dispatcher_send(self.hass, SIGNAL_STORAGE_UPDATED)
        async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return settings

    async def async_seed_starter_templates(self) -> dict[str, int]:
        """Seed sample chores and rewards only if requested (never overwrites existing items)."""
        kids = self.storage.get_kids()
        chores = self.storage.get_chores()
        rewards = self.storage.get_rewards()
        added_chores = 0
        added_rewards = 0
        enabled_kids = [k["kid_id"] for k in kids.values() if k.get("enabled", True)]

        starter_chores = [
            ("make_bed", "Make Bed", "🛏️", TIER_REQUIRED, SCHEDULE_DAILY, ASSIGN_EACH, 5),
            ("brush_teeth", "Brush Teeth", "🪥", TIER_REQUIRED, SCHEDULE_DAILY, ASSIGN_EACH, 5),
            ("pack_backpack", "Pack Backpack", "🎒", TIER_REQUIRED, SCHEDULE_SCHOOL_DAYS, ASSIGN_EACH, 5),
            ("clean_room", "Clean Room", "🧹", TIER_REQUIRED, SCHEDULE_WEEKLY, ASSIGN_EACH, 15),
            ("feed_dog", "Feed & Water Pet", "🐕", TIER_REQUIRED, SCHEDULE_DAILY, ASSIGN_ROTATE_WEEKLY, 10),
            ("vacuum_playroom", "Vacuum Playroom", "🫧", TIER_BONUS, SCHEDULE_DAILY, ASSIGN_UP_FOR_GRABS, 20),
        ]
        eval_data = self.get_snapshot_evaluation()
        week_key = eval_data["cycle"]["week_key"]

        for idx, (cid, name, emoji, tier, sched, assign, pts) in enumerate(starter_chores):
            if cid not in chores:
                chores[cid] = normalize_chore(
                    cid,
                    {
                        "name": name,
                        "emoji": emoji,
                        "tier": tier,
                        "schedule_type": sched,
                        "assignment_mode": assign,
                        "assigned_kids": list(enabled_kids),
                        "points": pts,
                        "order": idx,
                    },
                    default_order=idx,
                    default_week_key=week_key,
                )
                added_chores += 1

        starter_rewards = [
            {
                "reward_id": "bonus_tv_20m",
                "name": "+20m Bonus TV Time",
                "emoji": "📺",
                "cost": 50,
                "reward_type": REWARD_SMART_ACTION,
                "auto_approve": True,
                "smart_action": {
                    "action_kind": SMART_ACTION_SCREEN_TIME_TIMER,
                    "device_id": "all",
                    "duration_minutes": 20,
                },
            },
            {
                "reward_id": "ice_cream_run",
                "name": "Ice Cream Run",
                "emoji": "🍦",
                "cost": 100,
                "reward_type": REWARD_PARENT_FULFILLED,
                "auto_approve": False,
            },
            {
                "reward_id": "pick_movie_night",
                "name": "Pick Family Movie",
                "emoji": "🎬",
                "cost": 75,
                "reward_type": REWARD_PARENT_FULFILLED,
                "auto_approve": False,
            },
        ]
        for idx, rdata in enumerate(starter_rewards):
            rid = rdata["reward_id"]
            if rid not in rewards:
                rewards[rid] = normalize_reward(rid, rdata, default_order=idx)
                added_rewards += 1

        if added_chores or added_rewards:
            await self.storage.async_save()
            async_dispatcher_send(self.hass, SIGNAL_ENGINE_UPDATED)
        return {"chores_added": added_chores, "rewards_added": added_rewards}
