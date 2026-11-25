"""WebSocket API handlers for Passable Smart Chores Engine."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event
import voluptuous as vol

from .const import (
    DOMAIN,
    SIGNAL_ENGINE_UPDATED,
    SIGNAL_KID_ADDED,
    SIGNAL_KID_REMOVED,
    SIGNAL_KID_UPDATED,
    SIGNAL_STORAGE_UPDATED,
    TARGET_MODE_SCREEN_TIME,
    VERSION,
)
from .engine import PassableChoresEngine, evaluate_unlock_rule_satisfied

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket commands for frontend card interaction."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("websocket_registered"):
        return

    for cmd in (
        ws_get_data,
        ws_subscribe,
        ws_save_kid,
        ws_delete_kid,
        ws_reorder_kids,
        ws_save_chore,
        ws_delete_chore,
        ws_complete_chore,
        ws_uncomplete_chore,
        ws_approve_chore,
        ws_reject_chore,
        ws_approve_all_pending,
        ws_rotate_chore,
        ws_save_reward,
        ws_delete_reward,
        ws_redeem_reward,
        ws_resolve_redemption,
        ws_adjust_points,
        ws_save_unlock_rule,
        ws_delete_unlock_rule,
        ws_save_settings,
        ws_reset_chores,
        ws_seed_sample_data,
        ws_verify_pin,
        ws_save_security_settings,
    ):
        websocket_api.async_register_command(hass, cmd)

    domain_data["websocket_registered"] = True


def _get_engine(hass: HomeAssistant) -> PassableChoresEngine | None:
    entries = hass.data.get(DOMAIN, {})
    for k, v in entries.items():
        if k not in ("frontend_registered", "websocket_registered"):
            return v
    return None


def _build_candidates(hass: HomeAssistant) -> dict[str, Any]:
    """Discover Screen Time devices, switches, calendars, notify services, Nintendo numbers, and TTS."""
    screen_time_devices: list[dict[str, Any]] = []
    st_data = hass.data.get("passable_smart_screen_time_engine", {})
    for k, st_engine in st_data.items():
        if k in ("frontend_registered", "websocket_registered"):
            continue
        storage = getattr(st_engine, "storage", None)
        if storage and hasattr(storage, "get_all_devices"):
            for dev_id, dev in storage.get_all_devices().items():
                screen_time_devices.append(
                    {
                        "device_id": dev_id,
                        "name": dev.get("name") or dev_id,
                        "icon": dev.get("icon") or "mdi:television",
                        "device_category": dev.get("device_category", "tv"),
                        "locked": bool(dev.get("locked", False)),
                    }
                )
    screen_time_devices.sort(key=lambda d: d["name"].lower())

    switches: list[dict[str, str]] = []
    calendars: list[dict[str, str]] = []
    nintendo_numbers: list[dict[str, str]] = []
    tts_entities: list[dict[str, str]] = []

    for state_obj in hass.states.async_all():
        eid = state_obj.entity_id
        domain = eid.split(".", 1)[0]
        fname = state_obj.attributes.get("friendly_name") or eid
        if domain in ("switch", "media_player"):
            switches.append({"entity_id": eid, "name": fname, "domain": domain})
        elif domain == "calendar":
            calendars.append({"entity_id": eid, "name": fname})
        elif domain == "number" and ("nintendo" in eid or "screentime" in eid or "screen_time" in eid):
            nintendo_numbers.append({"entity_id": eid, "name": fname})
        elif domain == "tts":
            tts_entities.append({"entity_id": eid, "name": fname})

    notify_services: list[str] = []
    all_services = hass.services.async_services()
    for svc_name in sorted((all_services.get("notify") or {}).keys()):
        if svc_name not in ("notify", "persistent_notification"):
            notify_services.append(f"notify.{svc_name}")

    switches.sort(key=lambda x: x["name"].lower())
    calendars.sort(key=lambda x: x["name"].lower())
    nintendo_numbers.sort(key=lambda x: x["name"].lower())

    return {
        "screen_time_devices": screen_time_devices,
        "switches": switches,
        "calendars": calendars,
        "nintendo_numbers": nintendo_numbers,
        "notify_services": notify_services,
        "tts_entities": tts_entities,
    }


def _resolve_rule_live_locked(hass: HomeAssistant, rule: dict[str, Any]) -> bool | None:
    mode = rule.get("target_mode", TARGET_MODE_SCREEN_TIME)
    if mode == TARGET_MODE_SCREEN_TIME:
        dev_id = rule.get("screen_time_device_id")
        if not dev_id:
            return None
        st_data = hass.data.get("passable_smart_screen_time_engine", {})
        for k, st_engine in st_data.items():
            if k in ("frontend_registered", "websocket_registered"):
                continue
            storage = getattr(st_engine, "storage", None)
            if storage:
                if dev_id == "all" and hasattr(storage, "get_all_devices"):
                    devs = list((storage.get_all_devices() or {}).values())
                    if devs:
                        return all(bool(d.get("locked", False)) for d in devs)
                elif hasattr(storage, "get_device"):
                    dev = storage.get_device(dev_id)
                    if dev:
                        return bool(dev.get("locked", False))
        return rule.get("last_applied_locked")
    target = rule.get("target_entity")
    if not target:
        return None
    st = hass.states.get(target)
    if not st:
        return None
    if mode == "lockout_switch":
        return st.state == "on"
    if mode == "power_switch":
        return st.state in ("off", "standby")
    if mode == "nintendo_switch":
        try:
            return float(st.state) <= 0
        except (TypeError, ValueError):
            return None
    return None


def build_engine_snapshot(
    hass: HomeAssistant, engine: PassableChoresEngine
) -> dict[str, Any]:
    """Build JSON-serializable state snapshot for passable-chores-card."""
    eval_data = engine.get_snapshot_evaluation()
    rewards = sorted(
        engine.storage.get_rewards().values(),
        key=lambda r: (int(r.get("order", 0)), r.get("name", "").lower()),
    )
    chores = sorted(
        engine.storage.get_chores().values(),
        key=lambda c: (int(c.get("order", 0)), c.get("name", "").lower()),
    )
    unlock_rules = []
    for rule in engine.storage.get_unlock_rules().values():
        rcopy = dict(rule)
        sat, reason = evaluate_unlock_rule_satisfied(rule, eval_data["kids"])
        rcopy["is_currently_locked"] = _resolve_rule_live_locked(hass, rule)
        rcopy["is_satisfied"] = sat
        rcopy["status_reason"] = reason
        unlock_rules.append(rcopy)

    return {
        "version": VERSION,
        "cycle": eval_data["cycle"],
        "settings": dict(engine.storage.get_settings()),
        "security": engine.storage.get_public_security(),
        "kids": list(eval_data["kids"].values()),
        "chores": chores,
        "bonus_chores": eval_data["bonus_chores"],
        "pending_approvals": eval_data["pending_approvals"],
        "rewards": rewards,
        "redemptions": list(engine.storage.get_redemptions()),
        "unlock_rules": unlock_rules,
        "activity_log": list(engine.storage.get_activity_log()),
        "candidates": _build_candidates(hass),
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/get_data"})
@websocket_api.async_response
async def ws_get_data(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Passable Chores Engine is not loaded.")
        return
    connection.send_result(msg["id"], build_engine_snapshot(hass, engine))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Subscribe to real-time debounced chore engine state snapshots."""
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Passable Chores Engine is not loaded.")
        return

    pending_handle: asyncio.TimerHandle | None = None
    unsubs: list[Callable[[], None]] = []
    state_unsub: Callable[[], None] | None = None

    @callback
    def _push_now() -> None:
        nonlocal pending_handle
        pending_handle = None
        try:
            connection.send_message(
                websocket_api.event_message(msg["id"], build_engine_snapshot(hass, engine))
            )
        except Exception as err:
            _LOGGER.debug("Chores WS snapshot push failed: %s", err)

    @callback
    def _schedule_push(*_args: Any) -> None:
        nonlocal pending_handle
        if pending_handle is not None:
            return
        pending_handle = hass.loop.call_later(0.15, _push_now)

    @callback
    def _rebuild_state_listener(*_args: Any) -> None:
        nonlocal state_unsub
        if state_unsub is not None:
            state_unsub()
            state_unsub = None
        watched: set[str] = set()
        for rule in engine.storage.get_unlock_rules().values():
            if rule.get("target_entity"):
                watched.add(rule["target_entity"])
            if rule.get("screen_time_device_id"):
                watched.add(f"switch.{rule['screen_time_device_id']}_lockout")
        for cal in engine.storage.get_settings().get("no_school_calendars") or []:
            watched.add(cal)
        if watched:
            state_unsub = async_track_state_change_event(hass, list(watched), _schedule_push)

    for sig in (SIGNAL_ENGINE_UPDATED, SIGNAL_KID_UPDATED, SIGNAL_KID_ADDED, SIGNAL_KID_REMOVED):
        unsubs.append(async_dispatcher_connect(hass, sig, _schedule_push))

    @callback
    def _on_storage_updated(*_args: Any) -> None:
        _rebuild_state_listener()
        _schedule_push()

    unsubs.append(async_dispatcher_connect(hass, SIGNAL_STORAGE_UPDATED, _on_storage_updated))
    _rebuild_state_listener()

    @callback
    def _cleanup() -> None:
        nonlocal pending_handle, state_unsub
        if pending_handle is not None:
            pending_handle.cancel()
            pending_handle = None
        if state_unsub is not None:
            state_unsub()
            state_unsub = None
        for unsub in unsubs:
            try:
                unsub()
            except Exception:
                pass
        unsubs.clear()

    connection.subscriptions[msg["id"]] = _cleanup
    connection.send_result(msg["id"])
    connection.send_message(
        websocket_api.event_message(msg["id"], build_engine_snapshot(hass, engine))
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_kid",
        vol.Optional("kid_id"): vol.Any(str, None),
        vol.Required("name"): str,
        vol.Optional("avatar"): vol.Any(str, None),
        vol.Optional("icon"): vol.Any(str, None),
        vol.Optional("accent_color"): vol.Any(str, None),
        vol.Optional("enabled"): bool,
        vol.Optional("trust_mode"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_save_kid(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    payload = {k: v for k, v in msg.items() if k not in ("id", "type") and v is not None}
    kid = await engine.async_save_kid(payload)
    connection.send_result(msg["id"], {"success": True, "kid": kid})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/delete_kid", vol.Required("kid_id"): str}
)
@websocket_api.async_response
async def ws_delete_kid(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    await engine.async_delete_kid(msg["kid_id"])
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/reorder_kids", vol.Required("kid_ids"): [str]}
)
@websocket_api.async_response
async def ws_reorder_kids(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    await engine.async_reorder_kids(msg["kid_ids"])
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_chore",
        vol.Optional("chore_id"): vol.Any(str, None),
        vol.Required("name"): str,
        vol.Optional("emoji"): vol.Any(str, None),
        vol.Optional("image"): vol.Any(str, None),
        vol.Optional("icon"): vol.Any(str, None),
        vol.Optional("enabled"): bool,
        vol.Optional("tier"): str,
        vol.Optional("schedule_type"): str,
        vol.Optional("custom_days"): [str],
        vol.Optional("weekly_due_day"): vol.Any(str, None),
        vol.Optional("weekly_flexible"): bool,
        vol.Optional("assignment_mode"): str,
        vol.Optional("assigned_kids"): [str],
        vol.Optional("points"): vol.Coerce(int),
        vol.Optional("trust_mode"): str,
        vol.Optional("time_of_day"): str,
    }
)
@websocket_api.async_response
async def ws_save_chore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    payload = {k: v for k, v in msg.items() if k not in ("id", "type")}
    chore = await engine.async_save_chore(payload)
    connection.send_result(msg["id"], {"success": True, "chore": chore})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/delete_chore", vol.Required("chore_id"): str}
)
@websocket_api.async_response
async def ws_delete_chore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    await engine.async_delete_chore(msg["chore_id"])
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/complete_chore",
        vol.Required("chore_id"): str,
        vol.Required("kid_id"): str,
        vol.Optional("by_parent", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_complete_chore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    try:
        user_name = getattr(connection.user, "name", None) if msg.get("by_parent") else None
        res = await engine.async_complete_chore(
            msg["chore_id"], msg["kid_id"], by_parent=msg["by_parent"], parent_name=user_name
        )
        connection.send_result(msg["id"], {"success": True, **res})
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_request", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/uncomplete_chore",
        vol.Required("chore_id"): str,
        vol.Required("kid_id"): str,
    }
)
@websocket_api.async_response
async def ws_uncomplete_chore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    try:
        res = await engine.async_uncomplete_chore(msg["chore_id"], msg["kid_id"])
        connection.send_result(msg["id"], {"success": True, **res})
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_request", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/approve_chore",
        vol.Required("chore_id"): str,
        vol.Required("kid_id"): str,
    }
)
@websocket_api.async_response
async def ws_approve_chore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    parent_name = getattr(connection.user, "name", None) or "Parent"
    res = await engine.async_approve_chore(msg["chore_id"], msg["kid_id"], parent_name=parent_name)
    connection.send_result(msg["id"], {"success": True, **res})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/reject_chore",
        vol.Required("chore_id"): str,
        vol.Required("kid_id"): str,
        vol.Optional("note"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_reject_chore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    res = await engine.async_reject_chore(msg["chore_id"], msg["kid_id"], note=msg.get("note"))
    connection.send_result(msg["id"], {"success": True, **res})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/approve_all_pending",
        vol.Optional("kid_id"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_approve_all_pending(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    parent_name = getattr(connection.user, "name", None) or "Parent"
    count = await engine.async_approve_all_pending(
        kid_id=msg.get("kid_id"), parent_name=parent_name
    )
    connection.send_result(msg["id"], {"success": True, "approved_count": count})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/rotate_chore",
        vol.Required("chore_id"): str,
        vol.Optional("steps", default=1): vol.Coerce(int),
    }
)
@websocket_api.async_response
async def ws_rotate_chore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    chore = await engine.async_rotate_chore(msg["chore_id"], steps=msg["steps"])
    connection.send_result(msg["id"], {"success": True, "chore": chore})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_reward",
        vol.Optional("reward_id"): vol.Any(str, None),
        vol.Required("name"): str,
        vol.Optional("emoji"): vol.Any(str, None),
        vol.Optional("icon"): vol.Any(str, None),
        vol.Optional("cost"): vol.Coerce(int),
        vol.Optional("reward_type"): str,
        vol.Optional("auto_approve"): bool,
        vol.Optional("smart_action"): vol.Any(dict, None),
        vol.Optional("enabled"): bool,
    }
)
@websocket_api.async_response
async def ws_save_reward(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    payload = {k: v for k, v in msg.items() if k not in ("id", "type")}
    reward = await engine.async_save_reward(payload)
    connection.send_result(msg["id"], {"success": True, "reward": reward})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/delete_reward", vol.Required("reward_id"): str}
)
@websocket_api.async_response
async def ws_delete_reward(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    await engine.async_delete_reward(msg["reward_id"])
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/redeem_reward",
        vol.Required("reward_id"): str,
        vol.Required("kid_id"): str,
    }
)
@websocket_api.async_response
async def ws_redeem_reward(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    try:
        rdm = await engine.async_redeem_reward(msg["reward_id"], msg["kid_id"])
        connection.send_result(msg["id"], {"success": True, "redemption": rdm})
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_request", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/resolve_redemption",
        vol.Required("redemption_id"): str,
        vol.Required("approved"): bool,
    }
)
@websocket_api.async_response
async def ws_resolve_redemption(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    parent_name = getattr(connection.user, "name", None) or "Parent"
    rdm = await engine.async_resolve_redemption(
        msg["redemption_id"], approved=msg["approved"], resolved_by=parent_name
    )
    connection.send_result(msg["id"], {"success": True, "redemption": rdm})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/adjust_points",
        vol.Required("kid_id"): str,
        vol.Required("delta"): vol.Coerce(int),
        vol.Optional("reason", default="Parent Adjustment"): str,
    }
)
@websocket_api.async_response
async def ws_adjust_points(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    pts = await engine.async_adjust_points(
        msg["kid_id"], delta=msg["delta"], reason=msg["reason"]
    )
    connection.send_result(msg["id"], {"success": True, "points": pts})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_unlock_rule",
        vol.Optional("rule_id"): vol.Any(str, None),
        vol.Required("name"): str,
        vol.Optional("enabled"): bool,
        vol.Optional("scope"): str,
        vol.Optional("kid_id"): vol.Any(str, None),
        vol.Optional("shared_mode"): str,
        vol.Optional("target_mode"): str,
        vol.Optional("screen_time_device_id"): vol.Any(str, None),
        vol.Optional("target_entity"): vol.Any(str, None),
        vol.Optional("nintendo_bonus_minutes"): vol.Coerce(int),
        vol.Optional("lock_on_reset"): bool,
        vol.Optional("re_lock_if_uncompleted"): bool,
        vol.Optional("respect_screen_time_schedules"): bool,
        vol.Optional("zero_chores_behavior"): str,
    }
)
@websocket_api.async_response
async def ws_save_unlock_rule(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    payload = {k: v for k, v in msg.items() if k not in ("id", "type")}
    rule = await engine.async_save_unlock_rule(payload)
    connection.send_result(msg["id"], {"success": True, "rule": rule})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/delete_unlock_rule", vol.Required("rule_id"): str}
)
@websocket_api.async_response
async def ws_delete_unlock_rule(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    await engine.async_delete_unlock_rule(msg["rule_id"])
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_settings",
        vol.Optional("daily_reset_time"): str,
        vol.Optional("weekly_reset_day"): str,
        vol.Optional("weekly_due_day"): str,
        vol.Optional("default_trust_mode"): str,
        vol.Optional("undo_window_seconds"): vol.Coerce(int),
        vol.Optional("no_school_calendars"): [str],
        vol.Optional("no_school_keywords"): [str],
        vol.Optional("expand_weekends_on_no_school"): bool,
        vol.Optional("toggle_manual_no_school"): bool,
        vol.Optional("gamification_enabled"): bool,
        vol.Optional("points_enabled"): bool,
        vol.Optional("streaks_enabled"): bool,
        vol.Optional("rewards_enabled"): bool,
        vol.Optional("celebrations_enabled"): bool,
        vol.Optional("daily_all_done_bonus_points"): vol.Coerce(int),
        vol.Optional("parent_notify_services"): [str],
        vol.Optional("tts_entity"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_save_settings(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    updates = {k: v for k, v in msg.items() if k not in ("id", "type")}
    settings = await engine.async_save_settings(updates)
    connection.send_result(msg["id"], {"success": True, "settings": settings})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/reset_chores",
        vol.Optional("scope", default="daily"): vol.In(("daily", "weekly", "all")),
        vol.Optional("kid_id"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_reset_chores(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    cleared = await engine.async_reset_chores(scope=msg["scope"], kid_id=msg.get("kid_id"))
    connection.send_result(msg["id"], {"success": True, "cleared": cleared})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/seed_sample_data"})
@websocket_api.async_response
async def ws_seed_sample_data(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    res = await engine.async_seed_starter_templates()
    connection.send_result(msg["id"], {"success": True, **res})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/verify_pin", vol.Required("pin"): str}
)
@websocket_api.async_response
async def ws_verify_pin(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    valid = engine.storage.verify_pin(msg["pin"])
    connection.send_result(msg["id"], {"valid": valid})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_security_settings",
        vol.Optional("current_pin"): str,
        vol.Optional("new_pin"): str,
        vol.Optional("pin_enabled"): bool,
        vol.Optional("require_pin_for_approvals"): bool,
        vol.Optional("require_pin_for_settings"): bool,
        vol.Optional("bypass_for_ha_admins"): bool,
    }
)
@websocket_api.async_response
async def ws_save_security_settings(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    engine = _get_engine(hass)
    if not engine:
        connection.send_error(msg["id"], "not_found", "Engine not loaded")
        return
    sec = engine.storage.get_security()
    if sec.get("pin_enabled") and sec.get("pin_hash"):
        if not engine.storage.verify_pin(msg.get("current_pin", "")):
            connection.send_error(msg["id"], "invalid_pin", "Current Parental PIN is incorrect.")
            return

    new_pin = (msg.get("new_pin") or "").strip()
    if new_pin:
        if not (4 <= len(new_pin) <= 6 and new_pin.isdigit()):
            connection.send_error(msg["id"], "invalid_pin", "PIN must be 4 to 6 digits.")
            return
        engine.storage.set_pin(new_pin)
    elif msg.get("pin_enabled") is False:
        engine.storage.clear_pin()
    elif msg.get("pin_enabled") is True and not sec.get("pin_hash"):
        connection.send_error(msg["id"], "invalid_pin", "Enter a 4–6 digit PIN to enable protection.")
        return

    for field in ("require_pin_for_approvals", "require_pin_for_settings", "bypass_for_ha_admins"):
        if field in msg:
            sec[field] = bool(msg[field])

    await engine.storage.async_save()
    async_dispatcher_send_safe(hass, SIGNAL_ENGINE_UPDATED)
    connection.send_result(
        msg["id"], {"success": True, "security": engine.storage.get_public_security()}
    )


def async_dispatcher_send_safe(hass: HomeAssistant, signal: str) -> None:
    from homeassistant.helpers.dispatcher import async_dispatcher_send
    async_dispatcher_send(hass, signal)
