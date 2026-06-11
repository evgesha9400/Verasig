/* Verasig Marketing — content data */
const VRS_SITE = {
  products: [
    { id: 'verify', name: 'Verify', tint: 'var(--viz-1)', tagline: 'Cross-check any signal in milliseconds.',
      body: 'Every inbound signal is checked against independent sources, scored for confidence, and verified before it reaches production.',
      stat: '< 200ms', statLabel: 'Median verification' },
    { id: 'quorum', name: 'Quorum', tint: 'var(--viz-2)', tagline: 'Consensus on your terms.',
      body: 'Configure thresholds, source weighting and tolerance. Hold or reject anything that fails to reach quorum — automatically.',
      stat: '99.6%', statLabel: 'Quorum rate' },
    { id: 'channels', name: 'Channels', tint: 'var(--viz-5)', tagline: 'Ingest from anywhere.',
      body: 'Webhook, REST, gRPC or WebSocket. One integration ingests every provider and every channel through a single endpoint.',
      stat: '4', statLabel: 'Transport channels' },
    { id: 'provenance', name: 'Provenance', tint: 'var(--viz-3)', tagline: 'A signed, auditable trail.',
      body: 'Every verification is signed and logged with its sources, timing and decision — a tamper-evident record you can replay.',
      stat: '100%', statLabel: 'Signals signed' },
  ],
  stats: [
    { value: '4.1B+', label: 'Signals verified' },
    { value: '99.98%', label: 'Uptime' },
    { value: '182ms', label: 'Median latency' },
    { value: '120+', label: 'Connected providers' },
  ],
  providers: ['Coinbase', 'Pyth', 'Polymarket', 'Kalshi', 'Caplight', 'Stork', 'Binance', 'Kraken', 'dxFeed', 'CoinGecko', 'Finage', 'Blocksize'],
  why: [
    { icon: 'pulse', title: 'Signals that never sleep', body: 'Always-on verification across markets, telemetry and events — 365 days a year, sub-second.' },
    { icon: 'sources', title: 'Sources others can\u2019t reach', body: 'If a provider exists — public or private, push or pull — Verasig can ingest and verify it.' },
    { icon: 'tune', title: 'Verification you control', body: 'Bespoke quorum logic: source selection, weighting, smoothing and tolerance. No one-size-fits-all.' },
    { icon: 'shield', title: 'Tamper-evident by default', body: 'Signed provenance for every signal. Replay any decision with its full source breakdown.' },
  ],
};
window.VRS_SITE = VRS_SITE;
