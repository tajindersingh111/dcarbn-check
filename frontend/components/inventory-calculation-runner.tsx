"use client";

import Link from "next/link";
import { useState } from "react";

import { MutationMessage } from "@/components/api-state";
import { apiRequest } from "@/lib/api";
import type {
  CalculationRun,
  InventoryCalculationSummary,
  Scope2HeadlineBasis
} from "@/lib/types";

function tonnes(value: string): string {
  return (Number(value) / 1000).toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 3
  });
}

export function InventoryCalculationRunner({
  inventoryId,
  inventoryName,
  onCompleted
}: {
  inventoryId: string;
  inventoryName: string;
  onCompleted?: () => void | Promise<void>;
}) {
  const [headlineBasis, setHeadlineBasis] =
    useState<Scope2HeadlineBasis>("location_based");
  const [runId, setRunId] = useState<string | null>(null);
  const [summary, setSummary] = useState<InventoryCalculationSummary | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadSummary(id: string, basis: Scope2HeadlineBasis) {
    const result = await apiRequest<InventoryCalculationSummary>(
      `/calculation-runs/${id}/summary?scope_2_headline_basis=${basis}`
    );
    setSummary(result);
  }

  async function calculate() {
    setWorking(true);
    setError(null);
    setMessage(null);
    setSummary(null);
    try {
      const run = await apiRequest<CalculationRun>(
        `/inventories/${inventoryId}/calculation-runs`,
        { method: "POST", body: JSON.stringify({}) }
      );
      if (run.status !== "completed") {
        throw new Error(
          run.failure_message ??
            `${run.failed_count} of ${run.activity_count} activities could not be calculated.`
        );
      }
      setRunId(run.id);
      await loadSummary(run.id, headlineBasis);
      setMessage(
        `Calculation version ${run.version} completed: ${run.result_count} results from ${run.activity_count} activities.`
      );
      await onCompleted?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The calculation could not be completed.");
    } finally {
      setWorking(false);
    }
  }

  async function changeHeadlineBasis(basis: Scope2HeadlineBasis) {
    setHeadlineBasis(basis);
    if (!runId) return;
    setWorking(true);
    setError(null);
    try {
      await loadSummary(runId, basis);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The calculation summary could not be updated.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="calculation-runner">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Next step</p>
          <h2>Calculate Scope 1, 2 and 3</h2>
          <p>Run the governed methods for {inventoryName} and review the totals before approval.</p>
        </div>
      </div>

      <label>
        Headline Scope 2 basis
        <select
          aria-label="Calculation headline Scope 2 basis"
          disabled={working}
          onChange={(event) =>
            void changeHeadlineBasis(event.target.value as Scope2HeadlineBasis)
          }
          value={headlineBasis}
        >
          <option value="location_based">Location-based</option>
          <option value="market_based">Market-based</option>
        </select>
      </label>
      <p className="field-help">
        Both Scope 2 totals remain visible. This selection controls only the headline total and
        prevents double counting.
      </p>

      <MutationMessage error={error} success={message} />

      <button
        className="button button-primary"
        disabled={working}
        onClick={() => void calculate()}
        type="button"
      >
        {working ? "Calculating…" : runId ? "Recalculate inventory" : "Calculate inventory"}
      </button>

      {summary ? (
        <>
          <div className="metric-grid calculation-summary" aria-label="Calculation summary">
            <article className="metric-card">
              <span className="metric-card-header">Scope 1</span>
              <strong>{tonnes(summary.scope_1_kg_co2e)}</strong>
              <p>tCO₂e</p>
            </article>
            <article className="metric-card">
              <span className="metric-card-header">Scope 2 location</span>
              <strong>{tonnes(summary.scope_2_location_based_kg_co2e)}</strong>
              <p>tCO₂e · disclosed separately</p>
            </article>
            <article className="metric-card">
              <span className="metric-card-header">Scope 2 market</span>
              <strong>{tonnes(summary.scope_2_market_based_kg_co2e)}</strong>
              <p>tCO₂e · disclosed separately</p>
            </article>
            <article className="metric-card">
              <span className="metric-card-header">Scope 3</span>
              <strong>{tonnes(summary.scope_3_kg_co2e)}</strong>
              <p>tCO₂e</p>
            </article>
          </div>
          <section className="validation-banner calculation-total">
            <strong>
              Headline total ({headlineBasis === "location_based" ? "location-based" : "market-based"}):{" "}
              {Number(summary.total_t_co2e).toLocaleString("en-GB", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 3
              })} tCO₂e
            </strong>
            <p>Calculation complete. Scope 3 screening and independent approval are required before report generation.</p>
          </section>
          <div className="button-row">
            <Link className="button button-secondary" href="/scope-3-screening">
              Complete Scope 3 screening
            </Link>
            <Link className="button button-primary" href="/approvals">
              Continue to approval
            </Link>
          </div>
        </>
      ) : null}
    </div>
  );
}
