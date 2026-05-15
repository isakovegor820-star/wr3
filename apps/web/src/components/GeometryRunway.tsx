const runwaySteps = ["Статика", "Триаж", "PoC", "Оценка"];

export function GeometryRunway() {
  return (
    <div className="geometry-runway" aria-hidden="true">
      <div className="runway-track">
        {runwaySteps.map((step, index) => (
          <span key={step} className={`runway-step runway-step-${index + 1}`}>
            {step}
          </span>
        ))}
      </div>
      <div className="runway-blocks">
        <i />
        <i />
        <i />
        <i />
        <i />
      </div>
      <div className="runway-readout">
        <span>пассивно</span>
        <strong>движок риска</strong>
      </div>
    </div>
  );
}
