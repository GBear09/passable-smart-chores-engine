"""Config flow for Passable Smart Chores Engine."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_DAILY_RESET_TIME,
    CONF_DEFAULT_TRUST_MODE,
    CONF_GAMIFICATION_ENABLED,
    CONF_NO_SCHOOL_CALENDARS,
    CONF_SEED_STARTER_TEMPLATES,
    CONF_WEEKLY_DUE_DAY,
    CONF_WEEKLY_RESET_DAY,
    DEFAULT_DAILY_RESET_TIME,
    DEFAULT_WEEKLY_DUE_DAY,
    DEFAULT_WEEKLY_RESET_DAY,
    DOMAIN,
    TRUST_APPROVAL,
    TRUST_HONOR,
)
from .storage import normalize_hhmm, normalize_weekday

_LOGGER = logging.getLogger(__name__)

WEEKDAY_OPTIONS = [
    {"value": "mon", "label": "Monday"},
    {"value": "tue", "label": "Tuesday"},
    {"value": "wed", "label": "Wednesday"},
    {"value": "thu", "label": "Thursday"},
    {"value": "fri", "label": "Friday"},
    {"value": "sat", "label": "Saturday"},
    {"value": "sun", "label": "Sunday"},
]

TRUST_OPTIONS = [
    {"value": TRUST_HONOR, "label": "Honor System (Instant Check-Off)"},
    {"value": TRUST_APPROVAL, "label": "Parent Approval Required"},
]


class PassableChoresConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Passable Smart Chores Engine."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial setup step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            cleaned = {
                CONF_DAILY_RESET_TIME: normalize_hhmm(
                    user_input.get(CONF_DAILY_RESET_TIME), DEFAULT_DAILY_RESET_TIME
                ),
                CONF_WEEKLY_RESET_DAY: normalize_weekday(
                    user_input.get(CONF_WEEKLY_RESET_DAY), DEFAULT_WEEKLY_RESET_DAY
                ),
                CONF_WEEKLY_DUE_DAY: normalize_weekday(
                    user_input.get(CONF_WEEKLY_DUE_DAY), DEFAULT_WEEKLY_DUE_DAY
                ),
                CONF_DEFAULT_TRUST_MODE: user_input.get(
                    CONF_DEFAULT_TRUST_MODE, TRUST_HONOR
                ),
                CONF_NO_SCHOOL_CALENDARS: list(
                    user_input.get(CONF_NO_SCHOOL_CALENDARS) or []
                ),
                CONF_GAMIFICATION_ENABLED: bool(
                    user_input.get(CONF_GAMIFICATION_ENABLED, True)
                ),
                CONF_SEED_STARTER_TEMPLATES: bool(
                    user_input.get(CONF_SEED_STARTER_TEMPLATES, False)
                ),
            }
            return self.async_create_entry(
                title="Passable Smart Chores Engine",
                data=cleaned,
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DAILY_RESET_TIME, default=DEFAULT_DAILY_RESET_TIME
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_WEEKLY_RESET_DAY, default=DEFAULT_WEEKLY_RESET_DAY
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=WEEKDAY_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_WEEKLY_DUE_DAY, default=DEFAULT_WEEKLY_DUE_DAY
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=WEEKDAY_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_DEFAULT_TRUST_MODE, default=TRUST_HONOR
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=TRUST_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_NO_SCHOOL_CALENDARS, default=[]
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["calendar"],
                        multiple=True,
                    )
                ),
                vol.Optional(
                    CONF_GAMIFICATION_ENABLED, default=True
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_SEED_STARTER_TEMPLATES, default=False
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return options flow handler."""
        return PassableChoresOptionsFlow(config_entry)


class PassableChoresOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Passable Smart Chores Engine."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self._config_entry = config_entry

    @property
    def config_entry(self) -> config_entries.ConfigEntry:
        return self._config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit global chore scheduling, trust, and calendar settings."""
        engine = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if not engine:
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            updates = {
                CONF_DAILY_RESET_TIME: normalize_hhmm(
                    user_input.get(CONF_DAILY_RESET_TIME), DEFAULT_DAILY_RESET_TIME
                ),
                CONF_WEEKLY_RESET_DAY: normalize_weekday(
                    user_input.get(CONF_WEEKLY_RESET_DAY), DEFAULT_WEEKLY_RESET_DAY
                ),
                CONF_WEEKLY_DUE_DAY: normalize_weekday(
                    user_input.get(CONF_WEEKLY_DUE_DAY), DEFAULT_WEEKLY_DUE_DAY
                ),
                CONF_DEFAULT_TRUST_MODE: user_input.get(
                    CONF_DEFAULT_TRUST_MODE, TRUST_HONOR
                ),
                CONF_NO_SCHOOL_CALENDARS: list(
                    user_input.get(CONF_NO_SCHOOL_CALENDARS) or []
                ),
                CONF_GAMIFICATION_ENABLED: bool(
                    user_input.get(CONF_GAMIFICATION_ENABLED, True)
                ),
            }
            await engine.async_save_settings(updates)
            return self.async_create_entry(title="", data=updates)

        settings = engine.storage.get_settings()
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DAILY_RESET_TIME,
                    default=settings.get("daily_reset_time", DEFAULT_DAILY_RESET_TIME),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_WEEKLY_RESET_DAY,
                    default=settings.get("weekly_reset_day", DEFAULT_WEEKLY_RESET_DAY),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=WEEKDAY_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_WEEKLY_DUE_DAY,
                    default=settings.get("weekly_due_day", DEFAULT_WEEKLY_DUE_DAY),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=WEEKDAY_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_DEFAULT_TRUST_MODE,
                    default=settings.get("default_trust_mode", TRUST_HONOR),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=TRUST_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_NO_SCHOOL_CALENDARS,
                    default=settings.get("no_school_calendars", []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["calendar"],
                        multiple=True,
                    )
                ),
                vol.Optional(
                    CONF_GAMIFICATION_ENABLED,
                    default=settings.get("gamification_enabled", True),
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
