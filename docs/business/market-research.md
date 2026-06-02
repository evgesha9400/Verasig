# Market Research

## Verdict

- Generic algorithmic trading platform: crowded.
- Generic AI research and backtesting: crowded.
- Generic AI incident management: crowded.
- Signal automation: validated demand.
- Signal performance truth: weaker competitive coverage.
- Best first wedge: audited social signal ingestion plus provider performance scoring.

## Confirmed Or Disproved

- Confirmed: social signal automation demand exists.
- Confirmed: Deltalytic should validate wedges separately.
- Confirmed: Verasig has the strongest first fit with current Deltalytic docs.
- Disproved: full all-in-one agentic trading platform is the right MVP.
- Disproved: standalone InfraOps is the right first external business.
- Disproved: generic AI backtesting is a strong first wedge.

## Market Evidence

- Algorithmic trading is large and growing.
- Grand View Research estimates USD 21.06B in 2024 and USD 42.99B by 2030.
- Source: https://www.grandviewresearch.com/industry-analysis/algorithmic-trading-market-report

- QuantConnect already owns the serious quant platform narrative.
- QuantConnect offers research, backtesting, optimization, live trading, alternative data, and agentic AI.
- QuantConnect claims 503K quants, 500K+ backtests per month, and USD 45B monthly volume.
- Source: https://www.quantconnect.com/splash

- Capitalise.ai proves demand for no-code trading automation.
- Capitalise.ai supports plain-English scenarios, backtesting, simulation, notifications, and TradingView alert automation.
- Capitalise.ai is now part of Kraken.
- Source: https://capitalise.ai/

- TradingView webhooks are already a common signal transport.
- TradingView sends alert payloads to external apps over HTTP POST.
- TradingView warns against sending credentials in webhook bodies.
- TradingView webhook delivery may fail and should be monitored.
- Source: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/

- 3Commas validates signal-to-execution demand.
- 3Commas turns TradingView alerts into automated trades.
- 3Commas emphasizes risk controls, logs, delivery retry logic, and latency visibility.
- Source: https://3commas.io/trading-view

- Cornix validates Telegram and Discord signal automation.
- Cornix supports signal bots, TradingView bots, demo accounts, backtesting, tracking, and portfolio tracking.
- Cornix pricing exposes signal-bot and backtesting limits.
- Source: https://cornix.io/

- WunderTrading validates custom-signal and developer automation.
- WunderTrading turns TradingView alerts or custom signals into automated trades.
- WunderTrading exposes Open API and MCP for AI agents and custom workflows.
- Source: https://wundertrading.com/en

- AI SRE is not a clean first external business for Deltalytic.
- Incident.io offers AI SRE for investigation, root cause, fix drafting, and PR creation.
- PagerDuty is adding SRE Agent virtual responder and autonomous responder capabilities.
- Datadog offers Bits AI SRE for autonomous alert investigations.
- Incident.io source: https://incident.io/ai-sre
- PagerDuty source: https://www.pagerduty.com/newsroom/pagerduty-operations-cloud-spring-2026-release/
- Datadog source: https://www.datadoghq.com/product/ai/bits-ai-sre/

## Regulatory Evidence

- Do not sell guaranteed returns.
- CFTC warns that AI cannot predict future or sudden market changes.
- CFTC flags automated algorithms, trade signal strategies, and crypto trading schemes as scam vectors when they promise high returns.
- Source: https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/AITradingBots.html

- If serving regulated firms, algorithmic strategies need supervision and controls.
- FINRA says member firms using algorithmic strategies are subject to SEC and FINRA rules.
- FINRA explicitly references supervision obligations.
- Source: https://www.finra.org/rules-guidance/key-topics/algorithmic-trading

## Competitive Gap

- Most competitors automate signals.
- Most competitors expose bot performance.
- Few competitors make raw social-message provenance the core product.
- Few competitors score signal providers from immutable raw signals.
- Few competitors feed stored social signals into strategy research as a dataset.
- Few competitors combine signal parsing, audit, performance scoring, and research compatibility.

## Business Implication

- Do not compete head-on with QuantConnect.
- Do not compete head-on with PagerDuty, Datadog, Rootly, or Incident.io.
- Do not compete head-on with Cornix as a generic bot.
- Compete on proof, audit, and signal-provider performance truth.
- Treat execution as necessary plumbing.
- Treat agentic research as a later amplifier.
