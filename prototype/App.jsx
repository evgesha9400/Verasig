/* Verasig prototype — app shell, routing & workflow state machine */
const { useState, useEffect, useRef } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/ {}; /*EDITMODE-END*/

// Theme drives the brand signal color: dark = lime trace, light = azure.
// Mirrors design-system ThemeProvider.THEMES exactly so the prototype stays an
// accurate source of truth: accent-text is the readable foreground (light keeps
// the darker azure #2F6FE0, not the low-contrast hover), quiet is a 0.12 tint
// and glow a separate 0.28 — they are distinct tokens, not one shared value.
const THEME_ACCENTS = {
  dark: {
    accent: "#B9EE2E",
    hover: "#CBF457",
    press: "#8FB81E",
    text: "#CBF457",
    quiet: "rgba(185,238,46,0.12)",
    glow: "rgba(185,238,46,0.28)",
    verified: "#B9EE2E",
  },
  light: {
    accent: "#5197FF",
    hover: "#82B6FF",
    press: "#2F6FE0",
    text: "#2F6FE0",
    quiet: "rgba(81,151,255,0.12)",
    glow: "rgba(81,151,255,0.28)",
    verified: "#5197FF",
  },
};
const THEME_KEY = "vrs-theme-1";
function loadTheme() {
  try {
    return localStorage.getItem(THEME_KEY) || "dark";
  } catch (e) {
    return "dark";
  }
}

const LS_KEY = "vrs-proto-state-1";
function loadState() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY)) || null;
  } catch (e) {
    return null;
  }
}

const USER_KEY = "vrs-user-1";
const USER_DEFAULTS = {
  firstName: "Mara",
  lastName: "Voss",
  email: "mara@northwave.io",
  plan: "operator",
  pendingEmail: null,
  cancelAt: null,
};
function loadUser() {
  try {
    return {
      ...USER_DEFAULTS,
      ...(JSON.parse(localStorage.getItem(USER_KEY)) || {}),
    };
  } catch (e) {
    return { ...USER_DEFAULTS };
  }
}

// Overlay static integrity flags (history gaps / confirmed signal deletion) from the seed
// data onto any persisted chats, so older saved state still surfaces the pills.
function mergeChatFlags(savedChats) {
  if (!Array.isArray(savedChats)) return window.VRS_DATA.CHATS;
  const seed = Object.fromEntries(window.VRS_DATA.CHATS.map((c) => [c.id, c]));
  return savedChats.map((c) => {
    const s = seed[c.id];
    return s
      ? { ...c, historyGaps: s.historyGaps, signalDeletion: s.signalDeletion }
      : c;
  });
}

