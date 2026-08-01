import type { StatusTone } from "@/lib/types";

const toneByStatus: Record<string, StatusTone> = {
  active: "success",
  approved: "success",
  completed: "success",
  converted: "success",
  final: "success",
  locked: "info",
  in_review: "info",
  review_required: "warning",
  pending: "warning",
  draft: "neutral",
  rejected: "danger",
  failed: "danger",
  superseded: "neutral"
};

function titleCase(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function StatusBadge({ status }: { status: string }) {
  const tone = toneByStatus[status] ?? "neutral";

  return (
    <span className={`badge badge-${tone}`}>
      <span className="badge-dot" />
      {titleCase(status)}
    </span>
  );
}
