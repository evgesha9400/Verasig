/* Verasig prototype — Risk management & execution plan config */

/* Sample signal driving the plan preview (a real signal from this feed). */
const XP_SAMPLE = {
  id: "SIG-7F2A",
  side: "LONG",
  symbol: "BTC/USDT",
  rangeTop: 64200,
  rangeBottom: 63750,
  stop: 62400,
  tps: [66500, 68200, 71000],
  date: "Jun 6",
  time: "08:42",
};

function xpFmt(n) {
  return Math.round(n).toLocaleString("en-US");
}

/* Turn the current config into concrete orders for the sample signal. */
function xpPlan({
  entryMode,
  levels,
  weighting,
  mult,
  tpMode,
  mode,
  ownSl,
  ownTp,
}) {
  const s = XP_SAMPLE;
  let fills;
  if (entryMode === "first") {
    fills = [{ price: s.rangeTop, pct: 100 }];
  } else if (entryMode === "mid") {
    fills = [{ price: (s.rangeTop + s.rangeBottom) / 2, pct: 100 }];
  } else {
    const n = levels;
    const w = Array.from({ length: n }, (_, i) =>
      weighting === "martingale" ? Math.pow(mult, i) : 1,
    );
    const tot = w.reduce((a, b) => a + b, 0);
    let acc = 0;
    fills = w.map((wi, i) => {
      const price = s.rangeTop - ((s.rangeTop - s.rangeBottom) * i) / (n - 1);
      let pct = Math.round((wi / tot) * 100);
      acc += pct;
      if (i === n - 1) pct += 100 - acc;
      return { price, pct };
    });
  }
  const avg = fills.reduce((a, f) => a + f.price * f.pct, 0) / 100;

  let tps, stop;
  if (mode === "own") {
    stop = avg * (1 - ownSl / 100);
    tps = [{ label: "TP", price: avg * (1 + ownTp / 100), pct: 100 }];
  } else {
    stop = s.stop;
    const alloc =
      tpMode === "front"
        ? [50, 30, 20]
        : tpMode === "tp1"
          ? [100, 0, 0]
          : [34, 33, 33];
    tps = s.tps.map((p, i) => ({
      label: "TP" + (i + 1),
      price: p,
      pct: alloc[i],
    }));
  }
  return { fills, avg, tps, stop, slPct: ((stop - avg) / avg) * 100 };
}

function LadderRow({ tone, role, price, size, dim, note }) {
  return (
    <div className={`vrs-ladder__row ${dim ? "is-dim" : ""}`}>
      <span className={`vrs-ladder__node vrs-ladder__node--${tone}`}></span>
      <span className="vrs-ladder__role">{role}</span>
      <span className="vrs-ladder__price">
        {price}
        {note && <span className="vrs-ladder__note">{note}</span>}
      </span>
      <span className="vrs-ladder__size">{size}</span>
    </div>
  );
}

