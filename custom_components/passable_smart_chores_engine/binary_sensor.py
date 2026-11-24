"""Binary sensor platform for Passable Smart Chores Engine."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    SIGNAL_STORAGE_UPDATED,
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
    """Set up binary sensors for Passable Smart Chores Engine."""
    engine: PassableChoresEngine = hass.data[DOMAIN][entry.entry_id]
    added_kids: set[str] = set()

    entities: list[BinarySensorEntity] = [
        PassableAllChoresCompletedBinarySensor(engine),
        PassableAnyChoresCompletedBinarySensor(engine),
        PassablePendingApprovalsBinarySensor(engine),
    ]
    for kid_id in engine.storage.get_kids():
        added_kids.add(kid_id)
        entities.append(PassableKidCompletedBinarySensor(engine, kid_id))

    async_add_entities(entities)

    @callback
    def _handle_kid_added(kid_id: str) -> None:
        if not kid_id or kid_id in added_kids or kid_id not in engine.storage.get_kids():
            return
        added_kids.add(kid_id)
        async_add_entities([PassableKidCompletedBinarySensor(engine, kid_id)])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_KID_ADDED, _handle_kid_added)
    )


class _BaseHubBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = False

    def __init__(self, engine: PassableChoresEngine) -> None:
        self.engine = engine
        self._attr_device_info = _hub_device_info()

    async def async_added_to_hass(self) -> None:
        @callback
        def _handle_update(*_args: Any) -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_ENGINE_UPDATED, _handle_update)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_STORAGE_UPDATED, _handle_update)
        )


class PassableAllChoresCompletedBinarySensor(_BaseHubBinarySensor):
    """True when ALL active kids (with >=1 required chore today) have finished."""

    _attr_name = "Passable Chores All Completed"

    def __init__(self, engine: PassableChoresEngine) -> None:
        super().__init__(engine)
        self._attr_unique_id = f"{DOMAIN}_all_completed"
        self.entity_id = "binary_sensor.passable_chores_all_completed"

    @property
    def is_on(self) -> bool:
        eval_data = self.engine.get_snapshot_evaluation()
        active = [k for k in eval_data["kids"].values() if k.get("is_active_kid_today")]
        return bool(active) and all(k.get("is_all_done_today") for k in active)

    @property
    def icon(self) -> str:
        return "mdi:check-decagram" if self.is_on else "mdi:clipboard-list-outline"


class PassableAnyChoresCompletedBinarySensor(_BaseHubBinarySensor):
    """True when AT LEAST ONE active kid (with >=1 required chore today) has finished."""

    _attr_name = "Passable Chores Any Completed"

    def __init__(self, engine: PassableChoresEngine) -> None:
        super().__init__(engine)
        self._attr_unique_id = f"{DOMAIN}_any_completed"
        self.entity_id = "binary_sensor.passable_chores_any_completed"

    @property
    def is_on(self) -> bool:
        eval_data = self.engine.get_snapshot_evaluation()
        active = [k for k in eval_data["kids"].values() if k.get("is_active_kid_today")]
        return any(k.get("is_all_done_today") for k in active)

    @property
    def icon(self) -> str:
        return "mdi:check-circle" if self.is_on else "mdi:clock-outline"


class PassablePendingApprovalsBinarySensor(_BaseHubBinarySensor):
    """True when one or more chores or reward redemptions are waiting for parent approval."""

    _attr_name = "Passable Chores Pending Approvals"

    def __init__(self, engine: PassableChoresEngine) -> None:
        super().__init__(engine)
        self._attr_unique_id = f"{DOMAIN}_pending_approvals"
        self.entity_id = "binary_sensor.passable_chores_pending_approvals"

    @property
    def is_on(self) -> bool:
        eval_data = self.engine.get_snapshot_evaluation()
        return len(eval_data["pending_approvals"]) > 0

    @property
    def icon(self) -> str:
        return "mdi:bell-badge" if self.is_on else "mdi:bell-check-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        eval_data = self.engine.get_snapshot_evaluation()
        return {
            "count": len(eval_data["pending_approvals"]),
            "items": eval_data["pending_approvals"],
        }


class PassableKidCompletedBinarySensor(BinarySensorEntity):
    """Per-kid binary sensor indicating whether all required chores due today are completed."""

    _attr_has_entity_name = False

    def __init__(self, engine: PassableChoresEngine, kid_id: str) -> None:
        self.engine = engine
        self.kid_id = kid_id
        kid = engine.storage.get_kids().get(kid_id, {})
        self._attr_unique_id = f"{DOMAIN}_kid_{kid_id}_completed"
        self._attr_name = f"{kid.get('name', kid_id)} Chores Completed"
        self._attr_device_info = _hub_device_info()

    @property
    def is_on(self) -> bool:
        eval_data = self.engine.get_snapshot_evaluation()
        kboard = eval_data["kids"].get(self.kid_id)
        if not kboard:
            return False
        return bool(kboard.get("is_all_done_today"))

    @property
    def icon(self) -> str:
        return "mdi:check-bold" if self.is_on else "mdi:checkbox-blank-circle-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        eval_data = self.engine.get_snapshot_evaluation()
        kboard = eval_data["kids"].get(self.kid_id)
        if not kboard:
            return {}
        return {
            "required_completed": kboard["required_due_completed"],
            "required_total": kboard["required_due_total"],
            "is_active_today": kboard["is_active_kid_today"],
        }

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
