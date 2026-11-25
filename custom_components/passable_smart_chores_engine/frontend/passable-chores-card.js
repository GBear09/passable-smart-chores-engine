/**
 * Passable Chores Card
 * Bundled companion card for Passable Smart Chores Engine
 * https://github.com/GBear09/passable-smart-chores-engine
 *
 * Version 1.0.2 - Unlock Rule Edit Fix, Immediate Rule Eval & Command Center Guides
 */

const CARD_VERSION = "1.0.2";
const ENGINE_DOMAIN = "passable_smart_chores_engine";

const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace") ||
    customElements.get("hui-entities-card") ||
    customElements.get("hui-masonry-view") ||
    customElements.get("hc-main")
);
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;
const svg =
  LitElement.prototype.svg ||
  ((strings, ...values) => {
    const result = html(strings, ...values);
    if (result && typeof result === "object") {
      return Object.assign({}, result, { _$litType$: 2, type: "svg" });
    }
    return result;
  });

console.info(
  `%c PASSABLE-CHORES-CARD %c v${CARD_VERSION} IS LOADED `,
  "color: #ffffff; background: #10b981; font-weight: bold; padding: 2px 6px; border-radius: 4px 0 0 4px;",
  "color: #047857; background: #d1fae5; font-weight: bold; padding: 2px 6px; border-radius: 0 4px 4px 0;"
);

const MODAL_TABS = [
  { id: "chores", label: "Chores", icon: "mdi:clipboard-check-outline" },
  { id: "kids", label: "Kids & Trust", icon: "mdi:account-child-circle" },
  { id: "unlocks", label: "Unlocks & Rewards", icon: "mdi:television-lock" },
  { id: "setup", label: "Activity & Setup", icon: "mdi:cog-outline" },
];

const DAYS_LIST = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
const DAYS_SHORT = ["S", "M", "T", "W", "T", "F", "S"];

const KID_AVATAR_PRESETS = ["👧", "👦", "🧒", "👶", "🦄", "🦖", "🚀", "⚽", "🎨", "🐱"];
const KID_COLOR_PRESETS = [
  "#8E24AA",
  "#039BE5",
  "#4285F4",
  "#009688",
  "#f59e0b",
  "#22c55e",
  "#ec4899",
  "#6366f1",
];

const CHORE_EMOJI_PRESETS = [
  "🛏️", "🪥", "🧹", "🐕", "🍽️", "🎒", "🧺", "🗑️", "📚", "🧸", "🧼", "🫧", "🌱", "🎹", "🚿", "🥣",
];

const CHORE_STARTER_TEMPLATES = [
  { name: "Make Bed", emoji: "🛏️", tier: "required", schedule_type: "daily", assignment_mode: "each", points: 5 },
  { name: "Brush Teeth", emoji: "🪥", tier: "required", schedule_type: "daily", assignment_mode: "each", points: 5 },
  { name: "Pack Backpack", emoji: "🎒", tier: "required", schedule_type: "school_days", assignment_mode: "each", points: 5 },
  { name: "Clear Dishes", emoji: "🍽️", tier: "required", schedule_type: "daily", assignment_mode: "each", points: 5 },
  { name: "Clean Room", emoji: "🧹", tier: "required", schedule_type: "weekly", assignment_mode: "each", points: 15 },
  { name: "Feed Pet", emoji: "🐕", tier: "required", schedule_type: "daily", assignment_mode: "rotate_weekly", points: 10 },
  { name: "Put Away Laundry", emoji: "🧺", tier: "required", schedule_type: "weekends", assignment_mode: "each", points: 10 },
  { name: "Vacuum Playroom", emoji: "🫧", tier: "bonus", schedule_type: "daily", assignment_mode: "up_for_grabs", points: 20 },
];

const REWARD_EMOJI_PRESETS = ["📺", "🎮", "🍦", "🎬", "💵", "🍕", "⏰", "🎉"];

