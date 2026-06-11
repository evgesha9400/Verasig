import { useState, useEffect, useRef } from 'react'
import { Button } from '../../../design-system/index.js'
import { Icon } from '../../../design-system/index.js'

/* Verasig prototype — backfill infinite loader */
export function BackfillView({ chat, onCancel, onComplete }) {
  const [count, setCount] = useState(chat.fetched || 0);
  const [date, setDate] = useState(chat.lastDate || 'Jun 7, 2026');
  const [logLine, setLogLine] = useState('Opening MTProto session…');
  const countRef = useRef(chat.fetched || 0);

  // simulated, accelerating backfill that completes after a believable run
  useEffect(() => {
    const TARGET = (chat.fetched || 0) + 9800 + Math.floor(Math.random() * 3000);
    const dates = ['Jun 7, 2026','Jun 4, 2026','May 30, 2026','May 22, 2026','May 11, 2026','Apr 28, 2026','Apr 9, 2026','Mar 21, 2026','Feb 28, 2026','Feb 2, 2026','Jan 9, 2026','Dec 12, 2025','Nov 18, 2025'];
    const logs = ['Reading channel history…','Decrypting message batch…','Resolving media references…','Backfilling older window…','Indexing message bodies…'];
    let di = 0;
    const tick = setInterval(() => {
      countRef.current += 40 + Math.floor(Math.random() * 220);
      if (countRef.current >= TARGET) {
        countRef.current = TARGET;
        setCount(TARGET);
        clearInterval(tick);
        clearInterval(logTick);
        setLogLine('Backfill complete · finalizing index');
        setTimeout(() => onComplete(TARGET), 900);
        return;
      }
      setCount(countRef.current);
      di = Math.min(dates.length - 1, Math.floor((countRef.current / TARGET) * dates.length));
      setDate(dates[di]);
    }, 90);
    const logTick = setInterval(() => setLogLine(logs[Math.floor(Math.random() * logs.length)]), 1500);
    return () => { clearInterval(tick); clearInterval(logTick); };
  }, []);

  return (
    <div className="vrs-backfill vrs-fade-in">
      <svg className="vrs-bf-scope" viewBox="0 0 360 96" fill="none" preserveAspectRatio="none">
        <path d="M0 48 H90 L108 18 L128 78 L150 30 L168 60 L186 48 H360"
          stroke="var(--signal-500)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"
          style={{ filter: 'drop-shadow(0 0 6px var(--signal-glow))' }}
          strokeDasharray="600" strokeDashoffset="600">
          <animate attributeName="stroke-dashoffset" from="600" to="0" dur="1.6s" repeatCount="indefinite" />
        </path>
      </svg>

      <div>
        <div className="vrs-bf-title">Backfilling {chat.name}</div>
        <div className="vrs-bf-sub" style={{ marginTop: 6 }}>Pulling the full message history from {chat.tag}. This can take a while — you can leave and come back.</div>
      </div>

      <div className="vrs-bf-stats">
        <div>
          <div className="vrs-bf-stat__v">{count.toLocaleString()}</div>
          <div className="vrs-bf-stat__l">Messages fetched</div>
        </div>
        <div>
          <div className="vrs-bf-stat__v" style={{ fontSize: 'var(--text-2xl)', paddingTop: 14 }}>{date}</div>
          <div className="vrs-bf-stat__l">Oldest message reached</div>
        </div>
      </div>

      <div className="vrs-bf-track" />
      <div className="vrs-bf-log">{logLine}</div>

      <Button variant="ghost" iconLeft={<Icon name="x" size={15} />} onClick={() => onCancel(countRef.current, date)}>Cancel backfill</Button>
    </div>
  );
}
