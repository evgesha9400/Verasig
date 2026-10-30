/* Verasig — Template Mining: one label/value row of a signal-fields table.
   Shared by every "instrument/direction/entry/…" table in this feature —
   the audit's parsed-row detail, the family card's representative extraction,
   and a candidate's full worked example. */
function rowClassName({ muted, warning }) {
  return [muted ? 'is-muted' : null, warning ? 'is-warning' : null]
    .filter(Boolean)
    .join(' ')
}

export function SignalFieldRow({ label, value, muted, field, warning }) {
  const className = rowClassName({ muted, warning })
  return (
    <tr className={className || undefined} data-field={field}>
      <td>{label}</td>
      <td className={muted ? 'none' : undefined}>{value}</td>
    </tr>
  )
}
