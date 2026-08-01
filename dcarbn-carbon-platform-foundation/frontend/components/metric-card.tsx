import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  helper,
  icon
}: {
  label: string;
  value: string;
  helper: string;
  icon?: ReactNode;
}) {
  return (
    <article className="metric-card">
      <div className="metric-card-header">
        <span>{label}</span>
        {icon ? <span className="metric-icon">{icon}</span> : null}
      </div>
      <strong>{value}</strong>
      <p>{helper}</p>
    </article>
  );
}
