import { Badge, Card, Icon } from '@verasig/design-system'

/* Verasig — Template Mining: compiled parser rules.
   Accepting a family compiles it into a deterministic, inspectable rule. The
   rules are shown verbatim — the point of the approach is that they are explicit
   and auditable, never hidden behind a model. */
export function CompiledRulesPanel({ rules }) {
  if (rules.length === 0) {
    return (
      <Card
        title="Compiled parser rules"
        subtitle="Deterministic rules from accepted families"
      >
        <div className="vrs-empty vrs-empty--sm">
          <div className="vrs-empty__note">
            Accept a template family above to compile its parser rule here.
          </div>
        </div>
      </Card>
    )
  }

  return (
    <Card
      title="Compiled parser rules"
      subtitle="Deterministic rules from accepted families"
      headerActions={
        <Badge tone="verified" dot>
          {rules.length} rule{rules.length === 1 ? '' : 's'}
        </Badge>
      }
    >
      <div className="vrs-stack-xs">
        {rules.map((rule) => (
          <div key={rule.id}>
            <div className="vrs-tm-rule__name">
              <Icon name="check" size={14} />
              <strong>{rule.name}</strong>
            </div>
            <pre className="vrs-tm-rulejson">{JSON.stringify(rule, null, 2)}</pre>
          </div>
        ))}
      </div>
    </Card>
  )
}
