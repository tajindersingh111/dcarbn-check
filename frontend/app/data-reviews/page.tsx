"use client";

import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type {
  DataCalculationComparisonDetail,
  DataReviewQueueItem,
  Inventory,
  ListResponse
} from "@/lib/types";

function classification(scope: string | null, category: number | null): string {
  if (!scope) return "Not confirmed";
  const label = scope.replace("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  return category ? `${label} · Category ${category}` : label;
}

export default function DataReviewsPage() {
  const reviews = useApiQuery<ListResponse<DataReviewQueueItem>>("/integrations/data/reviews?limit=200");
  const inventories = useApiQuery<ListResponse<Inventory>>(
    "/inventories?limit=200&scope_2_headline_basis=location_based"
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [inventoryId, setInventoryId] = useState("");
  const [comment, setComment] = useState("");
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] =
    useState<DataCalculationComparisonDetail | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);

  const selected = useMemo(
    () => reviews.data?.items.find((item) => item.review.id === selectedId) ?? reviews.data?.items[0] ?? null,
    [reviews.data, selectedId]
  );

  useEffect(() => {
    if (selected && selected.review.id !== selectedId) setSelectedId(selected.review.id);
    if (selected?.review.inventory_id) setInventoryId(selected.review.inventory_id);
  }, [selected, selectedId]);

  useEffect(() => {
    if (!selected || selected.review.status !== "converted") {
      setComparison(null);
      return;
    }
    let active = true;
    setComparisonLoading(true);
    void apiRequest<DataCalculationComparisonDetail>(
      `/integrations/data/comparisons/operational-emissions/${selected.review.operational_emission_id}`
    )
      .then((response) => {
        if (active) setComparison(response);
      })
      .catch((caught) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Calculation comparison could not be loaded."
          );
        }
      })
      .finally(() => {
        if (active) setComparisonLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selected]);

  async function perform(action: "sync" | "start" | "approve" | "reject" | "convert") {
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      if (action === "sync") {
        await apiRequest("/integrations/data/reviews/sync", { method: "POST" });
      } else if (selected) {
        if (action === "start") {
          await apiRequest(`/integrations/data/reviews/${selected.review.id}/start`, {
            method: "POST",
            body: JSON.stringify({ inventory_id: inventoryId, reviewer_comment: comment || null })
          });
        } else if (action === "approve" || action === "reject") {
          await apiRequest(`/integrations/data/reviews/${selected.review.id}/decision`, {
            method: "POST",
            body: JSON.stringify({
              decision: action === "approve" ? "approved" : "rejected",
              reviewer_comment: comment || null,
              rejection_reason: action === "reject" ? comment || "Rejected during review." : null
            })
          });
        } else {
          const conversion = await apiRequest<{ comparison_id: string }>(
            `/integrations/data/reviews/${selected.review.id}/convert`,
            { method: "POST" }
          );
          await apiRequest(
            `/integrations/data/comparisons/${conversion.comparison_id}/government`,
            { method: "POST" }
          );
        }
      }
      setMessage("Workflow updated.");
      await reviews.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Review action failed.");
    } finally {
      setWorking(false);
    }
  }

  if (reviews.loading || inventories.loading) return <LoadingState label="Loading DATa review queue" />;
  if (reviews.error || inventories.error) return <ErrorState message={reviews.error ?? inventories.error ?? "Unknown error"} onRetry={() => { void reviews.refresh(); void inventories.refresh(); }} />;

  return (
    <>
      <PageHeader eyebrow="DATa integration" title="Operational-emissions review" description="Confirm classification and convert verified DATa results without applying another factor." actions={<button className="button button-secondary" onClick={() => void perform("sync")} type="button">Sync queue</button>} />
      <section className="split-layout">
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">Review queue</p><h2>Imported results</h2></div></div>
          <DataTable caption="DATa review queue" headers={["Calculation", "Customer", "kgCO₂e", "Status"]}>
            {(reviews.data?.items ?? []).map((item) => (
              <tr className={item.review.id === selected?.review.id ? "selected-row" : ""} key={item.review.id} onClick={() => setSelectedId(item.review.id)}>
                <td><strong>{item.external_calculation_id}</strong></td>
                <td>{item.external_customer_id ?? "Mapped organisation"}</td>
                <td>{Number(item.total_kg_co2e).toLocaleString("en-GB")}</td>
                <td><StatusBadge status={item.review.status} /></td>
              </tr>
            ))}
          </DataTable>
        </article>
        <aside className="panel detail-panel">
          {selected ? (
            <>
              <div className="panel-heading"><div><p className="eyebrow">Review detail</p><h2>{selected.external_calculation_id}</h2></div><StatusBadge status={selected.review.status} /></div>
              <dl className="detail-list">
                <div><dt>Verified result</dt><dd>{selected.total_kg_co2e} kgCO₂e</dd></div>
                <div><dt>Suggested</dt><dd>{classification(selected.suggested_scope, selected.suggested_scope_3_category)}</dd></div>
                <div><dt>Confirmed</dt><dd>{classification(selected.confirmed_scope, selected.confirmed_scope_3_category)}</dd></div>
                <div><dt>Methodology</dt><dd>{selected.methodology_version}</dd></div>
                <div><dt>Quality score</dt><dd>{selected.data_quality_score ?? "—"}/100</dd></div>
              </dl>
              {comparisonLoading ? (
                <LoadingState label="Loading calculation comparison" />
              ) : null}
              {comparison ? (
                <section
                  aria-label="DcarbN and UK Government comparison"
                  className="comparison-panel"
                >
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow">Calculation comparison</p>
                      <h3>DcarbN and UK Government</h3>
                    </div>
                    <StatusBadge status={comparison.status} />
                  </div>
                  <div className="comparison-results">
                    <article>
                      <span>DcarbN operational methodology</span>
                      <strong>
                        {comparison.dcarbn_result
                          ? `${Number(
                              comparison.dcarbn_result.allocated_kg_co2e
                            ).toLocaleString("en-GB")} kgCO₂e`
                          : "Not available"}
                      </strong>
                      <small>
                        {comparison.dcarbn_result?.methodology_version ?? "—"}
                      </small>
                    </article>
                    <article>
                      <span>UK Government factor comparator</span>
                      <strong>
                        {comparison.government_result
                          ? `${Number(
                              comparison.government_result.allocated_kg_co2e
                            ).toLocaleString("en-GB")} kgCO₂e`
                          : "Not available"}
                      </strong>
                      <small>
                        {comparison.government_result?.methodology_version ?? "—"}
                      </small>
                    </article>
                  </div>
                  {comparison.status === "ready" ? (
                    <dl className="detail-list">
                      <div>
                        <dt>Absolute difference</dt>
                        <dd>{comparison.absolute_delta_kg_co2e} kgCO₂e</dd>
                      </div>
                      <div>
                        <dt>Percentage difference</dt>
                        <dd>
                          {comparison.percentage_delta === null
                            ? "Not applicable — zero Government baseline"
                            : `${comparison.percentage_delta}%`}
                        </dd>
                      </div>
                      <div>
                        <dt>Headline basis</dt>
                        <dd>
                          {comparison.reporting_basis === "dcarbn_operational"
                            ? "DcarbN operational"
                            : "UK Government"}
                        </dd>
                      </div>
                      <div>
                        <dt>Data quality</dt>
                        <dd>{comparison.data_quality_score ?? "—"}/100</dd>
                      </div>
                    </dl>
                  ) : null}
                  {comparison.comparison_unavailable_reason ? (
                    <p className="comparison-warning">
                      {comparison.comparison_unavailable_reason}
                    </p>
                  ) : null}
                  <p className="comparison-disclaimer">
                    The UK Government result is a disclosure-only comparator and
                    is excluded from inventory totals. This comparison does not
                    imply UK Government endorsement of the DcarbN methodology.
                  </p>
                </section>
              ) : null}
              <label>Target inventory<select value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}><option value="">Select inventory</option>{(inventories.data?.items ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
              <label className="full-width-field">Reviewer comment<textarea rows={3} value={comment} onChange={(event) => setComment(event.target.value)} /></label>
              <MutationMessage error={error} success={message} />
              <div className="button-row workflow-buttons">
                {selected.review.status === "pending" ? <button className="button button-primary" disabled={working || !inventoryId} onClick={() => void perform("start")} type="button">Start review</button> : null}
                {selected.review.status === "in_review" ? <>
                  <button className="button button-danger" disabled={working} onClick={() => void perform("reject")} type="button">Reject</button>
                  <button className="button button-primary" disabled={working} onClick={() => void perform("approve")} type="button">Approve</button>
                </> : null}
                {selected.review.status === "approved" ? <button className="button button-primary" disabled={working} onClick={() => void perform("convert")} type="button">Convert to inventory</button> : null}
              </div>
            </>
          ) : <p>No DATa reviews are currently queued.</p>}
        </aside>
      </section>
    </>
  );
}