function hexToRgba(hex, alpha) {
  const clean = String(hex || "#039BE5").replace("#", "").trim();
  if (!/^[0-9a-fA-F]{6}$/.test(clean)) return `rgba(3, 155, 229, ${alpha})`;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

class PassableChoresCard extends LitElement {
  static getConfigElement() {
    return document.createElement("passable-chores-card-editor");
  }

  static getStubConfig() {
    return {
      title: "Family Chores",
      subtitle: "Smart Chores, Streaks & Screen Unlocks",
      display_mode: "summary",
      layout: "board",
      tile_size: "large",
      show_header: false,
      show_summary_strip: true,
      show_footer_strip: true,
      hide_inactive_kids: true,
      kids_filter: [],
      require_pin: "auto",
      admin_visibility: "everyone",
      admin_users: [],
      hide_admin_setup: false,
    };
  }

  static get properties() {
    return {
      hass: { attribute: false },
      config: { state: true },
      _wsData: { state: true },
      _wsError: { state: true },
      _drawerMode: { state: true },
      _selectedRewardKidId: { state: true },
      _selectedBountyKidId: { state: true },
      _celebratingKids: { state: true },
      _modalOpen: { state: true },
      _modalTab: { state: true },
      _choreFilterKid: { state: true },
      _choreFormOpen: { state: true },
      _choreMoreOpen: { state: true },
      _editingChoreId: { state: true },
      _choreDraft: { state: true },
      _kidFormOpen: { state: true },
      _kidCustomAvatar: { state: true },
      _editingKidId: { state: true },
      _kidDraft: { state: true },
      _unlocksSubTab: { state: true },
      _ruleFormOpen: { state: true },
      _editingRuleId: { state: true },
      _ruleDraft: { state: true },
      _rewardFormOpen: { state: true },
      _editingRewardId: { state: true },
      _rewardDraft: { state: true },
      _emojiPickerTarget: { state: true },
      _guideOpen: { state: true },
      _setupSubTab: { state: true },
      _secCurrentPin: { state: true },
      _secNewPin: { state: true },
      _secPinEnabled: { state: true },
      _secReqApprovals: { state: true },
      _secReqSettings: { state: true },
      _pinModalOpen: { state: true },
      _pinInput: { state: true },
      _pinError: { state: true },
      _pinUnlockedUntil: { state: true },
      _toastMsg: { state: true },
      _tickNow: { state: true },
    };
  }

  constructor() {
    super();
    this._wsData = null;
    this._wsError = null;
    this._wsUnsub = null;
    this._wsSubscribing = false;
    this._drawerMode = null;
    this._selectedRewardKidId = null;
    this._selectedBountyKidId = null;
    this._celebratingKids = {};
    this._prevKidAllDone = {};
    this._modalOpen = false;
    this._modalTab = "chores";
    this._choreFilterKid = "all";
    this._choreFormOpen = false;
    this._choreMoreOpen = false;
    this._editingChoreId = null;
    this._choreDraft = this._emptyChoreDraft();
    this._kidFormOpen = false;
    this._kidCustomAvatar = false;
    this._editingKidId = null;
    this._kidDraft = this._emptyKidDraft();
    this._unlocksSubTab = "unlocks";
    this._ruleFormOpen = false;
    this._editingRuleId = null;
    this._ruleDraft = this._emptyRuleDraft();
    this._rewardFormOpen = false;
    this._editingRewardId = null;
    this._rewardDraft = this._emptyRewardDraft();
    this._emojiPickerTarget = null;
    this._guideOpen = {};
    this._setupSubTab = "settings";

    this._secCurrentPin = "";
    this._secNewPin = "";
    this._secPinEnabled = false;
    this._secReqApprovals = true;
    this._secReqSettings = true;
    this._secSynced = false;

    this._pinModalOpen = false;
    this._pinInput = "";
    this._pinError = null;
    this._pinUnlockedUntil = 0;
    this._pendingProtectedFn = null;

    this._toastMsg = null;
    this._tickNow = Date.now();
    this._countdownInterval = null;
    this._toastTimer = null;
    this._closeModalTimer = null;
    this._celebrationTimers = {};

    this._touchStartY = undefined;
    this._touchStartX = undefined;
    this._touchCurrentY = undefined;
    this._touchTarget = null;
    this._touchInScroll = false;
    this._touchDragging = false;
    this._touchLockedHorizontal = false;
    this._swipeResetTimer = null;
    this._scrollLockedElements = null;
    this._scrollGuardOverlay = null;
    this._guardTouchY = 0;
    this._guardTouchX = 0;
    this._onOverlayWheel = this._onOverlayWheel.bind(this);
    this._onOverlayTouchStart = this._onOverlayTouchStart.bind(this);
    this._onOverlayTouchMove = this._onOverlayTouchMove.bind(this);
    this._onKeyDown = (ev) => {
      if (ev.key === "Escape") {
        if (this._pinModalOpen) this._closePinModal();
        else if (this._modalOpen) this._closeModal();
      }
    };
  }

  _emptyKidDraft() {
    return {
      kid_id: null,
      name: "",
      avatar: "👧",
      accent_color: "#8E24AA",
      enabled: true,
      trust_mode: "inherit",
    };
  }

  _emptyChoreDraft() {
    return {
      chore_id: null,
      name: "",
      emoji: "🧹",
      image: "",
      enabled: true,
      tier: "required",
      schedule_type: "daily",
      custom_days: ["mon", "wed", "fri"],
      weekly_due_day: "",
      weekly_flexible: true,
      assignment_mode: "each",
      assigned_kids: [],
      points: 5,
      trust_mode: "inherit",
    };
  }

  _emptyRuleDraft() {
    return {
      rule_id: null,
      name: "",
      enabled: true,
      scope: "shared",
      kid_id: "",
      shared_mode: "any_active_kid",
      target_mode: "passable_screen_time",
      screen_time_device_id: "",
      target_entity: "",
      nintendo_bonus_minutes: 60,
      lock_on_reset: true,
      re_lock_if_uncompleted: true,
      respect_screen_time_schedules: true,
    };
  }

  _emptyRewardDraft() {
    return {
      reward_id: null,
      name: "",
      emoji: "🎁",
      cost: 50,
      reward_type: "parent_fulfilled",
      auto_approve: false,
      action_kind: "screen_time_timer",
      device_id: "all",
      entity_id: "",
      duration_minutes: 20,
      service: "",
    };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    const displayMode = config.display_mode === "full" ? "full" : "summary";
    const defaultShowHeader = displayMode === "full";
    const layout = ["board", "tiles", "rows", "rings"].includes(config.layout)
      ? config.layout
      : "board";
    const legacyHide = config.hide_admin_setup === true;
    const hasAdminUsers = Array.isArray(config.admin_users) && config.admin_users.length > 0;
    const adminVisibility = ["everyone", "admins_only", "selected_users", "hidden"].includes(config.admin_visibility)
      ? config.admin_visibility
      : legacyHide
        ? "hidden"
        : hasAdminUsers
          ? "selected_users"
          : "everyone";
    this.config = {
      title: config.title !== undefined ? config.title : "Family Chores",
      subtitle:
        config.subtitle !== undefined
          ? config.subtitle
          : "Smart Chores, Streaks & Screen Unlocks",
      display_mode: displayMode,
      layout,
      tile_size: config.tile_size === "compact" ? "compact" : "large",
      show_header:
        config.show_header !== undefined
          ? config.show_header !== false
          : defaultShowHeader,
      show_summary_strip: config.show_summary_strip !== false,
      show_footer_strip: config.show_footer_strip !== false,
      hide_inactive_kids: config.hide_inactive_kids !== false,
      kids_filter: Array.isArray(config.kids_filter) ? config.kids_filter : [],
      require_pin: config.require_pin !== undefined ? config.require_pin : "auto",
      admin_visibility: adminVisibility,
      admin_users: Array.isArray(config.admin_users) ? config.admin_users : [],
      hide_admin_setup: adminVisibility === "hidden",
      ...config,
      admin_visibility: adminVisibility,
      admin_users: Array.isArray(config.admin_users) ? config.admin_users : [],
      hide_admin_setup: adminVisibility === "hidden",
    };
  }

  getCardSize() {
    if (this.config?.display_mode === "full") return 8;
    const layout = this.config?.layout || "board";
    if (layout === "rings" || layout === "tiles") return 3;
    return 5;
  }

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", this._onKeyDown);
    if (this.hass && !this._wsUnsub && !this._wsSubscribing) {
      this._subscribeEngine();
    }
    this._syncCountdownTimer();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this._onKeyDown);
    this._detachOverlayScrollGuard();
    this._unlockBackgroundScroll();
    this._unsubscribeEngine();
    clearInterval(this._countdownInterval);
    this._countdownInterval = null;
    clearTimeout(this._toastTimer);
    clearTimeout(this._closeModalTimer);
    clearTimeout(this._swipeResetTimer);
    Object.values(this._celebrationTimers).forEach((t) => clearTimeout(t));
  }

  updated(changedProps) {
    super.updated(changedProps);
    if (
      changedProps.has("hass") &&
      this.hass &&
      !this._wsUnsub &&
      !this._wsSubscribing &&
      !this._wsData
    ) {
      this._subscribeEngine();
    }
    if (
      (this._modalOpen && this.config?.display_mode !== "full") ||
      this._pinModalOpen
    ) {
      this._attachOverlayScrollGuard();
    } else {
      this._detachOverlayScrollGuard();
    }
  }

  shouldUpdate(changedProps) {
    if (!changedProps.has("hass")) return true;
    for (const key of changedProps.keys()) {
      if (key !== "hass") return true;
    }
    const oldHass = changedProps.get("hass");
    const newHass = this.hass;
    if (!oldHass || !newHass || !oldHass.states || !newHass.states) return true;
    return oldHass.states["sensor.passable_chores_summary"] !== newHass.states["sensor.passable_chores_summary"];
  }

  // =========================================================================
  // WEBSOCKET SUBSCRIPTION & COUNTDOWN GATING
  // =========================================================================

  async _subscribeEngine() {
    if (!this.hass || this._wsSubscribing) return;
    this._wsSubscribing = true;
    try {
      this._wsUnsub = await this.hass.connection.subscribeMessage(
        (snapshot) => this._handleSnapshot(snapshot),
        { type: `${ENGINE_DOMAIN}/subscribe` }
      );
      this._wsError = null;
    } catch (err) {
      this._wsError = err?.message || "Failed to connect to Passable Smart Chores Engine";
    } finally {
      this._wsSubscribing = false;
    }
  }

  _unsubscribeEngine() {
    if (typeof this._wsUnsub === "function") {
      try {
        this._wsUnsub();
      } catch (_e) {}
    }
    this._wsUnsub = null;
  }

  _handleSnapshot(snapshot) {
    if (!snapshot) return;

    // Detect newly completed 100% kids for celebration burst
    const nextKids = snapshot.kids || [];
    const hadBaseline = Object.keys(this._prevKidAllDone).length > 0;
    nextKids.forEach((kid) => {
      const wasDone = this._prevKidAllDone[kid.kid_id];
      if (
        hadBaseline &&
        wasDone === false &&
        kid.is_all_done_today &&
        snapshot.settings?.celebrations_enabled !== false
      ) {
        this._triggerCelebration(kid.kid_id);
      }
      this._prevKidAllDone[kid.kid_id] = Boolean(kid.is_all_done_today);
    });

    this._wsData = snapshot;
    this._wsError = null;

    if (!this._secSynced && snapshot.security) {
      this._secPinEnabled = Boolean(snapshot.security.pin_enabled);
      this._secReqApprovals = snapshot.security.require_pin_for_approvals !== false;
      this._secReqSettings = snapshot.security.require_pin_for_settings !== false;
      this._secSynced = true;
    }

    if (!this._selectedRewardKidId && nextKids.length > 0) {
      const firstActive = nextKids.find((k) => k.enabled) || nextKids[0];
      this._selectedRewardKidId = firstActive.kid_id;
      this._selectedBountyKidId = firstActive.kid_id;
    }

    this._syncCountdownTimer();
  }

  _triggerCelebration(kidId) {
    clearTimeout(this._celebrationTimers[kidId]);
    this._celebratingKids = { ...this._celebratingKids, [kidId]: true };
    this._celebrationTimers[kidId] = setTimeout(() => {
      const next = { ...this._celebratingKids };
      delete next[kidId];
      this._celebratingKids = next;
    }, 2600);
  }

  _hasActiveUndoCountdown() {
    const now = Date.now();
    for (const kid of this._wsData?.kids || []) {
      for (const item of kid.board || []) {
        if (item.undo_expires_at && new Date(item.undo_expires_at).getTime() > now) {
          return true;
        }
      }
    }
    return false;
  }

  _syncCountdownTimer() {
    const needsTick = this._hasActiveUndoCountdown();
    if (needsTick && !this._countdownInterval) {
      this._tickNow = Date.now();
      this._countdownInterval = setInterval(() => {
        this._tickNow = Date.now();
        if (!this._hasActiveUndoCountdown()) {
          clearInterval(this._countdownInterval);
          this._countdownInterval = null;
        }
      }, 1000);
    } else if (!needsTick && this._countdownInterval) {
      clearInterval(this._countdownInterval);
      this._countdownInterval = null;
    }
  }

  _getUndoRemainingSecs(item) {
    if (!item?.undo_expires_at) return 0;
    const diff = Math.ceil((new Date(item.undo_expires_at).getTime() - this._tickNow) / 1000);
    return diff > 0 ? diff : 0;
  }

  // =========================================================================
  // HELPERS, HAPTICS, TOASTS & PARENTAL PIN
  // =========================================================================

  _fireHaptic(type = "light") {
    this.dispatchEvent(
      new CustomEvent("haptic", { detail: type, bubbles: true, composed: true })
    );
  }

  _showToast(msg) {
    this._toastMsg = msg;
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      this._toastMsg = null;
    }, 2600);
  }

  _isPinSessionUnlocked() {
    return Date.now() < this._pinUnlockedUntil;
  }

  _requiresPin(actionKind) {
    if (this.config?.require_pin === false) return false;
    const sec = this._wsData?.security;
    if (!sec?.pin_enabled) return false;
    if (sec.bypass_for_ha_admins && this.hass?.user?.is_admin && this.config?.require_pin !== true) {
      return false;
    }
    if (this._isPinSessionUnlocked()) return false;
    if (actionKind === "approvals") return sec.require_pin_for_approvals !== false;
    if (actionKind === "settings") return sec.require_pin_for_settings !== false;
    return true;
  }

  _runProtectedAction(actionKind, fn) {
    if (!this._requiresPin(actionKind)) {
      return fn();
    }
    this._pendingProtectedFn = fn;
    this._pinInput = "";
    this._pinError = null;
    this._pinModalOpen = true;
    this._lockBackgroundScroll();
  }

  _closePinModal() {
    this._pinModalOpen = false;
    this._pinInput = "";
    this._pinError = null;
    this._pendingProtectedFn = null;
    if (!this._modalOpen) this._unlockBackgroundScroll();
  }

  _lockPinSession() {
    this._pinUnlockedUntil = 0;
    this._showToast("Parent PIN locked");
  }

  async _submitPinModal() {
    if (!this._pinInput || this._pinInput.length < 4) {
      this._pinError = "Enter 4–6 digits";
      return;
    }
    try {
      const res = await this.hass.callWS({
        type: `${ENGINE_DOMAIN}/verify_pin`,
        pin: this._pinInput,
      });
      if (!res?.valid) {
        this._fireHaptic("failure");
        this._pinError = "Incorrect PIN";
        this._pinInput = "";
        return;
      }
      this._fireHaptic("success");
      this._pinUnlockedUntil = Date.now() + 60000;
      const fn = this._pendingProtectedFn;
      this._closePinModal();
      if (fn) await fn();
    } catch (err) {
      this._pinError = err?.message || "PIN check failed";
    }
  }

  // =========================================================================
  // CHORE, APPROVAL, REWARD & RULE ACTIONS
  // =========================================================================

  async _onChoreTileClick(kid, item, ev) {
    if (ev) ev.stopPropagation();
    if (!this.hass) return;
    this._fireHaptic("light");

    if (item.status === "pending") {
      try {
        const res = await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/complete_chore`,
          chore_id: item.chore_id,
          kid_id: kid.kid_id,
          by_parent: false,
        });
        this._fireHaptic("success");
        if (res?.status === "waiting_approval") {
          this._showToast(`Sent to parents for approval ⏳`);
        }
      } catch (err) {
        this._showToast(err?.message || "Could not complete chore");
      }
      return;
    }

    // Completed or Waiting Approval: allow undo during undo window, or parent override
    const undoLeft = this._getUndoRemainingSecs(item);
    if (undoLeft > 0 || item.status === "waiting_approval") {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/uncomplete_chore`,
          chore_id: item.chore_id,
          kid_id: kid.kid_id,
        });
        this._showToast(`Reset "${item.name}"`);
      } catch (err) {
        this._showToast(err?.message || "Could not undo");
      }
      return;
    }

    // After undo window expires, require parent PIN if configured to uncheck
    return this._runProtectedAction("approvals", async () => {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/uncomplete_chore`,
          chore_id: item.chore_id,
          kid_id: kid.kid_id,
        });
        this._showToast(`Unchecked "${item.name}"`);
      } catch (err) {
        this._showToast(err?.message || "Could not uncheck");
      }
    });
  }

  _approveChore(choreId, kidId, ev = null) {
    if (ev) ev.stopPropagation();
    return this._runProtectedAction("approvals", async () => {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/approve_chore`,
          chore_id: choreId,
          kid_id: kidId,
        });
        this._fireHaptic("success");
        this._showToast("Chore approved!");
      } catch (err) {
        this._showToast(err?.message || "Approval failed");
      }
    });
  }

  _rejectChore(choreId, kidId, ev = null) {
    if (ev) ev.stopPropagation();
    return this._runProtectedAction("approvals", async () => {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/reject_chore`,
          chore_id: choreId,
          kid_id: kidId,
        });
        this._fireHaptic("warning");
        this._showToast("Sent back to Try Again");
      } catch (err) {
        this._showToast(err?.message || "Reject failed");
      }
    });
  }

  _approveAllPending(kidId = null) {
    return this._runProtectedAction("approvals", async () => {
      try {
        const res = await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/approve_all_pending`,
          kid_id: kidId,
        });
        this._fireHaptic("success");
        this._showToast(`Approved ${res?.approved_count || 0} chore(s)`);
      } catch (err) {
        this._showToast(err?.message || "Approve all failed");
      }
    });
  }

  async _claimBounty(choreId, kidId) {
    if (!kidId) {
      this._showToast("Select a kid first");
      return;
    }
    this._fireHaptic("light");
    try {
      const res = await this.hass.callWS({
        type: `${ENGINE_DOMAIN}/complete_chore`,
        chore_id: choreId,
        kid_id: kidId,
      });
      this._fireHaptic("success");
      this._showToast(
        res?.status === "waiting_approval"
          ? "Bonus claimed — waiting parent approval"
          : "Bonus chore claimed!"
      );
    } catch (err) {
      this._showToast(err?.message || "Could not claim bonus");
    }
  }

  async _redeemReward(rewardId, kidId) {
    if (!kidId) {
      this._showToast("Select a kid first");
      return;
    }
    this._fireHaptic("light");
    try {
      const res = await this.hass.callWS({
        type: `${ENGINE_DOMAIN}/redeem_reward`,
        reward_id: rewardId,
        kid_id: kidId,
      });
      this._fireHaptic("success");
      this._showToast(
        res?.redemption?.status === "approved"
          ? "Reward redeemed & activated!"
          : "Reward requested — waiting parent approval"
      );
    } catch (err) {
      this._showToast(err?.message || "Could not redeem reward");
    }
  }

  _resolveRedemption(redemptionId, approved) {
    return this._runProtectedAction("approvals", async () => {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/resolve_redemption`,
          redemption_id: redemptionId,
          approved,
        });
        this._fireHaptic(approved ? "success" : "warning");
        this._showToast(approved ? "Reward fulfilled!" : "Reward refunded");
      } catch (err) {
        this._showToast(err?.message || "Failed to resolve request");
      }
    });
  }

  _adjustPoints(kidId, delta) {
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/adjust_points`,
          kid_id: kidId,
          delta,
          reason: delta > 0 ? "Parent Star Bonus" : "Parent Star Deduction",
        });
        this._fireHaptic("light");
        this._showToast(`${delta > 0 ? "+" : ""}${delta} ⭐ updated`);
      } catch (err) {
        this._showToast(err?.message || "Failed to adjust stars");
      }
    });
  }

  // =========================================================================
  // CRUD ACTIONS (KIDS, CHORES, REWARDS, UNLOCK RULES, SETTINGS)
  // =========================================================================

  _saveKid() {
    if (!this._kidDraft.name.trim()) {
      this._showToast("Enter a child's name");
      return;
    }
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/save_kid`,
          kid_id: this._kidDraft.kid_id,
          name: this._kidDraft.name.trim(),
          avatar: this._kidDraft.avatar || "🧒",
          accent_color: this._kidDraft.accent_color || "#039BE5",
          enabled: this._kidDraft.enabled !== false,
          trust_mode: this._kidDraft.trust_mode || "inherit",
        });
        this._editingKidId = null;
        this._kidFormOpen = false;
        this._kidCustomAvatar = false;
        this._emojiPickerTarget = null;
        this._kidDraft = this._emptyKidDraft();
        this._fireHaptic("success");
        this._showToast("Child profile saved");
      } catch (err) {
        this._showToast(err?.message || "Failed to save child");
      }
    });
  }

  _deleteKid(kidId, name) {
    if (!confirm(`Delete "${name}" and remove their chore assignments?`)) return;
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({ type: `${ENGINE_DOMAIN}/delete_kid`, kid_id: kidId });
        if (this._drawerMode === kidId) this._drawerMode = null;
        this._showToast("Child removed");
      } catch (err) {
        this._showToast(err?.message || "Delete failed");
      }
    });
  }

  _saveChore() {
    if (!this._choreDraft.name.trim()) {
      this._showToast("Enter a chore name");
      return;
    }
    return this._runProtectedAction("settings", async () => {
      try {
        const d = this._choreDraft;
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/save_chore`,
          chore_id: d.chore_id,
          name: d.name.trim(),
          emoji: d.emoji || "🧹",
          image: d.image ? d.image.trim() : null,
          enabled: d.enabled !== false,
          tier: d.tier || "required",
          schedule_type: d.schedule_type || "daily",
          custom_days: d.custom_days || [],
          weekly_due_day: d.weekly_due_day || null,
          weekly_flexible: d.weekly_flexible !== false,
          assignment_mode: d.assignment_mode || "each",
          assigned_kids: d.assigned_kids || [],
          points: Number(d.points) || 0,
          trust_mode: d.trust_mode || "inherit",
        });
        this._editingChoreId = null;
        this._choreFormOpen = false;
        this._choreMoreOpen = false;
        this._emojiPickerTarget = null;
        this._choreDraft = this._emptyChoreDraft();
        this._fireHaptic("success");
        this._showToast("Chore saved");
      } catch (err) {
        this._showToast(err?.message || "Failed to save chore");
      }
    });
  }

  _deleteChore(choreId, name) {
    if (!confirm(`Delete chore "${name}"?`)) return;
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({ type: `${ENGINE_DOMAIN}/delete_chore`, chore_id: choreId });
        this._showToast("Chore deleted");
      } catch (err) {
        this._showToast(err?.message || "Delete failed");
      }
    });
  }

  _rotateChore(choreId) {
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/rotate_chore`,
          chore_id: choreId,
          steps: 1,
        });
        this._showToast("Turn rotated");
      } catch (err) {
        this._showToast(err?.message || "Rotate failed");
      }
    });
  }

  _saveUnlockRule() {
    const r = this._ruleDraft;
    if (!r.name.trim()) {
      this._showToast("Enter a rule name");
      return;
    }
    if (r.scope === "personal" && !r.kid_id) {
      this._showToast("Select a child for this personal rule");
      return;
    }
    if (r.target_mode === "passable_screen_time" && !r.screen_time_device_id) {
      this._showToast("Select a Screen Time device");
      return;
    }
    if (r.target_mode !== "passable_screen_time" && !r.target_entity) {
      this._showToast("Select a target entity");
      return;
    }
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/save_unlock_rule`,
          rule_id: r.rule_id,
          name: r.name.trim(),
          enabled: r.enabled !== false,
          scope: r.scope || "shared",
          kid_id: r.scope === "personal" ? r.kid_id || null : null,
          shared_mode: r.shared_mode || "any_active_kid",
          target_mode: r.target_mode || "passable_screen_time",
          screen_time_device_id: r.target_mode === "passable_screen_time" ? r.screen_time_device_id || null : null,
          target_entity: r.target_mode !== "passable_screen_time" ? r.target_entity || null : null,
          nintendo_bonus_minutes: Number(r.nintendo_bonus_minutes) || 60,
          lock_on_reset: r.lock_on_reset !== false,
          re_lock_if_uncompleted: r.re_lock_if_uncompleted !== false,
          respect_screen_time_schedules: r.respect_screen_time_schedules !== false,
        });
        this._editingRuleId = null;
        this._ruleFormOpen = false;
        this._ruleDraft = this._emptyRuleDraft();
        this._fireHaptic("success");
        this._showToast("Device unlock rule saved");
      } catch (err) {
        this._showToast(err?.message || "Failed to save rule");
      }
    });
  }

  _deleteUnlockRule(ruleId) {
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({ type: `${ENGINE_DOMAIN}/delete_unlock_rule`, rule_id: ruleId });
        this._showToast("Rule deleted");
      } catch (err) {
        this._showToast(err?.message || "Delete failed");
      }
    });
  }

  _saveReward() {
    const d = this._rewardDraft;
    if (!d.name.trim()) {
      this._showToast("Enter a reward name");
      return;
    }
    if (d.reward_type === "smart_action" && d.action_kind === "nintendo_bonus" && !d.entity_id) {
      this._showToast("Select a Nintendo Switch limit entity");
      return;
    }
    return this._runProtectedAction("settings", async () => {
      try {
        const smartAction =
          d.reward_type === "smart_action"
            ? {
                action_kind: d.action_kind || "screen_time_timer",
                device_id: d.device_id || "all",
                entity_id: d.entity_id || null,
                duration_minutes: Number(d.duration_minutes) || 20,
                service: d.service || null,
              }
            : null;
        await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/save_reward`,
          reward_id: d.reward_id,
          name: d.name.trim(),
          emoji: d.emoji || "🎁",
          cost: Number(d.cost) || 25,
          reward_type: d.reward_type || "parent_fulfilled",
          auto_approve: d.reward_type === "smart_action" ? d.auto_approve !== false : false,
          smart_action: smartAction,
          enabled: true,
        });
        this._editingRewardId = null;
        this._rewardFormOpen = false;
        this._emojiPickerTarget = null;
        this._rewardDraft = this._emptyRewardDraft();
        this._fireHaptic("success");
        this._showToast("Reward saved");
      } catch (err) {
        this._showToast(err?.message || "Failed to save reward");
      }
    });
  }

  _deleteReward(rewardId) {
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({ type: `${ENGINE_DOMAIN}/delete_reward`, reward_id: rewardId });
        this._showToast("Reward deleted");
      } catch (err) {
        this._showToast(err?.message || "Delete failed");
      }
    });
  }

  _saveSettingsPatch(patch, toast = "Settings saved") {
    return this._runProtectedAction("settings", async () => {
      try {
        await this.hass.callWS({ type: `${ENGINE_DOMAIN}/save_settings`, ...patch });
        this._fireHaptic("light");
        if (toast) this._showToast(toast);
      } catch (err) {
        this._showToast(err?.message || "Failed to save settings");
      }
    });
  }

  _resetChores(scope) {
    return this._runProtectedAction("settings", async () => {
      try {
        const res = await this.hass.callWS({
          type: `${ENGINE_DOMAIN}/reset_chores`,
          scope,
        });
        this._fireHaptic("success");
        this._showToast(`Reset ${res?.cleared || 0} ${scope} chore(s)`);
      } catch (err) {
        this._showToast(err?.message || "Reset failed");
      }
    });
  }

  _seedSampleData() {
    return this._runProtectedAction("settings", async () => {
      try {
        const res = await this.hass.callWS({ type: `${ENGINE_DOMAIN}/seed_sample_data` });
        this._fireHaptic("success");
        this._showToast(`Added ${res?.chores_added || 0} chores & ${res?.rewards_added || 0} rewards`);
      } catch (err) {
        this._showToast(err?.message || "Seed failed");
      }
    });
  }

  async _saveSecuritySettings() {
    return this._runProtectedAction("settings", async () => {
      try {
        const payload = {
          type: `${ENGINE_DOMAIN}/save_security_settings`,
          pin_enabled: this._secPinEnabled,
          require_pin_for_approvals: this._secReqApprovals,
          require_pin_for_settings: this._secReqSettings,
        };
        if (this._wsData?.security?.pin_enabled) {
          payload.current_pin = this._secCurrentPin;
        }
        if (this._secNewPin.trim() !== "") {
          payload.new_pin = this._secNewPin.trim();
        }
        const res = await this.hass.callWS(payload);
        this._secCurrentPin = "";
        this._secNewPin = "";
        if (res?.security) {
          this._secPinEnabled = Boolean(res.security.pin_enabled);
        }
        this._fireHaptic("success");
        this._showToast("Parental PIN settings saved");
      } catch (err) {
        this._showToast(err?.message || "Failed to save PIN settings");
      }
    });
  }

  // =========================================================================
  // DRAWER, MODAL & SCROLL GUARD (Passable Design Parity)
  // =========================================================================

  _toggleDrawer(mode, ev = null) {
    if (ev) ev.stopPropagation();
    this._fireHaptic("light");
    this._drawerMode = this._drawerMode === mode ? null : mode;
  }

  _openModal(tab = "chores", ev = null) {
    if (ev) ev.stopPropagation();
    this._fireHaptic("light");
    clearTimeout(this._closeModalTimer);
    clearTimeout(this._swipeResetTimer);
    this._modalTab = tab;
    this._modalOpen = true;
    this._lockBackgroundScroll();
    this.requestUpdate();
  }

  _closeModal() {
    if (!this._modalOpen) return;
    this._fireHaptic("light");
    const overlay = this.shadowRoot?.querySelector(".popup-overlay:not(.pin-overlay)");
    const content = overlay?.querySelector(".popup-content");
    if (overlay && content) {
      overlay.classList.add("closing");
      content.classList.add("closing");
      this._closeModalTimer = setTimeout(() => {
        this._modalOpen = false;
        if (!this._pinModalOpen) this._unlockBackgroundScroll();
      }, 170);
    } else {
      this._modalOpen = false;
      if (!this._pinModalOpen) this._unlockBackgroundScroll();
    }
  }

  _lockBackgroundScroll() {
    if (this._scrollLockedElements) return;
    const locked = [];
    let el = this;
    while (el) {
      if (el instanceof HTMLElement && el !== document.documentElement) {
        const oy = window.getComputedStyle(el).overflowY;
        if ((oy === "auto" || oy === "scroll" || oy === "overlay") && el.scrollHeight > el.clientHeight) {
          locked.push({ el, prevOverflowY: el.style.overflowY });
          el.style.overflowY = "hidden";
        }
      }
      if (el.parentElement) el = el.parentElement;
      else if (el.getRootNode && el.getRootNode() instanceof ShadowRoot) el = el.getRootNode().host;
      else break;
    }
    const docEl = document.documentElement;
    if (docEl) {
      locked.push({ el: docEl, prevOverflowY: docEl.style.overflowY });
      docEl.style.overflowY = "hidden";
    }
    this._scrollLockedElements = locked;
  }

  _unlockBackgroundScroll() {
    if (!this._scrollLockedElements) return;
    for (const item of this._scrollLockedElements) item.el.style.overflowY = item.prevOverflowY;
    this._scrollLockedElements = null;
  }

  _attachOverlayScrollGuard() {
    const overlay = this.shadowRoot?.querySelector(".popup-overlay");
    if (!overlay || this._scrollGuardOverlay === overlay) return;
    this._detachOverlayScrollGuard();
    overlay.addEventListener("wheel", this._onOverlayWheel, { passive: false });
    overlay.addEventListener("touchstart", this._onOverlayTouchStart, { passive: true });
    overlay.addEventListener("touchmove", this._onOverlayTouchMove, { passive: false });
    this._scrollGuardOverlay = overlay;
  }

  _detachOverlayScrollGuard() {
    const overlay = this._scrollGuardOverlay;
    if (!overlay) return;
    overlay.removeEventListener("wheel", this._onOverlayWheel);
    overlay.removeEventListener("touchstart", this._onOverlayTouchStart);
    overlay.removeEventListener("touchmove", this._onOverlayTouchMove);
    this._scrollGuardOverlay = null;
  }

  _findScrollableInEventPath(ev) {
    const path = ev.composedPath ? ev.composedPath() : [];
    for (const node of path) {
      if (!(node instanceof HTMLElement)) continue;
      if (node.classList?.contains("popup-overlay")) break;
      const st = window.getComputedStyle(node);
      if ((st.overflowY === "auto" || st.overflowY === "scroll") && node.scrollHeight > node.clientHeight + 1) {
        return node;
      }
    }
    return null;
  }

  _onOverlayWheel(ev) {
    const scroller = this._findScrollableInEventPath(ev);
    if (!scroller) {
      if (ev.cancelable) ev.preventDefault();
      return;
    }
    const dy = ev.deltaY;
    if ((dy < 0 && scroller.scrollTop <= 0) || (dy > 0 && scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 1)) {
      if (ev.cancelable) ev.preventDefault();
    }
  }

  _onOverlayTouchStart(ev) {
    if (!ev.touches || ev.touches.length !== 1) return;
    this._guardTouchY = ev.touches[0].clientY;
    this._guardTouchX = ev.touches[0].clientX;
  }

  _onOverlayTouchMove(ev) {
    if (!ev.touches || ev.touches.length !== 1) return;
    const scroller = this._findScrollableInEventPath(ev);
    if (!scroller) {
      if (ev.cancelable) ev.preventDefault();
      return;
    }
    const dy = this._guardTouchY - ev.touches[0].clientY;
    const dx = Math.abs(this._guardTouchX - ev.touches[0].clientX);
    if (dx > Math.abs(dy)) return;
    if ((dy < 0 && scroller.scrollTop <= 0) || (dy > 0 && scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 1)) {
      if (ev.cancelable) ev.preventDefault();
    }
  }

  _handlePopupTouchStart(ev) {
    if (ev.touches.length !== 1) return;
    const scrollArea = ev.currentTarget.querySelector(".modal-scroll-area");
    this._touchInScroll = Boolean(scrollArea && scrollArea.contains(ev.target) && scrollArea.scrollTop > 2);
    if (this._touchInScroll) return;
    this._touchStartY = ev.touches[0].clientY;
    this._touchStartX = ev.touches[0].clientX;
    this._touchCurrentY = this._touchStartY;
    this._touchTarget = ev.currentTarget;
    this._touchDragging = false;
    this._touchLockedHorizontal = false;
  }

  _handlePopupTouchMove(ev) {
    if (this._touchInScroll || this._touchStartY === undefined || this._touchLockedHorizontal) return;
    const curY = ev.touches[0].clientY;
    const curX = ev.touches[0].clientX;
    const dy = curY - this._touchStartY;
    const dx = curX - this._touchStartX;
    if (!this._touchDragging) {
      if (Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) {
        this._touchLockedHorizontal = true;
        return;
      }
      if (dy > 10) {
        this._touchDragging = true;
        this._touchTarget.style.transition = "none";
      } else {
        return;
      }
    }
    this._touchCurrentY = curY;
    const offset = Math.max(0, dy);
    this._touchTarget.style.transform = `translateY(${offset}px)`;
    const overlay = this.shadowRoot?.querySelector(".popup-overlay");
    if (overlay) overlay.style.opacity = String(Math.max(0.25, 1 - offset / 380));
  }

  _handlePopupTouchEnd() {
    const target = this._touchTarget;
    const dy = this._touchDragging && this._touchCurrentY !== undefined ? this._touchCurrentY - this._touchStartY : 0;
    const wasDragging = this._touchDragging;
    this._touchStartY = undefined;
    this._touchStartX = undefined;
    this._touchCurrentY = undefined;
    this._touchTarget = null;
    this._touchDragging = false;
    this._touchInScroll = false;
    this._touchLockedHorizontal = false;
    if (!wasDragging || !target) return;
    const overlay = this.shadowRoot?.querySelector(".popup-overlay");
    if (dy > 110) {
      this._closeModal();
      return;
    }
    target.style.transition = "transform 220ms cubic-bezier(0.2, 0, 0, 1)";
    target.style.transform = "";
    if (overlay) overlay.style.opacity = "";
    this._swipeResetTimer = setTimeout(() => {
      if (target) target.style.transition = "";
    }, 240);
  }

  // =========================================================================
  // DATA COMPUTATION & SUMMARY METRICS
  // =========================================================================

  _canViewAdminControls() {
    if (!this.hass) return false;
    const mode = this.config?.admin_visibility || (this.config?.hide_admin_setup ? "hidden" : "everyone");
    if (mode === "hidden") return false;
    if (mode === "admins_only") return this.hass.user?.is_admin === true;
    if (mode === "selected_users") {
      const allowed = Array.isArray(this.config?.admin_users) ? this.config.admin_users : [];
      const uid = this.hass.user?.id;
      const uname = this.hass.user?.name;
      return Boolean((uid && allowed.includes(uid)) || (uname && allowed.includes(uname)));
    }
    return true;
  }

  _canApproveOnCard() {
    return this._canViewAdminControls() || Boolean(this._wsData?.security?.pin_enabled);
  }

  _getVisibleKids() {
    const allKids = this._wsData?.kids || [];
    const filterIds = Array.isArray(this.config?.kids_filter) && this.config.kids_filter.length > 0
      ? new Set(this.config.kids_filter)
      : null;

    return allKids.filter((kid) => {
      if (!kid.enabled) return false;
      if (filterIds && !filterIds.has(kid.kid_id)) return false;
      if (this.config?.hide_inactive_kids !== false && (kid.board || []).length === 0) {
        return false;
      }
      return true;
    });
  }

  _getSummaryMetrics(visibleKids) {
    const pending = this._wsData?.pending_approvals || [];
    const bounties = this._wsData?.bonus_chores || [];
    const rules = (this._wsData?.unlock_rules || []).filter((r) => r.enabled !== false);
    const activeKids = visibleKids.filter((k) => k.required_due_total > 0);
    const totalReq = activeKids.reduce((sum, k) => sum + k.required_due_total, 0);
    const doneReq = activeKids.reduce((sum, k) => sum + k.required_due_completed, 0);
    const allDone = activeKids.length > 0 && doneReq >= totalReq;
    const unlockedRules = rules.filter((r) => r.is_currently_locked === false).length;
    const openBounties = bounties.filter((b) => !b.claimed_by_kid_id).length;

    return {
      totalReq,
      doneReq,
      allDone,
      pendingCount: pending.length,
      openBounties,
      rulesTotal: rules.length,
      unlockedRules,
    };
  }

  // =========================================================================
  // RENDERING: SUMMARY STRIP, 4 LAYOUTS, INLINE DRAWER & FOOTER
  // =========================================================================

  _renderSummaryStrip(visibleKids, metrics) {
    const cycle = this._wsData?.cycle || {};
    const settings = this._wsData?.settings || {};
    const gamified = settings.gamification_enabled !== false;

    const toneClass = metrics.pendingCount > 0
      ? "amber"
      : metrics.allDone
        ? "done"
        : metrics.totalReq > 0
          ? "active"
          : "idle";

    const pillLabel =
      visibleKids.length === 0
        ? "Setup Needed"
        : metrics.totalReq === 0
          ? "No Required Chores"
          : metrics.allDone
            ? `All ${metrics.doneReq}/${metrics.totalReq} Done 🎉`
            : `${metrics.doneReq}/${metrics.totalReq} Done`;

    return html`
      <div class="chores-summary-strip ${toneClass}">
        <div class="summary-strip-left">
          <span class="summary-status-dot ${toneClass}"></span>
          <span class="strip-active-pill ${toneClass}">${pillLabel}</span>
          ${cycle.is_no_school_override
            ? html`<span class="zone-inline-chip info">No School</span>`
            : ""}
          ${metrics.rulesTotal > 0
            ? html`
                <span class="zone-inline-chip ${metrics.unlockedRules > 0 ? "success" : "neutral"}">
                  <ha-icon icon="${metrics.unlockedRules > 0 ? "mdi:television-play" : "mdi:television-lock"}" style="--mdc-icon-size:12px;"></ha-icon>
                  <span>${metrics.unlockedRules}/${metrics.rulesTotal} Unlocked</span>
                </span>
              `
            : ""}
        </div>

        <div class="summary-strip-right">
          ${this._isPinSessionUnlocked()
            ? html`
                <button
                  type="button"
                  class="icon-circle-btn pin-unlocked"
                  @click=${() => this._lockPinSession()}
                  title="Parent session unlocked — tap to lock"
                >
                  <ha-icon icon="mdi:lock-open-check-outline" style="--mdc-icon-size:15px;"></ha-icon>
                </button>
              `
            : ""}

          ${metrics.pendingCount > 0 && this._canApproveOnCard()
            ? html`
                <button
                  type="button"
                  class="zone-inline-chip warning clickable"
                  @click=${() => this._toggleDrawer("approvals")}
                >
                  ⏳ ${metrics.pendingCount} Approve
                </button>
              `
            : ""}

          ${metrics.openBounties > 0
            ? html`
                <button
                  type="button"
                  class="zone-inline-chip info clickable"
                  @click=${() => this._toggleDrawer("bounties")}
                >
                  ⭐ ${metrics.openBounties} Bonus
                </button>
              `
            : ""}

          ${gamified && settings.rewards_enabled !== false && (this._wsData?.rewards || []).length > 0
            ? html`
                <button
                  type="button"
                  class="icon-circle-btn ${this._drawerMode === "rewards" ? "active" : ""}"
                  @click=${() => this._toggleDrawer("rewards")}
                  title="Reward Shop"
                >
                  <ha-icon icon="mdi:gift-outline" style="--mdc-icon-size:16px;"></ha-icon>
                </button>
              `
            : ""}

          ${this._canViewAdminControls()
            ? html`
                <button
                  type="button"
                  class="icon-circle-btn"
                  @click=${() => this._openModal("chores")}
                  title="Open Chores Command Center"
                >
                  <ha-icon icon="mdi:tune-variant" style="--mdc-icon-size:16px;"></ha-icon>
                </button>
              `
            : ""}
        </div>
      </div>
    `;
  }

  _renderAvatar(kid, size = 34) {
    const av = kid.avatar || "🧒";
    const isUrl = av.startsWith("/") || av.startsWith("http");
    return html`
      <div
        class="kid-avatar"
        style="width:${size}px;height:${size}px;border-color:${kid.accent_color};background:${hexToRgba(kid.accent_color, 0.16)};"
      >
        ${isUrl
          ? html`<img src="${av}" alt="${kid.name}" />`
          : html`<span>${av}</span>`}
      </div>
    `;
  }

  _renderChoreTile(kid, item, isLarge = true) {
    const undoLeft = this._getUndoRemainingSecs(item);
    const isDone = item.status === "completed";
    const isWaiting = item.status === "waiting_approval";
    const showPoints =
      this._wsData?.settings?.gamification_enabled !== false &&
      this._wsData?.settings?.points_enabled !== false &&
      item.points > 0;

    return html`
      <div
        class="chore-tile ${isLarge ? "large" : "compact"} ${item.status} ${item.is_due_today_for_unlock ? "" : "flexible"}"
        style="--kid-accent:${kid.accent_color};--kid-accent-soft:${hexToRgba(kid.accent_color, 0.14)};"
        @click=${(ev) => this._onChoreTileClick(kid, item, ev)}
        title=${isDone ? (undoLeft > 0 ? `Tap within ${undoLeft}s to undo` : "Completed") : "Tap to complete"}
      >
        <div class="chore-tile-visual">
          ${item.image
            ? html`<img class="chore-img" src="${item.image}" alt="${item.name}" />`
            : html`<span class="chore-emoji">${item.emoji || "🧹"}</span>`}
        </div>

        <div class="chore-tile-body">
          <div class="chore-tile-name">${item.name}</div>
          <div class="chore-tile-meta">
            ${isWaiting
              ? html`<span class="meta-pill waiting">⏳ Waiting</span>`
              : isDone
                ? html`<span class="meta-pill done">${undoLeft > 0 ? `✓ Undo (${undoLeft}s)` : "✓ Done"}</span>`
                : html`
                    ${item.due_label && !item.is_due_today_for_unlock
                      ? html`<span class="meta-pill neutral">${item.due_label}</span>`
                      : item.due_label && item.is_due_today_for_unlock
                        ? html`<span class="meta-pill due">Required Today</span>`
                        : ""}
                    ${item.is_rotation_turn
                      ? html`<span class="meta-pill turn">🔄 Turn</span>`
                      : ""}
                    ${showPoints
                      ? html`<span class="meta-pill stars">+${item.points} ⭐</span>`
                      : ""}
                  `}
          </div>
        </div>

        <div class="chore-tile-right">
          ${isWaiting
            ? this._canApproveOnCard()
              ? html`
                  <div class="inline-approve-pair" @click=${(ev) => ev.stopPropagation()}>
                    <button
                      type="button"
                      class="mini-approve-btn ok"
                      @click=${(ev) => this._approveChore(item.chore_id, kid.kid_id, ev)}
                      title="Approve chore"
                    >✓</button>
                    <button
                      type="button"
                      class="mini-approve-btn no"
                      @click=${(ev) => this._rejectChore(item.chore_id, kid.kid_id, ev)}
                      title="Send back (Try Again)"
                    >↺</button>
                  </div>
                `
              : html`
                  <div class="chore-check-circle waiting" title="Waiting for parent approval">
                    <ha-icon icon="mdi:clock-outline" style="--mdc-icon-size:18px;"></ha-icon>
                  </div>
                `
            : html`
                <div class="chore-check-circle ${item.status}">
                  <ha-icon
                    icon="${isDone ? "mdi:check-bold" : "mdi:circle-outline"}"
                    style="--mdc-icon-size:18px;"
                  ></ha-icon>
                </div>
              `}
        </div>
      </div>
    `;
  }

  _renderBoardLayout(visibleKids) {
    const settings = this._wsData?.settings || {};
    const showPoints = settings.gamification_enabled !== false && settings.points_enabled !== false;
    const showStreaks = settings.gamification_enabled !== false && settings.streaks_enabled !== false;
    const isLarge = this.config?.tile_size !== "compact";

    return html`
      <div class="kid-board-grid">
        ${visibleKids.map((kid) => {
          const celebrating = Boolean(this._celebratingKids[kid.kid_id]);
          return html`
            <div
              class="kid-column-card ${kid.is_all_done_today ? "all-done" : ""} ${celebrating ? "celebrating" : ""}"
              style="--kid-accent:${kid.accent_color};--kid-accent-soft:${hexToRgba(kid.accent_color, 0.1)};--kid-accent-border:${hexToRgba(kid.accent_color, 0.36)};"
            >
              ${celebrating
                ? html`
                    <div class="confetti-layer" aria-hidden="true">
                      <span>🎉</span><span>⭐</span><span>✨</span><span>🎊</span><span>🌟</span>
                    </div>
                  `
                : ""}
              <div class="kid-col-header">
                <div class="kid-col-identity">
                  ${this._renderAvatar(kid, 36)}
                  <div class="kid-col-titles">
                    <div class="kid-col-name">${kid.name}</div>
                    <div class="kid-col-sub">
                      ${kid.is_all_done_today
                        ? html`<span class="done-text">All Done! 🎉</span>`
                        : kid.required_due_total > 0
                          ? html`<span>${kid.required_due_completed}/${kid.required_due_total} required</span>`
                          : html`<span>${kid.visible_completed}/${kid.visible_total} optional</span>`}
                    </div>
                  </div>
                </div>

                <div class="kid-col-badges">
                  ${showStreaks && kid.streak_current > 0
                    ? html`<span class="kid-badge fire" title="Current streak">🔥 ${kid.streak_current}</span>`
                    : ""}
                  ${showPoints
                    ? html`
                        <button
                          type="button"
                          class="kid-badge stars clickable"
                          @click=${() => {
                            this._selectedRewardKidId = kid.kid_id;
                            this._toggleDrawer("rewards");
                          }}
                          title="Tap to open ${kid.name}'s Rewards"
                        >⭐ ${kid.points}</button>
                      `
                    : ""}
                </div>
              </div>

              <div class="kid-progress-track">
                <div
                  class="kid-progress-fill"
                  style="width:${kid.progress_pct}%;background:${kid.is_all_done_today ? "#22c55e" : kid.accent_color};"
                ></div>
              </div>

              <div class="kid-chore-list">
                ${(kid.board || []).length > 0
                  ? (kid.board || []).map((item) => this._renderChoreTile(kid, item, isLarge))
                  : html`<div class="kid-empty-board">No chores scheduled today</div>`}
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  _renderTilesLayout(visibleKids) {
    return html`
      <div class="kid-tiles-grid">
        ${visibleKids.map((kid, idx) => {
          const isSelected = this._drawerMode === kid.kid_id;
          const spanClass = visibleKids.length % 2 === 1 && idx === visibleKids.length - 1 ? "span-2" : "";
          return html`
            <div
              class="kid-summary-tile ${spanClass} ${kid.is_all_done_today ? "all-done" : ""} ${isSelected ? "selected" : ""}"
              style="--kid-accent:${kid.accent_color};"
              @click=${() => this._toggleDrawer(kid.kid_id)}
            >
              <div class="tile-main">
                <div class="tile-identity">
                  ${this._renderAvatar(kid, 34)}
                  <div class="tile-text">
                    <div class="tile-name">${kid.name}</div>
                    <div class="tile-sub">
                      ${kid.is_all_done_today
                        ? "All Done! 🎉"
                        : `${kid.required_due_completed}/${kid.required_due_total} required`}
                      ${kid.streak_current > 0 ? ` · 🔥${kid.streak_current}` : ""}
                    </div>
                  </div>
                </div>
                <div class="tile-stat" style="color:${kid.is_all_done_today ? "#16a34a" : kid.accent_color};">
                  ${kid.progress_pct}%
                </div>
              </div>
              <div class="tile-hairline">
                <div
                  class="tile-hairline-fill"
                  style="width:${kid.progress_pct}%;background:${kid.is_all_done_today ? "#22c55e" : kid.accent_color};"
                ></div>
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  _renderRowsLayout(visibleKids) {
    return html`
      <div class="kid-rows-stack">
        ${visibleKids.map((kid) => {
          const isSelected = this._drawerMode === kid.kid_id;
          return html`
            <div
              class="kid-summary-row ${kid.is_all_done_today ? "all-done" : ""} ${isSelected ? "selected" : ""}"
              @click=${() => this._toggleDrawer(kid.kid_id)}
            >
              <div class="tile-identity">
                ${this._renderAvatar(kid, 34)}
                <div class="tile-text">
                  <div class="tile-name">${kid.name}</div>
                  <div class="tile-sub">
                    ${kid.required_due_completed}/${kid.required_due_total} required
                    ${kid.streak_current > 0 ? ` · 🔥 ${kid.streak_current}` : ""}
                    ${kid.points > 0 ? ` · ⭐ ${kid.points}` : ""}
                  </div>
                </div>
              </div>
              <div class="row-right">
                <span class="tile-stat" style="color:${kid.is_all_done_today ? "#16a34a" : kid.accent_color};">
                  ${kid.progress_pct}%
                </span>
                <ha-icon icon="${isSelected ? "mdi:chevron-up" : "mdi:chevron-down"}" style="--mdc-icon-size:16px;"></ha-icon>
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  _renderRingsLayout(visibleKids) {
    const r = 16;
    const c = 2 * Math.PI * r;
    return html`
      <div class="kid-rings-grid" style="grid-template-columns:repeat(${Math.max(1, visibleKids.length)}, minmax(0, 1fr));">
        ${visibleKids.map((kid) => {
          const isSelected = this._drawerMode === kid.kid_id;
          const pct = Math.max(0, Math.min(100, kid.progress_pct || 0));
          const dash = (pct / 100) * c;
          const stroke = kid.is_all_done_today ? "#22c55e" : kid.accent_color;
          return html`
            <button
              type="button"
              class="ring-tile-btn ${isSelected ? "selected" : ""}"
              @click=${() => this._toggleDrawer(kid.kid_id)}
            >
              <div class="ring-wrap">
                ${svg`<svg class="ring-svg" viewBox="0 0 40 40">
                  <circle cx="20" cy="20" r="${r}" fill="none" stroke="rgba(148,163,184,0.18)" stroke-width="3.2"></circle>
                  <circle cx="20" cy="20" r="${r}" fill="none" stroke="${stroke}" stroke-width="3.2" stroke-linecap="round"
                    stroke-opacity="${pct > 0 ? 1 : 0}" stroke-dasharray="${dash} ${c}"></circle>
                </svg>`}
                <span class="ring-val">${kid.avatar || `${pct}%`}</span>
              </div>
              <span class="ring-name">${kid.name}</span>
              <span class="ring-sub">${kid.required_due_completed}/${kid.required_due_total}${kid.streak_current > 0 ? ` 🔥${kid.streak_current}` : ""}</span>
            </button>
          `;
        })}
      </div>
    `;
  }

  _renderInlineDrawer(visibleKids) {
    if (!this._drawerMode) return "";

    if (this._drawerMode === "approvals") {
      const pending = this._wsData?.pending_approvals || [];
      return html`
        <div class="chores-drawer">
          <div class="drawer-header">
            <span class="drawer-title">Pending Approvals (${pending.length})</span>
            <div class="drawer-actions">
              ${pending.some((p) => p.kind === "chore")
                ? html`<button type="button" class="drawer-manage-btn" @click=${() => this._approveAllPending()}>Approve All Chores</button>`
                : ""}
              <button type="button" class="drawer-close-btn" @click=${() => (this._drawerMode = null)}>
                <ha-icon icon="mdi:close" style="--mdc-icon-size:16px;"></ha-icon>
              </button>
            </div>
          </div>
          <div class="drawer-list thin-scroll">
            ${pending.length === 0
              ? html`<div class="drawer-empty">Nothing waiting for approval!</div>`
              : pending.map((p) =>
                  p.kind === "chore"
                    ? html`
                        <div class="drawer-row">
                          <div class="drawer-row-left">
                            <span class="drawer-emoji">${p.emoji}</span>
                            <div>
                              <div class="drawer-row-title">${p.title}</div>
                              <div class="drawer-row-sub">${p.kid_avatar} ${p.kid_name} · +${p.points} ⭐</div>
                            </div>
                          </div>
                          <div class="drawer-actions">
                            <button type="button" class="quick-chip green" @click=${() => this._approveChore(p.chore_id, p.kid_id)}>Approve</button>
                            <button type="button" class="quick-chip amber" @click=${() => this._rejectChore(p.chore_id, p.kid_id)}>Try Again</button>
                          </div>
                        </div>
                      `
                    : html`
                        <div class="drawer-row">
                          <div class="drawer-row-left">
                            <span class="drawer-emoji">${p.emoji}</span>
                            <div>
                              <div class="drawer-row-title">${p.title}</div>
                              <div class="drawer-row-sub">${p.kid_avatar} ${p.kid_name} · ${p.cost} ⭐</div>
                            </div>
                          </div>
                          <div class="drawer-actions">
                            <button type="button" class="quick-chip green" @click=${() => this._resolveRedemption(p.redemption_id, true)}>Fulfill</button>
                            <button type="button" class="quick-chip danger" @click=${() => this._resolveRedemption(p.redemption_id, false)}>Refund</button>
                          </div>
                        </div>
                      `
                )}
          </div>
        </div>
      `;
    }

    if (this._drawerMode === "bounties") {
      const bounties = this._wsData?.bonus_chores || [];
      const kids = (this._wsData?.kids || []).filter((k) => k.enabled);
      return html`
        <div class="chores-drawer">
          <div class="drawer-header">
            <span class="drawer-title">⭐ Bonus Chores Up for Grabs</span>
            <button type="button" class="drawer-close-btn" @click=${() => (this._drawerMode = null)}>
              <ha-icon icon="mdi:close" style="--mdc-icon-size:16px;"></ha-icon>
            </button>
          </div>
          ${kids.length > 0
            ? html`
                <div class="kid-selector-pills">
                  <span class="selector-label">Claim as:</span>
                  ${kids.map(
                    (k) => html`
                      <button
                        type="button"
                        class="kid-pick-pill ${this._selectedBountyKidId === k.kid_id ? "active" : ""}"
                        style="--kid-accent:${k.accent_color};"
                        @click=${() => (this._selectedBountyKidId = k.kid_id)}
                      >${k.avatar} ${k.name}</button>
                    `
                  )}
                </div>
              `
            : ""}
          <div class="drawer-list thin-scroll">
            ${bounties.map(
              (b) => html`
                <div class="drawer-row">
                  <div class="drawer-row-left">
                    <span class="drawer-emoji">${b.emoji}</span>
                    <div>
                      <div class="drawer-row-title">${b.name}</div>
                      <div class="drawer-row-sub">
                        +${b.points} ⭐
                        ${b.claimed_by_name ? ` · Claimed by ${b.claimed_by_name}` : " · Open"}
                      </div>
                    </div>
                  </div>
                  ${b.claimed_by_kid_id
                    ? html`<span class="meta-pill done">Claimed</span>`
                    : html`
                        <button
                          type="button"
                          class="quick-chip sky"
                          @click=${() => this._claimBounty(b.chore_id, this._selectedBountyKidId)}
                        >Claim +${b.points} ⭐</button>
                      `}
                </div>
              `
            )}
          </div>
        </div>
      `;
    }

    if (this._drawerMode === "rewards") {
      const rewards = (this._wsData?.rewards || []).filter((r) => r.enabled !== false);
      const kids = (this._wsData?.kids || []).filter((k) => k.enabled);
      const activeKid = kids.find((k) => k.kid_id === this._selectedRewardKidId) || kids[0];
      return html`
        <div class="chores-drawer">
          <div class="drawer-header">
            <span class="drawer-title">🎁 Reward Shop</span>
            <button type="button" class="drawer-close-btn" @click=${() => (this._drawerMode = null)}>
              <ha-icon icon="mdi:close" style="--mdc-icon-size:16px;"></ha-icon>
            </button>
          </div>
          ${kids.length > 0
            ? html`
                <div class="kid-selector-pills">
                  ${kids.map(
                    (k) => html`
                      <button
                        type="button"
                        class="kid-pick-pill ${activeKid?.kid_id === k.kid_id ? "active" : ""}"
                        style="--kid-accent:${k.accent_color};"
                        @click=${() => (this._selectedRewardKidId = k.kid_id)}
                      >${k.avatar} ${k.name} (${k.points} ⭐)</button>
                    `
                  )}
                </div>
              `
            : ""}
          <div class="drawer-list thin-scroll">
            ${rewards.length === 0
              ? html`<div class="drawer-empty">No rewards configured yet.</div>`
              : rewards.map((rw) => {
                  const canAfford = activeKid && activeKid.points >= rw.cost;
                  return html`
                    <div class="drawer-row">
                      <div class="drawer-row-left">
                        <span class="drawer-emoji">${rw.emoji}</span>
                        <div>
                          <div class="drawer-row-title">${rw.name}</div>
                          <div class="drawer-row-sub">${rw.cost} ⭐ · ${rw.reward_type === "smart_action" ? "Instant Smart Action" : "Parent Fulfilled"}</div>
                        </div>
                      </div>
                      <button
                        type="button"
                        class="quick-chip ${canAfford ? "green" : ""}"
                        ?disabled=${!canAfford}
                        @click=${() => this._redeemReward(rw.reward_id, activeKid?.kid_id)}
                      >Redeem</button>
                    </div>
                  `;
                })}
          </div>
        </div>
      `;
    }

    // Per-kid drawer (used for tiles / rows / rings layouts)
    const kid = visibleKids.find((k) => k.kid_id === this._drawerMode);
    if (!kid) return "";
    return html`
      <div class="chores-drawer">
        <div class="drawer-header">
          <span class="drawer-title">${kid.avatar} ${kid.name}'s Chores</span>
          <button type="button" class="drawer-close-btn" @click=${() => (this._drawerMode = null)}>
            <ha-icon icon="mdi:close" style="--mdc-icon-size:16px;"></ha-icon>
          </button>
        </div>
        <div class="kid-chore-list">
          ${(kid.board || []).map((item) => this._renderChoreTile(kid, item, this.config?.tile_size !== "compact"))}
        </div>
      </div>
    `;
  }

  _renderFooterStrip(metrics) {
    if (this.config?.show_footer_strip === false) return "";
    const settings = this._wsData?.settings || {};
    const cycle = this._wsData?.cycle || {};
    return html`
      <div class="engine-footer-strip">
        <div class="footer-chips">
          ${metrics.openBounties > 0
            ? html`
                <button type="button" class="footer-chip sky" @click=${() => this._toggleDrawer("bounties")}>
                  ⭐ ${metrics.openBounties} Bonus
                </button>
              `
            : ""}
          ${settings.gamification_enabled !== false && settings.rewards_enabled !== false
            ? html`
                <button type="button" class="footer-chip" @click=${() => this._toggleDrawer("rewards")}>
                  🎁 Rewards
                </button>
              `
            : ""}
          ${metrics.pendingCount > 0 && this._canApproveOnCard()
            ? html`
                <button type="button" class="footer-chip amber" @click=${() => this._toggleDrawer("approvals")}>
                  ⏳ ${metrics.pendingCount} Waiting
                </button>
              `
            : ""}
          ${cycle.manual_no_school_active
            ? html`<span class="footer-chip sky">No-School Active</span>`
            : ""}
        </div>

        ${this._canViewAdminControls()
          ? html`
              <button type="button" class="footer-command-link" @click=${() => this._openModal("chores")}>
                Command Center →
              </button>
            `
          : ""}
      </div>
    `;
  }

  // =========================================================================
  // 4-TAB COMMAND CENTER MODAL (STREAMLINED LIST-FIRST + DROPDOWNS)
  // =========================================================================

  _renderEmojiPopoverButton(targetKey, currentValue, presets, onSelect, allowCustomUrl = false) {
    const isOpen = this._emojiPickerTarget === targetKey;
    const isUrl = String(currentValue || "").startsWith("/") || String(currentValue || "").startsWith("http");
    const displayEmoji = isUrl ? "🖼️" : currentValue || presets[0];

    return html`
      <div class="emoji-picker-wrap" @click=${(ev) => ev.stopPropagation()}>
        <button
          type="button"
          class="emoji-trigger-btn ${isOpen ? "open" : ""}"
          @click=${(ev) => {
            ev.stopPropagation();
            this._emojiPickerTarget = isOpen ? null : targetKey;
          }}
          title="Choose icon"
        >
          <span class="emoji-trigger-val">${displayEmoji}</span>
          <span class="emoji-trigger-caret">▾</span>
        </button>

        ${isOpen
          ? html`
              <div class="emoji-popover" @click=${(ev) => ev.stopPropagation()}>
                <div class="emoji-popover-grid">
                  ${presets.map(
                    (em) => html`
                      <button
                        type="button"
                        class="emoji-chip ${currentValue === em ? "active" : ""}"
                        @click=${() => {
                          onSelect(em);
                          this._emojiPickerTarget = null;
                        }}
                      >${em}</button>
                    `
                  )}
                </div>
                <div class="emoji-popover-custom">
                  <input
                    class="field-input"
                    type="text"
                    placeholder=${allowCustomUrl ? "Emoji or /local/img.png" : "Custom emoji"}
                    .value=${currentValue || ""}
                    @input=${(ev) => onSelect(ev.target.value)}
                  />
                </div>
              </div>
            `
          : ""}
      </div>
    `;
  }

  _renderModal() {
    if (!this._modalOpen && this.config?.display_mode !== "full") return "";
    if (this.config?.display_mode === "full") return "";

    return html`
      <div class="popup-overlay" @click=${() => this._closeModal()}>
        <div
          class="popup-content"
          @click=${(ev) => {
            ev.stopPropagation();
            if (this._emojiPickerTarget) this._emojiPickerTarget = null;
          }}
          @touchstart=${(ev) => this._handlePopupTouchStart(ev)}
          @touchmove=${(ev) => this._handlePopupTouchMove(ev)}
          @touchend=${() => this._handlePopupTouchEnd()}
          @touchcancel=${() => this._handlePopupTouchEnd()}
        >
          <div class="drag-handle"></div>
          <div class="popup-header">
            <div class="popup-header-left">
              <ha-icon icon="mdi:clipboard-check-multiple-outline" style="color:#10b981;--mdc-icon-size:24px;"></ha-icon>
              <div>
                <h3>Chores Command Center</h3>
                <div class="popup-header-sub">Cycle ${this._wsData?.cycle?.cycle_date || ""} · Reset ${this._wsData?.cycle?.daily_reset_time || "05:00"}</div>
              </div>
            </div>
            <button type="button" class="close-button" @click=${() => this._closeModal()}>
              <ha-icon icon="mdi:close" style="--mdc-icon-size:20px;"></ha-icon>
            </button>
          </div>

          <div class="popup-tabs">
            ${MODAL_TABS.map(
              (t) => html`
                <button
                  type="button"
                  class="popup-tab ${this._modalTab === t.id ? "active-tab" : ""}"
                  @click=${() => {
                    this._fireHaptic("light");
                    this._emojiPickerTarget = null;
                    this._modalTab = t.id;
                  }}
                >
                  <ha-icon icon="${t.icon}"></ha-icon>
                  <span>${t.label}</span>
                </button>
              `
            )}
          </div>

          <div class="modal-scroll-area thin-scroll">
            ${this._renderTabContent()}
          </div>
        </div>
      </div>
    `;
  }

  _renderQuickGuide(guideKey, title, summary, bullets, isEmpty = false) {
    const isOpen = this._guideOpen?.[guideKey] !== undefined ? this._guideOpen[guideKey] : isEmpty;
    return html`
      <div class="guide-banner">
        <button
          type="button"
          class="guide-header"
          @click=${() => {
            this._guideOpen = { ...(this._guideOpen || {}), [guideKey]: !isOpen };
          }}
        >
          <div class="guide-title-wrap">
            <span>💡 <strong>${title}:</strong> ${summary}</span>
          </div>
          <span class="guide-toggle">${isOpen ? "Hide ▴" : "Guide ▾"}</span>
        </button>
        ${isOpen
          ? html`
              <ul class="guide-bullets">
                ${bullets.map((b) => html`<li>${b}</li>`)}
              </ul>
            `
          : ""}
      </div>
    `;
  }

  _renderTabContent() {
    if (this._modalTab === "chores") return this._renderChoresTab();
    if (this._modalTab === "kids") return this._renderKidsTab();
    if (this._modalTab === "unlocks") return this._renderUnlocksRewardsTab();
    return this._renderSetupActivityTab();
  }

  _renderChoresTab() {
    const kids = this._wsData?.kids || [];
    const chores = this._wsData?.chores || [];
    const d = this._choreDraft;
    const filtered = chores.filter(
      (c) => this._choreFilterKid === "all" || (c.assigned_kids || []).includes(this._choreFilterKid)
    );
    const defaultDueDay = (this._wsData?.cycle?.weekly_due_day || "sat").toUpperCase();

    return html`
      <div class="modal-tab-body">
        ${this._renderQuickGuide(
          "chores",
          "Step 2 · Chores",
          "Assign daily, school-day, weekend, or rotating weekly tasks.",
          [
            html`<strong>Required Chores</strong> unlock devices and earn daily 🔥 streaks + the all-done ⭐ bonus.`,
            html`<strong>Flexible Weekly Chores</strong> show all week so kids can work ahead, and only block unlocks on/after the <em>Required-By Day</em> (${defaultDueDay}).`,
            html`<strong>Bonus / Up for Grabs</strong> chores never block screen unlocks—anyone eligible can claim them for extra ⭐.`,
          ],
          chores.length === 0
        )}

        ${this._choreFormOpen
          ? html`
              <div class="passable-section-card editor-card">
                <div class="passable-section-header">
                  <span class="passable-section-title">${d.chore_id ? "Edit Chore" : "New Chore"}</span>
                  <button
                    type="button"
                    class="inline-link-btn muted"
                    @click=${() => {
                      this._choreFormOpen = false;
                      this._choreMoreOpen = false;
                      this._emojiPickerTarget = null;
                      this._choreDraft = this._emptyChoreDraft();
                    }}
                  >Cancel</button>
                </div>

                ${!d.chore_id
                  ? html`
                      <div class="field-group">
                        <select
                          class="field-input"
                          @change=${(ev) => {
                            const idx = ev.target.value;
                            if (idx === "") return;
                            const tpl = CHORE_STARTER_TEMPLATES[Number(idx)];
                            if (tpl) {
                              this._choreDraft = {
                                ...this._emptyChoreDraft(),
                                ...tpl,
                                assigned_kids: kids.filter((k) => k.enabled).map((k) => k.kid_id),
                              };
                            }
                            ev.target.value = "";
                          }}
                        >
                          <option value="">Quick-fill from a starter template…</option>
                          ${CHORE_STARTER_TEMPLATES.map(
                            (tpl, idx) => html`
                              <option value="${idx}">${tpl.emoji} ${tpl.name} (${tpl.schedule_type.replace("_", " ")} · ${tpl.points} ⭐)</option>
                            `
                          )}
                        </select>
                      </div>
                    `
                  : ""}

                <div class="icon-name-row">
                  <div class="field-group">
                    <label class="field-label">Icon</label>
                    ${this._renderEmojiPopoverButton(
                      "chore",
                      d.emoji,
                      CHORE_EMOJI_PRESETS,
                      (val) => (this._choreDraft = { ...d, emoji: val })
                    )}
                  </div>
                  <div class="field-group">
                    <label class="field-label">Chore Name</label>
                    <input
                      class="field-input"
                      type="text"
                      placeholder="e.g. Brush Teeth"
                      .value=${d.name}
                      @input=${(ev) => (this._choreDraft = { ...d, name: ev.target.value })}
                    />
                  </div>
                </div>

                <div class="two-col-grid">
                  <div class="field-group">
                    <label class="field-label">Schedule</label>
                    <select
                      class="field-input"
                      .value=${d.schedule_type}
                      @change=${(ev) => (this._choreDraft = { ...d, schedule_type: ev.target.value })}
                    >
                      <option value="daily" ?selected=${d.schedule_type === "daily"}>Daily</option>
                      <option value="school_days" ?selected=${d.schedule_type === "school_days"}>School Days (Mon–Fri)</option>
                      <option value="weekends" ?selected=${d.schedule_type === "weekends"}>Weekends (+ No-School)</option>
                      <option value="weekly" ?selected=${d.schedule_type === "weekly"}>Weekly</option>
                      <option value="custom_days" ?selected=${d.schedule_type === "custom_days"}>Custom Days</option>
                    </select>
                  </div>
                  <div class="field-group">
                    <label class="field-label">Assignment</label>
                    <select
                      class="field-input"
                      .value=${d.assignment_mode}
                      @change=${(ev) => (this._choreDraft = { ...d, assignment_mode: ev.target.value })}
                    >
                      <option value="each" ?selected=${d.assignment_mode === "each"}>Each Selected Kid</option>
                      <option value="rotate_weekly" ?selected=${d.assignment_mode === "rotate_weekly"}>Take Turns Weekly</option>
                      <option value="up_for_grabs" ?selected=${d.assignment_mode === "up_for_grabs"}>Up for Grabs (Bonus)</option>
                    </select>
                  </div>
                </div>

                ${d.schedule_type === "custom_days"
                  ? html`
                      <div class="day-chips">
                        ${DAYS_LIST.map((day, idx) => {
                          const sel = (d.custom_days || []).includes(day);
                          return html`
                            <button
                              type="button"
                              class="day-chip ${sel ? "selected" : ""}"
                              @click=${() => {
                                const set = new Set(d.custom_days || []);
                                if (set.has(day)) set.delete(day);
                                else set.add(day);
                                this._choreDraft = { ...d, custom_days: DAYS_LIST.filter((x) => set.has(x)) };
                              }}
                            >${DAYS_SHORT[idx]}</button>
                          `;
                        })}
                      </div>
                    `
                  : ""}

                ${d.schedule_type === "weekly"
                  ? html`
                      <div class="two-col-grid">
                        <div class="field-group">
                          <label class="field-label">Required By Day</label>
                          <select
                            class="field-input"
                            .value=${d.weekly_due_day || ""}
                            @change=${(ev) => (this._choreDraft = { ...d, weekly_due_day: ev.target.value })}
                          >
                            <option value="" ?selected=${!(d.weekly_due_day || "")}>Default (${defaultDueDay})</option>
                            ${DAYS_LIST.map((day) => html`<option value="${day}" ?selected=${d.weekly_due_day === day}>${day.toUpperCase()}</option>`)}
                          </select>
                        </div>
                        <div class="switch-control-row" style="align-self:end;padding-bottom:6px;">
                          <span class="switch-title">Show All Week</span>
                          <button
                            type="button"
                            class="m3-switch small ${d.weekly_flexible ? "on" : ""}"
                            @click=${() => (this._choreDraft = { ...d, weekly_flexible: !d.weekly_flexible })}
                          ><span class="m3-knob"></span></button>
                        </div>
                      </div>
                    `
                  : ""}

                <div class="two-col-grid">
                  <div class="field-group">
                    <label class="field-label">Type</label>
                    <select
                      class="field-input"
                      .value=${d.tier}
                      @change=${(ev) => (this._choreDraft = { ...d, tier: ev.target.value })}
                    >
                      <option value="required" ?selected=${d.tier === "required"}>Required (Gates Unlocks)</option>
                      <option value="bonus" ?selected=${d.tier === "bonus"}>Bonus (Extra Stars)</option>
                    </select>
                  </div>
                  <div class="field-group">
                    <label class="field-label">Star Points (⭐)</label>
                    <input
                      class="field-input"
                      type="number"
                      min="0"
                      max="500"
                      .value=${String(d.points)}
                      @input=${(ev) => (this._choreDraft = { ...d, points: Number(ev.target.value) })}
                    />
                  </div>
                </div>

                <div class="field-group">
                  <label class="field-label">${d.assignment_mode === "up_for_grabs" ? "Eligible Kids (leave empty for anyone)" : "Assigned Kids"}</label>
                  <div class="kid-selector-pills">
                    ${kids.map((k) => {
                      const sel = (d.assigned_kids || []).includes(k.kid_id);
                      return html`
                        <button
                          type="button"
                          class="kid-pick-pill ${sel ? "active" : ""}"
                          style="--kid-accent:${k.accent_color};"
                          @click=${() => {
                            const set = new Set(d.assigned_kids || []);
                            if (set.has(k.kid_id)) set.delete(k.kid_id);
                            else set.add(k.kid_id);
                            this._choreDraft = { ...d, assigned_kids: Array.from(set) };
                          }}
                        >${k.avatar} ${k.name}</button>
                      `;
                    })}
                  </div>
                </div>

                <button
                  type="button"
                  class="inline-link-btn"
                  style="align-self:flex-start;"
                  @click=${() => (this._choreMoreOpen = !this._choreMoreOpen)}
                >
                  ${this._choreMoreOpen ? "Hide advanced options ▴" : "More options (Approval override, Custom image) ▾"}
                </button>

                ${this._choreMoreOpen
                  ? html`
                      <div class="two-col-grid">
                        <div class="field-group">
                          <label class="field-label">Trust / Approval Override</label>
                          <select
                            class="field-input"
                            .value=${d.trust_mode}
                            @change=${(ev) => (this._choreDraft = { ...d, trust_mode: ev.target.value })}
                          >
                            <option value="inherit" ?selected=${d.trust_mode === "inherit"}>Inherit Kid / Global Default</option>
                            <option value="honor_system" ?selected=${d.trust_mode === "honor_system"}>Always Honor System</option>
                            <option value="parent_approval" ?selected=${d.trust_mode === "parent_approval"}>Always Parent Approval</option>
                          </select>
                        </div>
                        <div class="field-group">
                          <label class="field-label">Custom Image URL (Optional)</label>
                          <input
                            class="field-input"
                            type="text"
                            placeholder="/local/chores/bed.png"
                            .value=${d.image || ""}
                            @input=${(ev) => (this._choreDraft = { ...d, image: ev.target.value })}
                          />
                        </div>
                      </div>
                    `
                  : ""}

                <button type="button" class="primary-cta-btn" @click=${() => this._saveChore()}>
                  ${d.chore_id ? "Update Chore" : "Save Chore"}
                </button>
              </div>
            `
          : ""}

        <div class="passable-section-card">
          <div class="passable-section-header wrap">
            <div class="header-left-group">
              <span class="passable-section-title">Chores (${filtered.length})</span>
              <select
                class="compact-select"
                .value=${this._choreFilterKid}
                @change=${(ev) => (this._choreFilterKid = ev.target.value)}
                aria-label="Filter chores by child"
              >
                <option value="all" ?selected=${this._choreFilterKid === "all"}>All Kids</option>
                ${kids.map((k) => html`<option value="${k.kid_id}" ?selected=${this._choreFilterKid === k.kid_id}>${k.avatar} ${k.name}</option>`)}
              </select>
            </div>
            <div class="drawer-actions">
              <select
                class="compact-select"
                @change=${(ev) => {
                  const scope = ev.target.value;
                  if (scope) this._resetChores(scope);
                  ev.target.value = "";
                }}
                aria-label="Reset chores"
              >
                <option value="">Reset…</option>
                <option value="daily">Reset Daily</option>
                <option value="weekly">Reset Weekly</option>
                <option value="all">Reset All</option>
              </select>
              ${!this._choreFormOpen
                ? html`
                    <button
                      type="button"
                      class="mini-primary-btn"
                      @click=${() => {
                        this._choreDraft = {
                          ...this._emptyChoreDraft(),
                          assigned_kids: kids.filter((k) => k.enabled).map((k) => k.kid_id),
                        };
                        this._choreMoreOpen = false;
                        this._choreFormOpen = true;
                      }}
                    >+ Add</button>
                  `
                : ""}
            </div>
          </div>

          ${filtered.length === 0
            ? html`<div class="muted-hint">No chores configured yet. Tap "+ Add" to create your first chore.</div>`
            : filtered.map(
                (c) => html`
                  <div class="drawer-row">
                    <div class="drawer-row-left">
                      <span class="drawer-emoji">${c.emoji}</span>
                      <div>
                        <div class="drawer-row-title">${c.name}</div>
                        <div class="drawer-row-sub">${c.schedule_type} · ${c.assignment_mode} · ${c.points} ⭐</div>
                      </div>
                    </div>
                    <div class="drawer-actions">
                      ${c.assignment_mode === "rotate_weekly"
                        ? html`<button type="button" class="icon-mini-btn" @click=${() => this._rotateChore(c.chore_id)} title="Rotate turn"><ha-icon icon="mdi:rotate-right" style="--mdc-icon-size:15px;"></ha-icon></button>`
                        : ""}
                      <button
                        type="button"
                        class="icon-mini-btn"
                        @click=${() => {
                          this._choreDraft = { ...c, weekly_due_day: c.weekly_due_day || "" };
                          this._choreMoreOpen = Boolean(c.image || (c.trust_mode && c.trust_mode !== "inherit"));
                          this._choreFormOpen = true;
                        }}
                        title="Edit"
                      ><ha-icon icon="mdi:pencil-outline" style="--mdc-icon-size:15px;"></ha-icon></button>
                      <button
                        type="button"
                        class="icon-mini-btn danger"
                        @click=${() => this._deleteChore(c.chore_id, c.name)}
                        title="Delete"
                      ><ha-icon icon="mdi:trash-can-outline" style="--mdc-icon-size:15px;"></ha-icon></button>
                    </div>
                  </div>
                `
              )}
        </div>
      </div>
    `;
  }

  _renderKidsTab() {
    const kids = this._wsData?.kids || [];
    const k = this._kidDraft;
    return html`
      <div class="modal-tab-body">
        ${this._renderQuickGuide(
          "kids",
          "Step 1 · Kids & Trust",
          "Create child profiles and choose instant completion or parent approval.",
          [
            html`<strong>Honor System:</strong> Tapping a chore finishes it right away (with a 15s tap-again undo window) and awards ⭐.`,
            html`<strong>Parent Approval:</strong> Tapping marks it ⏳ Waiting and alerts parent phones with <em>Approve / Try Again</em> before awarding ⭐ or unlocking screens.`,
            html`<strong>Board Visibility:</strong> Kids with 0 chores scheduled today stay hidden on the card until assigned (or toggle <em>Hide Kids With 0 Chores</em> in Card Settings).`,
          ],
          kids.length === 0
        )}

        ${this._kidFormOpen
          ? html`
              <div class="passable-section-card editor-card">
                <div class="passable-section-header">
                  <span class="passable-section-title">${k.kid_id ? "Edit Child Profile" : "Add Child"}</span>
                  <button
                    type="button"
                    class="inline-link-btn muted"
                    @click=${() => {
                      this._kidFormOpen = false;
                      this._kidCustomAvatar = false;
                      this._emojiPickerTarget = null;
                      this._kidDraft = this._emptyKidDraft();
                    }}
                  >Cancel</button>
                </div>

                <div class="icon-name-row">
                  <div class="field-group">
                    <label class="field-label">Avatar</label>
                    ${this._renderEmojiPopoverButton(
                      "kid",
                      k.avatar,
                      KID_AVATAR_PRESETS,
                      (val) => (this._kidDraft = { ...k, avatar: val }),
                      true
                    )}
                  </div>
                  <div class="field-group">
                    <label class="field-label">Child Name</label>
                    <input
                      class="field-input"
                      type="text"
                      placeholder="e.g. Madeleine"
                      .value=${k.name}
                      @input=${(ev) => (this._kidDraft = { ...k, name: ev.target.value })}
                    />
                  </div>
                </div>

                ${this._kidCustomAvatar
                  ? html`
                      <div class="field-group">
                        <label class="field-label">Avatar Image URL (/local/...)</label>
                        <input
                          class="field-input"
                          type="text"
                          placeholder="/local/avatars/madeleine.jpg"
                          .value=${k.avatar}
                          @input=${(ev) => (this._kidDraft = { ...k, avatar: ev.target.value })}
                        />
                      </div>
                    `
                  : html`
                      <button
                        type="button"
                        class="inline-link-btn"
                        style="align-self:flex-start;"
                        @click=${() => (this._kidCustomAvatar = true)}
                      >Use custom /local/ image URL</button>
                    `}

                <div class="field-group">
                  <label class="field-label">Accent Color</label>
                  <div class="color-swatches-row">
                    ${KID_COLOR_PRESETS.map(
                      (col) => html`
                        <button
                          type="button"
                          class="color-swatch ${k.accent_color === col ? "active" : ""}"
                          style="background:${col};"
                          @click=${() => (this._kidDraft = { ...k, accent_color: col })}
                        ></button>
                      `
                    )}
                  </div>
                </div>

                <div class="two-col-grid">
                  <div class="field-group">
                    <label class="field-label">Trust Mode</label>
                    <select
                      class="field-input"
                      .value=${k.trust_mode}
                      @change=${(ev) => (this._kidDraft = { ...k, trust_mode: ev.target.value })}
                    >
                      <option value="inherit" ?selected=${k.trust_mode === "inherit"}>Inherit Global Setting</option>
                      <option value="honor_system" ?selected=${k.trust_mode === "honor_system"}>Honor System (Instant)</option>
                      <option value="parent_approval" ?selected=${k.trust_mode === "parent_approval"}>Require Parent Approval</option>
                    </select>
                  </div>
                  <div class="switch-control-row" style="align-self:end;padding-bottom:6px;">
                    <span class="switch-title">Profile Active</span>
                    <button
                      type="button"
                      class="m3-switch small ${k.enabled !== false ? "on" : ""}"
                      @click=${() => (this._kidDraft = { ...k, enabled: !(k.enabled !== false) })}
                    ><span class="m3-knob"></span></button>
                  </div>
                </div>

                <button type="button" class="primary-cta-btn" @click=${() => this._saveKid()}>
                  ${k.kid_id ? "Update Child" : "Save Child"}
                </button>
              </div>
            `
          : ""}

        <div class="passable-section-card">
          <div class="passable-section-header">
            <span class="passable-section-title">Children (${kids.length})</span>
            ${!this._kidFormOpen
              ? html`
                  <button
                    type="button"
                    class="mini-primary-btn"
                    @click=${() => {
                      this._kidDraft = this._emptyKidDraft();
                      this._kidCustomAvatar = false;
                      this._kidFormOpen = true;
                    }}
                  >+ Add Child</button>
                `
              : ""}
          </div>
          ${kids.length === 0
            ? html`<div class="muted-hint">Tap "+ Add Child" to create your kids' profiles.</div>`
            : kids.map(
                (kid) => html`
                  <div class="drawer-row">
                    <div class="drawer-row-left">
                      ${this._renderAvatar(kid, 32)}
                      <div>
                        <div class="drawer-row-title">${kid.name} ${!kid.enabled ? "(Paused)" : ""}</div>
                        <div class="drawer-row-sub">⭐ ${kid.points} · 🔥 ${kid.streak_current}d · ${kid.effective_trust_mode === "parent_approval" ? "Approval Req" : "Honor System"}</div>
                      </div>
                    </div>
                    <div class="drawer-actions">
                      <button type="button" class="tiny-preset-btn" @click=${() => this._adjustPoints(kid.kid_id, 5)}>+5⭐</button>
                      <button type="button" class="tiny-preset-btn" @click=${() => this._adjustPoints(kid.kid_id, -5)}>-5⭐</button>
                      <button
                        type="button"
                        class="icon-mini-btn"
                        @click=${() => {
                          this._kidDraft = { ...kid };
                          this._kidCustomAvatar = Boolean(kid.avatar && (kid.avatar.startsWith("/") || kid.avatar.startsWith("http")));
                          this._kidFormOpen = true;
                        }}
                      ><ha-icon icon="mdi:pencil-outline" style="--mdc-icon-size:15px;"></ha-icon></button>
                      <button
                        type="button"
                        class="icon-mini-btn danger"
                        @click=${() => this._deleteKid(kid.kid_id, kid.name)}
                      ><ha-icon icon="mdi:trash-can-outline" style="--mdc-icon-size:15px;"></ha-icon></button>
                    </div>
                  </div>
                `
              )}
        </div>
      </div>
    `;
  }

  _renderUnlocksRewardsTab() {
    const kids = this._wsData?.kids || [];
    const rules = this._wsData?.unlock_rules || [];
    const rewards = this._wsData?.rewards || [];
    const cands = this._wsData?.candidates || {};
    const stDevices = cands.screen_time_devices || [];
    const r = this._ruleDraft;
    const rw = this._rewardDraft;

    const scopeHelp =
      r.scope === "personal"
        ? "Unlocks when this specific child finishes 100% of their required chores due today."
        : "Unlocks a shared device (like a living room TV) when either the first active child finishes or all kids with chores today finish.";

    const targetModeHelp = {
      passable_screen_time:
        "Recommended: Calls Passable Screen Time Engine (set_lockout) to pause Wi-Fi or lock TVs, and waits until morning if downtime/bedtime is active.",
      lockout_switch:
        "Directly flips a standalone switch entity where ON = blocked/paused and OFF = allowed (for switches not in Screen Time Engine).",
      power_switch:
        "Directly turns a smart plug or media_player OFF while locked and ON when chores finish.",
      nintendo_switch:
        "Sets a Nintendo Switch parental-control daily limit entity to 0 min while locked, then restores your chosen minutes when unlocked.",
    }[r.target_mode] || "";

    const getFriendlyTargetName = (rule) => {
      const mode = rule.target_mode || "passable_screen_time";
      if (mode === "passable_screen_time") {
        if (!rule.screen_time_device_id) return null;
        if (rule.screen_time_device_id === "all") return "All Screen Time Devices";
        return stDevices.find((d) => d.device_id === rule.screen_time_device_id)?.name || rule.screen_time_device_id;
      }
      if (!rule.target_entity) return null;
      const pool = mode === "nintendo_switch" ? cands.nintendo_numbers || [] : cands.switches || [];
      return pool.find((e) => e.entity_id === rule.target_entity)?.name || rule.target_entity;
    };

    const getFriendlyScopeLabel = (rule) => {
      if (rule.scope === "personal") {
        if (!rule.kid_id) return "Personal (No child selected)";
        const kname = kids.find((kid) => kid.kid_id === rule.kid_id)?.name || rule.kid_id;
        return `Personal (${kname})`;
      }
      return rule.shared_mode === "all_active_kids" ? "Shared (All active kids)" : "Shared (Any active kid)";
    };

    return html`
      <div class="modal-tab-body">
        <div class="segmented-tabs two-up">
          <button
            type="button"
            class="seg-tab ${this._unlocksSubTab === "unlocks" ? "active sky" : ""}"
            @click=${() => (this._unlocksSubTab = "unlocks")}
          >Screen Unlocks (${rules.length})</button>
          <button
            type="button"
            class="seg-tab ${this._unlocksSubTab === "rewards" ? "active sky" : ""}"
            @click=${() => (this._unlocksSubTab = "rewards")}
          >Rewards Shop (${rewards.length})</button>
        </div>

        ${this._unlocksSubTab === "unlocks"
          ? html`
              ${this._renderQuickGuide(
                "unlocks",
                "Step 3 · Screen Unlocks",
                "Automatically lock tablets, TVs, or switches until required chores are 100% done.",
                [
                  html`<strong>Auto-Lock & Unlock:</strong> Locks at morning reset (and right when saved if chores are incomplete today), then unlocks as soon as required chores reach 100%.`,
                  html`<strong>0-Chore Safeguard & Latch:</strong> Kids with 0 chores today are ignored. Unlocks happen once per day so manual evening locks won't be overwritten.`,
                  html`<strong>Passable Screen Time Engine:</strong> Best choice for tablets/TVs already managed there—it handles anti-bypass and respects bedtime downtime automatically.`,
                ],
                rules.length === 0
              )}

              ${this._ruleFormOpen
                ? html`
                    <div class="passable-section-card editor-card">
                      <div class="passable-section-header">
                        <span class="passable-section-title">${r.rule_id ? "Edit Unlock Rule" : "New Device Unlock Rule"}</span>
                        <button
                          type="button"
                          class="inline-link-btn muted"
                          @click=${() => {
                            this._ruleFormOpen = false;
                            this._ruleDraft = this._emptyRuleDraft();
                          }}
                        >Cancel</button>
                      </div>

                      <div class="two-col-grid">
                        <div class="field-group">
                          <label class="field-label">Rule Name</label>
                          <input
                            class="field-input"
                            type="text"
                            placeholder="e.g. Madeleine's Tablet"
                            .value=${r.name}
                            @input=${(ev) => (this._ruleDraft = { ...r, name: ev.target.value })}
                          />
                        </div>
                        <div class="field-group">
                          <label class="field-label">Unlock Scope</label>
                          <select
                            class="field-input"
                            .value=${r.scope}
                            @change=${(ev) => (this._ruleDraft = { ...r, scope: ev.target.value })}
                          >
                            <option value="shared" ?selected=${r.scope === "shared"}>Shared Family Device</option>
                            <option value="personal" ?selected=${r.scope === "personal"}>Personal Child Device</option>
                          </select>
                        </div>
                      </div>

                      <div class="field-help">${scopeHelp}</div>

                      ${r.scope === "personal"
                        ? html`
                            <div class="field-group">
                              <label class="field-label">Child</label>
                              <select
                                class="field-input"
                                .value=${r.kid_id || ""}
                                @change=${(ev) => (this._ruleDraft = { ...r, kid_id: ev.target.value })}
                              >
                                <option value="" ?selected=${!r.kid_id}>Select Child...</option>
                                ${kids.map((kid) => html`<option value="${kid.kid_id}" ?selected=${r.kid_id === kid.kid_id}>${kid.avatar} ${kid.name}</option>`)}
                              </select>
                            </div>
                          `
                        : html`
                            <div class="field-group">
                              <label class="field-label">Shared Unlock Condition (0-Chore Kids Ignored)</label>
                              <select
                                class="field-input"
                                .value=${r.shared_mode}
                                @change=${(ev) => (this._ruleDraft = { ...r, shared_mode: ev.target.value })}
                              >
                                <option value="any_active_kid" ?selected=${r.shared_mode === "any_active_kid"}>Any Active Kid Finishes</option>
                                <option value="all_active_kids" ?selected=${r.shared_mode === "all_active_kids"}>All Active Kids Finish</option>
                              </select>
                            </div>
                          `}

                      <div class="two-col-grid">
                        <div class="field-group">
                          <label class="field-label">Target Integration / Mode</label>
                          <select
                            class="field-input"
                            .value=${r.target_mode}
                            @change=${(ev) => (this._ruleDraft = { ...r, target_mode: ev.target.value })}
                          >
                            <option value="passable_screen_time" ?selected=${r.target_mode === "passable_screen_time"}>Passable Screen Time Engine</option>
                            <option value="lockout_switch" ?selected=${r.target_mode === "lockout_switch"}>Lockout Switch (ON = Locked)</option>
                            <option value="power_switch" ?selected=${r.target_mode === "power_switch"}>Power Switch / TV (OFF = Locked)</option>
                            <option value="nintendo_switch" ?selected=${r.target_mode === "nintendo_switch"}>Nintendo Switch Max Time</option>
                          </select>
                        </div>

                        ${r.target_mode === "passable_screen_time"
                          ? html`
                              <div class="field-group">
                                <label class="field-label">Screen Time Device</label>
                                <select
                                  class="field-input"
                                  .value=${r.screen_time_device_id || ""}
                                  @change=${(ev) => (this._ruleDraft = { ...r, screen_time_device_id: ev.target.value })}
                                >
                                  <option value="" ?selected=${!r.screen_time_device_id}>Select Device...</option>
                                  <option value="all" ?selected=${r.screen_time_device_id === "all"}>All Screen Time Devices</option>
                                  ${stDevices.map(
                                    (dev) => html`<option value="${dev.device_id}" ?selected=${r.screen_time_device_id === dev.device_id}>${dev.name}</option>`
                                  )}
                                </select>
                              </div>
                            `
                          : html`
                              <div class="field-group">
                                <label class="field-label">Target Entity</label>
                                <select
                                  class="field-input"
                                  .value=${r.target_entity || ""}
                                  @change=${(ev) => (this._ruleDraft = { ...r, target_entity: ev.target.value })}
                                >
                                  <option value="" ?selected=${!r.target_entity}>Select Entity...</option>
                                  ${((r.target_mode === "nintendo_switch" ? cands.nintendo_numbers : cands.switches) || []).map(
                                    (ent) => html`<option value="${ent.entity_id}" ?selected=${r.target_entity === ent.entity_id}>${ent.name}</option>`
                                  )}
                                </select>
                              </div>
                            `}
                      </div>

                      ${targetModeHelp ? html`<div class="field-help">${targetModeHelp}</div>` : ""}

                      ${r.target_mode === "nintendo_switch"
                        ? html`
                            <div class="field-group">
                              <label class="field-label">Unlocked Daily Limit (Minutes)</label>
                              <input
                                class="field-input"
                                type="number"
                                min="5"
                                max="480"
                                .value=${String(r.nintendo_bonus_minutes || 60)}
                                @input=${(ev) => (this._ruleDraft = { ...r, nintendo_bonus_minutes: Number(ev.target.value) })}
                              />
                            </div>
                          `
                        : ""}

                      <div class="switch-control-row">
                        <span class="switch-sub">Lock on morning reset & respect Screen Time bedtime schedules</span>
                        <button
                          type="button"
                          class="m3-switch small ${r.respect_screen_time_schedules !== false ? "on" : ""}"
                          @click=${() => (this._ruleDraft = { ...r, respect_screen_time_schedules: !(r.respect_screen_time_schedules !== false) })}
                        ><span class="m3-knob"></span></button>
                      </div>

                      <button type="button" class="primary-cta-btn" @click=${() => this._saveUnlockRule()}>
                        ${r.rule_id ? "Update Unlock Rule" : "Save Unlock Rule"}
                      </button>
                    </div>
                  `
                : ""}

              <div class="passable-section-card">
                <div class="passable-section-header">
                  <span class="passable-section-title">Device Unlock Rules (${rules.length})</span>
                  ${!this._ruleFormOpen
                    ? html`
                        <button
                          type="button"
                          class="mini-primary-btn"
                          @click=${() => {
                            this._ruleDraft = this._emptyRuleDraft();
                            this._ruleFormOpen = true;
                          }}
                        >+ Add Rule</button>
                      `
                    : ""}
                </div>
                ${rules.length === 0
                  ? html`<div class="muted-hint">Tap "+ Add Rule" to lock tablets, TVs, or consoles each morning until required chores are complete.</div>`
                  : rules.map((rule) => {
                      const targetName = getFriendlyTargetName(rule);
                      const missingKid = rule.scope === "personal" && !rule.kid_id;
                      const isIncomplete = missingKid || !targetName;
                      const isLocked = rule.is_currently_locked !== false;
                      return html`
                        <div class="drawer-row">
                          <div class="drawer-row-left">
                            <ha-icon
                              icon="${isIncomplete ? "mdi:alert-circle-outline" : isLocked ? "mdi:lock" : "mdi:lock-open-variant"}"
                              style="--mdc-icon-size:18px;color:${isIncomplete ? "#ef4444" : isLocked ? "#d97706" : "#16a34a"};"
                            ></ha-icon>
                            <div>
                              <div class="drawer-row-title">${rule.name}</div>
                              <div class="drawer-row-sub">
                                ${getFriendlyScopeLabel(rule)} · ${targetName || "No device selected"}
                                ${isIncomplete
                                  ? html` · <span style="color:#ef4444;font-weight:700;">Tap ✏️ to select ${missingKid ? "Child" : "Device"}</span>`
                                  : rule.status_reason
                                    ? ` · ${isLocked ? "Locked" : "Unlocked"} (${rule.status_reason})`
                                    : ""}
                              </div>
                            </div>
                          </div>
                          <div class="drawer-actions">
                            <button
                              type="button"
                              class="icon-mini-btn"
                              @click=${() => {
                                this._ruleDraft = {
                                  ...this._emptyRuleDraft(),
                                  ...rule,
                                  kid_id: rule.kid_id || "",
                                  screen_time_device_id: rule.screen_time_device_id || "",
                                  target_entity: rule.target_entity || "",
                                };
                                this._ruleFormOpen = true;
                              }}
                              title="Edit"
                            ><ha-icon icon="mdi:pencil-outline" style="--mdc-icon-size:15px;"></ha-icon></button>
                            <button type="button" class="icon-mini-btn danger" @click=${() => this._deleteUnlockRule(rule.rule_id)} title="Delete"><ha-icon icon="mdi:trash-can-outline" style="--mdc-icon-size:15px;"></ha-icon></button>
                          </div>
                        </div>
                      `;
                    })}
              </div>
            `
          : html`
              ${this._renderQuickGuide(
                "rewards",
                "Optional · Rewards Shop",
                "Let kids spend earned ⭐ stars in the main card's 🎁 Rewards drawer.",
                [
                  html`<strong>Parent-Fulfilled:</strong> Deducts stars into ⏳ Waiting and sends an <em>Approve / Refund</em> push alert (denying refunds 100% of stars).`,
                  html`<strong>Smart Home Auto-Reward:</strong> Deducts stars and immediately starts a Screen Time viewing timer, adds bonus minutes, or adds Nintendo Switch time.`,
                ],
                rewards.length === 0
              )}

              ${this._rewardFormOpen
                ? html`
                    <div class="passable-section-card editor-card">
                      <div class="passable-section-header">
                        <span class="passable-section-title">${rw.reward_id ? "Edit Reward" : "New Reward"}</span>
                        <button
                          type="button"
                          class="inline-link-btn muted"
                          @click=${() => {
                            this._rewardFormOpen = false;
                            this._emojiPickerTarget = null;
                            this._rewardDraft = this._emptyRewardDraft();
                          }}
                        >Cancel</button>
                      </div>

                      <div class="icon-name-row">
                        <div class="field-group">
                          <label class="field-label">Icon</label>
                          ${this._renderEmojiPopoverButton(
                            "reward",
                            rw.emoji,
                            REWARD_EMOJI_PRESETS,
                            (val) => (this._rewardDraft = { ...rw, emoji: val })
                          )}
                        </div>
                        <div class="field-group">
                          <label class="field-label">Reward Name</label>
                          <input class="field-input" type="text" placeholder="e.g. +20m Bonus TV" .value=${rw.name} @input=${(ev) => (this._rewardDraft = { ...rw, name: ev.target.value })} />
                        </div>
                      </div>

                      <div class="two-col-grid">
                        <div class="field-group">
                          <label class="field-label">Star Cost (⭐)</label>
                          <input class="field-input" type="number" min="1" .value=${String(rw.cost)} @input=${(ev) => (this._rewardDraft = { ...rw, cost: Number(ev.target.value) })} />
                        </div>
                        <div class="field-group">
                          <label class="field-label">Reward Type</label>
                          <select class="field-input" .value=${rw.reward_type} @change=${(ev) => (this._rewardDraft = { ...rw, reward_type: ev.target.value })}>
                            <option value="parent_fulfilled" ?selected=${rw.reward_type === "parent_fulfilled"}>Parent-Fulfilled (Push Alert)</option>
                            <option value="smart_action" ?selected=${rw.reward_type === "smart_action"}>Smart Home Auto-Reward</option>
                          </select>
                        </div>
                      </div>

                      ${rw.reward_type === "smart_action"
                        ? html`
                            <div class="two-col-grid">
                              <div class="field-group">
                                <label class="field-label">Smart Action</label>
                                <select class="field-input" .value=${rw.action_kind} @change=${(ev) => (this._rewardDraft = { ...rw, action_kind: ev.target.value })}>
                                  <option value="screen_time_timer" ?selected=${rw.action_kind === "screen_time_timer"}>Screen Time Viewing Timer</option>
                                  <option value="screen_time_bonus" ?selected=${rw.action_kind === "screen_time_bonus"}>Screen Time +Daily Bonus</option>
                                  <option value="nintendo_bonus" ?selected=${rw.action_kind === "nintendo_bonus"}>Nintendo Switch +Minutes</option>
                                </select>
                              </div>
                              <div class="field-group">
                                <label class="field-label">Duration (Minutes)</label>
                                <input class="field-input" type="number" min="5" max="240" .value=${String(rw.duration_minutes || 20)} @input=${(ev) => (this._rewardDraft = { ...rw, duration_minutes: Number(ev.target.value) })} />
                              </div>
                            </div>
                            ${rw.action_kind === "nintendo_bonus"
                              ? html`
                                  <div class="field-group">
                                    <label class="field-label">Nintendo Switch Limit Entity</label>
                                    <select class="field-input" .value=${rw.entity_id || ""} @change=${(ev) => (this._rewardDraft = { ...rw, entity_id: ev.target.value })}>
                                      <option value="" ?selected=${!(rw.entity_id || "")}>Select Entity...</option>
                                      ${(cands.nintendo_numbers || []).map((ent) => html`<option value="${ent.entity_id}" ?selected=${rw.entity_id === ent.entity_id}>${ent.name}</option>`)}
                                    </select>
                                  </div>
                                `
                              : html`
                                  <div class="field-group">
                                    <label class="field-label">Target Screen Time Device</label>
                                    <select class="field-input" .value=${rw.device_id || "all"} @change=${(ev) => (this._rewardDraft = { ...rw, device_id: ev.target.value })}>
                                      <option value="all" ?selected=${(rw.device_id || "all") === "all"}>All Screen Time Devices</option>
                                      ${stDevices.map((dev) => html`<option value="${dev.device_id}" ?selected=${rw.device_id === dev.device_id}>${dev.name}</option>`)}
                                    </select>
                                  </div>
                                `}
                          `
                        : ""}

                      <button type="button" class="primary-cta-btn" @click=${() => this._saveReward()}>
                        ${rw.reward_id ? "Update Reward" : "Save Reward"}
                      </button>
                    </div>
                  `
                : ""}

              <div class="passable-section-card">
                <div class="passable-section-header">
                  <span class="passable-section-title">Rewards Shop (${rewards.length})</span>
                  ${!this._rewardFormOpen
                    ? html`
                        <button
                          type="button"
                          class="mini-primary-btn"
                          @click=${() => {
                            this._rewardDraft = this._emptyRewardDraft();
                            this._rewardFormOpen = true;
                          }}
                        >+ Add Reward</button>
                      `
                    : ""}
                </div>
                ${rewards.length === 0
                  ? html`<div class="muted-hint">Tap "+ Add Reward" to offer extra TV time or family treats for stars.</div>`
                  : rewards.map(
                      (item) => html`
                        <div class="drawer-row">
                          <div class="drawer-row-left">
                            <span class="drawer-emoji">${item.emoji}</span>
                            <div>
                              <div class="drawer-row-title">${item.name}</div>
                              <div class="drawer-row-sub">${item.cost} ⭐ · ${item.reward_type === "smart_action" ? "Auto Smart Action" : "Parent Fulfilled"}</div>
                            </div>
                          </div>
                          <div class="drawer-actions">
                            <button
                              type="button"
                              class="icon-mini-btn"
                              @click=${() => {
                                const sa = item.smart_action || {};
                                this._rewardDraft = {
                                  ...this._emptyRewardDraft(),
                                  ...item,
                                  action_kind: sa.action_kind || "screen_time_timer",
                                  device_id: sa.device_id || "all",
                                  entity_id: sa.entity_id || "",
                                  duration_minutes: sa.duration_minutes || 20,
                                };
                                this._rewardFormOpen = true;
                              }}
                              title="Edit"
                            ><ha-icon icon="mdi:pencil-outline" style="--mdc-icon-size:15px;"></ha-icon></button>
                            <button type="button" class="icon-mini-btn danger" @click=${() => this._deleteReward(item.reward_id)} title="Delete"><ha-icon icon="mdi:trash-can-outline" style="--mdc-icon-size:15px;"></ha-icon></button>
                          </div>
                        </div>
                      `
                    )}
              </div>
            `}
      </div>
    `;
  }

  _renderSetupActivityTab() {
    const settings = this._wsData?.settings || {};
    const cycle = this._wsData?.cycle || {};
    const cands = this._wsData?.candidates || {};
    const activity = this._wsData?.activity_log || [];

    return html`
      <div class="modal-tab-body">
        <div class="segmented-tabs two-up">
          <button type="button" class="seg-tab ${this._setupSubTab === "settings" ? "active sky" : ""}" @click=${() => (this._setupSubTab = "settings")}>Settings & PIN</button>
          <button type="button" class="seg-tab ${this._setupSubTab === "activity" ? "active sky" : ""}" @click=${() => (this._setupSubTab = "activity")}>Activity Log (${activity.length})</button>
        </div>

        ${this._setupSubTab === "activity"
          ? html`
              <div class="passable-section-card">
                ${activity.length === 0
                  ? html`<div class="muted-hint">No chore or reward activity recorded yet.</div>`
                  : activity.slice(0, 30).map(
                      (ev) => html`
                        <div class="drawer-row">
                          <div class="drawer-row-left">
                            <span class="drawer-emoji">${ev.emoji || "✅"}</span>
                            <div>
                              <div class="drawer-row-title">${ev.kid_name}: ${ev.title}</div>
                              <div class="drawer-row-sub">${new Date(ev.timestamp).toLocaleString()}</div>
                            </div>
                          </div>
                          ${ev.points_delta
                            ? html`<span class="meta-pill stars">${ev.points_delta > 0 ? "+" : ""}${ev.points_delta} ⭐</span>`
                            : ""}
                        </div>
                      `
                    )}
              </div>
            `
          : html`
              ${this._renderQuickGuide(
                "setup",
                "Schedules, Alerts & PIN",
                "Configure daily resets, school calendars, mobile approvals, and wall-tablet PINs.",
                [
                  html`<strong>Daily Reset Time:</strong> Clears daily completions and re-locks chore-gated devices each morning (default 05:00).`,
                  html`<strong>No-School Calendars:</strong> Automatically pauses School-Day chores and turns on Weekend chores on holidays.`,
                  html`<strong>Parent Push & PIN:</strong> Choose mobile notify targets for Approve/Try Again phone buttons, and set a 4–6 digit PIN for kiosks.`,
                ],
                false
              )}

              <div class="passable-section-card">
                <div class="passable-section-header">
                  <span class="passable-section-title">Schedules & Trust Mode</span>
                  <button type="button" class="inline-link-btn" @click=${() => this._seedSampleData()}>Seed Sample Templates</button>
                </div>

                <div class="two-col-grid">
                  <div class="field-group">
                    <label class="field-label">Daily Reset Time</label>
                    <input
                      class="field-input"
                      type="time"
                      .value=${settings.daily_reset_time || "05:00"}
                      @change=${(ev) => this._saveSettingsPatch({ daily_reset_time: ev.target.value })}
                    />
                  </div>
                  <div class="field-group">
                    <label class="field-label">Default Trust Mode</label>
                    <select
                      class="field-input"
                      .value=${settings.default_trust_mode || "honor_system"}
                      @change=${(ev) => this._saveSettingsPatch({ default_trust_mode: ev.target.value })}
                    >
                      <option value="honor_system" ?selected=${(settings.default_trust_mode || "honor_system") === "honor_system"}>Honor System (Instant)</option>
                      <option value="parent_approval" ?selected=${settings.default_trust_mode === "parent_approval"}>Parent Approval Required</option>
                    </select>
                  </div>
                </div>

                <div class="two-col-grid">
                  <div class="field-group">
                    <label class="field-label">Weekly Rollover Day</label>
                    <select
                      class="field-input"
                      .value=${settings.weekly_reset_day || "mon"}
                      @change=${(ev) => this._saveSettingsPatch({ weekly_reset_day: ev.target.value })}
                    >
                      ${DAYS_LIST.map((day) => html`<option value="${day}" ?selected=${(settings.weekly_reset_day || "mon") === day}>${day.toUpperCase()}</option>`)}
                    </select>
                  </div>
                  <div class="field-group">
                    <label class="field-label">Weekly Required-By Day</label>
                    <select
                      class="field-input"
                      .value=${settings.weekly_due_day || "sat"}
                      @change=${(ev) => this._saveSettingsPatch({ weekly_due_day: ev.target.value })}
                    >
                      ${DAYS_LIST.map((day) => html`<option value="${day}" ?selected=${(settings.weekly_due_day || "sat") === day}>${day.toUpperCase()}</option>`)}
                    </select>
                  </div>
                </div>

                <div class="switch-control-row">
                  <div>
                    <div class="switch-title">Treat Today as No-School Day</div>
                    <div class="switch-sub">Pauses school-day chores today; auto-clears tomorrow</div>
                  </div>
                  <button
                    type="button"
                    class="m3-switch small ${cycle.manual_no_school_active ? "on" : ""}"
                    @click=${() => this._saveSettingsPatch({ toggle_manual_no_school: !cycle.manual_no_school_active })}
                  ><span class="m3-knob"></span></button>
                </div>

                <div class="switch-control-row">
                  <div>
                    <div class="switch-title">Points, Streaks & Rewards Shop</div>
                    <div class="switch-sub">Toggle off for pure pass/fail checklist mode</div>
                  </div>
                  <button
                    type="button"
                    class="m3-switch small ${settings.gamification_enabled !== false ? "on" : ""}"
                    @click=${() => this._saveSettingsPatch({ gamification_enabled: !(settings.gamification_enabled !== false) })}
                  ><span class="m3-knob"></span></button>
                </div>

                ${(cands.calendars || []).length > 0
                  ? html`
                      <ha-selector
                        .hass=${this.hass}
                        .selector=${{
                          select: {
                            multiple: true,
                            mode: "dropdown",
                            options: (cands.calendars || []).map((cal) => ({
                              value: cal.entity_id,
                              label: cal.name,
                            })),
                          },
                        }}
                        .value=${settings.no_school_calendars || []}
                        .label=${"No-School / Holiday Calendars"}
                        @value-changed=${(ev) =>
                          this._saveSettingsPatch({ no_school_calendars: ev.detail.value || [] })}
                      ></ha-selector>
                    `
                  : ""}

                ${(cands.notify_services || []).length > 0
                  ? html`
                      <ha-selector
                        .hass=${this.hass}
                        .selector=${{
                          select: {
                            multiple: true,
                            mode: "dropdown",
                            options: (cands.notify_services || []).map((svc) => ({
                              value: svc,
                              label: svc.replace("notify.", ""),
                            })),
                          },
                        }}
                        .value=${settings.parent_notify_services || []}
                        .label=${"Parent Push Notification Targets"}
                        @value-changed=${(ev) =>
                          this._saveSettingsPatch({ parent_notify_services: ev.detail.value || [] })}
                      ></ha-selector>
                    `
                  : ""}
              </div>

              <div class="passable-section-card">
                <div class="passable-section-header">
                  <span class="passable-section-title">Wall-Panel Parental PIN</span>
                </div>
                <div class="switch-control-row">
                  <span class="switch-title">Enable 4–6 Digit Parental PIN</span>
                  <button
                    type="button"
                    class="m3-switch small ${this._secPinEnabled ? "on" : ""}"
                    @click=${() => (this._secPinEnabled = !this._secPinEnabled)}
                  ><span class="m3-knob"></span></button>
                </div>
                ${this._wsData?.security?.pin_enabled
                  ? html`
                      <div class="field-group">
                        <label class="field-label">Current PIN</label>
                        <input class="field-input" type="password" inputmode="numeric" maxlength="6" .value=${this._secCurrentPin} @input=${(ev) => (this._secCurrentPin = ev.target.value)} />
                      </div>
                    `
                  : ""}
                <div class="field-group">
                  <label class="field-label">${this._wsData?.security?.pin_enabled ? "New PIN (optional)" : "Set 4–6 Digit PIN"}</label>
                  <input class="field-input" type="password" inputmode="numeric" maxlength="6" .value=${this._secNewPin} @input=${(ev) => (this._secNewPin = ev.target.value)} />
                </div>
                <button type="button" class="primary-cta-btn" @click=${() => this._saveSecuritySettings()}>
                  Save PIN Settings
                </button>
              </div>
            `}
      </div>
    `;
  }

  _renderPinModal() {
    if (!this._pinModalOpen) return "";
    const dots = [0, 1, 2, 3, 4, 5].map((i) => i < this._pinInput.length);
    return html`
      <div class="popup-overlay pin-overlay" @click=${() => this._closePinModal()}>
        <div class="popup-content pin-dialog" @click=${(ev) => ev.stopPropagation()}>
          <div class="popup-header">
            <div class="popup-header-left">
              <ha-icon icon="mdi:shield-lock" style="color:var(--primary-color);--mdc-icon-size:22px;"></ha-icon>
              <h3>Parent PIN Required</h3>
            </div>
            <button type="button" class="close-button" @click=${() => this._closePinModal()}>
              <ha-icon icon="mdi:close" style="--mdc-icon-size:20px;"></ha-icon>
            </button>
          </div>
          <div class="pin-dots-row">
            ${dots.map((filled, idx) =>
              idx < 4 || filled ? html`<span class="pin-dot ${filled ? "filled" : ""}"></span>` : ""
            )}
          </div>
          ${this._pinError ? html`<div class="pin-error-text">${this._pinError}</div>` : ""}
          <div class="pin-keypad">
            ${["1", "2", "3", "4", "5", "6", "7", "8", "9"].map(
              (d) => html`
                <button
                  type="button"
                  class="pin-key"
                  @click=${() => {
                    this._fireHaptic("light");
                    if (this._pinInput.length < 6) {
                      this._pinInput += d;
                      this._pinError = null;
                    }
                  }}
                >${d}</button>
              `
            )}
            <button
              type="button"
              class="pin-key fn"
              @click=${() => {
                this._pinInput = this._pinInput.slice(0, -1);
                this._pinError = null;
              }}
            >⌫</button>
            <button
              type="button"
              class="pin-key"
              @click=${() => {
                if (this._pinInput.length < 6) this._pinInput += "0";
              }}
            >0</button>
            <button type="button" class="pin-key submit" @click=${() => this._submitPinModal()}>Unlock</button>
          </div>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // MAIN RENDER
  // =========================================================================

  render() {
    if (!this.hass || !this.config) return html``;
    const c = this.config;
    const visibleKids = this._getVisibleKids();
    const metrics = this._getSummaryMetrics(visibleKids);
    const isFull = c.display_mode === "full";
    const layout = c.layout || "board";

    return html`
      <ha-card>
        ${c.show_header !== false
          ? html`
              <div class="header">
                <div class="header-top-row">
                  <h1 class="title">
                    <ha-icon icon="mdi:clipboard-check-multiple-outline" style="margin-right:8px;color:#10b981;"></ha-icon>
                    ${c.title || "Family Chores"}
                  </h1>
                </div>
                <div class="header-subtitle-row">
                  <p class="subtitle">${c.subtitle || "Smart Chores, Streaks & Screen Unlocks"}</p>
                </div>
              </div>
            `
          : ""}

        ${isFull
          ? html`
              <div class="card-content ${c.show_header === false ? "no-header" : ""}">
                <div class="popup-tabs">
                  ${MODAL_TABS.map(
                    (t) => html`
                      <button
                        type="button"
                        class="popup-tab ${this._modalTab === t.id ? "active-tab" : ""}"
                        @click=${() => (this._modalTab = t.id)}
                      >
                        <ha-icon icon="${t.icon}"></ha-icon>
                        <span>${t.label}</span>
                      </button>
                    `
                  )}
                </div>
                ${this._renderTabContent()}
              </div>
            `
          : html`
              <div class="card-content ${c.show_header === false ? "no-header" : ""}">
                ${c.show_summary_strip !== false ? this._renderSummaryStrip(visibleKids, metrics) : ""}

                ${this._wsError
                  ? html`<div class="drawer-empty">${this._wsError}</div>`
                  : visibleKids.length === 0
                    ? html`
                        <div class="drawer-empty">
                          No active chores configured for today.
                          ${this._canViewAdminControls()
                            ? html`<button type="button" class="inline-link-btn" @click=${() => this._openModal("kids")}>Setup Kids & Chores →</button>`
                            : ""}
                        </div>
                      `
                    : layout === "rings"
                      ? this._renderRingsLayout(visibleKids)
                      : layout === "rows"
                        ? this._renderRowsLayout(visibleKids)
                        : layout === "tiles"
                          ? this._renderTilesLayout(visibleKids)
                          : this._renderBoardLayout(visibleKids)}

                ${this._renderInlineDrawer(visibleKids)}
                ${this._renderFooterStrip(metrics)}
              </div>
            `}

        ${this._toastMsg ? html`<div class="card-toast">${this._toastMsg}</div>` : ""}
        ${this._renderModal()}
        ${this._renderPinModal()}
      </ha-card>
    `;
  }

  // =========================================================================
  // PASSABLE DESIGN SYSTEM STYLES
  // =========================================================================

  static get styles() {
    return css`
      :host { display: block; }
      ha-card {
        border-radius: var(--ha-card-border-radius, 12px);
        background: var(--ha-card-background, var(--card-background-color, #fff));
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0, 0, 0, 0.1));
        overflow: hidden;
        color: var(--primary-text-color);
        position: relative;
      }
      .header {
        padding: 16px 16px 14px;
        display: flex;
        flex-direction: column;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        margin-bottom: 12px;
        gap: 4px;
      }
      .title { font-size: 24px; font-weight: 500; margin: 0; display: flex; align-items: center; }
      .subtitle { color: var(--secondary-text-color, #757575); font-size: 14px; margin: 2px 0 0; }
      .card-content {
        padding: 10px 12px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        container-type: inline-size;
      }
      .card-content.no-header { padding: 10px; }

      /* SUMMARY STRIP */
      .chores-summary-strip {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 6px 10px;
        padding: 7px 12px;
        border-radius: max(12px, calc(var(--ha-card-border-radius, 20px) - 8px));
        min-height: 36px;
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.1));
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.16));
      }
      .chores-summary-strip.done { background: rgba(34, 197, 94, 0.08); border-color: rgba(34, 197, 94, 0.3); }
      .chores-summary-strip.amber { background: rgba(245, 158, 11, 0.08); border-color: rgba(245, 158, 11, 0.32); }
      .chores-summary-strip.active { background: rgba(14, 165, 233, 0.06); border-color: rgba(14, 165, 233, 0.24); }
      .summary-strip-left, .summary-strip-right { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
      .summary-status-dot { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; }
      .summary-status-dot.done { background: #22c55e; box-shadow: 0 0 6px rgba(34, 197, 94, 0.65); }
      .summary-status-dot.amber { background: #f59e0b; box-shadow: 0 0 6px rgba(245, 158, 11, 0.65); }
      .summary-status-dot.active { background: #0ea5e9; box-shadow: 0 0 6px rgba(14, 165, 233, 0.65); }
      .strip-active-pill {
        padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 700;
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.22));
        background: var(--card-background-color, rgba(128, 128, 128, 0.1));
      }
      .strip-active-pill.done { background: rgba(34, 197, 94, 0.16); border-color: rgba(34, 197, 94, 0.4); color: #16a34a; }
      .zone-inline-chip {
        display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 999px;
        font-family: inherit; font-size: 11.5px; font-weight: 700; border: 1px solid transparent;
      }
      .zone-inline-chip.info { background: rgba(14, 165, 233, 0.16); color: #0284c7; border-color: rgba(14, 165, 233, 0.3); }
      .zone-inline-chip.warning { background: rgba(245, 158, 11, 0.16); color: #d97706; border-color: rgba(245, 158, 11, 0.35); }
      .zone-inline-chip.success { background: rgba(34, 197, 94, 0.16); color: #16a34a; border-color: rgba(34, 197, 94, 0.35); }
      .zone-inline-chip.neutral { background: rgba(128, 128, 128, 0.14); color: var(--secondary-text-color); border-color: rgba(128, 128, 128, 0.24); }
      .zone-inline-chip.clickable { cursor: pointer; }
      .icon-circle-btn {
        width: 28px; height: 28px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
        background: var(--card-background-color, rgba(128, 128, 128, 0.1));
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.2));
        color: var(--primary-text-color); cursor: pointer; padding: 0;
      }
      .icon-circle-btn.active { border-color: var(--primary-color, #0284c7); color: var(--primary-color, #0284c7); }
      .icon-circle-btn.pin-unlocked { color: #16a34a; border-color: rgba(34, 197, 94, 0.4); background: rgba(34, 197, 94, 0.12); }

      /* KID BOARD COLUMNS (DEFAULT) */
      .kid-board-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(215px, 1fr));
        gap: 10px;
      }
      @container (max-width: 440px) {
        .kid-board-grid { grid-template-columns: 1fr; }
      }
      .kid-column-card {
        position: relative;
        overflow: hidden;
        border-radius: max(12px, calc(var(--ha-card-border-radius, 20px) - 6px));
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.08));
        border: 1px solid var(--kid-accent-border, rgba(128, 128, 128, 0.2));
        border-top: 3px solid var(--kid-accent, #039BE5);
        padding: 10px;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .kid-column-card.all-done {
        border-top-color: #22c55e;
        background: rgba(34, 197, 94, 0.06);
      }
      .kid-col-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
      .kid-col-identity { display: flex; align-items: center; gap: 8px; min-width: 0; }
      .kid-avatar {
        border-radius: 50%; border: 2px solid; display: flex; align-items: center; justify-content: center;
        font-size: 20px; flex-shrink: 0; overflow: hidden;
      }
      .kid-avatar img { width: 100%; height: 100%; object-fit: cover; }
      .kid-col-titles { min-width: 0; }
      .kid-col-name { font-size: 14.5px; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .kid-col-sub { font-size: 11.5px; color: var(--secondary-text-color); font-weight: 600; }
      .kid-col-sub .done-text { color: #16a34a; font-weight: 700; }
      .kid-col-badges { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
      .kid-badge {
        padding: 2px 7px; border-radius: 999px; font-size: 11.5px; font-weight: 800;
        border: 1px solid transparent; font-family: inherit;
      }
      .kid-badge.fire { background: rgba(249, 115, 22, 0.16); color: #ea580c; border-color: rgba(249, 115, 22, 0.35); }
      .kid-badge.stars { background: rgba(234, 179, 8, 0.16); color: #ca8a04; border-color: rgba(234, 179, 8, 0.38); }
      .kid-badge.clickable { cursor: pointer; }
      .kid-progress-track { width: 100%; height: 5px; border-radius: 999px; background: rgba(148, 163, 184, 0.2); overflow: hidden; }
      .kid-progress-fill { height: 100%; border-radius: 999px; transition: width 0.25s ease; }

      /* CHORE TILES */
      .kid-chore-list { display: flex; flex-direction: column; gap: 6px; }
      .chore-tile {
        display: flex; align-items: center; justify-content: space-between; gap: 10px;
        padding: 8px 10px; border-radius: 12px; cursor: pointer;
        background: var(--card-background-color, rgba(255, 255, 255, 0.06));
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.18));
        transition: transform 0.12s ease, background 0.2s ease, border-color 0.2s ease;
        user-select: none;
      }
      .chore-tile.large { min-height: 54px; padding: 10px 12px; }
      .chore-tile:active { transform: scale(0.985); }
      .chore-tile.completed {
        background: rgba(34, 197, 94, 0.12);
        border-color: rgba(34, 197, 94, 0.38);
      }
      .chore-tile.waiting_approval {
        background: rgba(245, 158, 11, 0.12);
        border-color: rgba(245, 158, 11, 0.42);
      }
      .chore-tile-visual {
        width: 40px; height: 40px; border-radius: 11px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        background: var(--kid-accent-soft, rgba(128, 128, 128, 0.12));
        overflow: hidden;
      }
      .chore-tile.large .chore-emoji { font-size: 26px; line-height: 1; }
      .chore-tile.compact .chore-emoji { font-size: 20px; line-height: 1; }
      .chore-img { width: 100%; height: 100%; object-fit: cover; }
      .chore-tile-body { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 3px; }
      .chore-tile-name { font-size: 13.5px; font-weight: 700; line-height: 1.25; }
      .chore-tile.completed .chore-tile-name { text-decoration: line-through; opacity: 0.78; }
      .chore-tile-meta { display: flex; flex-wrap: wrap; gap: 4px; }
      .meta-pill {
        font-size: 10.5px; font-weight: 700; padding: 1px 6px; border-radius: 6px;
        background: rgba(128, 128, 128, 0.14); color: var(--secondary-text-color);
      }
      .meta-pill.done { background: rgba(34, 197, 94, 0.18); color: #16a34a; }
      .meta-pill.waiting { background: rgba(245, 158, 11, 0.18); color: #d97706; }
      .meta-pill.due { background: rgba(239, 68, 68, 0.15); color: #dc2626; }
      .meta-pill.turn { background: rgba(14, 165, 233, 0.15); color: #0284c7; }
      .meta-pill.stars { background: rgba(234, 179, 8, 0.18); color: #ca8a04; }
      .chore-check-circle {
        width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
        color: var(--secondary-text-color); background: rgba(128, 128, 128, 0.1);
      }
      .chore-check-circle.completed { background: #22c55e; color: #ffffff; }
      .chore-check-circle.waiting { background: rgba(245, 158, 11, 0.18); color: #d97706; }
      .kid-empty-board {
        padding: 12px 8px; text-align: center; font-size: 12px; color: var(--secondary-text-color);
        border: 1px dashed var(--divider-color, rgba(128, 128, 128, 0.22)); border-radius: 10px;
      }
      .inline-approve-pair { display: flex; gap: 4px; }
      .mini-approve-btn {
        width: 28px; height: 28px; border-radius: 8px; border: none; font-weight: 800; cursor: pointer;
      }
      .mini-approve-btn.ok { background: #22c55e; color: #fff; }
      .mini-approve-btn.no { background: #f59e0b; color: #fff; }

      /* CONFETTI CELEBRATION */
      @keyframes confettiBurst {
        0% { opacity: 0; transform: translateY(14px) scale(0.7); }
        25% { opacity: 1; transform: translateY(-6px) scale(1.1); }
        100% { opacity: 0; transform: translateY(-34px) scale(0.95); }
      }
      .confetti-layer {
        position: absolute; inset: 0; pointer-events: none; display: flex; justify-content: space-around; align-items: center; font-size: 22px; z-index: 2;
      }
      .confetti-layer span { animation: confettiBurst 2.2s ease-out forwards; }
      @media (prefers-reduced-motion: reduce) { .confetti-layer { display: none; } }

      /* TILES / ROWS / RINGS ALTERNATE LAYOUTS */
      .kid-tiles-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
      .kid-summary-tile {
        position: relative; overflow: hidden; padding: 9px 10px 11px; border-radius: 12px; cursor: pointer;
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.1));
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.16));
      }
      .kid-summary-tile.span-2 { grid-column: span 2; }
      .kid-summary-tile.selected { border-color: var(--kid-accent, #0284c7); }
      .tile-main { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
      .tile-identity { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
      .tile-text { min-width: 0; }
      .tile-name { font-size: 13.5px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .tile-sub { font-size: 11.5px; color: var(--secondary-text-color); }
      .tile-stat { font-size: 13px; font-weight: 800; }
      .tile-hairline { position: absolute; left: 0; right: 0; bottom: 0; height: 2.5px; background: rgba(148, 163, 184, 0.15); }
      .tile-hairline-fill { height: 100%; transition: width 0.25s ease; }

      .kid-rows-stack { display: flex; flex-direction: column; gap: 6px; }
      .kid-summary-row {
        display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 10px;
        border-radius: 12px; cursor: pointer;
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.1));
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.16));
      }
      .row-right { display: flex; align-items: center; gap: 6px; }

      .kid-rings-grid { display: grid; gap: 4px; }
      .ring-tile-btn {
        display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 6px 2px;
        border-radius: 11px; background: transparent; border: 1px solid transparent; font-family: inherit; cursor: pointer;
      }
      .ring-tile-btn.selected { background: var(--secondary-background-color, rgba(128, 128, 128, 0.12)); border-color: var(--primary-color, #0284c7); }
      .ring-wrap { position: relative; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; }
      .ring-svg { width: 100%; height: 100%; transform: rotate(-90deg); }
      .ring-val { position: absolute; font-size: 16px; }
      .ring-name { font-size: 12px; font-weight: 700; color: var(--primary-text-color); }
      .ring-sub { font-size: 11px; color: var(--secondary-text-color); }

      /* INLINE DRAWER */
      .chores-drawer {
        border-top: 1px dashed var(--divider-color, rgba(128, 128, 128, 0.25));
        padding-top: 8px; display: flex; flex-direction: column; gap: 8px;
      }
      .drawer-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
      .drawer-title { font-size: 13px; font-weight: 700; }
      .drawer-actions { display: flex; align-items: center; gap: 5px; }
      .drawer-manage-btn {
        padding: 3px 9px; border-radius: 999px; border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.22));
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.1));
        color: var(--primary-text-color); font-family: inherit; font-size: 11.5px; font-weight: 600; cursor: pointer;
      }
      .drawer-close-btn { background: none; border: none; padding: 2px; color: var(--secondary-text-color); cursor: pointer; display: inline-flex; }
      .drawer-list { max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
      .drawer-row {
        display: flex; align-items: center; justify-content: space-between; gap: 8px;
        padding: 7px 9px; border-radius: 10px;
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.16));
        background: var(--card-background-color, rgba(128, 128, 128, 0.06));
      }
      .drawer-row-left { display: flex; align-items: center; gap: 8px; min-width: 0; }
      .drawer-emoji { font-size: 20px; flex-shrink: 0; }
      .drawer-row-title { font-size: 12.5px; font-weight: 700; }
      .drawer-row-sub { font-size: 11px; color: var(--secondary-text-color); }
      .drawer-empty { padding: 14px 8px; text-align: center; font-size: 12.5px; color: var(--secondary-text-color); }

      /* CHIPS, PILLS & FOOTER */
      .kid-selector-pills { display: flex; flex-wrap: wrap; align-items: center; gap: 5px; }
      .selector-label { font-size: 11.5px; font-weight: 700; color: var(--secondary-text-color); }
      .kid-pick-pill {
        padding: 4px 9px; border-radius: 999px; font-family: inherit; font-size: 11.5px; font-weight: 700; cursor: pointer;
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.25));
        background: var(--card-background-color, rgba(128, 128, 128, 0.08));
        color: var(--primary-text-color);
      }
      .kid-pick-pill.active { background: var(--kid-accent, #0284c7); border-color: var(--kid-accent, #0284c7); color: #ffffff; }
      .quick-chip {
        padding: 4px 10px; border-radius: 999px; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.24));
        background: var(--card-background-color, rgba(128, 128, 128, 0.08)); color: var(--primary-text-color);
      }
      .quick-chip:disabled { opacity: 0.4; cursor: default; }
      .quick-chip.green { background: rgba(34, 197, 94, 0.14); border-color: rgba(34, 197, 94, 0.38); color: #16a34a; }
      .quick-chip.amber { background: rgba(245, 158, 11, 0.14); border-color: rgba(245, 158, 11, 0.38); color: #d97706; }
      .quick-chip.sky { background: rgba(14, 165, 233, 0.14); border-color: rgba(14, 165, 233, 0.38); color: #0284c7; }
      .quick-chip.danger { background: rgba(239, 68, 68, 0.14); border-color: rgba(239, 68, 68, 0.38); color: #dc2626; }

      .engine-footer-strip {
        padding-top: 6px; border-top: 1px solid var(--divider-color, rgba(128, 128, 128, 0.16));
        display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px;
      }
      .footer-chips { display: flex; flex-wrap: wrap; gap: 5px; }
      .footer-chip {
        display: inline-flex; align-items: center; gap: 4px; padding: 2px 9px; border-radius: 999px;
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.22));
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.1));
        color: var(--secondary-text-color); font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
      }
      .footer-chip.sky { background: rgba(14, 165, 233, 0.15); border-color: rgba(14, 165, 233, 0.35); color: #0284c7; }
      .footer-chip.amber { background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.38); color: #d97706; }
      .footer-command-link, .inline-link-btn {
        background: none; border: none; padding: 0; font-family: inherit; font-size: 12px; font-weight: 700;
        color: var(--primary-color, #0284c7); cursor: pointer;
      }

      /* TOAST & COMMAND CENTER MODAL */
      .card-toast {
        position: fixed; bottom: 18px; right: 18px; z-index: 10002; padding: 7px 14px; border-radius: 10px;
        background: var(--ha-card-background, #1c1c1e); border: 1px solid var(--primary-color, #0284c7);
        color: var(--primary-text-color); font-size: 12.5px; font-weight: 600;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35); pointer-events: none;
      }
      @keyframes ha-popup-backdrop-fade-in { from { opacity: 0; } to { opacity: 1; } }
      @keyframes ha-popup-backdrop-fade-out { from { opacity: 1; } to { opacity: 0; } }
      @keyframes ha-popup-dialog-in { from { opacity: 0; transform: translateY(20px) scale(0.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
      @keyframes ha-popup-dialog-out { from { opacity: 1; transform: translateY(0) scale(1); } to { opacity: 0; transform: translateY(12px) scale(0.97); } }
      .popup-overlay {
        position: fixed; inset: 0; background-color: var(--mdc-dialog-scrim-color, rgba(0, 0, 0, 0.42));
        display: flex; justify-content: center; align-items: center; padding: 16px; box-sizing: border-box;
        overscroll-behavior: contain; z-index: 9999; animation: ha-popup-backdrop-fade-in 220ms cubic-bezier(0.2, 0, 0, 1) forwards;
      }
      .popup-overlay.pin-overlay { z-index: 10001; }
      .popup-overlay.closing { animation: ha-popup-backdrop-fade-out 170ms cubic-bezier(0.2, 0, 0, 1) forwards; }
      .popup-content {
        background-color: var(--ha-card-background, var(--card-background-color, #fff));
        padding: 16px 18px 20px; border-radius: var(--ha-dialog-border-radius, var(--ha-card-border-radius, 24px));
        width: 100%; max-width: 560px; max-height: 90vh; overflow: hidden; color: var(--primary-text-color);
        display: flex; flex-direction: column; gap: 10px; box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1)); box-sizing: border-box;
        animation: ha-popup-dialog-in 220ms cubic-bezier(0.2, 0, 0, 1) forwards;
      }
      .popup-content.pin-dialog { max-width: 360px; }
      .popup-content.closing { animation: ha-popup-dialog-out 170ms cubic-bezier(0.2, 0, 0, 1) forwards; }
      .drag-handle { display: none; }
      @media (max-width: 560px) {
        .popup-overlay { align-items: flex-end; padding: 0; }
        .popup-content { max-width: 100%; border-bottom-left-radius: 0; border-bottom-right-radius: 0; }
        .drag-handle { display: block; width: 36px; height: 4px; border-radius: 999px; background: var(--divider-color, rgba(128, 128, 128, 0.4)); margin: 0 auto 4px; }
      }
      .popup-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding-bottom: 10px; border-bottom: 1px solid var(--divider-color, rgba(128, 128, 128, 0.16)); }
      .popup-header-left { display: flex; align-items: center; gap: 10px; }
      .popup-header h3 { margin: 0; font-size: 16px; font-weight: 700; }
      .popup-header-sub { font-size: 12px; color: var(--secondary-text-color); }
      .close-button { background: none; border: none; padding: 4px; cursor: pointer; color: var(--primary-text-color); display: flex; border-radius: 50%; }
      .popup-tabs { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); background: var(--secondary-background-color, rgba(128, 128, 128, 0.12)); padding: 4px; border-radius: 14px; gap: 4px; }
      .popup-tab {
        display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
        padding: 7px 4px; border-radius: 10px; background: transparent; border: none; font-family: inherit;
        color: var(--secondary-text-color); font-size: 11.5px; font-weight: 600; cursor: pointer;
      }
      .popup-tab ha-icon { --mdc-icon-size: 16px; }
      .popup-tab.active-tab { background: var(--primary-color, #0284c7); color: #ffffff; font-weight: 700; }
      .modal-scroll-area { overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; max-height: 62vh; padding-right: 2px; }
      .modal-tab-body { display: flex; flex-direction: column; gap: 10px; }

      .passable-section-card {
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.08));
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.14));
        border-radius: 16px; padding: 11px 12px; display: flex; flex-direction: column; gap: 9px;
      }
      .passable-section-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
      .passable-section-header.wrap { flex-wrap: wrap; }
      .header-left-group { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
      .passable-section-title { font-size: 12px; font-weight: 800; letter-spacing: 0.04em; text-transform: uppercase; }
      .editor-card { border-color: rgba(2, 132, 199, 0.35); background: rgba(2, 132, 199, 0.05); }
      .muted-hint { margin: 0; font-size: 12px; color: var(--secondary-text-color); }
      .guide-banner {
        border-radius: 13px; border: 1px solid rgba(14, 165, 233, 0.28);
        background: rgba(14, 165, 233, 0.08); overflow: hidden;
      }
      .guide-header {
        width: 100%; background: none; border: none; padding: 8px 11px;
        display: flex; align-items: center; justify-content: space-between; gap: 8px;
        text-align: left; color: var(--primary-text-color); font-family: inherit;
        font-size: 12px; line-height: 1.35; cursor: pointer;
      }
      .guide-title-wrap { flex: 1; min-width: 0; }
      .guide-toggle { font-size: 11.5px; font-weight: 700; color: var(--primary-color, #0284c7); white-space: nowrap; }
      .guide-bullets {
        margin: 0; padding: 0 12px 9px 26px; display: flex; flex-direction: column; gap: 4px;
        font-size: 11.5px; line-height: 1.4; color: var(--secondary-text-color);
      }
      .field-help {
        font-size: 11.5px; line-height: 1.38; color: var(--secondary-text-color);
        padding: 5px 8px; border-radius: 8px; background: rgba(128, 128, 128, 0.09);
      }
      .two-col-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
      .icon-name-row { display: grid; grid-template-columns: 62px 1fr; gap: 8px; align-items: end; }
      .field-group { display: flex; flex-direction: column; gap: 4px; position: relative; }
      .field-label { font-size: 11.5px; font-weight: 700; color: var(--secondary-text-color); }
      .field-input, .compact-select {
        width: 100%; box-sizing: border-box; padding: 7px 10px; border-radius: 9px;
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.28));
        background: var(--card-background-color, rgba(128, 128, 128, 0.06));
        color: var(--primary-text-color); font-family: inherit; font-size: 13px;
      }
      .compact-select { width: auto; padding: 4px 8px; font-size: 12px; font-weight: 600; border-radius: 8px; }
      .mini-primary-btn {
        padding: 5px 11px; border-radius: 999px; border: none; background: var(--primary-color, #0284c7);
        color: #ffffff; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
      }
      .inline-link-btn.muted { color: var(--secondary-text-color); }
      .emoji-picker-wrap { position: relative; }
      .emoji-trigger-btn {
        width: 100%; height: 34px; border-radius: 9px; display: inline-flex; align-items: center; justify-content: center; gap: 4px;
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.28));
        background: var(--card-background-color, rgba(128, 128, 128, 0.06));
        color: var(--primary-text-color); font-size: 18px; cursor: pointer; padding: 0 6px;
      }
      .emoji-trigger-btn.open { border-color: var(--primary-color, #0284c7); }
      .emoji-trigger-caret { font-size: 10px; color: var(--secondary-text-color); }
      .emoji-popover {
        position: absolute; top: 38px; left: 0; z-index: 30; width: 224px; padding: 8px; border-radius: 12px;
        background: var(--ha-card-background, var(--card-background-color, #1e293b));
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.3));
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.32); display: flex; flex-direction: column; gap: 8px;
      }
      .emoji-popover-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; }
      .emoji-popover-custom input { font-size: 12px; padding: 5px 8px; }
      ha-selector { display: block; width: 100%; }
      .preset-chips-row { display: flex; flex-wrap: wrap; gap: 5px; }
      .preset-chip, .emoji-chip, .tiny-preset-btn {
        padding: 4px 9px; border-radius: 999px; border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.25));
        background: var(--card-background-color, rgba(128, 128, 128, 0.08));
        color: var(--primary-text-color); font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
      }
      .emoji-chip.active { border-color: var(--primary-color, #0284c7); background: rgba(2, 132, 199, 0.18); }
      .color-swatches-row { display: flex; flex-wrap: wrap; gap: 7px; }
      .color-swatch { width: 26px; height: 26px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; }
      .color-swatch.active { border-color: var(--primary-text-color); transform: scale(1.12); }
      .day-chips { display: flex; justify-content: space-between; gap: 6px; }
      .day-chip {
        flex: 1; height: 32px; border-radius: 50%; border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.28));
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.1));
        color: var(--secondary-text-color); font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
      }
      .day-chip.selected { background: var(--primary-color, #0284c7); border-color: var(--primary-color, #0284c7); color: #ffffff; }
      .primary-cta-btn {
        display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 9px 14px;
        border-radius: 11px; font-family: inherit; font-size: 13px; font-weight: 700; cursor: pointer;
        border: none; background: var(--primary-color, #0284c7); color: #ffffff;
      }
      .icon-mini-btn {
        width: 28px; height: 28px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center;
        border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.22));
        background: var(--card-background-color, rgba(128, 128, 128, 0.08));
        color: var(--secondary-text-color); cursor: pointer; padding: 0;
      }
      .icon-mini-btn.danger { color: #dc2626; }
      .switch-control-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
      .switch-title { font-size: 13px; font-weight: 700; }
      .switch-sub { font-size: 11.5px; color: var(--secondary-text-color); }
      .m3-switch {
        width: 36px; height: 22px; border-radius: 999px; border: 1.5px solid var(--divider-color, #94a3b8);
        background: rgba(148, 163, 184, 0.24); position: relative; cursor: pointer; padding: 0; flex-shrink: 0;
      }
      .m3-switch.on { background: var(--primary-color, #0284c7); border-color: var(--primary-color, #0284c7); }
      .m3-knob {
        position: absolute; top: 50%; left: 3px; width: 14px; height: 14px; border-radius: 50%;
        background: #ffffff; transform: translateY(-50%); transition: left 0.18s ease;
      }
      .m3-switch.on .m3-knob { left: calc(100% - 17px); }
      .segmented-tabs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; padding: 4px; border-radius: 12px; background: var(--secondary-background-color, rgba(128, 128, 128, 0.12)); }
      .seg-tab { padding: 6px 8px; border-radius: 9px; border: none; background: transparent; color: var(--secondary-text-color); font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
      .seg-tab.active.sky { background: #0284c7; color: #ffffff; }

      /* PIN KEYPAD */
      .pin-dots-row { display: flex; justify-content: center; gap: 10px; padding: 10px 0 4px; }
      .pin-dot { width: 12px; height: 12px; border-radius: 50%; border: 1.5px solid var(--secondary-text-color); }
      .pin-dot.filled { background: var(--primary-color, #0284c7); border-color: var(--primary-color, #0284c7); }
      .pin-error-text { text-align: center; color: #dc2626; font-size: 12px; font-weight: 700; }
      .pin-keypad { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
      .pin-key {
        height: 48px; border-radius: 12px; border: 1px solid var(--divider-color, rgba(128, 128, 128, 0.24));
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.1));
        color: var(--primary-text-color); font-family: inherit; font-size: 18px; font-weight: 700; cursor: pointer;
      }
      .pin-key.submit { background: var(--primary-color, #0284c7); border-color: var(--primary-color, #0284c7); color: #ffffff; font-size: 14px; }
      .pin-key.fn { font-size: 16px; }
    `;
  }
}

class PassableChoresCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      config: { state: true },
      _users: { state: true },
    };
  }

  constructor() {
    super();
    this._users = [];
    this._usersLoaded = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchUsers();
  }

  updated(changedProps) {
    super.updated && super.updated(changedProps);
    if (changedProps.has("hass") && this.hass && !this._usersLoaded) {
      this._fetchUsers();
    }
  }

  async _fetchUsers() {
    if (!this.hass || this._usersLoaded) return;
    this._usersLoaded = true;
    try {
      const users = await this.hass.connection.sendMessagePromise({
        type: "config/auth/list",
      });
      if (Array.isArray(users)) {
        this._users = users
          .filter((u) => !u.system_generated && u.is_active !== false)
          .map((u) => ({
            id: u.id,
            name: u.name || u.id,
            is_admin: Boolean(u.is_admin),
          }));
      }
    } catch (_err) {
      if (this.hass.user?.id) {
        this._users = [
          {
            id: this.hass.user.id,
            name: this.hass.user.name || "Current User",
            is_admin: Boolean(this.hass.user.is_admin),
          },
        ];
      }
    }
  }

  setConfig(config) {
    this.config = { ...config };
  }

  _updateConfig(patch) {
    const next = { ...(this.config || {}), ...patch };
    this.config = next;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: next },
        bubbles: true,
        composed: true,
      })
    );
  }

  _toggleAdminUser(userId, enabled) {
    const current = new Set(Array.isArray(this.config?.admin_users) ? this.config.admin_users : []);
    if (enabled) current.add(userId);
    else current.delete(userId);
    this._updateConfig({ admin_users: Array.from(current) });
  }

  render() {
    if (!this.hass || !this.config) return html``;
    const c = this.config;
    const adminVis =
      ["everyone", "admins_only", "selected_users", "hidden"].includes(c.admin_visibility)
        ? c.admin_visibility
        : c.hide_admin_setup
          ? "hidden"
          : Array.isArray(c.admin_users) && c.admin_users.length > 0
            ? "selected_users"
            : "everyone";
    const selectedUsers = Array.isArray(c.admin_users) ? c.admin_users : [];

    return html`
      <div class="editor-container">
        <div class="section-box">
          <h3>Appearance & Layout</h3>
          <ha-textfield
            label="Card Title"
            .value=${c.title ?? "Family Chores"}
            @input=${(ev) => this._updateConfig({ title: ev.target.value })}
          ></ha-textfield>
          <ha-textfield
            label="Card Subtitle"
            .value=${c.subtitle ?? "Smart Chores, Streaks & Screen Unlocks"}
            @input=${(ev) => this._updateConfig({ subtitle: ev.target.value })}
          ></ha-textfield>

          <div class="form-group">
            <label class="form-label">Display Mode</label>
            <select class="custom-select" .value=${c.display_mode || "summary"} @change=${(ev) => this._updateConfig({ display_mode: ev.target.value })}>
              <option value="summary" ?selected=${(c.display_mode || "summary") === "summary"}>Summary Card + Popup Command Center (Recommended)</option>
              <option value="full" ?selected=${c.display_mode === "full"}>Full Embedded Command Center</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Layout Style</label>
            <select class="custom-select" .value=${c.layout || "board"} @change=${(ev) => this._updateConfig({ layout: ev.target.value })}>
              <option value="board" ?selected=${(c.layout || "board") === "board"}>Kid Columns Board (Recommended)</option>
              <option value="tiles" ?selected=${c.layout === "tiles"}>Compact 2-Column Kid Tiles</option>
              <option value="rows" ?selected=${c.layout === "rows"}>Stacked Kid Rows</option>
              <option value="rings" ?selected=${c.layout === "rings"}>Circular Progress Rings</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Chore Tile Size</label>
            <select class="custom-select" .value=${c.tile_size || "large"} @change=${(ev) => this._updateConfig({ tile_size: ev.target.value })}>
              <option value="large" ?selected=${(c.tile_size || "large") === "large"}>Large Picture / Emoji Tiles (Kid-Friendly)</option>
              <option value="compact" ?selected=${c.tile_size === "compact"}>Compact Rows</option>
            </select>
          </div>

          <div class="switch-row">
            <label class="form-label">Show Card Header</label>
            <ha-switch .checked=${c.show_header === true} @change=${(ev) => this._updateConfig({ show_header: ev.target.checked })}></ha-switch>
          </div>
          <div class="switch-row">
            <label class="form-label">Show Top Summary Strip</label>
            <ha-switch .checked=${c.show_summary_strip !== false} @change=${(ev) => this._updateConfig({ show_summary_strip: ev.target.checked })}></ha-switch>
          </div>
          <div class="switch-row">
            <label class="form-label">Show Bottom Footer Strip</label>
            <ha-switch .checked=${c.show_footer_strip !== false} @change=${(ev) => this._updateConfig({ show_footer_strip: ev.target.checked })}></ha-switch>
          </div>
          <div class="switch-row">
            <label class="form-label">Hide Kids With 0 Chores Today</label>
            <ha-switch .checked=${c.hide_inactive_kids !== false} @change=${(ev) => this._updateConfig({ hide_inactive_kids: ev.target.checked })}></ha-switch>
          </div>
        </div>

        <div class="section-box">
          <h3>Wall Panel & Access Control</h3>
          <div class="form-group">
            <label class="form-label">Parental PIN Requirement</label>
            <select
              class="custom-select"
              .value=${String(c.require_pin ?? "auto")}
              @change=${(ev) => {
                const v = ev.target.value;
                this._updateConfig({ require_pin: v === "true" ? true : v === "false" ? false : "auto" });
              }}
            >
              <option value="auto" ?selected=${String(c.require_pin ?? "auto") === "auto"}>Auto (Use Integration PIN Settings)</option>
              <option value="true" ?selected=${String(c.require_pin ?? "auto") === "true"}>Always Enforce on This Card</option>
              <option value="false" ?selected=${String(c.require_pin ?? "auto") === "false"}>Bypass on This Card (Trusted Parent View)</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Admin Setup Controls Visibility</label>
            <select
              class="custom-select"
              .value=${adminVis}
              @change=${(ev) => {
                const val = ev.target.value;
                this._updateConfig({ admin_visibility: val, hide_admin_setup: val === "hidden" });
              }}
            >
              <option value="everyone" ?selected=${adminVis === "everyone"}>Everyone</option>
              <option value="admins_only" ?selected=${adminVis === "admins_only"}>Home Assistant Admins Only</option>
              <option value="selected_users" ?selected=${adminVis === "selected_users"}>Selected Users Only</option>
              <option value="hidden" ?selected=${adminVis === "hidden"}>Hidden (Always Kiosk)</option>
            </select>
          </div>

          ${adminVis === "selected_users"
            ? html`
                <div class="users-checklist">
                  <div class="users-help">Select users who can view Command Center & admin controls (like HA's Visibility → User tab):</div>
                  ${this._users.length === 0
                    ? html`<div class="users-help">No active users loaded.</div>`
                    : this._users.map(
                        (u) => html`
                          <div class="user-check-row">
                            <div class="user-check-info">
                              <ha-icon icon="mdi:account-circle-outline" style="--mdc-icon-size:18px;"></ha-icon>
                              <span>${u.name}</span>
                              ${u.is_admin ? html`<span class="user-role-tag">Admin</span>` : ""}
                            </div>
                            <ha-switch
                              .checked=${selectedUsers.includes(u.id) || selectedUsers.includes(u.name)}
                              @change=${(ev) => this._toggleAdminUser(u.id, ev.target.checked)}
                            ></ha-switch>
                          </div>
                        `
                      )}
                </div>
              `
            : ""}
        </div>
      </div>
    `;
  }

  static get styles() {
    return css`
      .editor-container { display: flex; flex-direction: column; gap: 14px; }
      .section-box { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
      .section-box h3 { margin: 0; font-size: 14px; font-weight: 700; }
      .switch-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
      .form-group { display: flex; flex-direction: column; gap: 4px; }
      .form-label { font-size: 13px; color: var(--primary-text-color); }
      .custom-select { padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color, #ccc); background: var(--card-background-color, #fff); color: var(--primary-text-color); font-family: inherit; }
      .users-checklist { border-top: 1px solid var(--divider-color, #e0e0e0); padding-top: 8px; display: flex; flex-direction: column; gap: 8px; }
      .users-help { font-size: 12px; color: var(--secondary-text-color); }
      .user-check-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 4px 2px; }
      .user-check-info { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 500; }
      .user-role-tag { font-size: 10.5px; font-weight: 700; padding: 1px 6px; border-radius: 999px; background: rgba(2, 132, 199, 0.14); color: #0284c7; }
    `;
  }
}

if (!customElements.get("passable-chores-card")) {
  customElements.define("passable-chores-card", PassableChoresCard);
}
if (!customElements.get("passable-chores-card-editor")) {
  customElements.define("passable-chores-card-editor", PassableChoresCardEditor);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "passable-chores-card",
  name: "Passable Chores Card",
  description:
    "Passable design-system kids chore board with large emoji tiles, streaks, star rewards, parent approval, and Screen Time Engine unlocks.",
  preview: true,
  documentationURL: "https://github.com/GBear09/passable-smart-chores-engine",
});
