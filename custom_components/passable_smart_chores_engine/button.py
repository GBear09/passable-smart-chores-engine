"""Button platform for Passable Smart Chores Engine."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VERSION
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
    """Set up action buttons for Passable Smart Chores Engine."""
    engine: PassableChoresEngine = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PassableResetDailyChoresButton(engine),
            PassableApproveAllPendingButton(engine),
        ]
    )


class PassableResetDailyChoresButton(ButtonEntity):
    """Button to manually reset today's daily chores."""

    _attr_has_entity_name = False
    _attr_name = "Passable Chores Reset Daily"
    _attr_icon = "mdi:refresh"

    def __init__(self, engine: PassableChoresEngine) -> None:
        self.engine = engine
        self._attr_unique_id = f"{DOMAIN}_reset_daily"
        self.entity_id = "button.passable_chores_reset_daily"
        self._attr_device_info = _hub_device_info()

    async def async_press(self) -> None:
        await self.engine.async_reset_chores(scope="daily")


class PassableApproveAllPendingButton(ButtonEntity):
    """Button to approve all pending chore requests."""

    _attr_has_entity_name = False
    _attr_name = "Passable Chores Approve All Pending"
    _attr_icon = "mdi:check-all"

    def __init__(self, engine: PassableChoresEngine) -> None:
        self.engine = engine
        self._attr_unique_id = f"{DOMAIN}_approve_all"
        self.entity_id = "button.passable_chores_approve_all"
        self._attr_device_info = _hub_device_info()

    async def async_press(self) -> None:
        await self.engine.async_approve_all_pending(parent_name="HA Button")
