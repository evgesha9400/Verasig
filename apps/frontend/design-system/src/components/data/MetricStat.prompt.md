Headline metric — big mono value, label, unit, trend delta, caption.

```jsx
<MetricStat label="Uptime" value="99.98" unit="%" delta="+0.01" trend="up" caption="Last 30 days" />
<MetricStat label="Median latency" value="182" unit="ms" delta="−12ms" trend="up" />
<MetricStat label="Rejected" value="3" delta="+1" trend="down" caption="Today" />
```

`trend` (`up | down | flat`) sets the delta color and arrow. Note: "up" is good (green) regardless of metric.
