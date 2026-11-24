"""Unit tests for Passable Smart Chores Engine."""

from __future__ import annotations

from datetime import date, datetime, timezone
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests.ha_mock  # noqa: E402, F401
from custom_components.passable_smart_chores_engine.const import (  # noqa: E402
    ASSIGN_EACH,
    ASSIGN_ROTATE_WEEKLY,
    REDEMPTION_DENIED,
    REDEMPTION_PENDING,
    REWARD_PARENT_FULFILLED,
    REWARD_SMART_ACTION,
    SCHEDULE_DAILY,
    SCHEDULE_SCHOOL_DAYS,
    SCHEDULE_WEEKLY,
    SCHEDULE_WEEKENDS,
    SHARED_MODE_ALL_ACTIVE,
    SHARED_MODE_ANY_ACTIVE,
    SMART_ACTION_SCREEN_TIME_TIMER,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_WAITING_APPROVAL,
    TARGET_MODE_LOCKOUT_SWITCH,
    TARGET_MODE_SCREEN_TIME,
    TIER_REQUIRED,
    TRUST_APPROVAL,
    TRUST_HONOR,
    UNLOCK_SCOPE_PERSONAL,
    UNLOCK_SCOPE_SHARED,
)
from custom_components.passable_smart_chores_engine.engine import (  # noqa: E402
    PassableChoresEngine,
    compute_cycle_date,
    compute_week_start_date,
    evaluate_kid_boards,
    evaluate_unlock_rule_satisfied,
    resolve_weekly_assignee,
)
from custom_components.passable_smart_chores_engine.storage import (  # noqa: E402
    PassableChoresStorage,
    normalize_chore,
    normalize_kid,
    normalize_reward,
    normalize_unlock_rule,
)


def make_fake_hass():
    hass = mock.MagicMock()
    hass.data = {}
    hass.states = mock.MagicMock()
    hass.states.get = mock.MagicMock(return_value=None)
    hass.states.async_all = mock.MagicMock(return_value=[])
    hass.bus = mock.MagicMock()
    hass.bus.async_fire = mock.MagicMock()
    hass.bus.async_listen = mock.MagicMock(return_value=lambda: None)
    hass.services = mock.MagicMock()
    hass.services.has_service = mock.MagicMock(return_value=True)
    hass.services.async_call = mock.AsyncMock(return_value=None)
    hass.async_create_task = mock.MagicMock()
    return hass


