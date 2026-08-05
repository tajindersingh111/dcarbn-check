"use client";

import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type { Inventory, ListResponse } from "@/lib/types";

type DispositionStatus = "included" | "not_relevant" | "excluded";

interface Disposition {
  id?: string;
  category: number;
  disposition: DispositionStatus;
  rationale: string;
  evidence_reference: string | null;
  prepared_by?: string;
  approved_by?: string | null;
}

interface DispositionResponse {
  items: Disposition[];
  total: number;
  complete: boolean;
  approved: boolean;
}

const categoryNames = [
  "Purchased goods and services",
  "Capital goods",
  "Fuel- and energy-related activities",
  "Upstream transportation and distribution",
  "Waste generated in operations",
  "Business travel",
  "Employee commuting",
  "Upstream leased assets",
  "Downstream transportation and distribution",
  "Processing of sold products",
  "Use of sold products",
  "End-of-life treatment of sold products",
  "Downstream leased assets",
  "Franchises",
  "Investments"
];

function emptyDecisions(): Disposition[] {
  return categoryNames.map((_, index) => ({
    category: index + 1,
    disposition: "included",
    rationale: "",
    evidence_reference: null
  }));
}

export default function Scope3ScreeningPage() {
  const inventories = useApiQuery<ListResponse<Inventory>>("/inventories?limit=200");
  const [inventoryId, setInventoryId] = useState("");
  const [decisions, setDecisions] = useState<Disposition[]>(emptyDecisions);
  const [status, setStatus] = useState<DispositionResponse | null>(null);
  const [loadingScreening, setLoadingScreening] = useState(false);
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedInventory = useMemo(
    () => inventories.data?.items.find((item) => item.id === inventoryId),
    [inventories.data, inventoryId]
  );

  useEffect(() => {
    if (!inventoryId) {
      setDecisions(emptyDecisions());
      setStatus(null);
      return;
    }
    let active = true;
    setLoadingScreening(true);
    setError(null);
    void apiRequest<DispositionResponse>(
      `/inventories/${inventoryId}/scope-3-category-dispositions`
    )
      .then((response) => {
        if (!active) return;
        setStatus(response);
        setDecisions(response.items.length === 15 ? response.items : emptyDecisions());
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "Screening could not be loaded.");
      })
      .finally(() => {
        if (active) setLoadingScreening(false);
      });
    return () => { active = false; };
  }, [inventoryId]);

  function updateDecision(category: number, patch: Partial<Disposition>) {
    setDecisions((items) => items.map((item) =>
      item.category === category ? { ...item, ...patch } : item
    ));
    setMessage(null);
  }

  function validationError(): string | null {
    const shortRationale = decisions.find((item) => item.rationale.trim().length < 20);
    if (shortRationale) return `Category ${shortRationale.category} needs a rationale of at least 20 characters.`;
    const missingEvidence = decisions.find(
      (item) => item.disposition === "excluded" && !item.evidence_reference?.trim()
    );
    if (missingEvidence) return `Category ${missingEvidence.category} needs an evidence reference when excluded.`;
    return null;
  }

  async function save() {
    if (!inventoryId) return;
    const invalid = validationError();
    if (invalid) {
      setError(invalid);
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const response = await apiRequest<DispositionResponse>(
        `/inventories/${inventoryId}/scope-3-category-dispositions`,
        {
          method: "PUT",
          body: JSON.stringify({
            items: decisions.map(({ category, disposition, rationale, evidence_reference }) => ({
              category,
              disposition,
              rationale: rationale.trim(),
              evidence_reference: evidence_reference?.trim() || null
            }))
          })
        }
      );
      setStatus(response);
      setDecisions(response.items);
      setMessage("All 15 category decisions were saved. Independent approval is still required.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Screening could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function approve() {
    if (!inventoryId) return;
    setApproving(true);
    setError(null);
    setMessage(null);
    try {
      const response = await apiRequest<DispositionResponse>(
        `/inventories/${inventoryId}/scope-3-category-dispositions/approve`,
        { method: "POST" }
      );
      setStatus(response);
      setDecisions(response.items);
      setMessage("Scope 3 screening approved. Calculation-method validation remains a separate release control.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Screening could not be approved.");
    } finally {
      setApproving(false);
    }
  }

  if (inventories.loading) return <LoadingState label="Loading Scope 3 screening" />;
  if (inventories.error) return <ErrorState message={inventories.error} onRetry={() => void inventories.refresh()} />;

  return (
    <>
      <PageHeader
        eyebrow="Scope 3 governance"
        title="Scope 3 category screening"
        description="Document the relevance, inclusion and exclusion decision for every GHG Protocol Scope 3 category."
      />

      <section className="validation-banner" aria-label="Validation status">
        <strong>Draft — calculation not fully validated</strong>
        <p>Completing this screening is mandatory, but it does not validate each category calculation method or constitute independent assurance.</p>
      </section>

      <section className="panel screening-selector">
        <label>
          Reporting inventory
          <select aria-label="Reporting inventory" value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}>
            <option value="">Select an inventory</option>
            {(inventories.data?.items ?? []).map((inventory) => (
              <option key={inventory.id} value={inventory.id}>{inventory.name} · {inventory.reporting_period_name}</option>
            ))}
          </select>
        </label>
        {selectedInventory ? (
          <div className="screening-status">
            <span>{status?.total ?? 0}/15 decisions</span>
            <StatusBadge status={status?.approved ? "approved" : status?.complete ? "review_required" : "draft"} />
          </div>
        ) : null}
      </section>

      {loadingScreening ? <LoadingState label="Loading category decisions" /> : null}
      {inventoryId && !loadingScreening ? (
        <>
          <MutationMessage error={error} success={message} />
          <div className="scope3-grid">
            {decisions.map((item) => (
              <article className="panel scope3-card" key={item.category}>
                <header>
                  <span>Category {item.category}</span>
                  <h2>{categoryNames[item.category - 1]}</h2>
                </header>
                <label>
                  Decision
                  <select
                    aria-label={`Category ${item.category} decision`}
                    disabled={Boolean(status?.approved)}
                    value={item.disposition}
                    onChange={(event) => updateDecision(item.category, {
                      disposition: event.target.value as DispositionStatus,
                      evidence_reference: event.target.value === "excluded" ? item.evidence_reference : null
                    })}
                  >
                    <option value="included">Included</option>
                    <option value="not_relevant">Not relevant</option>
                    <option value="excluded">Excluded</option>
                  </select>
                </label>
                <label>
                  Rationale
                  <textarea
                    aria-label={`Category ${item.category} rationale`}
                    disabled={Boolean(status?.approved)}
                    minLength={20}
                    rows={3}
                    value={item.rationale}
                    onChange={(event) => updateDecision(item.category, { rationale: event.target.value })}
                  />
                </label>
                {item.disposition === "excluded" ? (
                  <label>
                    Evidence reference
                    <input
                      aria-label={`Category ${item.category} evidence reference`}
                      disabled={Boolean(status?.approved)}
                      required
                      value={item.evidence_reference ?? ""}
                      onChange={(event) => updateDecision(item.category, { evidence_reference: event.target.value })}
                    />
                  </label>
                ) : null}
                {item.prepared_by ? <small>Prepared by {item.prepared_by}{item.approved_by ? ` · Approved by ${item.approved_by}` : ""}</small> : null}
              </article>
            ))}
          </div>
          <section className="panel screening-actions">
            <div>
              <strong>Release control</strong>
              <p>Saving invalidates any earlier approval. The preparer cannot approve their own decisions.</p>
            </div>
            <div className="button-row">
              <button className="button button-secondary" disabled={saving || Boolean(status?.approved)} onClick={() => void save()} type="button">
                {saving ? "Saving…" : "Save all 15 decisions"}
              </button>
              <button className="button button-primary" disabled={approving || !status?.complete || Boolean(status?.approved)} onClick={() => void approve()} type="button">
                {approving ? "Approving…" : status?.approved ? "Approved" : "Approve screening"}
              </button>
            </div>
          </section>
        </>
      ) : null}
    </>
  );
}
