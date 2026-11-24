"""Lightweight Home Assistant mocks for unit testing Passable Smart Chores Engine."""

from __future__ import annotations

from datetime import datetime, timezone
import sys
from unittest import mock


class MockModule(mock.MagicMock):
    __path__ = []


class FakeStore:
    """In-memory async Store replacement."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, version, key):
        self.hass = hass
        self.version = version
        self.key = key
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        import copy
        self._data = copy.deepcopy(data)


def setup_ha_mocks():
    """Install minimal homeassistant.* mocks into sys.modules."""
    if "homeassistant" in sys.modules and getattr(sys.modules["homeassistant"], "_passable_chores_mocked", False):
        return

    ha_root = MockModule()
    ha_root._passable_chores_mocked = True
    helpers_module = MockModule()
    util_module = MockModule()
    components_module = MockModule()

    dt_module = mock.MagicMock()
    dt_module.parse_datetime = lambda s: datetime.fromisoformat(str(s))
    dt_module.utcnow = lambda: datetime.now(timezone.utc)
    dt_module.now = lambda: datetime.now(timezone.utc)
    dt_module.as_utc = lambda dt: dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    dt_module.as_local = lambda dt: dt

    storage_module = mock.MagicMock()
    storage_module.Store = FakeStore

    dispatcher_module = mock.MagicMock()
    dispatcher_module.async_dispatcher_send = mock.MagicMock()
    dispatcher_module.async_dispatcher_connect = mock.MagicMock(return_value=lambda: None)

    event_module = mock.MagicMock()
    event_module.async_track_time_interval = mock.MagicMock(return_value=lambda: None)
    event_module.async_track_time_change = mock.MagicMock(return_value=lambda: None)
    event_module.async_track_state_change_event = mock.MagicMock(return_value=lambda: None)

    helpers_module.storage = storage_module
    helpers_module.dispatcher = dispatcher_module
    helpers_module.event = event_module
    helpers_module.entity = mock.MagicMock()
    helpers_module.entity_platform = mock.MagicMock()
    helpers_module.entity_registry = mock.MagicMock()
    helpers_module.selector = mock.MagicMock()
    helpers_module.config_validation = mock.MagicMock()

    util_module.dt = dt_module

    ha_root.components = components_module
    ha_root.config_entries = mock.MagicMock()
    ha_root.const = mock.MagicMock()
    ha_root.core = mock.MagicMock()
    ha_root.core.callback = lambda fn: fn
    ha_root.helpers = helpers_module
    ha_root.util = util_module

    sys.modules["homeassistant"] = ha_root
    sys.modules["homeassistant.components"] = components_module
    sys.modules["homeassistant.components.websocket_api"] = mock.MagicMock()
    sys.modules["homeassistant.components.sensor"] = mock.MagicMock()
    sys.modules["homeassistant.components.binary_sensor"] = mock.MagicMock()
    sys.modules["homeassistant.components.switch"] = mock.MagicMock()
    sys.modules["homeassistant.components.button"] = mock.MagicMock()
    sys.modules["homeassistant.config_entries"] = ha_root.config_entries
    sys.modules["homeassistant.const"] = ha_root.const
    sys.modules["homeassistant.core"] = ha_root.core
    sys.modules["homeassistant.helpers"] = helpers_module
    sys.modules["homeassistant.helpers.storage"] = storage_module
    sys.modules["homeassistant.helpers.dispatcher"] = dispatcher_module
    sys.modules["homeassistant.helpers.event"] = event_module
    sys.modules["homeassistant.helpers.entity"] = helpers_module.entity
    sys.modules["homeassistant.helpers.entity_platform"] = helpers_module.entity_platform
    sys.modules["homeassistant.helpers.entity_registry"] = helpers_module.entity_registry
    sys.modules["homeassistant.helpers.selector"] = helpers_module.selector
    sys.modules["homeassistant.helpers.config_validation"] = helpers_module.config_validation
    sys.modules["homeassistant.util"] = util_module
    sys.modules["homeassistant.util.dt"] = dt_module

    try:
        import voluptuous  # noqa: F401
    except ImportError:
        sys.modules["voluptuous"] = mock.MagicMock()


setup_ha_mocks()
