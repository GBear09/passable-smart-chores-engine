# Changelog

All notable changes to **Passable Smart Chores Engine** will be documented in this file.

## [1.0.2] - 2026-11-25

### 🐛 Fixed
- **Unlock Rule Edit Dropdowns Opening Blank**: Fixed Lit `<select>` initial selection timing across all Command Center and Card Editor forms (including **Child**, **Screen Time Device**, **Target Entity**, and **Weekly Due Day**) by binding `?selected` directly on `<option>` elements so saved selections load reliably when editing an existing rule or chore.
- **Immediate Mid-Day Evaluation for New / Edited Unlock Rules**: Newly created or rebound unlock rules now evaluate and apply their initial lock/unlock state immediately on save (without overriding manual parent unlocks on later 60s ticks), and dispatch `SIGNAL_STORAGE_UPDATED` so WebSocket listeners stay synchronized.
- **Unlock Rule List & Validation**: Added validation toasts before saving incomplete rules, resolved friendly kid/device names on rule rows, highlighted incomplete rules needing attention, and exposed live `is_satisfied` + `status_reason` in WebSocket snapshots.

### ✨ Added
- **Command Center Quick Guides & Contextual Field Help**:
  - Added compact, collapsible **How It Works** setup guides at the top of **Kids & Trust**, **Chores**, **Screen Unlocks**, **Rewards Shop**, and **Settings & PIN** (auto-expanded while a section is empty, collapsed cleanly once configured).
  - Added dynamic inline descriptions directly below **Unlock Scope** and **Target Integration / Mode** explaining what **Passable Screen Time Engine**, **Lockout Switch**, **Power Switch / TV**, and **Nintendo Switch Max Time** do, plus a **Unlocked Daily Limit (Minutes)** input for Nintendo Switch rules.

## [1.0.1] - 2026-11-25

### ✨ Improved (Streamlined Command Center & User-Based Admin Visibility)
- **List-First Collapsible Command Center Forms**:
  - **Chores**, **Kids & Trust**, **Screen Unlocks**, and **Rewards Shop** now open directly to clean lists of your configured items with `+ Add` and `✏️ Edit` buttons that auto-collapse on save/cancel.
  - Added a 2-way segmented toggle inside **Unlocks & Rewards** (`Screen Unlocks` | `Rewards Shop`) and full **Edit Reward** support (including Smart Action target configuration).
  - Moved less-used chore options (Trust override, Custom Image URL) under a collapsible **More options** toggle.
- **Dropdown & Native Multi-Select Controls (Fewer Pill Clouds)**:
  - Replaced starter chore template pills with a **`Quick-fill from a starter template…`** dropdown.
  - Replaced inline emoji/avatar pill walls with compact **icon picker popovers** (`[🧹 ▾]` / `[👧 ▾]`) next to the name field.
  - Replaced kid filter and reset button rows with compact dropdown selectors (`All Kids`, `Reset…`), and upgraded **No-School / Holiday Calendars** and **Parent Push Notification Targets** to native Home Assistant multi-select `<ha-selector>` dropdowns.
  - Added **Weekly Rollover Day** and **Weekly Required-By Day** selectors directly inside **Settings & PIN**.
- **User-Based Admin Controls Visibility**:
  - Replaced the single kiosk toggle with **Admin Setup Controls Visibility** (`everyone`, `admins_only`, `selected_users`, `hidden`) plus a Home Assistant user checklist (`admin_users` populated via `config/auth/list`, matching HA's native **Visibility → User** tab while remaining backwards-compatible with `hide_admin_setup`).
  - Also gates inline chore approval buttons (`⏳ Approve`, `✓` / `↺`) behind admin visibility or Parental PIN protection.

### 🐛 Fixed
- **Paused Child Profiles**: Children with `Profile Active = Off` (`enabled: false`) now stay hidden even when `hide_inactive_kids: false` is set, and enabled kids with `0` chores display a clean `"No chores scheduled today"` placeholder in Board mode.

## [1.0.0] - 2026-11-24

### ✨ Added (Initial Release)
- **Native Home Assistant Integration (`passable_smart_chores_engine`)**:
  - Atomic `.storage` persistence (`Store`) for kid profiles, chores, completions, rewards, redemptions, device unlock rules, security PINs, and activity logs—zero manual helper clutter.
  - Configurable daily reset boundary (`05:00` AM default), weekly rollover day (`Monday` default), and weekly due-day promotion (`Saturday` default).
  - Schedule types: `daily`, `school_days` (with optional `calendar.*` holiday/break detection and 1-tap manual No-School override), `weekends`, `weekly` (flexible all-week visibility that promotes to required on due day), and `custom_days`.
  - Assignment modes: `each` (per-kid), `rotate_weekly` (deterministic weekly turn-taking across active kids), and `up_for_grabs` (bonus bounties).
  - Configurable Trust Mode (`honor_system` vs. `parent_approval`) at global, per-kid (`switch.<kid>_require_parent_approval`), and per-chore levels, with a 15s undo window and actionable mobile push notifications (`Approve` / `Try Again`).
  - Two-tier hybrid gamification (`points`, `streaks` preserving days with `0` required chores, and `rewards` shop with instant Smart Home auto-rewards and refund-safe parent-fulfilled requests).
  - Personal & Shared (`any_active_kid` / `all_active_kids`) device unlock engine integrating with `Passable Smart Screen Time Engine`, lockout switches, power switches, and Nintendo Switch `number.*` limits, excluding 0-chore kids from premature unlocks and respecting downtime schedules.
- **Bundled Passable Chores Card (`passable-chores-card.js`)**:
  - Auto-registered Lovelace module resource with Passable Suite design-system parity (`passable-hvac-card`, `passable-vehicle-card`, `passable-lighting-card`, `passable-screen-time-card`).
  - Four layouts (`board` default kid columns with large emoji/picture tiles, `tiles`, `rows`, and `rings`), inline quick-drawer (`approvals`, `bounties`, `rewards`, per-kid), 4-tab Command Center popup (`Chores`, `Kids & Trust`, `Unlocks & Rewards`, `Activity & Setup`), Parental PIN keypad modal, and visual config editor.
- **Full Entity & Service Suite**:
  - Global and per-kid `sensor`, `binary_sensor`, `switch`, and `button` entities, plus 10 native Home Assistant service actions and event bus notifications.
