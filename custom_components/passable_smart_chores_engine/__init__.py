"""Passable Smart Chores Engine integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    CONF_DAILY_RESET_TIME,
    CONF_DEFAULT_TRUST_MODE,
    CONF_GAMIFICATION_ENABLED,
    CONF_NO_SCHOOL_CALENDARS,
    CONF_SEED_STARTER_TEMPLATES,
    CONF_WEEKLY_DUE_DAY,
    CONF_WEEKLY_RESET_DAY,
    DOMAIN,
    FRONTEND_URL_PATH,
    VERSION,
)
from .engine import PassableChoresEngine
from .storage import PassableChoresStorage
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register static frontend path and Lovelace card resource."""
    if hass.data.setdefault(DOMAIN, {}).get("frontend_registered"):
        return

    card_path = Path(__file__).parent / "frontend" / "passable-chores-card.js"
    if not await hass.async_add_executor_job(card_path.is_file):
        _LOGGER.warning("Passable Chores Card file not found at %s", card_path)
        return

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(FRONTEND_URL_PATH, str(card_path), cache_headers=False)]
        )
        hass.data[DOMAIN]["frontend_registered"] = True
        _LOGGER.info("Passable Chores Card registered at %s", FRONTEND_URL_PATH)
    except Exception:
        try:
            hass.http.register_static_path(
                FRONTEND_URL_PATH, str(card_path), cache_headers=False
            )
            hass.data[DOMAIN]["frontend_registered"] = True
            _LOGGER.info(
                "Passable Chores Card registered at %s (legacy)", FRONTEND_URL_PATH
            )
        except Exception as legacy_err:
            _LOGGER.error("Failed to register static path: %s", legacy_err)

    hass.async_create_task(_async_register_lovelace_resource(hass))


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register passable-chores-card.js as a Lovelace module resource automatically."""
    try:
        lovelace = hass.data.get("lovelace")
        if not lovelace:
            return
        resources = getattr(lovelace, "resources", None)
        if not resources:
            return
        if not resources.loaded:
            await resources.async_load()

        url_path = f"{FRONTEND_URL_PATH}?v={VERSION}"
        for resource in resources.async_items():
            existing_url = resource.get("url", "")
            if existing_url == url_path:
                return
            if existing_url.startswith(FRONTEND_URL_PATH):
                res_id = resource.get("id")
                if res_id:
                    await resources.async_update_item(
                        res_id, {"res_type": "module", "url": url_path}
                    )
                    _LOGGER.info("Updated Lovelace resource URL to %s", url_path)
                return

        await resources.async_create_item({"res_type": "module", "url": url_path})
        _LOGGER.info("Automatically registered Lovelace resource: %s", url_path)
    except Exception as err:
        _LOGGER.debug("Could not automatically register Lovelace resource: %s", err)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Passable Smart Chores Engine component."""
    await _async_register_frontend(hass)
    async_register_websocket_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Passable Smart Chores Engine from a config entry."""
    storage = PassableChoresStorage(hass)
    engine = PassableChoresEngine(hass, storage, entry.entry_id)

    await engine.async_setup()

    # Apply initial config entry settings on first load
    initial_updates: dict[str, Any] = {}
    for key in (
        CONF_DAILY_RESET_TIME,
        CONF_WEEKLY_RESET_DAY,
        CONF_WEEKLY_DUE_DAY,
        CONF_DEFAULT_TRUST_MODE,
        CONF_NO_SCHOOL_CALENDARS,
        CONF_GAMIFICATION_ENABLED,
    ):
        if key in entry.options:
            initial_updates[key] = entry.options[key]
        elif key in entry.data and not storage.data.get("initial_config_applied"):
            initial_updates[key] = entry.data[key]

    if initial_updates:
        await engine.async_save_settings(initial_updates)

    if not storage.data.get("initial_config_applied"):
        if entry.data.get(CONF_SEED_STARTER_TEMPLATES):
            await engine.async_seed_starter_templates()
        storage.data["initial_config_applied"] = True
        await storage.async_save()

    # Clean up any orphaned kid entities from entity registry
    active_kids = set(storage.get_kids().keys())
    try:
        from homeassistant.helpers import entity_registry as er

        ent_reg = er.async_get(hass)
        global_uids = {
            f"{DOMAIN}_summary",
            f"{DOMAIN}_all_completed",
            f"{DOMAIN}_any_completed",
            f"{DOMAIN}_pending_approvals",
            f"{DOMAIN}_reset_daily",
            f"{DOMAIN}_approve_all",
        }
        orphans = [
            entity_id
            for entity_id, reg_entry in ent_reg.entities.items()
            if reg_entry.config_entry_id == entry.entry_id
            and reg_entry.unique_id not in global_uids
            and not any(
                reg_entry.unique_id.startswith(f"{DOMAIN}_kid_{kid_id}_")
                for kid_id in active_kids
            )
        ]
        for oid in orphans:
            _LOGGER.info("Cleaning up orphan chores entity: %s", oid)
            ent_reg.async_remove(oid)
    except Exception as err:
        _LOGGER.debug("Orphan entity cleanup skipped: %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = engine
    _async_register_services(hass, engine)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


def _async_register_services(
    hass: HomeAssistant, engine: PassableChoresEngine
) -> None:
    """Register integration service actions."""
    if hass.services.has_service(DOMAIN, "complete_chore"):
        return

    async def handle_complete_chore(call: ServiceCall) -> None:
        await engine.async_complete_chore(
            call.data["chore_id"],
            call.data["kid_id"],
            by_parent=call.data.get("by_parent", False),
        )

    async def handle_uncomplete_chore(call: ServiceCall) -> None:
        await engine.async_uncomplete_chore(call.data["chore_id"], call.data["kid_id"])

    async def handle_approve_chore(call: ServiceCall) -> None:
        await engine.async_approve_chore(
            call.data["chore_id"],
            call.data["kid_id"],
            parent_name=call.data.get("parent_name"),
        )

    async def handle_reject_chore(call: ServiceCall) -> None:
        await engine.async_reject_chore(
            call.data["chore_id"],
            call.data["kid_id"],
            note=call.data.get("note"),
        )

    async def handle_approve_all_pending(call: ServiceCall) -> None:
        await engine.async_approve_all_pending(kid_id=call.data.get("kid_id"))

    async def handle_redeem_reward(call: ServiceCall) -> None:
        await engine.async_redeem_reward(call.data["reward_id"], call.data["kid_id"])

    async def handle_resolve_redemption(call: ServiceCall) -> None:
        await engine.async_resolve_redemption(
            call.data["redemption_id"], approved=call.data["approved"]
        )

    async def handle_adjust_points(call: ServiceCall) -> None:
        await engine.async_adjust_points(
            call.data["kid_id"],
            delta=call.data["delta"],
            reason=call.data.get("reason", "Parent Adjustment"),
        )

    async def handle_reset_chores(call: ServiceCall) -> None:
        await engine.async_reset_chores(
            scope=call.data.get("scope", "daily"),
            kid_id=call.data.get("kid_id"),
        )

    async def handle_rotate_chore(call: ServiceCall) -> None:
        await engine.async_rotate_chore(
            call.data["chore_id"], steps=call.data.get("steps", 1)
        )

    hass.services.async_register(
        DOMAIN,
        "complete_chore",
        handle_complete_chore,
        schema=vol.Schema(
            {
                vol.Required("chore_id"): cv.string,
                vol.Required("kid_id"): cv.string,
                vol.Optional("by_parent", default=False): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "uncomplete_chore",
        handle_uncomplete_chore,
        schema=vol.Schema(
            {vol.Required("chore_id"): cv.string, vol.Required("kid_id"): cv.string}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "approve_chore",
        handle_approve_chore,
        schema=vol.Schema(
            {
                vol.Required("chore_id"): cv.string,
                vol.Required("kid_id"): cv.string,
                vol.Optional("parent_name"): vol.Any(cv.string, None),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "reject_chore",
        handle_reject_chore,
        schema=vol.Schema(
            {
                vol.Required("chore_id"): cv.string,
                vol.Required("kid_id"): cv.string,
                vol.Optional("note"): vol.Any(cv.string, None),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "approve_all_pending",
        handle_approve_all_pending,
        schema=vol.Schema({vol.Optional("kid_id"): vol.Any(cv.string, None)}),
    )
    hass.services.async_register(
        DOMAIN,
        "redeem_reward",
        handle_redeem_reward,
        schema=vol.Schema(
            {vol.Required("reward_id"): cv.string, vol.Required("kid_id"): cv.string}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "resolve_reward_redemption",
        handle_resolve_redemption,
        schema=vol.Schema(
            {vol.Required("redemption_id"): cv.string, vol.Required("approved"): cv.boolean}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "adjust_points",
        handle_adjust_points,
        schema=vol.Schema(
            {
                vol.Required("kid_id"): cv.string,
                vol.Required("delta"): vol.Coerce(int),
                vol.Optional("reason", default="Parent Adjustment"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "reset_chores",
        handle_reset_chores,
        schema=vol.Schema(
            {
                vol.Optional("scope", default="daily"): vol.In(("daily", "weekly", "all")),
                vol.Optional("kid_id"): vol.Any(cv.string, None),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "rotate_chore",
        handle_rotate_chore,
        schema=vol.Schema(
            {
                vol.Required("chore_id"): cv.string,
                vol.Optional("steps", default=1): vol.Coerce(int),
            }
        ),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    engine: PassableChoresEngine | None = hass.data[DOMAIN].get(entry.entry_id)
    if engine:
        await engine.async_unload()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