function App() {
  const { Button, IconButton, ToastStack, Toast, Badge, Dialog } =
    window.VerasigDesignSystem_fd565b;
  const [t, setTweak] = useTweaks({
    execControls: "Segmented",
    ...TWEAK_DEFAULTS,
  });

  const saved = useRef(loadState()).current;
  const [theme, setTheme] = useState(loadTheme());
  function changeTheme(next) {
    setTheme(next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch (e) {}
  }
  const [nav, setNav] = useState("sources");
  const [user, setUser] = useState(loadUser());
  const prevNavRef = useRef("sources");
  function updateUser(patch) {
    setUser((u) => {
      const n = { ...u, ...patch };
      try {
        localStorage.setItem(USER_KEY, JSON.stringify(n));
      } catch (e) {}
      return n;
    });
  }
  function openSettings() {
    if (nav !== "settings") prevNavRef.current = nav;
    setNav("settings");
  }
  const [screen, setScreen] = useState(saved ? saved.screen : "sources");
  const [telegramConnected, setTelegramConnected] = useState(
    saved ? saved.telegramConnected : false,
  );
  const [chats, setChats] = useState(
    saved ? mergeChatFlags(saved.chats) : window.VRS_DATA.CHATS,
  );
  const [activeChatId, setActiveChatId] = useState(
    saved ? saved.activeChatId : null,
  );
  const [labelsByChat, setLabelsByChat] = useState(
    saved ? saved.labelsByChat : {},
  );
  const [verifyAttempt, setVerifyAttempt] = useState(
    saved ? saved.verifyAttempt : 1,
  );
  const [bybitConnected, setBybitConnected] = useState(
    saved ? saved.bybitConnected : false,
  );
  const [toast, setToast] = useState(null);
  const [backTarget, setBackTarget] = useState(null); // pending back-navigation that needs confirmation
  const [signalsPreset, setSignalsPreset] = useState(null);

  function goToDeletedSignals(c) {
    setSignalsPreset({
      source: "all",
      feed: c.id,
      tab: "deleted",
      _t: Date.now(),
    });
    setNav("signals");
  }

  // persist
  useEffect(() => {
    localStorage.setItem(
      LS_KEY,
      JSON.stringify({
        screen,
        telegramConnected,
        chats,
        activeChatId,
        labelsByChat,
        verifyAttempt,
        bybitConnected,
      }),
    );
  }, [
    screen,
    telegramConnected,
    chats,
    activeChatId,
    labelsByChat,
    verifyAttempt,
    bybitConnected,
  ]);

  // apply tweaks
  useEffect(() => {
    const root = document.documentElement;
    const t = THEME_ACCENTS[theme] || THEME_ACCENTS.dark;
    root.style.setProperty("--accent", t.accent);
    root.style.setProperty("--accent-hover", t.hover);
    root.style.setProperty("--accent-press", t.press);
    root.style.setProperty("--accent-text", t.text);
    root.style.setProperty("--accent-quiet", t.quiet);
    root.style.setProperty("--signal-500", t.accent);
    root.style.setProperty("--signal-400", t.hover);
    root.style.setProperty("--signal-600", t.press);
    root.style.setProperty("--signal-glow", t.glow);
    root.style.setProperty("--verified-500", t.verified);
    root.setAttribute("data-density", "regular");
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-wide", "center");
  }, [theme]);

  // Any view that renders a persistent right rail (Label, Verify, …) needs the
  // topbar + stepper to center over the work area, not the full main width.
  // The rail can appear/disappear from a child component's INTERNAL state change
  // (e.g. Verify's pass/fail screens) without App re-rendering, so a render-time
  // check goes stale. Watch the DOM itself: recompute on every subtree mutation.
  React.useLayoutEffect(() => {
    const update = () => {
      const hasRail = !!document.querySelector(".vrs-scroll .vrs-rail");
      document.documentElement.setAttribute(
        "data-rail",
        hasRail ? "on" : "off",
      );
    };
    update();
    const mo = new MutationObserver(update);
    mo.observe(document.body, { childList: true, subtree: true });
    return () => mo.disconnect();
  }, []);

  const activeChat = chats.find((c) => c.id === activeChatId) || null;
  const labels = (activeChatId && labelsByChat[activeChatId]) || {};
  // 'modifier' is a legacy label value from an earlier flow — a reply that is a
  // signal IS an update, so it counts as a signal; the link is derived, not labelled.
  const signalCount = Object.values(labels).filter(
    (v) => v === "signal" || v === "modifier",
  ).length;
  const noiseCount = Object.values(labels).filter((v) => v === "noise").length;

  function patchChat(id, patch) {
    setChats((cs) => cs.map((c) => (c.id === id ? { ...c, ...patch } : c)));
  }
  function fireToast(tone, title, msg) {
    setToast({
      tone,
      title,
      msg,
      time: new Date().toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    });
    setTimeout(() => setToast(null), 4200);
  }

  // ---- workflow transitions ----
  function startBackfill(c) {
    setActiveChatId(c.id);
    patchChat(c.id, { status: "backfilling" });
    setScreen("backfill");
  }
  function retryBackfill(c) {
    setActiveChatId(c.id);
    patchChat(c.id, { status: "backfilling" });
    setScreen("backfill");
  }
  function resumeChat(c) {
    setActiveChatId(c.id);
    if (c.status === "analyzed") setScreen("backtest-result");
    else if (c.status === "backfilled") setScreen("label");
    else setScreen("label");
  }
  function reanalyze(c) {
    setActiveChatId(c.id);
    patchChat(c.id, { status: "backfilling" });
    setScreen("backfill");
    fireToast("info", "Re-backfilling", `Fetching new signals from ${c.name}.`);
  }
  function restartChat(c) {
    patchChat(c.id, {
      status: "new",
      fetched: 0,
      lastDate: null,
      score: null,
      winRate: null,
      pnl: null,
    });
    setLabelsByChat((m) => {
      const n = { ...m };
      delete n[c.id];
      return n;
    });
    fireToast(
      "rejected",
      "Feed reset",
      `${c.name} backfill and labels deleted.`,
    );
  }
  function checkGaps(c) {
    if (c.signalDeletion)
      fireToast(
        "rejected",
        "Signal deletion confirmed",
        `${c.name} is missing extracted signals — quality is floored to 0.`,
      );
    else if (c.historyGaps)
      fireToast(
        "pending",
        "History gaps found",
        `${c.name} has breaks in its message-ID sequence — some history may be missing.`,
      );
    else
      fireToast(
        "verified",
        "No gaps found",
        `${c.name}’s message history is contiguous — no missing IDs.`,
      );
  }
  // Stop after Verify: save the source as verified without backtesting / connecting an exchange.
  function stopAfterVerify() {
    const c = chats.find((x) => x.id === activeChatId);
    patchChat(activeChatId, { status: "verified", hasRisk: true });
    setScreen("chats");
    fireToast(
      "verified",
      "Source verified",
      `${c ? c.name : "Feed"} is verified and saved. Backtest it any time from the feed options.`,
    );
  }
  // Backtest later: pick up a verified-only feed at the exchange step of the happy path.
  function backtestFeed(c) {
    setActiveChatId(c.id);
    setScreen("exchange");
  }

  function onBackfillComplete(total) {
    patchChat(activeChatId, {
      status: "backfilled",
      fetched: total,
      lastDate: "Nov 18, 2025",
    });
    setScreen("label");
  }
  function onBackfillCancel(count, date) {
    patchChat(activeChatId, {
      status: "cancelled",
      fetched: count,
      lastDate: date,
    });
    setScreen("chats");
    fireToast(
      "pending",
      "Backfill paused",
      `Saved at ${count.toLocaleString()} messages. Retry any time.`,
    );
  }

  function setLabel(msgId, label) {
    setLabelsByChat((m) => ({
      ...m,
      [activeChatId]: { ...(m[activeChatId] || {}), [msgId]: label },
    }));
  }

  // ---- backward navigation (pipeline stepper) ----
  // Free for review/config steps; going back to Label from beyond Verify
  // invalidates the distilled rules, so that one asks first.
  function requestStepBack(stepId) {
    const order = window.PIPELINE_STEPS.map((s) => s.id);
    const cur = { "backtest-result": "backtest" }[screen] || screen;
    if (stepId === "label" && order.indexOf(cur) > order.indexOf("verify")) {
      setBackTarget(stepId);
      return;
    }
    setScreen(stepId);
  }
  function confirmStepBack() {
    const target = backTarget;
    setBackTarget(null);
    setScreen(target);
    fireToast(
      "pending",
      "Back to Label",
      "Your labels are kept. Distill and Verify will run again before routing.",
    );
  }

  // ---- screen rendering ----
  const isWorkflow = [
    "backfill",
    "label",
    "distill",
    "verify",
    "exchange",
    "risk",
    "backtest",
    "backtest-result",
  ].includes(screen);
  const pipelineStep = {
    backfill: "backfill",
    label: "label",
    distill: "distill",
    verify: "verify",
    exchange: "exchange",
    risk: "risk",
    backtest: "backtest",
    "backtest-result": "backtest",
  }[screen];

  function exitToChats() {
    setScreen("chats");
  }
  function exitToSources() {
    setScreen("sources");
  }

  // top bar title/sub per screen
  let title = "Sources",
    subtitle = "Connect where your signals come from",
    breadcrumb = null,
    onExit = null,
    pipeline = null,
    body = null,
    actions = null;

  if (nav === "signals") {
    title = "Signals";
    subtitle = "Signals extracted from your analyzed feeds";
    body = (
      <SignalsView
        feeds={chats}
        initial={signalsPreset}
        onGoToSources={() => {
          setNav("sources");
          setScreen(telegramConnected ? "chats" : "sources");
        }}
      />
    );
  } else if (nav === "exchanges") {
    title = "Exchanges";
    subtitle = "Where verified signals are routed";
    body = (
      <ExchangesView
        bybitConnected={bybitConnected}
        onConnect={() => {
          setBybitConnected(true);
          fireToast(
            "verified",
            "Bybit connected",
            "Verified signals will route to Bybit.",
          );
        }}
        onDisconnect={() => {
          setBybitConnected(false);
          fireToast(
            "rejected",
            "Bybit disconnected",
            "Verified signals are no longer routing to Bybit.",
          );
        }}
      />
    );
  } else if (nav === "settings") {
    title = "Account settings";
    subtitle = "Profile, security & subscription";
    breadcrumb = "Back";
    onExit = () => setNav(prevNavRef.current || "sources");
    body = (
      <SettingsView user={user} onUpdateUser={updateUser} onToast={fireToast} />
    );
  } else {
    // nav === 'sources'
    if (screen === "sources") {
      title = "Sources";
      subtitle = "Connect where your signals come from";
      body = (
        <SourcesView
          telegramConnected={telegramConnected}
          chats={chats}
          onConnectTelegram={() => setScreen("tg-setup")}
          onOpenTelegram={() => setScreen("chats")}
        />
      );
    } else if (screen === "tg-setup") {
      title = "Connect Telegram";
      subtitle = "Source setup";
      breadcrumb = "Sources";
      onExit = exitToSources;
      body = (
        <TelegramSetup
          onConnected={() => {
            setTelegramConnected(true);
            setScreen("chats");
            fireToast(
              "verified",
              "Telegram connected",
              "Pulling your feed list.",
            );
          }}
          onCancel={exitToSources}
        />
      );
    } else if (screen === "chats") {
      title = "Telegram";
      subtitle = `${chats.length} feeds · ${chats.filter((c) => c.status === "analyzed").length} analyzed`;
      breadcrumb = "Sources";
      onExit = exitToSources;
      body = (
        <ChatsView
          chats={chats}
          onStartBackfill={startBackfill}
          onRetry={retryBackfill}
          onResume={resumeChat}
          onReanalyze={reanalyze}
          onRestart={restartChat}
          onViewDeleted={goToDeletedSignals}
          onCheckGaps={checkGaps}
          onBacktest={backtestFeed}
        />
      );
    } else if (isWorkflow && activeChat) {
      breadcrumb = activeChat.name;
      onExit = exitToChats;
      pipeline = (
        <Pipeline current={pipelineStep} onStepBack={requestStepBack} />
      );
      const stepTitles = {
        backfill: ["Backfill", "Pulling message history"],
        label: ["Label", "Teach Verasig what a signal looks like"],
        distill: ["Distill", "Generating filter rules"],
        verify: ["Verify", "Confirm the rules hold"],
        exchange: ["Exchange", "Route verified signals"],
        risk: ["Execution", "Size, entry and exit for every verified signal"],
        backtest: ["Backtest", "Simulating performance"],
        "backtest-result": ["Signal quality", "Backtest results"],
      };
      title = stepTitles[screen][0];
      subtitle = `${activeChat.name} · ${stepTitles[screen][1]}`;

      if (screen === "backfill")
        body = (
          <BackfillView
            chat={activeChat}
            onCancel={onBackfillCancel}
            onComplete={onBackfillComplete}
          />
        );
      else if (screen === "label")
        body = (
          <LabelView
            messages={window.VRS_DATA.MESSAGES}
            labels={labels}
            onLabel={setLabel}
            signalCount={signalCount}
            noiseCount={noiseCount}
            onDistill={() => setScreen("distill")}
            key={"label-" + verifyAttempt}
          />
        );
      else if (screen === "distill")
        body = <DistillView onComplete={() => setScreen("verify")} />;
      else if (screen === "verify")
        body = (
          <VerifyView
            key={"verify-" + verifyAttempt}
            attempt={verifyAttempt}
            onPass={() => setScreen("exchange")}
            onStop={stopAfterVerify}
            onLoop={() => {
              setVerifyAttempt((a) => a + 1);
              setScreen("label");
              fireToast(
                "pending",
                "Refining rules",
                "Label a few more, then we’ll re-verify.",
              );
            }}
          />
        );
      else if (screen === "exchange")
        body = (
          <ExchangeView
            bybitConnected={bybitConnected}
            onConnected={() => {
              setBybitConnected(true);
              setScreen("risk");
            }}
          />
        );
      else if (screen === "risk")
        body = (
          <ExecutionView
            layout="flow"
            controls={t.execControls === "Radio cards" ? "radio" : "segmented"}
            hasRisk={true}
            onRun={() => setScreen("backtest")}
          />
        );
      else if (screen === "backtest")
        body = (
          <BacktestView
            chat={activeChat}
            onComplete={(sd) => {
              patchChat(activeChatId, {
                status: "analyzed",
                score: sd.score,
                winRate: sd.winRate,
                pnl: sd.pnl,
                hasRisk: true,
              });
              setScreen("chats");
              fireToast(
                "verified",
                "Source verified",
                `${activeChat.name} scored ${sd.score}/100 and is ready to go live.`,
              );
            }}
          />
        );
      else if (screen === "backtest-result")
        body = (
          <BacktestView
            chat={activeChat}
            skipRun={true}
            onComplete={() => setScreen("chats")}
          />
        );
    } else {
      title = "Sources";
      body = (
        <SourcesView
          telegramConnected={telegramConnected}
          chats={chats}
          onConnectTelegram={() => setScreen("tg-setup")}
          onOpenTelegram={() => setScreen("chats")}
        />
      );
    }
  }

  // top-right actions
  if (nav === "sources" && screen === "chats") {
    actions = (
      <IconButton
        label="Refresh feeds"
        onClick={() =>
          fireToast("info", "Refreshed", "Feed list synced with Telegram.")
        }
      >
        <Icon name="refresh" size={16} />
      </IconButton>
    );
  }

  function handleNav(id) {
    setNav(id);
    if (id === "sources")
      setScreen(
        telegramConnected ? (isWorkflow ? screen : "sources") : "sources",
      );
  }

  return (
    <>
      <Shell
        nav={nav}
        onNavigate={handleNav}
        title={title}
        subtitle={subtitle}
        breadcrumb={breadcrumb}
        onExit={onExit}
        actions={actions}
        pipeline={pipeline}
        theme={theme}
        onThemeChange={changeTheme}
        onLogout={() => {
          window.location.href = "Marketing.html";
        }}
        user={user}
        onOpenSettings={openSettings}
      >
        {body}
      </Shell>

      <Dialog
        open={!!backTarget}
        onClose={() => setBackTarget(null)}
        title="Go back to Label?"
        description="Changing labels invalidates the distilled ruleset."
        icon={<Icon name="alert" size={19} />}
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setBackTarget(null)}
            >
              Stay here
            </Button>
            <Button variant="primary" size="sm" onClick={confirmStepBack}>
              Go back to Label
            </Button>
          </>
        }
      >
        Your existing labels are kept, but Distill and Verify will run again
        before signals can route. Exchange and execution settings are
        unaffected.
      </Dialog>

      {toast && (
        <ToastStack>
          <Toast
            tone={toast.tone}
            title={toast.title}
            time={toast.time}
            onClose={() => setToast(null)}
          >
            {toast.msg}
          </Toast>
        </ToastStack>
      )}

      <TweaksPanel title="Tweaks">
        <TweakSection label="Execution step" />
        <TweakRadio
          label="Choice style"
          value={t.execControls}
          options={["Segmented", "Radio cards"]}
          onChange={(v) => setTweak("execControls", v)}
        />
        <TweakSection label="Prototype" />
        <TweakButton
          label="Clear progress & restart"
          onClick={() => {
            localStorage.removeItem(LS_KEY);
            location.reload();
          }}
        />
      </TweaksPanel>
    </>
  );
}

