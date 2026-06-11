/* Verasig App — fake data + shared helpers (assigned to window). */
const VRS_DATA = (function () {
  const providers = [
    { id: 'coinbase', name: 'Coinbase', tint: 'var(--viz-2)', channel: 'WebSocket', health: 'verified', uptime: 99.99 },
    { id: 'polymarket', name: 'Polymarket', tint: 'var(--viz-3)', channel: 'REST · us-east', health: 'verified', uptime: 99.94 },
    { id: 'caplight', name: 'Caplight', tint: 'var(--viz-4)', channel: 'gRPC', health: 'pending', uptime: 99.71 },
    { id: 'stork', name: 'Stork', tint: 'var(--viz-5)', channel: 'WebSocket', health: 'verified', uptime: 99.98 },
    { id: 'kalshi', name: 'Kalshi', tint: 'var(--viz-6)', channel: 'REST', health: 'rejected', uptime: 98.40 },
    { id: 'pyth', name: 'Pyth', tint: 'var(--viz-1)', channel: 'gRPC · global', health: 'verified', uptime: 99.97 },
  ];

  const signals = [
    { id: 'SIG-7F2A·0x9d4e', symbol: 'BTC/USD', provider: 'Coinbase', tint: 'var(--viz-2)', channel: 'WebSocket', confidence: 99.4, status: 'verified', time: '11:32:04', sources: 12, agree: 12 },
    { id: 'SIG-7F22·0x4c10', symbol: 'ETH/USD', provider: 'Pyth', tint: 'var(--viz-1)', channel: 'gRPC · global', confidence: 98.7, status: 'verified', time: '11:32:01', sources: 11, agree: 11 },
    { id: 'SIG-7F19·0x2b81', symbol: 'ELECTION-2028', provider: 'Polymarket', tint: 'var(--viz-3)', channel: 'REST · us-east', confidence: 62.0, status: 'pending', time: '11:31:58', sources: 14, agree: 9 },
    { id: 'SIG-7F11·0x88fa', symbol: 'USA500.idx', provider: 'Stork', tint: 'var(--viz-5)', channel: 'WebSocket', confidence: 96.2, status: 'verified', time: '11:31:50', sources: 9, agree: 9 },
    { id: 'SIG-7F03·0x77ac', symbol: 'AAPL.pre', provider: 'Caplight', tint: 'var(--viz-4)', channel: 'gRPC', confidence: 41.0, status: 'rejected', time: '11:30:51', sources: 8, agree: 3 },
    { id: 'SIG-7EF8·0x10dd', symbol: 'NVDA.pre', provider: 'Caplight', tint: 'var(--viz-4)', channel: 'gRPC', confidence: 84.5, status: 'verified', time: '11:30:39', sources: 8, agree: 7 },
    { id: 'SIG-7EE0·0x5a92', symbol: 'SB-FINALS-W', provider: 'Kalshi', tint: 'var(--viz-6)', channel: 'REST', confidence: 73.1, status: 'observing', time: '11:30:12', sources: 10, agree: 7 },
    { id: 'SIG-7ED4·0x3f6b', symbol: 'XAU/USD', provider: 'Pyth', tint: 'var(--viz-1)', channel: 'gRPC · global', confidence: 99.1, status: 'verified', time: '11:29:55', sources: 11, agree: 11 },
  ];

  const sources = [
    { name: 'Coinbase', value: '67,412.08', dev: '0.00%', ok: true },
    { name: 'Binance', value: '67,409.51', dev: '−0.004%', ok: true },
    { name: 'Kraken', value: '67,418.20', dev: '+0.009%', ok: true },
    { name: 'Pyth', value: '67,411.94', dev: '0.00%', ok: true },
    { name: 'Stork', value: '67,402.10', dev: '−0.015%', ok: true },
    { name: 'CoinGecko', value: '67,512.40', dev: '+0.148%', ok: false },
  ];

  return { providers, signals, sources };
})();
window.VRS_DATA = VRS_DATA;
