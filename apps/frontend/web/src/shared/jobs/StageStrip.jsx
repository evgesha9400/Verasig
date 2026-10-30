/* Verasig — the staged progress strip shared by the job loaders (mine, backfill).
   Each stage lights up when active and marks done once the job moves past it. */

export function StageStrip({ stages, stage }) {
  const activeIndex = stages.findIndex((item) => item.id === stage)
  return (
    <div className="vrs-bf-stages">
      {stages.map((item, index) => (
        <span
          key={item.id}
          className={`vrs-bf-stage ${index === activeIndex ? 'is-active' : ''} ${
            index < activeIndex ? 'is-done' : ''
          }`.trim()}
        >
          {item.label}
        </span>
      ))}
    </div>
  )
}
