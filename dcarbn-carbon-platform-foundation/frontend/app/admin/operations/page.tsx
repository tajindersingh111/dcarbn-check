"use client";

import { ErrorState, LoadingState } from "@/components/api-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useApiQuery } from "@/lib/use-api";

interface Dependency {
  status: string;
  latency_ms: number | null;
  detail: string | null;
}

interface OperationalHealth {
  status: string;
  timestamp: string;
  database: Dependency;
  redis: Dependency;
  backup: {
    status: string;
    latest_success_at: string | null;
    age_seconds: number | null;
    backup_id: string | null;
    verified: boolean | null;
  };
}


interface RecoveryReadiness {
  status: string;
  timestamp: string;
  wal_archive: {
    status: string;
    latest_wal: string | null;
    latest_archived_at: string | null;
    age_seconds: number | null;
    region: string | null;
  };
  pitr: {
    status: string;
    latest_base_backup_id: string | null;
    latest_base_backup_at: string | null;
    age_seconds: number | null;
    verified: boolean | null;
    region: string | null;
  };
  failover: {
    status: string;
    active_region: string | null;
    region: string | null;
    in_recovery: boolean | null;
    current_lsn: string | null;
    replay_timestamp: string | null;
    timeline: number | null;
    checked_at: string | null;
  };
}

interface EvidenceSummary {
  status: string;
  timestamp: string;
  evidence_count: number;
  latest_release_gate: {
    decision: string | null;
    generated_at: string | null;
    filename: string;
  } | null;
  latest_failover_exercise: {
    result: string | null;
    generated_at: string | null;
    filename: string;
    payload: {
      measurements?: {
        rto_seconds?: number;
        rpo_seconds?: number;
      };
    };
  } | null;
  latest_chaos_exercise: {
    result: string | null;
    generated_at: string | null;
    filename: string;
  } | null;
}

interface SupplyChainSummary {
  status: string;
  timestamp: string;
  component_count: number;
  evidence_count: number;
  latest_assurance: {
    result: string | null;
    generated_at: string | null;
    commit_sha: string | null;
    components: Array<{
      component: string;
      digest: string | null;
      signature: boolean;
      provenance: boolean;
      vulnerability_policy: string;
      license_policy: string;
    }>;
  } | null;
}

interface GitOpsSummary {
  status: string;
  timestamp: string;
  evidence_count: number;
  latest_reconciliation: {
    result: string | null;
    generated_at: string | null;
    application: string | null;
    health: string | null;
    sync: string | null;
    rollout: {
      name?: string;
      phase?: string;
      stable_revision?: string;
      current_revision?: string;
    } | null;
  } | null;
  latest_promotion: {
    result: string | null;
    generated_at: string | null;
    release_version: string | null;
    commit_sha: string | null;
  } | null;
}

