"use client";

import Link from "next/link";
import { useState } from "react";

import { ErrorState, LoadingState } from "@/components/api-state";
import {
  ActivityIcon,
  ApprovalIcon,
  InventoryIcon,
  ReportIcon,
  ReviewIcon
} from "@/components/icons";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useApiQuery } from "@/lib/use-api";
import type { DashboardSummary, Inventory, ListResponse } from "@/lib/types";

const workflowItems = [
  ["Enter activity data", "Record governed Scope 1, 2 and 3 activity.", "/activities/new", ActivityIcon],
  ["Review DATa results", "Confirm classification and inventory assignment.", "/data-reviews", ReviewIcon],
  ["Approve inventory", "Review evidence, boundaries, factors and results.", "/approvals", ApprovalIcon],
  ["Generate audit report", "Create an immutable, hash-stamped snapshot.", "/audit-reports", ReportIcon]
] as const;

function tonnes(value: string | null): string {
  if (value === null) return "—";
  return (Number(value) / 1000).toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

export default function DashboardPage() {
  const [scope2HeadlineBasis, setScope2HeadlineBasis] = useState<"location_based" | "market_based">("location_based");
  const summary = useApiQuery<DashboardSummary>(
    `/dashboard?scope_2_headline_basis=${scope2HeadlineBasis}`
  );
  const inventories = useApiQuery<ListResponse<Inventory>>(
    `/inventories?limit=5&scope_2_headline_basis=${scope2HeadlineBasis}`
  );

  if (summary.loading || inventories.loading) {
    return <LoadingState label="Loading dashboard" />;
  }
  if (summary.error || inventories.error) {
    return (
      <ErrorState
        message={summary.error ?? inventories.error ?? "Unknown error"}
        onRetry={() => {
          void summary.refresh();
          void inventories.refresh();
        }}
      />
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Corporate carbon accounting"
        title="Dashboard"
        description="Monitor reporting inventories, review DATa operational results and complete governed approvals."
        actions={
          <>
            <label>Headline Scope 2 basis<select aria-label="Headline Scope 2 basis" onChange={(event) => setScope2HeadlineBasis(event.target.value as "location_based" | "market_based")} value={scope2HeadlineBasis}><option value="location_based">Location-based</option><option value="market_based">Market-based</option></select></label>
            <Link className="button button-primary" href="/activities/new">
              Add activity
            </Link>
          </>
        }
      />

      <section className="metric-grid" aria-label="Carbon inventory summary">
        <MetricCard
          helper={`Across current inventory calculations · ${scope2HeadlineBasis === "location_based" ? "location-based" : "market-based"} Scope 2 headline`}
          icon={<InventoryIcon />}
          label="Reported emissions"
          value={`${Number(summary.data?.total_t_co2e ?? 0).toLocaleString("en-GB", { maximumFractionDigits: 2 })} tCO₂e`}
        />
        <MetricCard
          helper="Awaiting review or classification"
          icon={<ReviewIcon />}
          label="DATa reviews"
          value={String(summary.data?.open_data_review_count ?? 0)}
        />
        <MetricCard
          helper="Independent decisions required"
          icon={<ApprovalIcon />}
          label="Approval tasks"
          value={String(summary.data?.open_approval_count ?? 0)}
        />
        <MetricCard
          helper="Current locked reporting inventories"
          icon={<ReportIcon />}
          label="Locked inventories"
          value={String(summary.data?.locked_inventory_count ?? 0)}
        />
      </section>

      <section className="dashboard-grid">
        <article className="panel panel-span-2">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Current reporting</p>
              <h2>Inventory portfolio</h2>
            </div>
            <Link className="text-link" href="/inventories">View all</Link>
          </div>
          <div className="inventory-list">
            {(inventories.data?.items ?? []).map((inventory) => (
              <Link className="inventory-list-item" href="/inventories" key={inventory.id}>
                <div>
                  <strong>{inventory.name}</strong>
                  <span>{inventory.reporting_period_name}</span>
                </div>
                <div className="inventory-list-metric">
                  <strong>{tonnes(inventory.total_kg_co2e)}</strong>
                  <span>tCO₂e</span>
                </div>
                <StatusBadge status={inventory.status} />
              </Link>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Workflow</p>
              <h2>Next actions</h2>
            </div>
          </div>
          <div className="workflow-list">
            {workflowItems.map(([title, description, href, Icon]) => (
              <Link className="workflow-item" href={href} key={title}>
                <span className="workflow-icon"><Icon /></span>
                <span><strong>{title}</strong><small>{description}</small></span>
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </article>
      </section>
    </>
  );
}