function PlanPreview({ plan, entryMode, beAfterTp1, followAuthor, mode }) {
  const s = XP_SAMPLE;
  const tpsDesc = [...plan.tps].reverse(); // highest target first, price descends down the rail
  return (
    <div className="vrs-plan-card">
      <div className="vrs-plan-card__head">
        <span className={`vrs-side vrs-side--${s.side.toLowerCase()}`}>
          {s.side}
        </span>
        <span className="vrs-plan-card__sym">{s.symbol}</span>
        <span className="vrs-plan-card__id">{s.id}</span>
      </div>
      <div className="vrs-ladder">
        {tpsDesc.map((tp) => (
          <LadderRow
            key={tp.label}
            tone="tp"
            role={tp.label}
            price={xpFmt(tp.price)}
            size={tp.pct + "%"}
            dim={tp.pct === 0}
          />
        ))}
        <div className="vrs-ladder__zone">
          <div className="vrs-ladder__zonehead">
            <span className="vrs-ladder__zonelabel">
              Entry zone · {xpFmt(s.rangeTop)} – {xpFmt(s.rangeBottom)}
            </span>
          </div>
          {plan.fills.map((f, i) => (
            <LadderRow
              key={i}
              tone="entry"
              role={entryMode === "ladder" ? "L" + (i + 1) : "Fill"}
              price={xpFmt(f.price)}
              size={f.pct + "%"}
            />
          ))}
        </div>
        <LadderRow
          tone="sl"
          role="SL"
          price={xpFmt(plan.stop)}
          size={plan.slPct.toFixed(1) + "%"}
          note={
            beAfterTp1 && mode === "signal"
              ? `moves to ${xpFmt(plan.avg)} (break-even) after TP1`
              : null
          }
        />
        <div className="vrs-ladder__stats">
          <div className="vrs-ladder__stat">
            <span className="vrs-ladder__statlabel">Avg entry</span>
            <span className="vrs-ladder__statval">{xpFmt(plan.avg)}</span>
          </div>
          <div className="vrs-ladder__stat">
            <span className="vrs-ladder__statlabel">First fill</span>
            <span className="vrs-ladder__statval">{plan.fills[0].pct}%</span>
          </div>
          <div className="vrs-ladder__stat">
            <span className="vrs-ladder__statlabel">Entry → SL</span>
            <span className="vrs-ladder__statval">
              {plan.slPct.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>
      <div className="vrs-plan-card__cap">
        {followAuthor && mode === "signal"
          ? "Author updates — partial closes, stop moves, early exits — override this plan when posted."
          : "Orders are placed exactly as planned; author updates are ignored."}
      </div>
    </div>
  );
}

function RiskView({ hasRisk = true, onRun }) {
  const { Button, Input, Banner, Select, Tabs, Switch } =
    window.VerasigDesignSystem_fd565b;
  const { useState } = React;
  const [mode, setMode] = useState(hasRisk ? "signal" : "own"); // signal | own
  const [missing, setMissing] = useState("fallback"); // fallback | skip

  /* Execution plan */
  const [entryMode, setEntryMode] = useState("ladder"); // first | mid | ladder
  const [levels, setLevels] = useState("3");
  const [weighting, setWeighting] = useState("equal"); // equal | martingale
  const [mult, setMult] = useState("×2");
  const [tpMode, setTpMode] = useState("equal"); // equal | front | tp1
  const [followAuthor, setFollowAuthor] = useState(true);
  const [beAfterTp1, setBeAfterTp1] = useState(false);
  const [ownSl, setOwnSl] = useState("4.0");
  const [ownTp, setOwnTp] = useState("8.0");

  const plan = xpPlan({
    entryMode,
    levels: parseInt(levels, 10),
    weighting,
    mult: parseFloat(mult.replace("×", "")),
    tpMode,
    mode,
    ownSl: parseFloat(ownSl) || 0,
    ownTp: parseFloat(ownTp) || 0,
  });

  const entryHints = {
    first:
      "The full position fills the moment price touches the top of the range. No averaging.",
    mid: "One limit order at the middle of the posted range. Misses fills when price only grazes the range.",
    ladder:
      weighting === "martingale"
        ? `${levels} limit orders from the top of the range to the bottom — each level ${mult} the size of the one before, so deeper fills carry more weight.`
        : `${levels} equal limit orders spread from the top of the range to the bottom.`,
  };
  const tpHints = {
    equal: "The position is split evenly across every posted target.",
    front: "50 / 30 / 20 — most of the position comes off at the first target.",
    tp1: "Close the full position at the first target. Later targets are ignored.",
  };

  return (
    <div
      className="vrs-page vrs-fade-in"
      style={{ maxWidth: 1010, margin: "0 auto", paddingTop: 40 }}
    >
      <div className="vrs-setup__hero" style={{ alignItems: "flex-start" }}>
        <span
          className="vrs-rule__ic"
          style={{ width: 44, height: 44, borderRadius: 10 }}
        >
          <Icon name="shield" size={22} />
        </span>
        <div>
          <div
            className="vrs-setup__title"
            style={{ fontSize: "var(--text-xl)" }}
          >
            Risk management
          </div>
          <div className="vrs-setup__sub">
            Decide how position sizing, stops and entries are applied to every
            verified signal before it reaches Bybit.
          </div>
        </div>
      </div>

      <div className="vrs-risk-grid">
        <div className="vrs-risk-grid__main">
          {hasRisk ? (
            <Banner tone="verified" title="Signals include risk management">
              92% of this feed’s signals define a stop-loss and at least one
              target. You can trust the source or override it.
            </Banner>
          ) : (
            <Banner tone="pending" title="No risk management detected">
              This feed’s signals don’t define stops or targets. Configure your
              own risk rules below.
            </Banner>
          )}

          <div className="vrs-opt-grid">
            {hasRisk && (
              <div
                className={`vrs-opt ${mode === "signal" ? "is-selected" : ""}`}
                onClick={() => setMode("signal")}
              >
                <span className="vrs-opt__radio"></span>
                <div className="vrs-opt__body">
                  <div className="vrs-opt__title">
                    Use the signal’s risk management
                  </div>
                  <div className="vrs-opt__desc">
                    Apply the entry, stop-loss and targets exactly as posted in
                    each signal.
                  </div>
                  {mode === "signal" && (
                    <div
                      className="vrs-opt__config"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Select
                        label="When a signal omits a stop-loss or take-profit"
                        value={missing}
                        onChange={(e) =>
                          setMissing(e.target ? e.target.value : missing)
                        }
                        options={[
                          {
                            value: "fallback",
                            label: "Apply a fallback stop-loss & take-profit",
                          },
                          {
                            value: "skip",
                            label: "Skip the signal — don’t trade it",
                          },
                        ]}
                      />
                      {missing === "fallback" ? (
                        <div className="vrs-form__row">
                          <Input
                            label="Fallback stop-loss"
                            mono
                            defaultValue="3.0"
                            trailing={<span className="vrs-input__kbd">%</span>}
                          />
                          <Input
                            label="Fallback take-profit"
                            mono
                            defaultValue="6.0"
                            trailing={<span className="vrs-input__kbd">%</span>}
                          />
                        </div>
                      ) : (
                        <div
                          className="vrs-rail__note"
                          style={{ maxWidth: "52ch" }}
                        >
                          Signals without a defined stop-loss and take-profit
                          will be skipped and never routed to Bybit.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div
              className={`vrs-opt ${mode === "own" ? "is-selected" : ""}`}
              onClick={() => setMode("own")}
            >
              <span className="vrs-opt__radio"></span>
              <div className="vrs-opt__body">
                <div className="vrs-opt__title">
                  Configure my own risk management
                </div>
                <div className="vrs-opt__desc">
                  Override every signal with a fixed risk model.
                </div>
                {mode === "own" && (
                  <div
                    className="vrs-opt__config"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="vrs-form__row">
                      <Input
                        label="Risk per trade"
                        mono
                        defaultValue="2.0"
                        trailing={<span className="vrs-input__kbd">%</span>}
                      />
                      <Select
                        label="Max leverage"
                        options={["3x", "5x", "10x", "20x"]}
                        defaultValue="5x"
                      />
                    </div>
                    <div className="vrs-form__row">
                      <Input
                        label="Stop-loss"
                        mono
                        value={ownSl}
                        onChange={(e) => setOwnSl(e.target.value)}
                        trailing={<span className="vrs-input__kbd">%</span>}
                      />
                      <Input
                        label="Take-profit"
                        mono
                        value={ownTp}
                        onChange={(e) => setOwnTp(e.target.value)}
                        trailing={<span className="vrs-input__kbd">%</span>}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="vrs-xplan">
            <div className="vrs-xplan__group">
              <div className="vrs-xplan__title">Entry ranges</div>
              <div className="vrs-xplan__hint">
                When a signal posts an entry range — like{" "}
                {xpFmt(XP_SAMPLE.rangeTop)} – {xpFmt(XP_SAMPLE.rangeBottom)} —
                decide how it becomes orders.
              </div>
              <Tabs
                variant="pill"
                value={entryMode}
                onChange={setEntryMode}
                items={[
                  { id: "first", label: "First touch" },
                  { id: "mid", label: "Midpoint" },
                  { id: "ladder", label: "Laddered (DCA)" },
                ]}
              />
              {entryMode === "ladder" && (
                <div className="vrs-xplan__row">
                  <Select
                    label="Levels"
                    value={levels}
                    onChange={(e) => setLevels(e.target.value)}
                    options={["2", "3", "4", "5"]}
                  />
                  <Select
                    label="Size per level"
                    value={weighting}
                    onChange={(e) => setWeighting(e.target.value)}
                    options={[
                      { value: "equal", label: "Equal" },
                      { value: "martingale", label: "Martingale" },
                    ]}
                  />
                  {weighting === "martingale" && (
                    <Select
                      label="Multiplier"
                      value={mult}
                      onChange={(e) => setMult(e.target.value)}
                      options={["×1.5", "×2", "×3"]}
                    />
                  )}
                </div>
              )}
              <div className="vrs-help">{entryHints[entryMode]}</div>
            </div>

            <div className="vrs-xplan__group">
              <div className="vrs-xplan__title">Take profits</div>
              {mode === "signal" ? (
                <>
                  <div className="vrs-xplan__hint">
                    How the position is split when a signal posts multiple
                    targets.
                  </div>
                  <Tabs
                    variant="pill"
                    value={tpMode}
                    onChange={setTpMode}
                    items={[
                      { id: "equal", label: "Equal split" },
                      { id: "front", label: "Front-heavy" },
                      { id: "tp1", label: "TP1 only" },
                    ]}
                  />
                  <div className="vrs-help">{tpHints[tpMode]}</div>
                  <div className="vrs-xplan__switches">
                    <div>
                      <Switch
                        label="Follow the author’s updates"
                        checked={followAuthor}
                        onChange={(e) => setFollowAuthor(e.target.checked)}
                      />
                      <div className="vrs-xplan__swdesc">
                        Partial closes, stop moves and early exits posted as
                        replies override this allocation.
                      </div>
                    </div>
                    <div>
                      <Switch
                        label="Move stop to break-even after TP1"
                        checked={beAfterTp1}
                        onChange={(e) => setBeAfterTp1(e.target.checked)}
                      />
                      <div className="vrs-xplan__swdesc">
                        Once the first target fills, the stop moves to the
                        average entry — the rest of the position runs risk-free.
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="vrs-xplan__hint">
                  Your fixed take-profit replaces the signal’s targets, so
                  allocation across multiple targets doesn’t apply. Entry-range
                  handling above still does.
                </div>
              )}
            </div>
          </div>

          <div className="vrs-form__actions">
            <Button
              variant="primary"
              size="lg"
              iconLeft={<Icon name="play" size={15} fill />}
              onClick={onRun}
            >
              Run backtest
            </Button>
          </div>
        </div>

        <aside className="vrs-risk-aside">
          <PlanPreview
            plan={plan}
            entryMode={entryMode}
            beAfterTp1={beAfterTp1}
            followAuthor={followAuthor}
            mode={mode}
          />
          <div
            className="vrs-plan-card__cap"
            style={{ marginTop: 10, paddingInline: 4 }}
          >
            Plan preview · sample signal from this feed, {XP_SAMPLE.date} ·{" "}
            {XP_SAMPLE.time}. The backtest applies this plan to every signal.
          </div>
        </aside>
      </div>
    </div>
  );
}
window.RiskView = RiskView;
