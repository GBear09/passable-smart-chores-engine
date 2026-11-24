"""Switch platform for Passable Smart Chores Engine (per-kid trust mode toggle)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SIGNAL_ENGINE_UPDATED,
    SIGNAL_KID_ADDED,
    SIGNAL_KID_UPDATED,
    TRUST_APPROVAL,
    TRUST_HONOR,
    VERSION,
)
from .engine import PassableChoresEngine


def _hub_device_info() -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, "hub")},
        name="Passable Smart Chores Engine",
        manufacturer="Passable",
        model="Smart Chores & Rewards Hub",
        sw_version=VERSION,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-kid parent approval switches."""
    engine: PassableChoresEngine = hass.data[DOMAIN][entry.entry_id]
    added_kids: set[str] = set()
    entities: list[SwitchEntity] = []

    for kid_id in engine.storage.get_kids():
        added_kids.add(kid_id)
        entities.append(PassableKidApprovalSwitch(engine, kid_id))

    async_add_entities(entities)

    @callback
    def _handle_kid_added(kid_id: str) -> None:
        if not kid_id or kid_id in added_kids or kid_id not in engine.storage.get_kids():
            return
        added_kids.add(kid_id)
        async_add_entities([PassableKidApprovalSwitch(engine, kid_id)])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_KID_ADDED, _handle_kid_added)
    )


class PassableKidApprovalSwitch(SwitchEntity):
    """Switch toggling Parent Approval Required vs Honor System for a child."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:account-check-outline"

    def __init__(self, engine: PassableChoresEngine, kid_id: str) -> None:
        self.engine = engine
        self.kid_id = kid_id
        kid = engine.storage.get_kids().get(kid_id, {})
        self._attr_unique_id = f"{DOMAIN}_kid_{kid_id}_require_approval"
        self._attr_name = f"{kid.get('name', kid_id)} Require Parent Approval"
        self._attr_device_info = _hub_device_info()

    @property
    def is_on(self) -> bool:
        eval_data = self.engine.get_snapshot_evaluation()
        kboard = eval_data["kids"].get(self.kid_id)
        if not kboard:
            return False
        return kboard.get("effective_trust_mode") == TRUST_APPROVAL

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.engine.async_save_kid(
            {"kid_id": self.kid_id, "trust_mode": TRUST_APPROVAL}
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.engine.async_save_kid(
            {"kid_id": self.kid_id, "trust_mode": TRUST_HONOR}
        )

    async def async_added_to_hass(self) -> None:
        @callback
        def _handle_update(kid_id: str = "") -> None:
            if not kid_id or kid_id == self.kid_id:
                self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_KID_UPDATED, _handle_update)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_ENGINE_UPDATED, _handle_update)
        )