function duration(seconds: number | null): string {
  if (seconds === null) return "Unknown";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

export default function OperationsPage() {
  const query = useApiQuery<OperationalHealth>("/health/operational");
  const recovery = useApiQuery<RecoveryReadiness>("/health/recovery-readiness");
  const evidence = useApiQuery<EvidenceSummary>("/operations/evidence-summary");
  const supplyChain = useApiQuery<SupplyChainSummary>("/operations/supply-chain-summary");
  const gitOps = useApiQuery<GitOpsSummary>("/operations/gitops-summary");

  if (query.loading || recovery.loading || evidence.loading || supplyChain.loading || gitOps.loading) return <LoadingState label="Loading operational status" />;
  if (query.error || recovery.error || evidence.error || supplyChain.error || gitOps.error) {
    return <ErrorState message={query.error ?? recovery.error ?? evidence.error ?? supplyChain.error ?? gitOps.error ?? "Unknown error"} onRetry={() => { void query.refresh(); void recovery.refresh(); void evidence.refresh(); void supplyChain.refresh(); void gitOps.refresh(); }} />;
  }

  const data = query.data;
  const recoveryData = recovery.data;
  const evidenceData = evidence.data;
  const supplyChainData = supplyChain.data;
  const gitOpsData = gitOps.data;
  if (!data || !recoveryData || !evidenceData || !supplyChainData || !gitOpsData) return null;

  return (
    <>
      <PageHeader
        eyebrow="Platform operations"
        title="Operational status"
        description="Review dependency health, latency, and verified backup freshness."
        actions={
          <button
            className="button button-secondary"
            onClick={() => { void query.refresh(); void recovery.refresh(); void evidence.refresh(); void supplyChain.refresh(); void gitOps.refresh(); }}
            type="button"
          >
            Refresh status
          </button>
        }
      />

      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-card-header">
            <span>Platform</span>
            <StatusBadge status={data.status === "ok" ? "completed" : "warning"} />
          </div>
          <strong>{data.status === "ok" ? "Operational" : "Degraded"}</strong>
          <p>Checked {new Date(data.timestamp).toLocaleString("en-GB")}</p>
        </article>

        <article className="metric-card">
          <div className="metric-card-header">
            <span>PostgreSQL</span>
            <StatusBadge status={data.database.status === "ok" ? "completed" : "failed"} />
          </div>
          <strong>{data.database.latency_ms ?? "—"} ms</strong>
          <p>{data.database.detail ?? "Primary data store reachable"}</p>
        </article>

        <article className="metric-card">
          <div className="metric-card-header">
            <span>Redis</span>
            <StatusBadge status={data.redis.status === "ok" ? "completed" : "failed"} />
          </div>
          <strong>{data.redis.latency_ms ?? "—"} ms</strong>
          <p>{data.redis.detail ?? "Rate-limit and session dependency reachable"}</p>
        </article>

        <article className="metric-card">
          <div className="metric-card-header">
            <span>Latest backup</span>
            <StatusBadge status={data.backup.status === "ok" ? "completed" : "warning"} />
          </div>
          <strong>{duration(data.backup.age_seconds)}</strong>
          <p>{data.backup.backup_id ?? "No verified backup metadata"}</p>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Recovery readiness</p>
            <h2>Backup verification</h2>
          </div>
        </div>
        <dl className="detail-list">
          <div>
            <dt>Status</dt>
            <dd>{data.backup.status}</dd>
          </div>
          <div>
            <dt>Backup ID</dt>
            <dd>{data.backup.backup_id ?? "—"}</dd>
          </div>
          <div>
            <dt>Latest success</dt>
            <dd>
              {data.backup.latest_success_at
                ? new Date(data.backup.latest_success_at).toLocaleString("en-GB")
                : "—"}
            </dd>
          </div>
          <div>
            <dt>Integrity verified</dt>
            <dd>{data.backup.verified ? "Yes" : "No"}</dd>
          </div>
        </dl>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Point-in-time recovery</p>
            <h2>WAL and regional readiness</h2>
          </div>
          <StatusBadge
            status={recoveryData.status === "ok" ? "completed" : "warning"}
          />
        </div>
        <dl className="detail-list">
          <div>
            <dt>WAL archive</dt>
            <dd>{recoveryData.wal_archive.status} · {duration(recoveryData.wal_archive.age_seconds)}</dd>
          </div>
          <div>
            <dt>Latest WAL</dt>
            <dd>{recoveryData.wal_archive.latest_wal ?? "—"}</dd>
          </div>
          <div>
            <dt>PITR base backup</dt>
            <dd>{recoveryData.pitr.latest_base_backup_id ?? "—"}</dd>
          </div>
          <div>
            <dt>Database role</dt>
            <dd>{recoveryData.failover.status}</dd>
          </div>
          <div>
            <dt>Region</dt>
            <dd>{recoveryData.failover.active_region ?? recoveryData.failover.region ?? "—"}</dd>
          </div>
          <div>
            <dt>Timeline</dt>
            <dd>{recoveryData.failover.timeline ?? "—"}</dd>
          </div>
        </dl>
      </section>


      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Release assurance</p>
            <h2>Exercises and release evidence</h2>
          </div>
          <StatusBadge
            status={
              evidenceData.latest_release_gate?.decision === "approved"
                ? "completed"
                : "warning"
            }
          />
        </div>
        <dl className="detail-list">
          <div>
            <dt>Latest release gate</dt>
            <dd>{evidenceData.latest_release_gate?.decision ?? "No evidence"}</dd>
          </div>
          <div>
            <dt>Failover exercise</dt>
            <dd>{evidenceData.latest_failover_exercise?.result ?? "No evidence"}</dd>
          </div>
          <div>
            <dt>Measured RTO</dt>
            <dd>{evidenceData.latest_failover_exercise?.payload.measurements?.rto_seconds ?? "—"} seconds</dd>
          </div>
          <div>
            <dt>Measured RPO</dt>
            <dd>{evidenceData.latest_failover_exercise?.payload.measurements?.rpo_seconds ?? "—"} seconds</dd>
          </div>
          <div>
            <dt>Latest chaos exercise</dt>
            <dd>{evidenceData.latest_chaos_exercise?.result ?? "No evidence"}</dd>
          </div>
          <div>
            <dt>Evidence bundles</dt>
            <dd>{evidenceData.evidence_count}</dd>
          </div>
        </dl>
      </section>


      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Software supply chain</p>
            <h2>Image assurance</h2>
          </div>
          <StatusBadge
            status={supplyChainData.status === "ok" ? "completed" : "warning"}
          />
        </div>
        <dl className="detail-list">
          <div>
            <dt>Latest assurance</dt>
            <dd>{supplyChainData.latest_assurance?.result ?? "No evidence"}</dd>
          </div>
          <div>
            <dt>Commit</dt>
            <dd>{supplyChainData.latest_assurance?.commit_sha ?? "—"}</dd>
          </div>
          <div>
            <dt>Components</dt>
            <dd>{supplyChainData.component_count}</dd>
          </div>
          <div>
            <dt>Evidence files</dt>
            <dd>{supplyChainData.evidence_count}</dd>
          </div>
          <div>
            <dt>Signatures</dt>
            <dd>
              {supplyChainData.latest_assurance?.components.every(
                (component) => component.signature
              )
                ? "Verified"
                : "Missing or unverified"}
            </dd>
          </div>
          <div>
            <dt>Provenance</dt>
            <dd>
              {supplyChainData.latest_assurance?.components.every(
                (component) => component.provenance
              )
                ? "Verified"
                : "Missing or unverified"}
            </dd>
          </div>
        </dl>
      </section>


      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">GitOps deployment</p>
            <h2>Reconciliation and progressive delivery</h2>
          </div>
          <StatusBadge
            status={gitOpsData.status === "ok" ? "completed" : "warning"}
          />
        </div>
        <dl className="detail-list">
          <div>
            <dt>Application</dt>
            <dd>{gitOpsData.latest_reconciliation?.application ?? "No evidence"}</dd>
          </div>
          <div>
            <dt>Argo CD health</dt>
            <dd>{gitOpsData.latest_reconciliation?.health ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Sync state</dt>
            <dd>{gitOpsData.latest_reconciliation?.sync ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Rollout phase</dt>
            <dd>{gitOpsData.latest_reconciliation?.rollout?.phase ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Stable revision</dt>
            <dd>{gitOpsData.latest_reconciliation?.rollout?.stable_revision ?? "—"}</dd>
          </div>
          <div>
            <dt>Latest promotion</dt>
            <dd>{gitOpsData.latest_promotion?.release_version ?? "No promotion evidence"}</dd>
          </div>
          <div>
            <dt>Promotion commit</dt>
            <dd>{gitOpsData.latest_promotion?.commit_sha ?? "—"}</dd>
          </div>
          <div>
            <dt>Evidence bundles</dt>
            <dd>{gitOpsData.evidence_count}</dd>
          </div>
        </dl>
      </section>

    </>
  );
}