class TestChoresEngine(unittest.IsolatedAsyncioTestCase):
    """Comprehensive unit tests covering reset boundaries, rotation, trust modes, streaks, and unlocks."""

    async def asyncSetUp(self) -> None:
        self.hass = make_fake_hass()
        self.storage = PassableChoresStorage(self.hass)
        await self.storage.async_load()
        self.engine = PassableChoresEngine(self.hass, self.storage, "entry_1")

        # Configure kids: Madeleine, Maggie, and Max (0 chores initially)
        self.storage.data["kids"] = {
            "madeleine": normalize_kid("madeleine", {"name": "Madeleine", "accent_color": "#8E24AA", "order": 0}),
            "maggie": normalize_kid("maggie", {"name": "Maggie", "accent_color": "#039BE5", "order": 1}),
            "max": normalize_kid("max", {"name": "Max", "accent_color": "#4285F4", "order": 2}),
        }
        await self.storage.async_save()

    def test_cycle_date_and_week_start_before_and_after_0500(self) -> None:
        before_reset = datetime(2026, 11, 24, 4, 59, tzinfo=timezone.utc)
        at_reset = datetime(2026, 11, 24, 5, 0, tzinfo=timezone.utc)
        self.assertEqual(compute_cycle_date(before_reset, "05:00"), date(2026, 11, 23))
        self.assertEqual(compute_cycle_date(at_reset, "05:00"), date(2026, 11, 24))

        # 2026-11-24 is a Tuesday; Monday start is 2026-11-23
        self.assertEqual(compute_week_start_date(date(2026, 11, 24), "mon"), date(2026, 11, 23))
        # Sunday 2026-11-29 still belongs to the week starting Monday 2026-11-23
        self.assertEqual(compute_week_start_date(date(2026, 11, 29), "mon"), date(2026, 11, 23))

    def test_school_days_and_no_school_holiday_override(self) -> None:
        self.storage.data["chores"] = {
            "pack_bag": normalize_chore(
                "pack_bag",
                {
                    "name": "Pack Backpack",
                    "schedule_type": SCHEDULE_SCHOOL_DAYS,
                    "assigned_kids": ["madeleine"],
                },
            ),
            "weekend_laundry": normalize_chore(
                "weekend_laundry",
                {
                    "name": "Put Away Laundry",
                    "schedule_type": SCHEDULE_WEEKENDS,
                    "assigned_kids": ["madeleine"],
                },
            ),
        }
        monday = datetime(2026, 11, 23, 8, 0, tzinfo=timezone.utc)
        saturday = datetime(2026, 11, 28, 9, 0, tzinfo=timezone.utc)

        # Regular Monday: school_days active, weekends hidden
        ev_mon = evaluate_kid_boards(self.storage, monday, set())
        m_mon = [c["chore_id"] for c in ev_mon["kids"]["madeleine"]["board"]]
        self.assertEqual(m_mon, ["pack_bag"])

        # Regular Saturday: weekends active, school_days hidden
        ev_sat = evaluate_kid_boards(self.storage, saturday, set())
        m_sat = [c["chore_id"] for c in ev_sat["kids"]["madeleine"]["board"]]
        self.assertEqual(m_sat, ["weekend_laundry"])

        # Monday flagged as No-School holiday: school_days pauses, weekends activates
        ev_holiday = evaluate_kid_boards(self.storage, monday, {"2026-11-23"})
        m_hol = [c["chore_id"] for c in ev_holiday["kids"]["madeleine"]["board"]]
        self.assertEqual(m_hol, ["weekend_laundry"])

    def test_flexible_weekly_chore_gating_and_rotation(self) -> None:
        self.storage.data["chores"] = {
            "clean_room": normalize_chore(
                "clean_room",
                {
                    "name": "Clean Room",
                    "schedule_type": SCHEDULE_WEEKLY,
                    "weekly_flexible": True,
                    "weekly_due_day": "sat",
                    "assigned_kids": ["madeleine"],
                },
            ),
            "feed_dog": normalize_chore(
                "feed_dog",
                {
                    "name": "Feed Dog",
                    "schedule_type": SCHEDULE_DAILY,
                    "assignment_mode": ASSIGN_ROTATE_WEEKLY,
                    "assigned_kids": ["madeleine", "maggie"],
                    "rotation_anchor_date": "2026-11-23",
                },
            ),
        }
        tuesday = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)
        saturday = datetime(2026, 11, 28, 10, 0, tzinfo=timezone.utc)
        next_monday = datetime(2026, 11, 30, 10, 0, tzinfo=timezone.utc)

        # Tuesday: clean_room is visible, but NOT due_today_for_unlock
        ev_tue = evaluate_kid_boards(self.storage, tuesday)
        m_board_tue = {c["chore_id"]: c for c in ev_tue["kids"]["madeleine"]["board"]}
        self.assertIn("clean_room", m_board_tue)
        self.assertFalse(m_board_tue["clean_room"]["is_due_today_for_unlock"])
        self.assertIn("feed_dog", m_board_tue)  # Week 0 = Madeleine
        self.assertEqual(ev_tue["kids"]["madeleine"]["required_due_total"], 1)  # only feed_dog

        # Saturday: clean_room promotes to required today
        ev_sat = evaluate_kid_boards(self.storage, saturday)
        m_board_sat = {c["chore_id"]: c for c in ev_sat["kids"]["madeleine"]["board"]}
        self.assertTrue(m_board_sat["clean_room"]["is_due_today_for_unlock"])
        self.assertEqual(ev_sat["kids"]["madeleine"]["required_due_total"], 2)

        # Next Monday: feed_dog rotates to Maggie
        assignee_w1 = resolve_weekly_assignee(
            self.storage.data["chores"]["feed_dog"],
            self.storage.data["kids"],
            next_monday.date(),
            "mon",
        )
        self.assertEqual(assignee_w1, "maggie")

        # Disable Maggie -> rotation automatically stays on Madeleine
        self.storage.data["kids"]["maggie"]["enabled"] = False
        assignee_disabled = resolve_weekly_assignee(
            self.storage.data["chores"]["feed_dog"],
            self.storage.data["kids"],
            next_monday.date(),
            "mon",
        )
        self.assertEqual(assignee_disabled, "madeleine")

    async def test_honor_vs_approval_undo_and_streak_preservation(self) -> None:
        self.storage.data["chores"] = {
            "make_bed": normalize_chore(
                "make_bed",
                {
                    "name": "Make Bed",
                    "schedule_type": SCHEDULE_DAILY,
                    "assigned_kids": ["madeleine", "maggie"],
                    "points": 10,
                },
            ),
        }
        self.storage.data["kids"]["maggie"]["trust_mode"] = TRUST_APPROVAL
        tue = datetime(2026, 11, 24, 9, 0, tzinfo=timezone.utc)

        # Madeleine (Honor System): completes immediately, gets 10 + 5 daily bonus, streak=1
        res_mad = await self.engine.async_complete_chore("make_bed", "madeleine", now_local=tue)
        self.assertEqual(res_mad["status"], STATUS_COMPLETED)
        self.assertEqual(self.storage.data["kids"]["madeleine"]["points"], 15)
        self.assertEqual(self.storage.data["kids"]["madeleine"]["streak_current"], 1)

        # Same-day undo rolls back points, daily bonus, and streak cleanly
        await self.engine.async_uncomplete_chore("make_bed", "madeleine", now_local=tue)
        self.assertEqual(self.storage.data["kids"]["madeleine"]["points"], 0)
        self.assertEqual(self.storage.data["kids"]["madeleine"]["streak_current"], 0)

        # Maggie (Parent Approval): waits for approval -> then parent approves
        res_mag = await self.engine.async_complete_chore("make_bed", "maggie", now_local=tue)
        self.assertEqual(res_mag["status"], STATUS_WAITING_APPROVAL)
        self.assertEqual(self.storage.data["kids"]["maggie"]["points"], 0)

        await self.engine.async_approve_chore("make_bed", "maggie", parent_name="Myles", now_local=tue)
        self.assertEqual(self.storage.data["kids"]["maggie"]["points"], 15)
        self.assertEqual(self.storage.data["kids"]["maggie"]["streak_current"], 1)

        # Rollover to next day: Max had 0 required chores -> streak preserved at 0 (or any prior streak)
        self.storage.data["kids"]["max"]["streak_current"] = 5
        await self.engine.async_check_cycle_rollover(now_local=tue, evaluate_unlocks=False)
        wed = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)
        await self.engine.async_check_cycle_rollover(now_local=wed, evaluate_unlocks=False)
        self.assertEqual(self.storage.data["kids"]["max"]["streak_current"], 5)
        self.assertEqual(self.storage.data["kids"]["maggie"]["streak_current"], 1)
        # Madeleine missed Tuesday after undoing -> streak reset to 0 on Wednesday rollover
        self.assertEqual(self.storage.data["kids"]["madeleine"]["streak_current"], 0)

    async def test_shared_and_personal_unlocks_with_zero_chore_kid_safeguard(self) -> None:
        self.storage.data["chores"] = {
            "brush_teeth": normalize_chore(
                "brush_teeth",
                {
                    "name": "Brush Teeth",
                    "schedule_type": SCHEDULE_DAILY,
                    "assigned_kids": ["madeleine", "maggie"],
                },
            ),
        }
        self.storage.data["unlock_rules"] = {
            "living_room_tv": normalize_unlock_rule(
                "living_room_tv",
                {
                    "name": "Living Room TV",
                    "scope": UNLOCK_SCOPE_SHARED,
                    "shared_mode": SHARED_MODE_ANY_ACTIVE,
                    "target_mode": TARGET_MODE_SCREEN_TIME,
                    "screen_time_device_id": "living_room_tv_2",
                },
            ),
            "madeleine_tablet": normalize_unlock_rule(
                "madeleine_tablet",
                {
                    "name": "Madeleine Tablet",
                    "scope": UNLOCK_SCOPE_PERSONAL,
                    "kid_id": "madeleine",
                    "target_mode": TARGET_MODE_LOCKOUT_SWITCH,
                    "target_entity": "switch.madeleine_s_tablet_pause_wireless_lockout",
                },
            ),
        }
        tue = datetime(2026, 11, 24, 9, 0, tzinfo=timezone.utc)

        # Before any chores done: Max has 0 chores, MUST NOT satisfy shared TV!
        ev0 = evaluate_kid_boards(self.storage, tue)
        sat0, _ = evaluate_unlock_rule_satisfied(
            self.storage.data["unlock_rules"]["living_room_tv"], ev0["kids"]
        )
        self.assertFalse(sat0)

        # Madeleine completes her chore -> both living_room_tv (any_active_kid) and madeleine_tablet unlock
        await self.engine.async_complete_chore("brush_teeth", "madeleine", now_local=tue)
        calls = [c.args for c in self.hass.services.async_call.call_args_list]
        self.assertIn(
            (
                "passable_smart_screen_time_engine",
                "set_lockout",
                {"device_id": "living_room_tv_2", "locked": False, "power_on": False, "rest_of_day": False},
            ),
            calls,
        )
        self.assertIn(
            ("switch", "turn_off", {"entity_id": "switch.madeleine_s_tablet_pause_wireless_lockout"}),
            calls,
        )

        # Latch check: calling evaluate again today does NOT re-issue unlock if parent locks TV manually
        self.hass.services.async_call.reset_mock()
        await self.engine.async_evaluate_unlock_rules(now_local=tue)
        self.hass.services.async_call.assert_not_called()

        # Switch shared rule to all_active_kids -> Maggie hasn't finished yet, so unsatisfied!
        self.storage.data["unlock_rules"]["living_room_tv"]["shared_mode"] = SHARED_MODE_ALL_ACTIVE
        ev1 = evaluate_kid_boards(self.storage, tue)
        sat_all, _ = evaluate_unlock_rule_satisfied(
            self.storage.data["unlock_rules"]["living_room_tv"], ev1["kids"]
        )
        self.assertFalse(sat_all)

        # Maggie finishes -> now all_active_kids is True (still ignoring Max at 0/0)
        await self.engine.async_complete_chore("brush_teeth", "maggie", now_local=tue)
        ev2 = evaluate_kid_boards(self.storage, tue)
        sat_all_done, _ = evaluate_unlock_rule_satisfied(
            self.storage.data["unlock_rules"]["living_room_tv"], ev2["kids"]
        )
        self.assertTrue(sat_all_done)

    async def test_reward_redemption_smart_action_and_parent_refund(self) -> None:
        self.storage.data["kids"]["madeleine"]["points"] = 100
        self.storage.data["rewards"] = {
            "tv_20m": normalize_reward(
                "tv_20m",
                {
                    "name": "+20m TV",
                    "cost": 40,
                    "reward_type": REWARD_SMART_ACTION,
                    "auto_approve": True,
                    "smart_action": {
                        "action_kind": SMART_ACTION_SCREEN_TIME_TIMER,
                        "device_id": "living_room_tv_2",
                        "duration_minutes": 20,
                    },
                },
            ),
            "ice_cream": normalize_reward(
                "ice_cream",
                {
                    "name": "Ice Cream",
                    "cost": 50,
                    "reward_type": REWARD_PARENT_FULFILLED,
                    "auto_approve": False,
                },
            ),
        }

        # Smart action auto-executes Screen Time timer and deducts 40 stars
        await self.engine.async_redeem_reward("tv_20m", "madeleine")
        self.assertEqual(self.storage.data["kids"]["madeleine"]["points"], 60)
        self.hass.services.async_call.assert_any_call(
            "passable_smart_screen_time_engine",
            "start_timer",
            {
                "device_id": "living_room_tv_2",
                "mode": "unlock",
                "duration": 20,
                "unit": "minutes",
                "power_on": False,
            },
            blocking=False,
        )

        # Parent-fulfilled holds 50 stars as pending -> denying refunds 50 stars
        rdm = await self.engine.async_redeem_reward("ice_cream", "madeleine")
        self.assertEqual(rdm["status"], REDEMPTION_PENDING)
        self.assertEqual(self.storage.data["kids"]["madeleine"]["points"], 10)

        resolved = await self.engine.async_resolve_redemption(rdm["redemption_id"], approved=False)
        self.assertEqual(resolved["status"], REDEMPTION_DENIED)
        self.assertEqual(self.storage.data["kids"]["madeleine"]["points"], 60)


if __name__ == "__main__":
    unittest.main()
