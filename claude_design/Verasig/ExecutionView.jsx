/* Verasig prototype — Execution step (reorganised risk step) exploration.
   Lifecycle order: 01 Position size → 02 Entry → 03 Exit.
   layout: 'cards' | 'flow' | 'ledger' · controls: 'segmented' | 'radio' */

const VX_SAMPLE = {
  id: 'SIG-7F2A', side: 'LONG', symbol: 'BTC/USDT',
  rangeTop: 64200, rangeBottom: 63750, stop: 62400,
  tps: [66500, 68200, 71000],
  date: 'Jun 6', time: '08:42',
};

function vxFmt(n) { return Math.round(n).toLocaleString('en-US'); }

function vxPlan({ entryMode, levels, weighting, mult, tpMode, exitSrc, ownSl, ownTp }) {
  const s = VX_SAMPLE;
  let fills;
  if (entryMode === 'first') {
    fills = [{ price: s.rangeTop, pct: 100 }];
  } else if (entryMode === 'mid') {
    fills = [{ price: (s.rangeTop + s.rangeBottom) / 2, pct: 100 }];
  } else {
    const n = levels;
    const w = Array.from({ length: n }, (_, i) => (weighting === 'martingale' ? Math.pow(mult, i) : 1));
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
  if (exitSrc === 'own') {
    stop = avg * (1 - ownSl / 100);
    tps = [{ label: 'TP', price: avg * (1 + ownTp / 100), pct: 100 }];
  } else {
    stop = s.stop;
    const alloc = tpMode === 'front' ? [50, 30, 20] : tpMode === 'tp1' ? [100, 0, 0] : [34, 33, 33];
    tps = s.tps.map((p, i) => ({ label: 'TP' + (i + 1), price: p, pct: alloc[i] }));
  }
  return { fills, avg, tps, stop, slPct: ((stop - avg) / avg) * 100 };
}

function VxLadderRow({ tone, role, price, size, dim, note, tie }) {
  return (
    <div className={`vrs-ladder__row vx-tie ${tie || ''} ${dim ? 'is-dim' : ''}`}>
      <span className={`vrs-ladder__node vrs-ladder__node--${tone}`}></span>
      <span className="vrs-ladder__role">{role}</span>
      <span className="vrs-ladder__price">{price}{note && <span className="vrs-ladder__note">{note}</span>}</span>
      <span className="vrs-ladder__size">{size}</span>
    </div>
  );
}

/* Preview ladder. `hot` = section id under the pointer; matching rungs light
   up, the rest fade — this is the rung↔section tie. */
function VxPreview({ plan, hot, entryMode, beAfterTp1, followAuthor, exitSrc, sizeSum }) {
  const s = VX_SAMPLE;
  const tie = (sec) => (hot ? (hot === sec ? 'is-tied' : 'is-faded') : '');
  const tpsDesc = [...plan.tps].reverse();
  return (
    <div className="vrs-plan-card">
      <div className="vrs-plan-card__head">
        <span className={`vrs-side vrs-side--${s.side.toLowerCase()}`}>{s.side}</span>
        <span className="vrs-plan-card__sym">{s.symbol}</span>
        <span className="vrs-plan-card__id">{s.id}</span>
      </div>
      <div className={`vx-prev-size vx-tie ${tie('size')}`}>
        <span className="vrs-ladder__statlabel">Size</span>
        <span className="vrs-ladder__statval">{sizeSum}</span>
      </div>
      <div className="vrs-ladder">
        {tpsDesc.map((tp) => (
          <VxLadderRow key={tp.label} tone="tp" role={tp.label} price={vxFmt(tp.price)} size={tp.pct === 0 ? '0%' : tp.pct + '%'} dim={tp.pct === 0} tie={tie('exit')} />
        ))}
        <div className={`vrs-ladder__zone vx-tie ${tie('entry')}`}>
          <div className="vrs-ladder__zonehead">
            <span className="vrs-ladder__zonelabel">Entry zone · {vxFmt(s.rangeTop)} – {vxFmt(s.rangeBottom)}</span>
          </div>
          {plan.fills.map((f, i) => (
            <VxLadderRow key={i} tone="entry"
              role={entryMode === 'ladder' ? 'L' + (i + 1) : 'Fill'}
              price={vxFmt(f.price)} size={f.pct + '%'} />
          ))}
        </div>
        <VxLadderRow tone="sl" role="SL" price={vxFmt(plan.stop)} size={plan.slPct.toFixed(1) + '%'}
          note={beAfterTp1 && exitSrc === 'signal' ? `moves to ${vxFmt(plan.avg)} (break-even) after TP1` : null}
          tie={tie('exit')} />
        <div className="vrs-ladder__stats">
          <div className={`vrs-ladder__stat vx-tie ${tie('entry')}`}>
            <span className="vrs-ladder__statlabel">Avg entry</span>
            <span className="vrs-ladder__statval">{vxFmt(plan.avg)}</span>
          </div>
          <div className={`vrs-ladder__stat vx-tie ${tie('exit')}`}>
            <span className="vrs-ladder__statlabel">Entry → SL</span>
            <span className="vrs-ladder__statval">{plan.slPct.toFixed(1)}%</span>
          </div>
        </div>
      </div>
      <div className="vrs-plan-card__cap">
        {exitSrc === 'signal' && followAuthor
          ? 'Author updates — partial closes, stop moves, early exits — override this plan when posted.'
          : 'Orders are placed exactly as planned; author updates are ignored.'}
      </div>
    </div>
  );
}

function VxRadio({ on, onClick, title, desc }) {
  return (
    <div className={`vx-radio ${on ? 'is-on' : ''}`} onClick={onClick}>
      <span className="vrs-opt__radio"></span>
      <div>
        <div className="vx-radio__t">{title}</div>
        {desc && <div className="vx-radio__d">{desc}</div>}
      </div>
    </div>
  );
}

function ExecutionView({ layout = 'cards', controls = 'segmented', hasRisk = true, onRun }) {
  const { Button, Input, Select, Tabs, Switch } = window.VerasigDesignSystem_fd565b;
  const { useState } = React;

  /* 01 · Position size — always yours, regardless of exit source */
  const [riskPct, setRiskPct] = useState('2.0');
  const [lev, setLev] = useState('5x');

  /* 02 · Entry */
  const [entryMode, setEntryMode] = useState('ladder');
  const [levels, setLevels] = useState('3');
  const [weighting, setWeighting] = useState('equal');
  const [mult, setMult] = useState('×2');

  /* 03 · Exit */
  const [exitSrc, setExitSrc] = useState(hasRisk ? 'signal' : 'own');
  const [missing, setMissing] = useState('fallback');
  const [tpMode, setTpMode] = useState('equal');
  const [followAuthor, setFollowAuthor] = useState(true);
  const [beAfterTp1, setBeAfterTp1] = useState(false);
  const [ownSl, setOwnSl] = useState('4.0');
  const [ownTp, setOwnTp] = useState('8.0');

  const [hot, setHot] = useState(null);

  const plan = vxPlan({
    entryMode, levels: parseInt(levels, 10), weighting,
    mult: parseFloat(mult.replace('×', '')), tpMode, exitSrc,
    ownSl: parseFloat(ownSl) || 0, ownTp: parseFloat(ownTp) || 0,
  });

  const entryHints = {
    first: 'The full position fills the moment price touches the top of the range. No averaging.',
    mid: 'One limit order at the middle of the posted range. Misses fills when price only grazes the range.',
    ladder: weighting === 'martingale'
      ? `${levels} limit orders from the top of the range to the bottom — each level ${mult} the size of the one before.`
      : `${levels} equal limit orders spread from the top of the range to the bottom.`,
  };
  const tpHints = {
    equal: 'The position is split evenly across every posted target.',
    front: '50 / 30 / 20 — most of the position comes off at the first target.',
    tp1: 'Close the full position at the first target. Later targets are ignored.',
  };

  /* ── Section bodies (shared across the three layouts) ── */

  const sizeBody = (
    <>
      <div className="vrs-form__row" style={{ width: '100%', maxWidth: 420 }}>
        <Input label="Risk per trade" mono value={riskPct} onChange={(e) => setRiskPct(e.target.value)} trailing={<span className="vrs-input__kbd">%</span>} />
        <Select label="Max leverage" value={lev} onChange={(e) => setLev(e.target.value)} options={['3x', '5x', '10x', '20x']} />
      </div>
      <div className="vrs-help">Sizing is always yours — signal authors decide where to trade, never how much of your account to risk.</div>
    </>
  );

  const entryBody = (
    <>
      <Tabs variant="pill" value={entryMode} onChange={setEntryMode}
        items={[
          { id: 'first', label: 'First touch' },
          { id: 'mid', label: 'Midpoint' },
          { id: 'ladder', label: 'Laddered (DCA)' },
        ]} />
      {entryMode === 'ladder' && (
        <div className="vrs-xplan__row">
          <Select label="Levels" value={levels} onChange={(e) => setLevels(e.target.value)} options={['2', '3', '4', '5']} />
          <Select label="Size per level" value={weighting} onChange={(e) => setWeighting(e.target.value)}
            options={[
              { value: 'equal', label: 'Equal' },
              { value: 'martingale', label: 'Martingale' },
            ]} />
          {weighting === 'martingale' && (
            <Select label="Multiplier" value={mult} onChange={(e) => setMult(e.target.value)} options={['×1.5', '×2', '×3']} />
          )}
        </div>
      )}
      <div className="vrs-help">{entryHints[entryMode]}</div>
    </>
  );

  const srcControl = controls === 'segmented' ? (
    <Tabs variant="pill" value={exitSrc} onChange={setExitSrc}
      items={[
        { id: 'signal', label: 'Signal’s stops & targets' },
        { id: 'own', label: 'My own stop & target' },
      ]} />
  ) : (
    <div className="vx-radiogrp">
      <VxRadio on={exitSrc === 'signal'} onClick={() => setExitSrc('signal')}
        title="Signal’s stops & targets" desc="Exit exactly where each signal says to." />
      <VxRadio on={exitSrc === 'own'} onClick={() => setExitSrc('own')}
        title="My own stop & target" desc="One fixed stop-loss and take-profit for every signal." />
    </div>
  );

  const missingControl = controls === 'segmented' ? (
    <Tabs variant="pill" value={missing} onChange={setMissing}
      items={[
        { id: 'fallback', label: 'Apply a fallback' },
        { id: 'skip', label: 'Skip the signal' },
      ]} />
  ) : (
    <div className="vx-radiogrp">
      <VxRadio on={missing === 'fallback'} onClick={() => setMissing('fallback')} title="Apply a fallback" />
      <VxRadio on={missing === 'skip'} onClick={() => setMissing('skip')} title="Skip the signal" />
    </div>
  );

  const exitBody = (
    <>
      {srcControl}
      {exitSrc === 'signal' ? (
        <>
          {hasRisk && (
            <div className="vx-note vx-note--ok">
              <Icon name="check" size={13} />
              <span className="vx-note__txt">92% of this feed’s signals post a stop-loss and at least one target.</span>
            </div>
          )}
          <div className="vx-grouplabel">If a signal omits a stop or target</div>
          {missingControl}
          {missing === 'fallback' ? (
            <div className="vrs-form__row" style={{ width: '100%', maxWidth: 420 }}>
              <Input label="Fallback stop-loss" mono defaultValue="3.0" trailing={<span className="vrs-input__kbd">%</span>} />
              <Input label="Fallback take-profit" mono defaultValue="6.0" trailing={<span className="vrs-input__kbd">%</span>} />
            </div>
          ) : (
            <div className="vrs-help" style={{ maxWidth: '52ch' }}>Signals without a defined stop-loss and take-profit are never routed to Bybit.</div>
          )}
          <div className="vx-grouplabel">Across multiple targets</div>
          <Tabs variant="pill" value={tpMode} onChange={setTpMode}
            items={[
              { id: 'equal', label: 'Equal split' },
              { id: 'front', label: 'Front-heavy' },
              { id: 'tp1', label: 'TP1 only' },
            ]} />
          <div className="vrs-help">{tpHints[tpMode]}</div>
          <div className="vrs-xplan__switches" style={{ marginTop: 6 }}>
            <div>
              <Switch label="Follow the author’s updates" checked={followAuthor} onChange={(e) => setFollowAuthor(e.target.checked)} />
              <div className="vrs-xplan__swdesc">Partial closes, stop moves and early exits posted as replies override this plan. Relative updates — like “move stop to break-even” — resolve against your fills, not the author’s entry.</div>
            </div>
            <div>
              <Switch label="Move stop to break-even after TP1" checked={beAfterTp1} onChange={(e) => setBeAfterTp1(e.target.checked)} />
              <div className="vrs-xplan__swdesc">Once the first target fills, the stop moves to the average entry.</div>
            </div>
          </div>
          {followAuthor && beAfterTp1 && (
            <div className="vx-note vx-note--info">
              <Icon name="alert" size={13} />
              <span className="vx-note__txt">If these disagree, the tighter stop wins — an author update can tighten your stop, but never loosen it back below break-even.</span>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="vrs-form__row" style={{ width: '100%', maxWidth: 420 }}>
            <Input label="Stop-loss" mono value={ownSl} onChange={(e) => setOwnSl(e.target.value)} trailing={<span className="vrs-input__kbd">%</span>} />
            <Input label="Take-profit" mono value={ownTp} onChange={(e) => setOwnTp(e.target.value)} trailing={<span className="vrs-input__kbd">%</span>} />
          </div>
          <div className="vrs-help" style={{ maxWidth: '52ch' }}>Every signal exits at this fixed stop and target. Posted stops, targets and author updates are ignored.</div>
        </>
      )}
    </>
  );

  const secs = [
    { id: 'size', n: '01', title: 'Position size', hint: 'How much of your account each signal can put at risk.', sum: `${riskPct}% · ${lev}`, body: sizeBody },
    { id: 'entry', n: '02', title: 'Entry', hint: `How a posted range — like ${vxFmt(VX_SAMPLE.rangeTop)} – ${vxFmt(VX_SAMPLE.rangeBottom)} — becomes orders.`, sum: entryMode === 'ladder' ? `Ladder · ${levels} levels` : entryMode === 'first' ? 'First touch' : 'Midpoint', body: entryBody },
    { id: 'exit', n: '03', title: 'Exit', hint: 'Where stops and targets come from once you’re in.', sum: exitSrc === 'signal' ? 'Signal’s plan' : `SL ${ownSl}% · TP ${ownTp}%`, body: exitBody },
  ];

  const hover = (id) => ({ onMouseEnter: () => setHot(id), onMouseLeave: () => setHot(null) });

  let main;
  if (layout === 'flow') {
    main = (
      <div className="vx-flow">
        {secs.map((s) => (
          <div key={s.id} className={`vx-flow__sec ${hot === s.id ? 'is-hot' : ''}`} {...hover(s.id)}>
            <span className="vx-num">{s.n}</span>
            <div className="vx-flow__head"><span className="vx-flow__title">{s.title}</span></div>
            <div className="vx-flow__hint">{s.hint}</div>
            <div className="vx-flow__body">{s.body}</div>
          </div>
        ))}
      </div>
    );
  } else if (layout === 'ledger') {
    main = (
      <div className="vx-ledger">
        {secs.map((s) => (
          <div key={s.id} className={`vx-ledger__row ${hot === s.id ? 'is-hot' : ''}`} {...hover(s.id)}>
            <div className="vx-ledger__label">
              <div className="vx-ledger__title"><span className="vx-num">{s.n}</span>{s.title}</div>
              <div className="vx-ledger__hint">{s.hint}</div>
            </div>
            <div className="vx-ledger__body">{s.body}</div>
          </div>
        ))}
      </div>
    );
  } else {
    main = secs.map((s) => (
      <div key={s.id} className={`vx-card ${hot === s.id ? 'is-hot' : ''}`} {...hover(s.id)}>
        <div className="vx-card__head">
          <span className="vx-num">{s.n}</span>
          <span className="vx-card__title">{s.title}</span>
          <span className="vx-card__sum">{s.sum}</span>
        </div>
        <div className="vx-card__body">
          <div className="vx-hint">{s.hint}</div>
          {s.body}
        </div>
      </div>
    ));
  }

  return (
    <div className="vrs-page vrs-fade-in vx-page" style={{ paddingTop: 40 }}>
      <div className="vrs-setup__hero" style={{ alignItems: 'flex-start' }}>
        <span className="vrs-rule__ic" style={{ width: 44, height: 44, borderRadius: 10 }}><Icon name="target" size={22} /></span>
        <div>
          <div className="vrs-setup__title" style={{ fontSize: 'var(--text-xl)' }}>Execution</div>
          <div className="vrs-setup__sub">How each verified signal becomes orders on Bybit — size the position, enter the range, manage the exit.</div>
        </div>
      </div>

      <div className="vx-grid">
        <div className="vx-col">
          {main}
          <div className="vrs-form__actions">
            <Button variant="primary" size="lg" iconLeft={<Icon name="play" size={15} fill />} onClick={onRun}>Run backtest</Button>
          </div>
        </div>
        <aside className="vx-aside">
          <VxPreview plan={plan} hot={hot} entryMode={entryMode} beAfterTp1={beAfterTp1}
            followAuthor={followAuthor} exitSrc={exitSrc} sizeSum={`${riskPct}% · ${lev}`} />
          <div className="vrs-plan-card__cap" style={{ marginTop: 10, paddingInline: 4 }}>
            Plan preview · sample signal from this feed, {VX_SAMPLE.date} · {VX_SAMPLE.time}. Hover a section to see what it controls.
          </div>
        </aside>
      </div>
    </div>
  );
}
window.ExecutionView = ExecutionView;