/* ---- small auxiliary views ---- */
function PlaceholderView({ label, note }) {
  return (
    <div className="vrs-page">
      <div
        className="vrs-empty"
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          minHeight: 360,
          textAlign: "center",
        }}
      >
        <svg
          width="34"
          height="34"
          viewBox="0 0 40 40"
          fill="none"
          style={{ color: "var(--text-faint)" }}
        >
          <path
            d="M4 22 L11 22 L17 30 L24 9 L30 18"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="30" cy="18" r="3" fill="currentColor" />
        </svg>
        <div
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "var(--text-lg)",
            color: "var(--text-strong)",
            marginTop: 6,
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: "var(--text-sm)",
            color: "var(--text-muted)",
            maxWidth: "34ch",
          }}
        >
          {note}
        </div>
      </div>
    </div>
  );
}

function ExchangesView({ bybitConnected, onConnect, onDisconnect }) {
  const { Badge, Button, Dialog, Input, Banner, Switch } =
    window.VerasigDesignSystem_fd565b;
  const { EXCHANGES } = window.VRS_DATA;
  const bybit = EXCHANGES.find((d) => d.id === "bybit");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [key, setKey] = useState("");
  const [secret, setSecret] = useState("");
  const valid = key.trim().length >= 12 && secret.trim().length >= 12;
  function startConfigure() {
    setConfiguring(true);
    setKey("");
    setSecret("");
  }
  function cancelConfigure() {
    if (verifying) return;
    setConfiguring(false);
    setKey("");
    setSecret("");
  }
  function verifyAndConnect() {
    if (!valid || verifying) return;
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      setConfiguring(false);
      setKey("");
      setSecret("");
      onConnect && onConnect();
    }, 1700);
  }
  const ByLogo = () => (
    <span
      className="vrs-src-logo"
      style={{
        background: `color-mix(in srgb, ${bybit.brand} 18%, transparent)`,
        color: bybit.brand,
      }}
    >
      <Icon name="bybit" size={26} fill />
    </span>
  );
  return (
    <div className="vrs-page">
      {/* Connected */}
      <div>
        <div className="vrs-sec-h">
          <span className="vrs-sec-t">Connected exchanges</span>
        </div>
        <div className="vrs-src-grid" style={{ marginTop: 12 }}>
          {bybitConnected ? (
            <div className="vrs-src-card is-clickable">
              <div className="vrs-src-card__top">
                <ByLogo />
                <div style={{ flex: 1 }}>
                  <div className="vrs-src-card__name">{bybit.name}</div>
                  <div className="vrs-src-card__kind">{bybit.kind}</div>
                </div>
                <Badge tone="verified" dot>
                  Connected
                </Badge>
              </div>
              <div className="vrs-src-card__desc">
                Trade-only API key linked. Verified signals route here in real
                time.
              </div>
              <div className="vrs-src-card__foot">
                <span className="vrs-src-meta">
                  <Icon name="key" size={13} /> {bybit.account}
                </span>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setConfirmOpen(true)}
                >
                  Disconnect
                </Button>
              </div>
            </div>
          ) : (
            <div
              className="vrs-src-card"
              style={{
                borderStyle: "dashed",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                minHeight: 168,
                color: "var(--text-faint)",
              }}
            >
              <div className="vrs-src-card__desc" style={{ flex: "none" }}>
                No exchanges connected yet.
                <br />
                Configure {bybit.name} below to route signals.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Available */}
      <div>
        <div className="vrs-sec-h">
          <span className="vrs-sec-t">Available to configure</span>
        </div>
        <div className="vrs-src-grid" style={{ marginTop: 12 }}>
          {!bybitConnected && (
            <div
              className="vrs-src-card"
              style={
                configuring
                  ? { gridColumn: "1 / -1", maxWidth: 520 }
                  : undefined
              }
            >
              <div className="vrs-src-card__top">
                <ByLogo />
                <div style={{ flex: 1 }}>
                  <div className="vrs-src-card__name">{bybit.name}</div>
                  <div className="vrs-src-card__kind">{bybit.kind}</div>
                </div>
                {configuring && <Badge tone="pending">Not configured</Badge>}
              </div>
              {configuring ? (
                <div
                  className="vrs-opt__config"
                  style={{ marginTop: 0, paddingTop: 4, borderTop: 0 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {verifying ? (
                    <Banner tone="info" title="Verifying API credentials…">
                      Checking permissions and placing a zero-value test order.
                    </Banner>
                  ) : (
                    <Banner tone="pending" title="Use a trade-only key">
                      Create an API key with trade permission in Bybit → API
                      Management. Disable withdrawal — Verasig only needs read +
                      trade.
                    </Banner>
                  )}
                  <Input
                    label="API Key"
                    mono
                    placeholder="J7n2Kp9XvR4mQ1wL"
                    value={key}
                    onChange={(e) => setKey(e.target.value)}
                    disabled={verifying}
                    iconLeft={<Icon name="key" size={15} />}
                    required
                  />
                  <Input
                    label="API Secret"
                    mono
                    placeholder="••••••••••••••••••••••••"
                    value={secret}
                    onChange={(e) => setSecret(e.target.value)}
                    disabled={verifying}
                    iconLeft={<Icon name="lock" size={15} />}
                    required
                    type="password"
                  />
                  <div className="vrs-row-between" style={{ padding: "0 2px" }}>
                    <Switch label="Use testnet first" />
                    <span className="vrs-help">
                      Recommended for the first run.
                    </span>
                  </div>
                  <div className="vrs-row-between">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={cancelConfigure}
                      disabled={verifying}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      loading={verifying}
                      disabled={!valid && !verifying}
                      onClick={verifyAndConnect}
                      iconLeft={
                        verifying ? null : <Icon name="check" size={16} />
                      }
                    >
                      {verifying ? "Verifying…" : "Connect & verify"}
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="vrs-src-card__desc">
                    Route verified signals to Bybit for execution. Uses a
                    trade-only API key — Verasig never withdraws funds.
                  </div>
                  <div className="vrs-src-card__foot">
                    <span className="vrs-src-meta">
                      <Icon name="clock" size={13} /> ~1 min setup
                    </span>
                    <Button
                      variant="primary"
                      size="sm"
                      iconLeft={<Icon name="plus" size={14} />}
                      onClick={startConfigure}
                    >
                      Configure
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <Dialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Disconnect Bybit?"
        description="Verified signals will stop routing to Bybit immediately."
        icon={<Icon name="trash" size={19} />}
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                setConfirmOpen(false);
                onDisconnect && onDisconnect();
              }}
            >
              Disconnect Bybit
            </Button>
          </>
        }
      >
        Your trade-only API key ({bybit.account}) will be removed from Verasig.
        Open positions are unaffected — only new signal routing stops. You can
        reconnect any time.
      </Dialog>
    </div>
  );
}

window.App = App;
