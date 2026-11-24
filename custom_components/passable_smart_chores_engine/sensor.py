"""Sensor platform for Passable Smart Chores Engine."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
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

_LOGGER = logging.getLogger(__name__)


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
    """Set up chore sensors from a config entry."""
    engine: PassableChoresEngine = hass.data[DOMAIN][entry.entry_id]
    added_kids: set[str] = set()

    entities: list[SensorEntity] = [PassableChoresSummarySensor(engine)]
    for kid_id in engine.storage.get_kids():
        added_kids.add(kid_id)
        entities.extend(
            [
                PassableKidProgressSensor(engine, kid_id),
                PassableKidPointsSensor(engine, kid_id),
                PassableKidStreakSensor(engine, kid_id),
            ]
        )

    async_add_entities(entities)

    @callback
    def _handle_kid_added(kid_id: str) -> None:
        if not kid_id or kid_id in added_kids:
            return
        if kid_id not in engine.storage.get_kids():
            return
        added_kids.add(kid_id)
        async_add_entities(
            [
                PassableKidProgressSensor(engine, kid_id),
                PassableKidPointsSensor(engine, kid_id),
                PassableKidStreakSensor(engine, kid_id),
            ]
        )

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_KID_ADDED, _handle_kid_added)
    )


class PassableChoresSummarySensor(SensorEntity):
    """Household summary sensor reporting remaining required chores and rich snapshot metadata."""

    _attr_has_entity_name = False
    _attr_name = "Passable Chores Summary"
    _attr_icon = "mdi:clipboard-check-multiple-outline"

    def __init__(self, engine: PassableChoresEngine) -> None:
        self.engine = engine
        self._attr_unique_id = f"{DOMAIN}_summary"
        self.entity_id = "sensor.passable_chores_summary"
        self._attr_device_info = _hub_device_info()

    @property
    def native_value(self) -> int:
        """Return total incomplete required chores due today across active kids."""
        eval_data = self.engine.get_snapshot_evaluation()
        remaining = 0
        for kid in eval_data["kids"].values():
            if kid.get("enabled", True):
                remaining += max(
                    0, kid["required_due_total"] - kid["required_due_completed"]
                )
        return remaining

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        eval_data = self.engine.get_snapshot_evaluation()
        kids_summary = {
            kid_id: {
                "name": k["name"],
                "required_completed": k["required_due_completed"],
                "required_total": k["required_due_total"],
                "progress_pct": k["progress_pct"],
                "points": k["points"],
                "streak": k["streak_current"],
                "all_done": k["is_all_done_today"],
            }
            for kid_id, k in eval_data["kids"].items()
            if k.get("enabled", True)
        }
        return {
            "cycle_date": eval_data["cycle"]["cycle_date"],
            "week_key": eval_data["cycle"]["week_key"],
            "is_school_day": eval_data["cycle"]["is_school_day"],
            "is_no_school_override": eval_data["cycle"]["is_no_school_override"],
            "pending_approvals_count": len(eval_data["pending_approvals"]),
            "active_kids_count": sum(
                1 for k in eval_data["kids"].values() if k.get("is_active_kid_today")
            ),
            "kids": kids_summary,
        }

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


class _BaseKidSensor(SensorEntity):
    """Shared base class for per-kid chore sensors."""

    _attr_has_entity_name = False

    def __init__(self, engine: PassableChoresEngine, kid_id: str) -> None:
        self.engine = engine
        self.kid_id = kid_id
        self._attr_device_info = _hub_device_info()

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


class PassableKidProgressSensor(_BaseKidSensor):
    """Percentage of today's required chores completed for a child."""

    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:progress-check"

    def __init__(self, engine: PassableChoresEngine, kid_id: str) -> None:
        super().__init__(engine, kid_id)
        kid = engine.storage.get_kids().get(kid_id, {})
        self._attr_unique_id = f"{DOMAIN}_kid_{kid_id}_progress"
        self._attr_name = f"{kid.get('name', kid_id)} Chores Progress"

    @property
    def native_value(self) -> int:
        eval_data = self.engine.get_snapshot_evaluation()
        kboard = eval_data["kids"].get(self.kid_id)
        if not kboard:
            return 0
        return int(kboard.get("progress_pct", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        eval_data = self.engine.get_snapshot_evaluation()
        kboard = eval_data["kids"].get(self.kid_id)
        if not kboard:
            return {}
        return {
            "required_completed": kboard["required_due_completed"],
            "required_total": kboard["required_due_total"],
            "waiting_approval": kboard["required_due_waiting"],
            "visible_total": kboard["visible_total"],
            "all_done": kboard["is_all_done_today"],
            "effective_trust_mode": kboard["effective_trust_mode"],
        }


class PassableKidPointsSensor(_BaseKidSensor):
    """Current redeemable star points bank for a child."""

    _attr_native_unit_of_measurement = "stars"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:star-circle-outline"

    def __init__(self, engine: PassableChoresEngine, kid_id: str) -> None:
        super().__init__(engine, kid_id)
        kid = engine.storage.get_kids().get(kid_id, {})
        self._attr_unique_id = f"{DOMAIN}_kid_{kid_id}_points"
        self._attr_name = f"{kid.get('name', kid_id)} Chore Points"

    @property
    def native_value(self) -> int:
        kid = self.engine.storage.get_kids().get(self.kid_id, {})
        return int(kid.get("points", 0) or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        kid = self.engine.storage.get_kids().get(self.kid_id, {})
        return {"lifetime_points": int(kid.get("lifetime_points", 0) or 0)}


class PassableKidStreakSensor(_BaseKidSensor):
    """Consecutive chore completion day streak for a child."""

    _attr_native_unit_of_measurement = "days"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:fire"

    def __init__(self, engine: PassableChoresEngine, kid_id: str) -> None:
        super().__init__(engine, kid_id)
        kid = engine.storage.get_kids().get(kid_id, {})
        self._attr_unique_id = f"{DOMAIN}_kid_{kid_id}_streak"
        self._attr_name = f"{kid.get('name', kid_id)} Chore Streak"

    @property
    def native_value(self) -> int:
        kid = self.engine.storage.get_kids().get(self.kid_id, {})
        return int(kid.get("streak_current", 0) or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        kid = self.engine.storage.get_kids().get(self.kid_id, {})
        return {
            "best_streak": int(kid.get("streak_best", 0) or 0),
            "last_streak_date": kid.get("last_streak_date"),
        }
