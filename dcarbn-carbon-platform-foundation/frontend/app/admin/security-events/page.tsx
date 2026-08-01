"use client";

import { ErrorState, LoadingState } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useApiQuery } from "@/lib/use-api";

interface SecurityEvent {
  id: string;
  event_type: string;
  severity: string;
  success: boolean;
  ip_address: string | null;
  description: string;
  occurred_at: string;
}

export default function SecurityEventsPage() {
  const query = useApiQuery<{ items: SecurityEvent[]; total: number }>(
    "/security/events?limit=200"
  );

  if (query.loading) return <LoadingState label="Loading security events" />;
  if (query.error) return <ErrorState message={query.error} onRetry={query.refresh} />;

  return (
    <>
      <PageHeader
        eyebrow="Security monitoring"
        title="Security events"
        description="Review authentication, MFA, recovery, session, and access-administration events."
      />
      <section className="panel">
        <DataTable
          caption="Security events"
          headers={["Occurred", "Event", "Description", "IP address", "Severity", "Outcome"]}
        >
          {(query.data?.items ?? []).map((event) => (
            <tr key={event.id}>
              <td>{new Date(event.occurred_at).toLocaleString("en-GB")}</td>
              <td><code>{event.event_type}</code></td>
              <td>{event.description}</td>
              <td>{event.ip_address ?? "—"}</td>
              <td><StatusBadge status={event.severity} /></td>
              <td><StatusBadge status={event.success ? "completed" : "failed"} /></td>
            </tr>
          ))}
        </DataTable>
      </section>
    </>
  );
}
