"use strict";

const CORE = globalThis.DCARBN_PILOT_CORE;
if (!CORE) throw new Error("The governed browser-pilot core did not load.");
const STORAGE_KEY = "dcarbn.new-era.local-demo.encrypted.v1";
const LEGACY_STORAGE_KEY = "dcarbn.new-era.local-demo.v2";
const FACTOR_SOURCE = CORE.FACTOR_PACK.source;

const METHODS = CORE.METHODS;

const ACTIVITY_TEMPLATE_HEADINGS = [
  "template_type", "source_record_id", "activity_date", "description", "site_location", "source_type",
  "vehicle_or_transport_type", "fuel_or_energy_type", "owned_or_leased", "origin", "destination",
  "return_trip", "passengers_or_rooms", "journeys_or_nights", "distance_km", "payload_tonnes",
  "annual_spend_gbp", "supplier_data_attached", "calculation_method_id", "activity_value", "activity_unit",
  "evidence_reference", "equipment_reference", "supplier_name", "supplier_methodology",
  "supplier_methodology_version", "boundary_description", "assurance_status", "notes", "row_purpose",
];

const PROFILE_TEMPLATE_HEADINGS = [
  "template_type", "organisation_name", "reporting_period_start", "reporting_period_end",
  "full_time_equivalent_employees", "headcount", "revenue_gbp", "completed_by", "evidence_reference",
  "organisational_boundary", "reporting_scopes", "responsible_contributor_role", "evidence_completeness_confirmed", "notes",
];

function templateRow(methodId, purpose) {
  const method = METHODS.find((item) => item.id === methodId);
  if (!method) throw new Error(`Template method is not configured: ${methodId}`);
  return {
    template_type: "activity_data", calculation_method_id: method.id, activity_unit: method.unit, row_purpose: purpose,
  };
}

const TEMPLATE_LIBRARY = {
  organisation: {
    filename: "dcarbn-new-era-info-needed.csv",
    label: "Organisation information",
    headings: PROFILE_TEMPLATE_HEADINGS,
    rows: [{ template_type: "organisation_information", organisation_name: "", reporting_period_start: "2025-01-01", reporting_period_end: "2025-12-31", full_time_equivalent_employees: "", headcount: "", revenue_gbp: "", completed_by: "", evidence_reference: "", organisational_boundary: "", reporting_scopes: "Scope 1, Scope 2 and Scope 3", responsible_contributor_role: "", evidence_completeness_confirmed: "Yes", notes: "Complete one organisation row" }],
  },
  utilities: {
    filename: "dcarbn-new-era-utilities-and-rent.csv",
    label: "Utilities & rent",
    rows: [
      templateRow("scope2.location_electricity.kwh.uk_2025.v1", "Purchased electricity in kWh"),
      templateRow("scope1.stationary_natural_gas.gross_cv.kwh.uk_2025.v1", "Natural gas in gross-CV kWh"),
      templateRow("scope1.stationary_natural_gas.cubic_metres.uk_2025.v1", "Natural gas in cubic metres"),
      templateRow("scope1.refrigerant.r410a.service_top_up.kg.uk_2025.v1", "R410A service top-up; equipment_reference is required"),
      templateRow("scope3.category5.commercial_waste.landfill.tonnes.uk_2025.v1", "Commercial waste sent to landfill"),
      templateRow("scope3.category5.commercial_waste.combustion.tonnes.uk_2025.v1", "Commercial waste sent to combustion"),
    ],
  },
  travel: {
    filename: "dcarbn-new-era-company-vehicles-and-business-travel.csv",
    label: "Vehicles & business travel",
    rows: [
      templateRow("scope1.mobile_combustion.diesel.litres.uk_2025.v1", "Fuel used by owned or controlled diesel vehicles"),
      templateRow("scope3.category3.diesel_wtt.litres.uk_2025.v1", "Well-to-tank emissions for the same diesel litres; use a distinct source ID"),
      templateRow("scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2025.v1", "Distance travelled by owned or controlled Class I diesel vans"),
      templateRow("scope1.mobile_combustion.average_car.petrol.km.uk_2025.v1", "Distance travelled by owned or controlled average petrol cars"),
      templateRow("scope3.category6.domestic_air.with_rf.passenger_km.uk_2025.v1", "Domestic UK air travel; total passenger-km including return journeys"),
      templateRow("scope3.category6.national_rail.passenger_km.uk_2025.v1", "National rail travel; total passenger-km including return journeys"),
      templateRow("scope3.category6.average_ferry_passenger.passenger_km.uk_2025.v1", "Ferry travel; total passenger-km including return journeys"),
      templateRow("scope3.category6.uk_hotel.room_night.uk_2025.v1", "UK overnight stays; total rooms multiplied by nights"),
    ],
  },
  procurement: {
    filename: "dcarbn-new-era-procurement.csv",
    label: "Procurement",
    rows: [
      templateRow("scope3.category1.supplier_specific.reported_kgco2e.ghgp.v1", "Purchased goods or services; complete every supplier-lineage field"),
      templateRow("scope3.category2.supplier_specific.reported_kgco2e.ghgp.v1", "Capital goods; complete every supplier-lineage field"),
    ],
  },
  freight: {
    filename: "dcarbn-new-era-transportation-and-distribution.csv",
    label: "Transport & distribution",
    rows: [
      templateRow("scope3.category4.diesel_van.tonne_km.uk_2025.v1", "Upstream Class I diesel van freight; payload tonnes multiplied by distance km"),
      templateRow("scope3.category9.average_diesel_van.tonne_km.uk_2025.v1", "Downstream average diesel van freight; payload tonnes multiplied by distance km"),
      templateRow("scope3.category9.average_non_refrigerated_hgv.average_laden.tonne_km.uk_2025.v1", "Downstream non-refrigerated HGV freight; payload tonnes multiplied by distance km"),
      templateRow("scope3.category9.rail_freight.tonne_km.uk_2025.v1", "Downstream rail freight; payload tonnes multiplied by distance km"),
    ],
  },
  commuting: {
    filename: "dcarbn-new-era-employee-commuting.csv",
    label: "Employee commuting",
    rows: [
      templateRow("scope3.category7.average_car.unknown_fuel.km.uk_2025.v1", "Total employee commuting kilometres by average car"),
    ],
  },
};

const METHOD_BY_ID = new Map(METHODS.map((method) => [method.id, method]));
let state;
let uploadRows = [];
let uploadKind = "activity";
let selectedFile = null;
let toastTimer = null;

const ROLE_DEFINITIONS = {
  contributor: { label: "New Era Contributor", short: "NE", helper: "Uploads and corrects customer activity data" },
  analyst: { label: "D-carbN Analyst", short: "DA", helper: "Validates methods, evidence and calculation treatment" },
  approver: { label: "D-carbN Approver", short: "AP", helper: "Authorises and locks the customer report" },
};

const PILOT_STAGES = [
  { id: "draft", label: "Customer preparation" },
  { id: "analyst_review", label: "D-carbN review" },
  { id: "ready_for_approval", label: "Final approval" },
  { id: "locked", label: "Locked report" },
];

let sessionPassphrase = "";
let lastActivityAt = Date.now();
let saveSequence = Promise.resolve();
let pendingInitialState = null;
state = normalisePilotState(defaultState());

function uid(prefix) {
  if (globalThis.crypto?.randomUUID) return `${prefix}-${globalThis.crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function seedActivity({ id, date, description, methodId, value, evidence, status = "approved", lineage = {} }) {
  const method = METHOD_BY_ID.get(methodId);
  return {
    id,
    sourceRecordId: id,
    date,
    description,
    methodId,
    quantity: value,
    unit: method.unit,
    factor: method.factor,
    kgCo2e: method.directResult ? value : value * method.factor,
    factorYear: method.factorYear,
    factorVersion: method.factorVersion,
    factorSource: method.factorSource,
    evidence,
    lineage,
    status,
    validation: "Exact governed method and compatible unit confirmed.",
    source: "New Era Group sample",
    createdAt: "2026-08-17T09:00:00.000Z",
  };
}

function defaultState() {
  return {
    version: 3,
    organisation: "New Era Group",
    period: "Calendar year 2025",
    profile: {
      reportingPeriodStart: "2025-01-01", reportingPeriodEnd: "2025-12-31",
      fullTimeEquivalentEmployees: null, headcount: null, revenueGbp: null,
      completedBy: "Fictional Sustainability Coordinator", evidenceReference: "FICTIONAL-ORG-2025",
      organisationalBoundary: "Operational control", reportingScopes: "Scope 1, Scope 2 and Scope 3",
      responsibleContributorRole: "Sustainability Coordinator", evidenceCompletenessConfirmed: true, notes: "Fictional demonstration profile",
    },
    activities: [
      seedActivity({ id: "NEG-UTIL-GAS-001", date: "2025-03-31", description: "Head office natural gas", methodId: "scope1.stationary_natural_gas.gross_cv.kwh.uk_2025.v1", value: 48000, evidence: "NEG-GAS-Q1-2025" }),
      seedActivity({ id: "NEG-FLEET-DSL-001", date: "2025-04-30", description: "Owned delivery fleet diesel", methodId: "scope1.mobile_combustion.diesel.litres.uk_2025.v1", value: 7200, evidence: "NEG-FUEL-APR-2025" }),
      seedActivity({ id: "NEG-REF-001", date: "2025-05-16", description: "Warehouse R410A service top-up", methodId: "scope1.refrigerant.r410a.service_top_up.kg.uk_2025.v1", value: 2.4, evidence: "SERVICE-AC-14-2025", lineage: { equipment_reference: "WAREHOUSE-AC-14", service_performed: true } }),
      seedActivity({ id: "NEG-ELEC-001", date: "2025-03-31", description: "UK grid electricity", methodId: "scope2.location_electricity.kwh.uk_2025.v1", value: 130000, evidence: "NEG-ELEC-Q1-2025" }),
      seedActivity({ id: "NEG-RAIL-001", date: "2025-06-30", description: "Employee national rail travel", methodId: "scope3.category6.national_rail.passenger_km.uk_2025.v1", value: 4500, evidence: "TRAVEL-LEDGER-H1-2025" }),
      seedActivity({ id: "NEG-HOTEL-001", date: "2025-06-30", description: "UK hotel stays", methodId: "scope3.category6.uk_hotel.room_night.uk_2025.v1", value: 44, evidence: "HOTEL-LEDGER-H1-2025" }),
      seedActivity({ id: "NEG-COMMUTE-001", date: "2025-06-30", description: "Average car employee commuting", methodId: "scope3.category7.average_car.unknown_fuel.km.uk_2025.v1", value: 12000, evidence: "STAFF-SURVEY-2025", status: "ready" }),
      seedActivity({ id: "NEG-SUPPLIER-001", date: "2025-06-30", description: "Supplier-reported packaging footprint", methodId: "scope3.category1.supplier_specific.reported_kgco2e.ghgp.v1", value: 8400, evidence: "SUPPLIER-PCF-PACK-2025", status: "ready", lineage: { supplier_name: "Fictional Packaging Ltd", supplier_methodology: "Product carbon footprint", supplier_methodology_version: "2025.1", boundary_description: "Cradle-to-gate", assurance_status: "limited_assurance" } }),
    ],
    batches: [],
    audit: [
      { id: "audit-seed-3", at: "2026-08-17T09:12:00.000Z", action: "Supplier and commuting records queued for review", actor: "Local demo" },
      { id: "audit-seed-2", at: "2026-08-17T09:06:00.000Z", action: "Six governed activities approved", actor: "D-carbN Analyst" },
      { id: "audit-seed-1", at: "2026-08-17T09:00:00.000Z", action: "New Era Group demonstration inventory created", actor: "Local demo" },
    ],
    report: null,
    intake: { organisationValidated: false, validatedScopes: { 1: true, 2: true, 3: true }, unresolvedRecords: [], duplicateChecksPassed: true, confirmations: { complete: true, duplicates: true } },
    pilot: { stage: "draft", activeRole: "contributor", submittedAt: null, reviewedAt: null, lockedAt: null },
  };
}

function normalisePilotState(candidate) {
  const pilot = candidate.pilot || {};
  const stage = PILOT_STAGES.some((item) => item.id === pilot.stage) ? pilot.stage : "draft";
  const activeRole = ROLE_DEFINITIONS[pilot.activeRole] ? pilot.activeRole : "contributor";
  const activities = (candidate.activities || []).map((activity) => {
    const currentId = String(activity.methodId || "").replace("uk_2026", "uk_2025");
    const governed = METHOD_BY_ID.get(currentId);
    if (!governed) return activity;
    return { ...activity, methodId: currentId, factor: governed.factor, kgCo2e: governed.directResult ? activity.quantity : activity.quantity * governed.factor, factorYear: governed.factorYear, factorVersion: governed.factorVersion, factorSource: governed.factorSource };
  });
  return {
    ...candidate,
    version: 3,
    activities,
    profile: { ...defaultState().profile, ...(candidate.profile || {}) },
    intake: { ...defaultState().intake, ...(candidate.intake || {}), validatedScopes: { ...defaultState().intake.validatedScopes, ...(candidate.intake?.validatedScopes || {}) }, confirmations: { ...defaultState().intake.confirmations, ...(candidate.intake?.confirmations || {}) } },
    pilot: { stage, activeRole, submittedAt: pilot.submittedAt || null, reviewedAt: pilot.reviewedAt || null, lockedAt: pilot.lockedAt || null },
  };
}

function saveState() {
  if (!sessionPassphrase) return;
  const snapshot = structuredClone(state);
  saveSequence = saveSequence
    .then(async () => localStorage.setItem(STORAGE_KEY, JSON.stringify(await CORE.encryptPayload(CORE.createSessionBundle(snapshot), sessionPassphrase))))
    .catch((error) => { console.error("Encrypted local save failed", error); showToast("Secure local save failed; export the session before closing this page."); });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value, maximumFractionDigits = 2) {
  return Number(value || 0).toLocaleString("en-GB", { maximumFractionDigits });
}

function formatTonnes(kg) {
  return `${formatNumber(kg / 1000, 2)} tCO₂e`;
}

function methodFor(activity) {
  return METHOD_BY_ID.get(activity.methodId);
}

function lineageComplete(activity) {
  const method = methodFor(activity);
  const lineage = activity.lineage || {};
  if (method.id === "scope1.refrigerant.r410a.service_top_up.kg.uk_2025.v1") {
    return Boolean(lineage.equipment_reference && lineage.service_performed === true);
  }
  if (method.directResult) {
    return ["supplier_name", "supplier_methodology", "supplier_methodology_version", "boundary_description", "assurance_status"].every((field) => Boolean(lineage[field]));
  }
  return true;
}

function lineageSummary(activity) {
  const method = methodFor(activity);
  const lineage = activity.lineage || {};
  if (method.id === "scope1.refrigerant.r410a.service_top_up.kg.uk_2025.v1") return `Equipment ${lineage.equipment_reference || "missing"}`;
  if (method.directResult) return `${lineage.supplier_name || "Supplier missing"} · ${lineage.supplier_methodology || "Method missing"}`;
  return "Government factor hierarchy retained";
}

function scopeLabel(method) {
  return method.scope === 3 ? `Scope 3 · Cat. ${method.category}` : `Scope ${method.scope}`;
}

function statusBadge(status) {
  const labels = { approved: "Approved", ready: "Ready for review", needs_attention: "Needs attention" };
  const tones = { approved: "success", ready: "warning", needs_attention: "danger" };
  return `<span class="badge badge-${tones[status] || "info"}">${labels[status] || escapeHtml(status)}</span>`;
}

function totals() {
  const valid = state.activities.filter((item) => item.status !== "needs_attention");
  const scopes = { 1: 0, 2: 0, 3: 0 };
  valid.forEach((item) => { scopes[methodFor(item).scope] += item.kgCo2e; });
  return {
    scopes,
    total: scopes[1] + scopes[2] + scopes[3],
    approved: valid.filter((item) => item.status === "approved").length,
    ready: valid.filter((item) => item.status === "ready").length,
    attention: state.activities.filter((item) => item.status === "needs_attention").length,
  };
}

function addAudit(action, actor = "D-carbN Analyst") {
  state.audit.unshift({ id: uid("audit"), at: new Date().toISOString(), action, actor });
}

function metricCard(label, value, helper, icon, options = {}) {
  const classes = options.featured ? "metric-card metric-card-featured" : "metric-card";
  const note = options.note ? `<span class="metric-card-note">${escapeHtml(options.note)}</span>` : "";
  return `<article class="${classes}"><div class="metric-card-header"><span>${escapeHtml(label)}</span><span class="metric-card-icon">${escapeHtml(icon)}</span></div><strong>${escapeHtml(value)}</strong><p>${escapeHtml(helper)}</p>${note}</article>`;
}

function currentRole() {
  return state.pilot.activeRole;
}

function currentStageIndex() {
  return PILOT_STAGES.findIndex((item) => item.id === state.pilot.stage);
}

function canAccessView(view) {
  const role = currentRole();
  if (role === "contributor") {
    if (state.pilot.stage === "locked") return ["dashboard", "activities", "results", "reports"].includes(view);
    return ["dashboard", "upload", "activities"].includes(view);
  }
  if (role === "analyst") return ["dashboard", "activities", "review", "results", "reports"].includes(view);
  return ["dashboard", "review", "results", "reports"].includes(view);
}

function contributorCanEdit() {
  return currentRole() === "contributor" && state.pilot.stage === "draft";
}

function analystCanReview() {
  return currentRole() === "analyst" && state.pilot.stage === "analyst_review";
}

function renderPilotStrip() {
  const role = ROLE_DEFINITIONS[currentRole()];
  const stageIndex = currentStageIndex();
  const summary = totals();
  let action = "";
  let helper = "";
  if (state.pilot.stage === "draft") {
    const blockers = CORE.submissionBlockers(state);
    if (currentRole() === "contributor") {
      action = `<button class="button button-primary" data-pilot-action="submit"${blockers.length ? " disabled" : ""}>Submit to D-carbN</button>`;
      helper = blockers.length ? blockers.join(" ") : "All required files and confirmations are complete.";
    } else helper = "Awaiting customer submission.";
  } else if (state.pilot.stage === "analyst_review") {
    if (currentRole() === "analyst") {
      const reviewComplete = summary.ready === 0 && summary.attention === 0;
      action = `<button class="button button-primary" data-pilot-action="review"${reviewComplete ? "" : " disabled"}>Complete analyst review</button>`;
      helper = reviewComplete ? "All activities have an analyst decision." : `${summary.ready} review and ${summary.attention} correction item(s) remain.`;
    } else helper = "D-carbN is reviewing the submitted inventory.";
  } else if (state.pilot.stage === "ready_for_approval") {
    if (currentRole() === "approver") action = `<button class="button button-primary" data-pilot-action="lock"${reportChecks().some((check) => !check.ok) ? " disabled" : ""}>Lock and release report</button>`;
    else helper = "Awaiting independent D-carbN approval.";
  } else {
    action = `<span class="badge badge-success">Report locked</span>`;
    helper = "The released snapshot is available to the customer.";
  }

  document.querySelector("#pilot-strip").innerHTML = `<div class="pilot-role"><strong>${escapeHtml(role.label)}</strong><span>${escapeHtml(role.helper)}</span></div><div class="pilot-steps">${PILOT_STAGES.map((stage, index) => `<span class="pilot-step ${index < stageIndex ? "complete" : index === stageIndex ? "current" : ""}">${escapeHtml(stage.label)}</span>`).join("")}</div><div class="pilot-action">${action}<small>${escapeHtml(helper)}</small></div>`;
  document.querySelector("#role-select").value = currentRole();
  document.querySelector("#role-avatar").textContent = role.short;
}

function applyRoleControls() {
  document.querySelectorAll(".nav-link").forEach((button) => {
    const allowed = canAccessView(button.dataset.view);
    button.disabled = !allowed;
    button.title = allowed ? "" : "Unavailable for this pilot role";
  });
  ["#open-activity-form", "#validate-upload", "#load-sample", "#accept-valid-rows"].forEach((selector) => {
    const button = document.querySelector(selector);
    if (button) button.disabled = !contributorCanEdit() || (selector === "#validate-upload" && !selectedFile);
  });
  const fileInput = document.querySelector("#file-input");
  if (fileInput) fileInput.disabled = !contributorCanEdit();
  if (!contributorCanEdit()) document.querySelector("#activity-form-panel")?.classList.add("hidden");
  const approveAll = document.querySelector("#approve-all-ready");
  if (approveAll) approveAll.disabled = !analystCanReview();
  const generate = document.querySelector("#generate-report");
  if (generate) generate.disabled = !["analyst", "approver"].includes(currentRole()) || state.pilot.stage === "locked";
  const exportWorkspaceButton = document.querySelector("#export-workspace");
  if (exportWorkspaceButton) exportWorkspaceButton.disabled = currentRole() !== "analyst";
  const resultsExportButton = document.querySelector("#export-results");
  if (resultsExportButton) resultsExportButton.disabled = currentRole() === "contributor" && state.pilot.stage !== "locked";
  const openApprovals = document.querySelector("#open-approvals");
  if (openApprovals) openApprovals.disabled = !canAccessView("review") || totals().ready === 0;
}

function renderDashboard() {
  const summary = totals();
  const valid = state.activities.filter((item) => item.status !== "needs_attention");
  const evidenceCount = valid.filter((item) => item.evidence).length;
  const evidenceCoverage = valid.length ? Math.round(evidenceCount / valid.length * 100) : 0;
  const qualityScore = state.activities.length ? Math.max(0, 5 - summary.attention / state.activities.length * 5) : 0;
  const openControls = summary.ready + summary.attention;
  const checks = reportChecks();
  const readiness = Math.round(checks.filter((check) => check.ok).length / checks.length * 100);
  const scopePanel = document.querySelector("#scope-chart").closest(".panel");
  scopePanel.querySelector(".eyebrow").textContent = "Reported footprint";
  scopePanel.querySelector("h2").textContent = "Emissions by scope";

  if (currentRole() === "contributor" && state.pilot.stage !== "locked") {
    const intakeChecks = [state.intake.organisationValidated, state.intake.validatedScopes[1], state.intake.validatedScopes[2], state.intake.validatedScopes[3], state.intake.duplicateChecksPassed, !state.intake.unresolvedRecords.length, state.intake.confirmations.complete, state.intake.confirmations.duplicates];
    const intakeProgress = Math.round(intakeChecks.filter(Boolean).length / intakeChecks.length * 100);
    const intakeBlockers = CORE.submissionBlockers(state);
    document.querySelector("#dashboard-readiness").innerHTML = `<span>Submission readiness</span><strong>${intakeProgress}%</strong><small>${intakeBlockers.length ? escapeHtml(intakeBlockers[0]) : "Ready to submit"}</small>`;
    document.querySelector("#dashboard-metrics").innerHTML = [
      metricCard("Activity records", state.activities.length, "Customer source records prepared", "ACT", { featured: true, note: "New Era Group workspace" }),
      metricCard("Evidence references", `${evidenceCoverage}%`, `${evidenceCount} of ${valid.length} valid records`, "EV", { note: evidenceCoverage === 100 ? "Complete coverage" : "Evidence required" }),
      metricCard("Validation issues", summary.attention, "Resolve before submission", "DQ", { note: summary.attention ? "Customer action required" : "No open validation flags" }),
      metricCard("Imported batches", state.batches.length, "Controlled customer uploads", "UP", { note: state.pilot.stage === "draft" ? "Preparation in progress" : "Submitted to D-carbN" }),
    ].join("");
    scopePanel.querySelector(".eyebrow").textContent = "D-carbN service boundary";
    scopePanel.querySelector("h2").textContent = "Calculations remain governed";
    document.querySelector("#scope-chart").innerHTML = `<div class="service-boundary"><div><h2>Customer data received. D-carbN completes the carbon assessment.</h2><p>Emission-factor selection, calculation outputs, methodology decisions and the final report remain within the controlled D-carbN analyst and approval workflow.</p></div><span class="service-boundary-badge">Protected service layer</span></div>`;
    const workflow = [
      ["1", "Prepare activity data", `${state.activities.length} source records`, "upload", state.pilot.stage !== "draft"],
      ["2", "Submit to D-carbN", state.pilot.submittedAt ? "Submission received" : "Customer action", "dashboard", !state.pilot.submittedAt],
      ["3", "Analyst review", state.pilot.stage === "analyst_review" ? "In progress" : "Starts after submission", "dashboard", state.pilot.stage === "draft"],
      ["4", "Locked customer report", state.pilot.stage === "locked" ? "Released" : "Controlled by D-carbN", "dashboard", state.pilot.stage !== "locked"],
    ];
    document.querySelector("#workflow-list").innerHTML = workflow.map(([number, title, helper, view, attention]) => `<button class="workflow-item${attention ? " attention" : ""}" data-go="${view}"><span class="workflow-number">${number}</span><span><strong>${title}</strong><small>${helper}</small></span><span>→</span></button>`).join("");
    const material = [...state.activities].slice(0, 5);
    document.querySelector("#material-activities").innerHTML = material.map((item) => {
      const method = methodFor(item);
      return `<tr><td><div class="stacked"><strong>${escapeHtml(item.description)}</strong><span>${escapeHtml(item.sourceRecordId)}</span></div></td><td><span class="badge scope-badge">${scopeLabel(method)}</span></td><td>D-carbN governed</td><td><span class="badge badge-info">Available after approval</span></td><td>${statusBadge(item.status)}</td></tr>`;
    }).join("");
    return;
  }

  document.querySelector("#dashboard-readiness").innerHTML = `<span>Report readiness</span><strong>${readiness}%</strong><small>${openControls ? `${openControls} control${openControls === 1 ? "" : "s"} remaining` : "Ready to generate"}</small>`;
  document.querySelector("#dashboard-metrics").innerHTML = [
    metricCard("Total reported emissions", formatTonnes(summary.total), "tCO₂e · governed inventory headline", "CO₂", { featured: true, note: "Current reporting year" }),
    metricCard("Evidence coverage", `${evidenceCoverage}%`, `${evidenceCount} of ${valid.length} calculated records`, "EV", { note: evidenceCoverage === 100 ? "Complete coverage" : `${valid.length - evidenceCount} items need attention` }),
    metricCard("Data quality", `${formatNumber(qualityScore, 1)} / 5`, "Weighted inventory score", "DQ", { note: qualityScore >= 4 ? "High confidence" : "Review flagged records" }),
    metricCard("Open controls", openControls, "Validation and independent approvals", "CT", { note: openControls ? "Due before locking" : "All controls complete" }),
  ].join("");

  const p1 = summary.total ? summary.scopes[1] / summary.total * 100 : 0;
  const p2 = summary.total ? summary.scopes[2] / summary.total * 100 : 0;
  const scopeDescriptions = { 1: "Fleet fuel and refrigerants", 2: "Location-based electricity", 3: "Travel and value chain" };
  const scopeRows = [1, 2, 3].map((scope) => `<div class="scope-ledger-row"><span class="scope-dot scope-${scope}"></span><span><strong>Scope ${scope}</strong><small>${scopeDescriptions[scope]}</small></span><strong>${formatNumber(summary.scopes[scope] / 1000, 1)}</strong><span>${summary.total ? formatNumber(summary.scopes[scope] / summary.total * 100, 0) : 0}%</span></div>`).join("");
  document.querySelector("#scope-chart").innerHTML = `<div class="dashboard-donut" style="background:conic-gradient(var(--green) 0 ${p1}%, var(--gold) ${p1}% ${p1 + p2}%, var(--brand) ${p1 + p2}% 100%)"><span>${formatNumber(summary.total / 1000, 1)}<small>tCO₂e</small></span></div><div class="scope-ledger">${scopeRows}</div>`;

  const workflow = [
    ["1", "Upload source data", `${state.batches.length} imported batch${state.batches.length === 1 ? "" : "es"}`, "upload"],
    ["2", "Review validation", `${summary.ready} awaiting approval`, "review"],
    ["3", "Confirm calculations", `${state.activities.length - summary.attention} governed results`, "results"],
    ["4", "Generate snapshot", state.report ? "Latest report available" : "Not generated", "reports"],
  ];
  document.querySelector("#workflow-list").innerHTML = workflow.map(([number, title, helper, view]) => {
    const incomplete = (view === "review" && summary.ready > 0) || (view === "reports" && !state.report);
    return `<button class="workflow-item${incomplete ? " attention" : ""}" data-go="${view}"><span class="workflow-number">${number}</span><span><strong>${title}</strong><small>${helper}</small></span><span>→</span></button>`;
  }).join("");

  const material = [...state.activities].filter((item) => item.status !== "needs_attention").sort((a, b) => b.kgCo2e - a.kgCo2e).slice(0, 5);
  document.querySelector("#material-activities").innerHTML = material.map((item) => {
    const method = methodFor(item);
    return `<tr><td><div class="stacked"><strong>${escapeHtml(item.description)}</strong><span>${escapeHtml(item.sourceRecordId)}</span></div></td><td><span class="badge scope-badge">${scopeLabel(method)}</span></td><td>${escapeHtml(method.short)}</td><td><strong>${formatNumber(item.kgCo2e)} kgCO₂e</strong></td><td>${statusBadge(item.status)}</td></tr>`;
  }).join("");
}

function renderActivities() {
  const search = document.querySelector("#activity-search").value.trim().toLowerCase();
  const scope = document.querySelector("#scope-filter").value;
  const status = document.querySelector("#status-filter").value;
  const filtered = state.activities.filter((item) => {
    const method = methodFor(item);
    const matchesText = !search || [item.description, item.sourceRecordId, item.evidence].some((value) => value.toLowerCase().includes(search));
    return matchesText && (scope === "all" || String(method.scope) === scope) && (status === "all" || item.status === status);
  });
  document.querySelector("#activities-table").innerHTML = filtered.map((item) => {
    const method = methodFor(item);
    const customerRestricted = currentRole() === "contributor" && state.pilot.stage !== "locked";
    const factorValue = customerRestricted ? "D-carbN governed" : (method.directResult ? "Reported" : formatNumber(item.factor, 5));
    const resultValue = customerRestricted ? `<span class="badge badge-info">After approval</span>` : `<strong>${formatNumber(item.kgCo2e)}</strong>`;
    const removeAction = contributorCanEdit() ? `<button class="table-action" data-delete="${escapeHtml(item.id)}">Remove</button>` : "";
    return `<tr>
      <td><div class="stacked"><strong>${escapeHtml(item.description)}</strong><span>${escapeHtml(item.sourceRecordId)} · ${escapeHtml(item.date)}</span></div></td>
      <td><span class="badge scope-badge">${scopeLabel(method)}</span></td>
      <td>${formatNumber(item.quantity, 4)} ${escapeHtml(item.unit)}</td>
      <td><div class="stacked"><strong>${factorValue}</strong><span>${escapeHtml(item.factorVersion || "Missing version")} · ${escapeHtml(item.factorYear || "Missing year")}</span></div></td>
      <td>${resultValue}</td>
      <td><div class="stacked"><strong>${item.evidence ? "Complete" : "Missing"}</strong><span>${escapeHtml(item.evidence || "—")}</span></div></td>
      <td>${statusBadge(item.status)}</td>
      <td>${removeAction}</td>
    </tr>`;
  }).join("");
  document.querySelector("#activities-empty").classList.toggle("hidden", filtered.length > 0);
}

function renderReview() {
  const summary = totals();
  document.querySelector("#review-summary").innerHTML = [
    [summary.ready, "Ready for decision", "Complete method and evidence lineage"],
    [summary.approved, "Approved", "Included in reviewed inventory"],
    [summary.attention, "Needs attention", "Excluded until corrected"],
  ].map(([value, title, helper]) => `<article class="summary-card"><span>${value}</span><div><strong>${title}</strong><small>${helper}</small></div></article>`).join("");
  document.querySelector("#review-count").textContent = `${state.activities.length} records`;
  document.querySelector("#review-list").innerHTML = state.activities.map((item) => {
    const method = methodFor(item);
    const decisionActions = item.status === "ready" && analystCanReview() ? `<button class="button button-secondary" data-return="${escapeHtml(item.id)}">Return</button><button class="button button-primary" data-approve="${escapeHtml(item.id)}">Approve</button>` : "";
    return `<article class="review-item">
      <div class="review-item-header"><div><h3>${escapeHtml(item.description)}</h3><p>${escapeHtml(item.sourceRecordId)} · ${escapeHtml(item.date)}</p></div>${statusBadge(item.status)}</div>
      <div class="review-details">
        <div><span>Classification</span><strong>${scopeLabel(method)}</strong></div>
        <div><span>Activity</span><strong>${formatNumber(item.quantity, 4)} ${escapeHtml(item.unit)}</strong></div>
        <div><span>Factor / basis</span><strong>${method.directResult ? "Supplier reported" : formatNumber(item.factor, 5)} · ${escapeHtml(item.factorVersion)}</strong></div>
        <div><span>Result</span><strong>${formatNumber(item.kgCo2e)} kgCO₂e</strong></div>
        <div><span>Evidence</span><strong>${escapeHtml(item.evidence || "Missing")}</strong></div>
        <div><span>Method</span><strong>${escapeHtml(method.short)}</strong></div>
        <div><span>Source</span><strong>${escapeHtml(item.source)}</strong></div>
        <div><span>Method lineage</span><strong>${escapeHtml(lineageSummary(item))}</strong></div>
        <div><span>Validation</span><strong>${escapeHtml(item.validation)}</strong></div>
      </div>
      <div class="review-actions">
        ${decisionActions || `<span class="record-count">${state.pilot.stage === "analyst_review" ? "Read-only for this role" : "No decision required"}</span>`}
      </div>
    </article>`;
  }).join("");
}

function renderResults() {
  const summary = totals();
  document.querySelector("#results-metrics").innerHTML = [1, 2, 3].map((scope) => metricCard(`Scope ${scope}`, formatTonnes(summary.scopes[scope]), `${summary.total ? formatNumber(summary.scopes[scope] / summary.total * 100, 1) : 0}% of inventory`, `S${scope}`)).concat([
    metricCard("Combined total", formatTonnes(summary.total), "Valid records before rounding", "Σ"),
  ]).join("");

  const p1 = summary.total ? summary.scopes[1] / summary.total * 100 : 0;
  const p2 = summary.total ? summary.scopes[2] / summary.total * 100 : 0;
  const donut = document.querySelector("#scope-donut");
  donut.style.background = `conic-gradient(var(--green) 0 ${p1}%, var(--gold) ${p1}% ${p1 + p2}%, var(--brand) ${p1 + p2}% 100%)`;
  donut.querySelector("span").innerHTML = `${formatNumber(summary.total / 1000, 1)}<br><small>tCO₂e</small>`;
  document.querySelector("#donut-legend").innerHTML = [1, 2, 3].map((scope) => `<div class="legend-item"><span class="legend-swatch scope-${scope}"></span><span>Scope ${scope}</span><strong>${summary.total ? formatNumber(summary.scopes[scope] / summary.total * 100, 1) : 0}%</strong></div>`).join("");

  const byMethod = new Map();
  state.activities.filter((item) => item.status !== "needs_attention").forEach((item) => {
    const method = methodFor(item);
    byMethod.set(method.short, (byMethod.get(method.short) || 0) + item.kgCo2e);
  });
  const methodRows = [...byMethod.entries()].sort((a, b) => b[1] - a[1]).slice(0, 7);
  const max = methodRows[0]?.[1] || 1;
  document.querySelector("#method-bars").innerHTML = methodRows.map(([label, value]) => `<div class="method-bar"><div class="method-bar-label"><span>${escapeHtml(label)}</span><strong>${formatNumber(value)} kg</strong></div><div class="bar-track"><div class="bar-fill scope-2" style="width:${value / max * 100}%"></div></div></div>`).join("");

  const valid = state.activities.filter((item) => item.status !== "needs_attention");
  document.querySelector("#result-count").textContent = `${valid.length} calculated records`;
  document.querySelector("#results-table").innerHTML = valid.map((item) => {
    const method = methodFor(item);
    const expression = method.directResult ? `${formatNumber(item.quantity)} reported kgCO₂e` : `${formatNumber(item.quantity, 4)} × ${formatNumber(item.factor, 5)}`;
    return `<tr><td><div class="stacked"><strong>${escapeHtml(item.description)}</strong><span>${escapeHtml(item.sourceRecordId)}</span></div></td><td>${scopeLabel(method)}</td><td><div class="stacked"><strong>${escapeHtml(method.short)}</strong><span class="mono">${escapeHtml(method.id)}</span><span>${escapeHtml(item.factorSource)} · pack ${escapeHtml(item.factorVersion)}</span></div></td><td>${expression}</td><td><strong>${formatNumber(item.kgCo2e)} kgCO₂e</strong></td><td>${statusBadge(item.status)}</td></tr>`;
  }).join("");
}

function reportChecks() {
  const summary = totals();
  const valid = state.activities.filter((item) => item.status !== "needs_attention");
  const lockBlockers = CORE.reportLockBlockers(state);
  return [
    { ok: state.activities.length > 0, title: "Activity population", helper: `${state.activities.length} records loaded` },
    { ok: summary.attention === 0, title: "Validation complete", helper: summary.attention ? `${summary.attention} record(s) need attention` : "No unresolved validation flags" },
    { ok: summary.ready === 0, title: "Review complete", helper: summary.ready ? `${summary.ready} decision(s) outstanding` : "All valid records approved" },
    { ok: valid.every((item) => item.evidence), title: "Evidence references", helper: "Every valid result retains evidence lineage" },
    { ok: valid.every((item) => methodFor(item) && lineageComplete(item)), title: "Factor and method lineage", helper: "Every valid result retains its governed and method-specific lineage" },
    { ok: lockBlockers.length === 0, title: "Organisation and release controls", helper: lockBlockers.length ? lockBlockers.join(" ") : "Boundary, scopes, contributor, evidence, files and methodology are complete" },
  ];
}

function renderReports() {
  const checks = reportChecks();
  document.querySelector("#report-checklist").innerHTML = checks.map((check) => `<div class="checklist-item"><span class="checklist-icon ${check.ok ? "badge-success" : "badge-warning"}">${check.ok ? "✓" : "!"}</span><div><strong>${escapeHtml(check.title)}</strong><small>${escapeHtml(check.helper)}</small></div><span class="badge badge-${check.ok ? "success" : "warning"}">${check.ok ? "Passed" : "Open"}</span></div>`).join("");
  const report = state.report;
  document.querySelector("#report-identity").innerHTML = report ? [
    ["Status", report.status], ["Version", `v${report.version}`], ["Generated", new Date(report.generatedAt).toLocaleString("en-GB")], ["Snapshot hash", report.hash],
  ].map(([label, value]) => `<div class="identity-row"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`).join("") : `<div class="empty-state"><strong>No snapshot generated</strong><span>Complete review decisions, then generate a report.</span></div>`;

  const summary = totals();
  const valid = state.activities.filter((item) => item.status !== "needs_attention");
  const evidenceCount = valid.filter((item) => item.evidence).length;
  const evidenceCoverage = valid.length ? Math.round(evidenceCount / valid.length * 100) : 0;
  const p1 = summary.total ? summary.scopes[1] / summary.total * 100 : 0;
  const p2 = summary.total ? summary.scopes[2] / summary.total * 100 : 0;
  const p3 = Math.max(0, 100 - p1 - p2);
  const reportStatus = report?.status || "Working draft";
  const coverStatus = state.pilot.stage === "locked" || reportStatus.startsWith("Assurance-ready") ? "Approved for issue" : "Draft for approval";
  const preparedDate = new Date(report?.generatedAt || Date.now()).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const reportYear = state.period.match(/\b\d{4}\b/)?.[0] || "2025";
  const reportIdentity = report ? `v${report.version} · ${report.hash.slice(0, 16)}…` : "Snapshot not yet sealed";
  const scopeDescriptions = { 1: "Direct operations", 2: "Purchased energy · location-based", 3: "Value-chain emissions" };
  const scopeRows = [1, 2, 3].map((scope) => `<div class="report-scope-row"><span class="scope-dot scope-${scope}"></span><span><strong>Scope ${scope}</strong><small>${scopeDescriptions[scope]}</small></span><strong>${formatNumber(summary.scopes[scope] / 1000, 2)}</strong><span>${summary.total ? formatNumber(summary.scopes[scope] / summary.total * 100, 0) : 0}%</span></div>`).join("");
  const controlRows = checks.map((check) => `<div class="report-control-row"><span class="checklist-icon ${check.ok ? "badge-success" : "badge-warning"}">${check.ok ? "✓" : "!"}</span><span><strong>${escapeHtml(check.title)}</strong><small>${escapeHtml(check.helper)}</small></span><em>${check.ok ? "Complete" : "Open"}</em></div>`).join("");
  const pendingApprovals = state.activities.filter((item) => item.status === "ready");
  document.querySelector("#final-controls-title").textContent = pendingApprovals.length ? `${pendingApprovals.length} action${pendingApprovals.length === 1 ? "" : "s"} before locking` : "Ready for locking";
  document.querySelector("#report-final-controls").innerHTML = pendingApprovals.length ? pendingApprovals.map((item) => `<div class="final-control-item"><span>!</span><div><strong>Approve ${escapeHtml(item.description.toLowerCase())}</strong><small>Assigned to Data Reviewer</small></div></div>`).join("") : `<div class="final-control-item complete"><span>✓</span><div><strong>All approvals complete</strong><small>The inventory is ready to be sealed.</small></div></div>`;

  document.querySelector("#report-preview").innerHTML = `
    <div class="report-cover-brand"><span>d</span><div><strong>D-carbN Analytics</strong><small>Scope 1, 2 &amp; 3</small></div></div>
    <div class="report-cover-title"><p>Corporate greenhouse gas inventory</p><h2>Scope 1, 2 &amp; 3 Report</h2><strong>${escapeHtml(state.organisation)}</strong><span>1 January – 31 December ${escapeHtml(reportYear)}</span></div>
    <div class="report-cover-green"></div>
    <div class="report-cover-meta"><strong>${escapeHtml(coverStatus)}</strong><span>Prepared ${escapeHtml(preparedDate)}</span></div>`;

  document.querySelector("#report-detail-document").innerHTML = `<article class="report-document">
      <section class="report-section report-executive">
        <div class="report-section-heading"><div><p class="eyebrow">Executive carbon position</p><h2>Inventory at a glance</h2></div><span>${escapeHtml(reportIdentity)}</span></div>
        <p class="report-introduction">This governed inventory brings activity data, calculation methods, evidence, approvals and report lineage into one reviewable carbon position.</p>
        <div class="report-kpi-grid">
          <div class="report-kpi primary"><span>Total emissions</span><strong>${formatNumber(summary.total / 1000, 2)}</strong><small>tCO₂e</small></div>
          <div class="report-kpi"><span>Evidence coverage</span><strong>${evidenceCoverage}%</strong><small>${evidenceCount} of ${valid.length} results</small></div>
          <div class="report-kpi"><span>Approved records</span><strong>${summary.approved}</strong><small>${summary.ready} awaiting review</small></div>
          <div class="report-kpi"><span>Open controls</span><strong>${checks.filter((check) => !check.ok).length}</strong><small>${checks.every((check) => check.ok) ? "Ready to release" : "Resolve before release"}</small></div>
        </div>
      </section>

      <section class="report-section report-scope-section">
        <div><p class="eyebrow">Reported footprint</p><h2>Emissions by scope</h2><div class="report-donut" style="background:conic-gradient(var(--green) 0 ${p1}%, var(--gold) ${p1}% ${p1 + p2}%, var(--brand) ${p1 + p2}% 100%)"><span>${formatNumber(summary.total / 1000, 1)}<small>tCO₂e</small></span></div></div>
        <div class="report-scope-ledger">${scopeRows}<p>Scope mix: ${formatNumber(p1, 1)}% direct · ${formatNumber(p2, 1)}% energy · ${formatNumber(p3, 1)}% value chain.</p></div>
      </section>

      <section class="report-section report-detail-grid">
        <div><p class="eyebrow">Inventory basis</p><h2>Boundary and methodology</h2><dl class="report-definition-list"><div><dt>Organisation</dt><dd>${escapeHtml(state.organisation)}</dd></div><div><dt>Reporting period</dt><dd>${escapeHtml(state.period)}</dd></div><div><dt>Factor source</dt><dd>${escapeHtml(FACTOR_SOURCE)}</dd></div><div><dt>Factor pack</dt><dd>${escapeHtml(CORE.FACTOR_PACK.version)} · ${escapeHtml(CORE.FACTOR_PACK.year)}</dd></div><div><dt>Organisational boundary</dt><dd>${escapeHtml(state.profile.organisationalBoundary || "Open")}</dd></div><div><dt>Scope 2 basis</dt><dd>Location-based headline</dd></div><div><dt>Calculation unit</dt><dd>kgCO₂e before report rounding</dd></div></dl></div>
        <div><p class="eyebrow">Assurance controls</p><h2>Readiness and lineage</h2><div class="report-controls">${controlRows}</div></div>
      </section>

      <footer class="report-document-footer"><div><strong>D-carbN Analytics</strong><span>Local design-validation report · not an externally assured filing</span></div><div><span>Snapshot identity</span><strong>${escapeHtml(reportIdentity)}</strong></div></footer>
    </article>`;

  document.querySelector("#audit-count").textContent = `${state.audit.length} events`;
  document.querySelector("#audit-timeline").innerHTML = state.audit.map((event) => `<div class="timeline-item"><strong>${escapeHtml(event.action)}</strong><span>${new Date(event.at).toLocaleString("en-GB")} · ${escapeHtml(event.actor)}</span></div>`).join("");
}

function renderUploadPreview() {
  const panel = document.querySelector("#upload-preview-panel");
  const correctionGuidance = document.querySelector("#upload-correction-guidance");
  panel.classList.toggle("hidden", uploadRows.length === 0);
  if (!uploadRows.length) {
    correctionGuidance.classList.add("hidden");
    correctionGuidance.innerHTML = "";
    return;
  }
  const validCount = uploadRows.filter((item) => item.valid).length;
  document.querySelector("#upload-summary").textContent = `${validCount} valid · ${uploadRows.length - validCount} flagged`;
  document.querySelector("#upload-preview").innerHTML = uploadRows.map((item, index) => {
    if (uploadKind === "profile") {
      return `<tr><td>${index + 1}</td><td class="mono">PROFILE</td><td>${escapeHtml(item.values.organisation_name || "—")}</td><td>Organisation information</td><td>${escapeHtml(item.values.full_time_equivalent_employees || "—")} FTE · ${escapeHtml(item.values.headcount || "—")} people</td><td><span class="badge badge-${item.valid ? "success" : "danger"} upload-validation">${item.valid ? "Valid" : escapeHtml(item.errors.join(" · "))}</span></td></tr>`;
    }
    const method = METHOD_BY_ID.get(item.values.calculation_method_id);
    return `<tr><td>${index + 1}</td><td class="mono">${escapeHtml(item.values.source_record_id || "—")}</td><td>${escapeHtml(item.values.description || "—")}</td><td>${escapeHtml(method?.short || item.values.calculation_method_id || "—")}</td><td>${escapeHtml(item.values.activity_value || "—")} ${escapeHtml(item.values.activity_unit || "")}</td><td><span class="badge badge-${item.valid ? "success" : "danger"} upload-validation">${item.valid ? "Valid" : escapeHtml(item.errors.join(" · "))}</span></td></tr>`;
  }).join("");
  const correctionItems = [...new Set(uploadRows.filter((item) => !item.valid).flatMap((item) => item.errors))];
  correctionGuidance.classList.toggle("hidden", correctionItems.length === 0);
  correctionGuidance.innerHTML = correctionItems.length ? `<strong>Correct the flagged rows before continuing</strong><p>Edit the CSV, save it again as CSV UTF-8, then select and validate the corrected file.</p><ul>${correctionItems.map((error) => `<li>${escapeHtml(error)}</li>`).join("")}</ul>` : "";
  const acceptButton = document.querySelector("#accept-valid-rows");
  acceptButton.textContent = uploadKind === "profile" ? "Save organisation information" : "Add valid rows to inventory";
  acceptButton.disabled = validCount === 0 || validCount !== uploadRows.length;
}

function renderAll() {
  renderPilotStrip();
  renderDashboard();
  renderActivities();
  renderReview();
  renderResults();
  renderReports();
  renderUploadPreview();
  bindDynamicActions();
  applyRoleControls();
}

function bindDynamicActions() {
  document.querySelectorAll("[data-go]").forEach((button) => { button.onclick = () => navigate(button.dataset.go); });
  document.querySelectorAll("[data-delete]").forEach((button) => { button.onclick = () => removeActivity(button.dataset.delete); });
  document.querySelectorAll("[data-approve]").forEach((button) => { button.onclick = () => approveActivity(button.dataset.approve); });
  document.querySelectorAll("[data-return]").forEach((button) => { button.onclick = () => returnActivity(button.dataset.return); });
  document.querySelectorAll("[data-pilot-action]").forEach((button) => { button.onclick = () => performPilotAction(button.dataset.pilotAction); });
}

function navigate(view) {
  if (!canAccessView(view)) return showToast("This area is reserved for a different role or release stage.");
  document.querySelectorAll(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${view}`));
  document.querySelectorAll(".nav-link").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  document.querySelector("#sidebar").classList.remove("open");
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (view === "results") renderResults();
  if (view === "reports") renderReports();
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2800);
}

function removeActivity(id) {
  if (!contributorCanEdit()) return showToast("Customer records can only be changed before submission.");
  const item = state.activities.find((activity) => activity.id === id);
  if (!item || !confirm(`Remove “${item.description}” from this local demo?`)) return;
  state.activities = state.activities.filter((activity) => activity.id !== id);
  addAudit(`Activity removed: ${item.sourceRecordId}`);
  state.report = null;
  saveState();
  renderAll();
  showToast("Activity removed from the local inventory.");
}

function approveActivity(id) {
  const item = state.activities.find((activity) => activity.id === id);
  if (!item || item.status !== "ready" || !analystCanReview()) return showToast("Only the D-carbN Analyst can approve during analyst review.");
  item.status = "approved";
  addAudit(`Activity approved: ${item.sourceRecordId}`);
  state.report = null;
  saveState();
  renderAll();
  showToast("Activity approved.");
}

function returnActivity(id) {
  const item = state.activities.find((activity) => activity.id === id);
  if (!item || item.status !== "ready" || !analystCanReview()) return showToast("Only the D-carbN Analyst can return a submitted record.");
  item.status = "needs_attention";
  item.validation = "Returned by reviewer for clarification.";
  state.pilot.stage = "draft";
  addAudit(`Activity returned for clarification: ${item.sourceRecordId}`);
  state.report = null;
  saveState();
  renderAll();
  showToast("Activity returned for clarification.");
}

function approveAllReady() {
  if (!analystCanReview()) return showToast("Switch to the D-carbN Analyst during analyst review.");
  const ready = state.activities.filter((item) => item.status === "ready");
  if (!ready.length) return showToast("There are no ready records awaiting approval.");
  ready.forEach((item) => { item.status = "approved"; });
  addAudit(`${ready.length} ready activit${ready.length === 1 ? "y" : "ies"} approved`);
  state.report = null;
  saveState();
  renderAll();
  showToast(`${ready.length} records approved.`);
}

function parseCsv(csv) {
  const records = [];
  let row = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < csv.length; index += 1) {
    const character = csv[index];
    if (character === '"') {
      if (quoted && csv[index + 1] === '"') { value += '"'; index += 1; }
      else quoted = !quoted;
    } else if (character === "," && !quoted) { row.push(value.trim()); value = ""; }
    else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && csv[index + 1] === "\n") index += 1;
      row.push(value.trim()); value = "";
      if (row.some(Boolean)) records.push(row);
      row = [];
    } else value += character;
  }
  row.push(value.trim());
  if (row.some(Boolean)) records.push(row);
  if (quoted) throw new Error("The CSV contains an unclosed quoted value.");
  if (records.length < 2) throw new Error("The CSV must contain headings and at least one data row.");
  const [headers, ...rows] = records;
  if (new Set(headers).size !== headers.length) throw new Error("The CSV contains duplicate headings.");
  return rows.map((cells) => Object.fromEntries(headers.map((header, index) => [header.trim(), cells[index]?.trim() || ""])));
}

function positiveComponent(values, field, errors) {
  const raw = String(values[field] || "").trim();
  if (!raw) return null;
  const number = Number(raw);
  if (!Number.isFinite(number) || number <= 0) {
    errors.push(`${field} must be a positive number when supplied`);
    return null;
  }
  return number;
}

function normaliseActivityRow(input) {
  const values = { ...input };
  const errors = [];
  const method = METHOD_BY_ID.get(String(values.calculation_method_id || "").trim());
  let derivedValue = null;

  if (method?.unit === "passenger.km") {
    const distance = positiveComponent(values, "distance_km", errors);
    const passengers = positiveComponent(values, "passengers_or_rooms", errors);
    const journeys = positiveComponent(values, "journeys_or_nights", errors);
    const returnTrip = String(values.return_trip || "").trim().toLowerCase();
    if (returnTrip && !["yes", "no", "true", "false", "y", "n"].includes(returnTrip)) errors.push("return_trip must be Yes or No");
    if (distance !== null && passengers !== null && journeys !== null) {
      derivedValue = distance * passengers * journeys * (["yes", "true", "y"].includes(returnTrip) ? 2 : 1);
    }
  } else if (method?.unit === "tonne.km") {
    const distance = positiveComponent(values, "distance_km", errors);
    const payload = positiveComponent(values, "payload_tonnes", errors);
    const journeys = String(values.journeys_or_nights || "").trim()
      ? positiveComponent(values, "journeys_or_nights", errors)
      : 1;
    if (distance !== null && payload !== null && journeys !== null) derivedValue = distance * payload * journeys;
  } else if (method?.unit === "Room per night") {
    const rooms = positiveComponent(values, "passengers_or_rooms", errors);
    const nights = positiveComponent(values, "journeys_or_nights", errors);
    if (rooms !== null && nights !== null) derivedValue = rooms * nights;
  }

  const suppliedValue = String(values.activity_value || "").trim();
  if (!suppliedValue && derivedValue !== null) values.activity_value = String(derivedValue);
  if (suppliedValue && derivedValue !== null) {
    const suppliedNumber = Number(suppliedValue);
    const tolerance = Math.max(0.01, Math.abs(derivedValue) * 0.000001);
    if (Number.isFinite(suppliedNumber) && Math.abs(suppliedNumber - derivedValue) > tolerance) {
      errors.push(`Component total must equal ${formatNumber(derivedValue, 4)} ${method.unit}`);
    }
  }
  return { values, errors };
}

function validateRows(rows) {
  const existingIds = new Set(state.activities.map((item) => item.sourceRecordId.toLocaleUpperCase("en-GB")));
  const incomingIds = new Set();
  return rows.map((input) => {
    const normalised = normaliseActivityRow(input);
    const values = normalised.values;
    const errors = [...normalised.errors];
    const id = String(values.source_record_id || "").trim();
    const idKey = id.toLocaleUpperCase("en-GB");
    const methodId = String(values.calculation_method_id || "").trim();
    const method = METHOD_BY_ID.get(methodId);
    const activityValue = String(values.activity_value || "").trim();
    const number = Number(activityValue);
    if (!id) errors.push("Add a unique source_record_id, for example NEG-GAS-001");
    else if (existingIds.has(idKey)) errors.push(`Source ID ${id} already exists in this pilot session; correct the ID or remove the duplicate row`);
    else if (incomingIds.has(idKey)) errors.push(`Source ID ${id} is repeated in this file; keep one row or assign distinct IDs`);
    else incomingIds.add(idKey);
    const activityDate = String(values.activity_date || "").trim();
    if (!CORE.isValidIsoDate(activityDate)) errors.push("Enter a real calendar activity_date as YYYY-MM-DD (for example, 2025-02-28; 2025-02-30 is invalid)");
    else if (state.profile?.reportingPeriodStart && state.profile?.reportingPeriodEnd && (activityDate < state.profile.reportingPeriodStart || activityDate > state.profile.reportingPeriodEnd)) errors.push(`activity_date must fall within ${state.profile.reportingPeriodStart} to ${state.profile.reportingPeriodEnd}`);
    if (!String(values.description || "").trim()) errors.push("Add a description that identifies the site, supplier or journey");
    if (!method) errors.push("Use a 2025 calculation_method_id supplied in a downloaded D-carbN template");
    else {
      try { CORE.resolveMethod(method.id, 2025); } catch (error) { errors.push(error.message); }
    }
    if (!activityValue || !Number.isFinite(number) || number <= 0) errors.push("activity_value must be a positive number or derivable from completed component fields");
    if (method && String(values.activity_unit || "").trim() !== method.unit) errors.push(`Change activity_unit to the exact required unit: ${method.unit}`);
    if (!String(values.evidence_reference || "").trim()) errors.push("Add an evidence_reference such as an invoice, meter or travel-ledger ID");
    if (method?.id === "scope1.refrigerant.r410a.service_top_up.kg.uk_2025.v1" && !String(values.equipment_reference || "").trim()) errors.push("Add equipment_reference for the serviced refrigerant asset");
    if (method?.directResult) {
      const supplierFields = ["supplier_name", "supplier_methodology", "supplier_methodology_version", "boundary_description", "assurance_status"];
      const missingSupplierFields = supplierFields.filter((field) => !String(values[field] || "").trim());
      if (missingSupplierFields.length) errors.push(`Complete supplier lineage: ${missingSupplierFields.join(", ")}`);
    }
    return { values, errors, valid: errors.length === 0 };
  });
}

function validateProfileRows(rows) {
  return rows.map((values) => {
    const errors = [];
    const start = String(values.reporting_period_start || "").trim();
    const end = String(values.reporting_period_end || "").trim();
    const fteRaw = String(values.full_time_equivalent_employees || "").trim();
    const headcountRaw = String(values.headcount || "").trim();
    const revenueRaw = String(values.revenue_gbp || "").trim();
    const fte = Number(fteRaw);
    const headcount = Number(headcountRaw);
    const revenue = Number(revenueRaw);
    if (!String(values.organisation_name || "").trim()) errors.push("Add the legal or reporting organisation name");
    if (!CORE.isValidIsoDate(start)) errors.push("Enter a real reporting_period_start as YYYY-MM-DD");
    if (!CORE.isValidIsoDate(end)) errors.push("Enter a real reporting_period_end as YYYY-MM-DD");
    if (start && end && !Number.isNaN(Date.parse(start)) && !Number.isNaN(Date.parse(end)) && Date.parse(end) < Date.parse(start)) errors.push("reporting_period_end must be on or after the start date");
    if (start !== "2025-01-01" || end !== "2025-12-31") errors.push("This governed pilot is fixed to Calendar year 2025; use 2025-01-01 to 2025-12-31");
    if (!fteRaw || !Number.isFinite(fte) || fte < 0) errors.push("Enter full_time_equivalent_employees as zero or a positive number");
    if (!headcountRaw || !Number.isFinite(headcount) || headcount < 0) errors.push("Enter headcount as zero or a positive number");
    if (Number.isFinite(fte) && Number.isFinite(headcount) && fte > headcount) errors.push("FTE cannot exceed headcount; correct one of these values");
    if (!revenueRaw || !Number.isFinite(revenue) || revenue < 0) errors.push("Enter revenue_gbp as zero or a positive number without currency symbols");
    if (!String(values.completed_by || "").trim()) errors.push("Add the person or team that completed this information");
    if (!String(values.evidence_reference || "").trim()) errors.push("Add an evidence_reference for the organisation information");
    if (!String(values.organisational_boundary || "").trim()) errors.push("Define organisational_boundary, for example Operational control");
    if (!String(values.reporting_scopes || "").trim()) errors.push("Confirm reporting_scopes");
    if (!String(values.responsible_contributor_role || "").trim()) errors.push("Add responsible_contributor_role");
    if (!["yes", "true"].includes(String(values.evidence_completeness_confirmed || "").trim().toLowerCase())) errors.push("Set evidence_completeness_confirmed to Yes after checking the evidence register");
    return { values, errors, valid: errors.length === 0 };
  });
}

function importedActivity(values, batchReference) {
  const method = METHOD_BY_ID.get(String(values.calculation_method_id).trim());
  const quantity = Number(values.activity_value);
  return {
    id: uid("activity"), sourceRecordId: values.source_record_id.trim(), date: values.activity_date,
    description: values.description.trim(), methodId: method.id, quantity, unit: method.unit,
    factor: method.factor, kgCo2e: method.directResult ? quantity : quantity * method.factor,
    factorYear: method.factorYear, factorVersion: method.factorVersion, factorSource: method.factorSource,
    evidence: String(values.evidence_reference).trim(), status: "ready",
    lineage: {
      ...(values.equipment_reference ? { equipment_reference: String(values.equipment_reference).trim(), service_performed: true } : {}),
      ...(method.directResult ? {
        supplier_name: String(values.supplier_name).trim(),
        supplier_methodology: String(values.supplier_methodology).trim(),
        supplier_methodology_version: String(values.supplier_methodology_version).trim(),
        boundary_description: String(values.boundary_description).trim(),
        assurance_status: String(values.assurance_status).trim(),
      } : {}),
      source_context: Object.fromEntries([
        "template_type", "site_location", "source_type", "vehicle_or_transport_type", "fuel_or_energy_type",
        "owned_or_leased", "origin", "destination", "return_trip", "passengers_or_rooms", "journeys_or_nights",
        "distance_km", "payload_tonnes", "annual_spend_gbp", "supplier_data_attached", "notes",
      ].filter((field) => String(values[field] || "").trim()).map((field) => [field, String(values[field]).trim()])),
    },
    validation: "Exact governed method and compatible unit confirmed.", source: batchReference,
    createdAt: new Date().toISOString(),
  };
}

async function validateSelectedFile() {
  if (!contributorCanEdit()) return showToast("This submission is read-only at the current pilot stage.");
  if (!selectedFile) return;
  if (!document.querySelector("#complete-attestation").checked || !document.querySelector("#double-count-attestation").checked) {
    return showToast("Confirm completeness and double-counting checks before validation.");
  }
  try {
    const text = await selectedFile.text();
    const data = selectedFile.name.toLowerCase().endsWith(".json") ? JSON.parse(text) : parseCsv(text);
    const rows = Array.isArray(data) ? data : data.records;
    if (!Array.isArray(rows) || !rows.length) throw new Error("No activity rows were found.");
    const profileRows = rows.filter((row) => String(row.template_type || "").trim() === "organisation_information");
    if (profileRows.length && profileRows.length !== rows.length) throw new Error("Organisation information and activity rows must be uploaded as separate CSV files.");
    if (profileRows.length > 1) throw new Error("The organisation information CSV must contain exactly one data row.");
    uploadKind = profileRows.length === 1 ? "profile" : "activity";
    uploadRows = uploadKind === "profile" ? validateProfileRows(rows) : validateRows(rows);
    state.intake.confirmations = { complete: true, duplicates: true };
    state.intake.unresolvedRecords = uploadRows.filter((row) => !row.valid).map((row, index) => ({ row: index + 1, sourceRecordId: String(row.values.source_record_id || "PROFILE"), errors: row.errors }));
    state.intake.duplicateChecksPassed = !uploadRows.some((row) => row.errors.some((error) => error.toLowerCase().includes("duplicate") || error.toLowerCase().includes("repeated") || error.toLowerCase().includes("already exists")));
    saveState();
    renderUploadPreview();
    showToast(`${uploadRows.filter((row) => row.valid).length} valid rows found.`);
  } catch (error) {
    uploadRows = [];
    uploadKind = "activity";
    renderUploadPreview();
    showToast(error instanceof Error ? error.message : "The file could not be read.");
  }
}

function clearUploadSelection() {
  uploadRows = [];
  uploadKind = "activity";
  selectedFile = null;
  const input = document.querySelector("#file-input");
  const dropZone = document.querySelector("#drop-zone");
  input.value = "";
  document.querySelector("#validate-upload").disabled = true;
  dropZone.querySelector("strong").textContent = "Drop a completed D-carbN CSV here";
  dropZone.querySelector("small").textContent = "or choose a CSV or JSON file from this computer";
  renderUploadPreview();
}

function acceptValidRows() {
  if (!contributorCanEdit()) return showToast("This submission is read-only at the current pilot stage.");
  const validRows = uploadRows.filter((item) => item.valid);
  if (!validRows.length) return;
  if (validRows.length !== uploadRows.length) return showToast("Nothing was imported. Correct every flagged row and re-upload the complete file.");
  const batchReference = document.querySelector("#batch-reference").value.trim() || `LOCAL-${Date.now()}`;
  if (uploadKind === "profile") {
    const values = validRows[0].values;
    const start = String(values.reporting_period_start).trim();
    const end = String(values.reporting_period_end).trim();
    const startDate = new Date(`${start}T00:00:00`);
    const endDate = new Date(`${end}T00:00:00`);
    const calendarYear = start.slice(5) === "01-01" && end.slice(5) === "12-31" && startDate.getFullYear() === endDate.getFullYear();
    state.organisation = String(values.organisation_name).trim();
    state.period = calendarYear ? `Calendar year ${startDate.getFullYear()}` : `${start} to ${end}`;
    state.profile = {
      reportingPeriodStart: start,
      reportingPeriodEnd: end,
      fullTimeEquivalentEmployees: Number(values.full_time_equivalent_employees),
      headcount: Number(values.headcount),
      revenueGbp: Number(values.revenue_gbp),
      completedBy: String(values.completed_by).trim(),
      evidenceReference: String(values.evidence_reference).trim(),
      organisationalBoundary: String(values.organisational_boundary).trim(),
      reportingScopes: String(values.reporting_scopes).trim(),
      responsibleContributorRole: String(values.responsible_contributor_role).trim(),
      evidenceCompletenessConfirmed: ["yes", "true"].includes(String(values.evidence_completeness_confirmed).trim().toLowerCase()),
      notes: String(values.notes || "").trim(),
    };
    state.intake.organisationValidated = true;
    state.intake.unresolvedRecords = [];
    state.intake.duplicateChecksPassed = true;
    state.batches.unshift({ id: uid("batch"), reference: batchReference, importedAt: new Date().toISOString(), rows: 1, kind: "organisation_information" });
    addAudit(`Organisation information imported from batch ${batchReference}`);
    state.report = null;
    saveState();
    clearUploadSelection();
    renderAll();
    navigate("dashboard");
    return showToast("Organisation information passed integrity checks and was saved.");
  }
  state.activities.push(...validRows.map((item) => importedActivity(item.values, batchReference)));
  const importedScopes = new Set(validRows.map((item) => METHOD_BY_ID.get(String(item.values.calculation_method_id).trim()).scope));
  importedScopes.forEach((scope) => { state.intake.validatedScopes[scope] = true; });
  state.intake.unresolvedRecords = [];
  state.intake.duplicateChecksPassed = true;
  state.batches.unshift({ id: uid("batch"), reference: batchReference, importedAt: new Date().toISOString(), rows: validRows.length });
  addAudit(`Batch ${batchReference} imported with ${validRows.length} valid row(s)`);
  state.report = null;
  saveState();
  clearUploadSelection();
  renderAll();
  navigate("review");
  showToast("Valid rows added and queued for review.");
}

function sampleUploadRows() {
  return validateRows([
    { source_record_id: "NEG-UPLOAD-GAS-002", activity_date: "2025-07-31", description: "July natural gas", calculation_method_id: "scope1.stationary_natural_gas.gross_cv.kwh.uk_2025.v1", activity_value: "12500", activity_unit: "kWh (Gross CV)", evidence_reference: "NEG-GAS-JUL-2025" },
    { source_record_id: "NEG-UPLOAD-RAIL-002", activity_date: "2025-07-31", description: "July national rail travel", calculation_method_id: "scope3.category6.national_rail.passenger_km.uk_2025.v1", activity_value: "880", activity_unit: "passenger.km", evidence_reference: "NEG-TRAVEL-JUL-2025" },
    { source_record_id: "NEG-UPLOAD-WASTE-002", activity_date: "2025-07-31", description: "Waste with ambiguous treatment", calculation_method_id: "scope3.category5.commercial_waste.closed_loop.tonnes.uk_2025.v1", activity_value: "3.2", activity_unit: "kg", evidence_reference: "NEG-WASTE-JUL-2025" },
  ]);
}

function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = name; document.body.append(anchor); anchor.click(); anchor.remove();
  URL.revokeObjectURL(url);
}

function templateCsv(template) {
  const headings = template.headings || ACTIVITY_TEMPLATE_HEADINGS;
  const rows = template.rows.map((row) => headings.map((heading) => row[heading] ?? ""));
  return [headings, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n") + "\n";
}

function downloadTemplate(templateId) {
  const template = TEMPLATE_LIBRARY[templateId];
  if (!template) return showToast("That template is not available.");
  download(template.filename, templateCsv(template), "text/csv;charset=utf-8");
  showToast(`${template.label} CSV downloaded.`);
}

function downloadScopeTemplate(scope) {
  const scopeNumber = Number(scope);
  const rows = METHODS
    .filter((method) => method.scope === scopeNumber && !method.unavailableReason)
    .map((method) => templateRow(method.id, `Scope ${scopeNumber}: ${method.label}`));
  if (!rows.length) return showToast("No governed methods are configured for that scope.");
  download(`dcarbn-new-era-scope-${scopeNumber}-2025.csv`, templateCsv({ rows }), "text/csv;charset=utf-8");
  showToast(`Scope ${scopeNumber} CSV downloaded with ${rows.length} supported data categories.`);
}

function downloadCompleteTemplatePack() {
  const rows = Object.entries(TEMPLATE_LIBRARY)
    .filter(([templateId]) => templateId !== "organisation")
    .flatMap(([, template]) => template.rows);
  download("dcarbn-new-era-complete-activity-template.csv", templateCsv({ rows }), "text/csv;charset=utf-8");
  showToast("Complete calculation-ready activity pack downloaded. Organisation information is a separate CSV.");
}

function exportResults() {
  if (currentRole() === "contributor" && state.pilot.stage !== "locked") return showToast("Calculation exports are released only after D-carbN approval.");
  const headings = ["source_record_id", "activity_date", "description", "scope", "scope_3_category", "calculation_method_id", "activity_value", "activity_unit", "factor", "factor_year", "factor_version", "factor_source", "kg_co2e", "review_status", "evidence_reference"];
  const rows = state.activities.map((item) => {
    const method = methodFor(item);
    return [item.sourceRecordId, item.date, item.description, method.scope, method.category || "", method.id, item.quantity, item.unit, item.factor ?? "supplier_reported", item.factorYear, item.factorVersion, item.factorSource, item.kgCo2e, item.status, item.evidence];
  });
  download("new-era-group-calculation-results.csv", [headings, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n"), "text/csv;charset=utf-8");
  showToast("Calculation results exported.");
}

function stableReportPayload() {
  const summary = totals();
  return {
    organisation: state.organisation,
    reporting_period: state.period,
    organisation_profile: state.profile,
    factor_pack: CORE.FACTOR_PACK,
    totals_kg_co2e: { scope_1: summary.scopes[1], scope_2: summary.scopes[2], scope_3: summary.scopes[3], total: summary.total },
    activities: [...state.activities].sort((a, b) => a.sourceRecordId.localeCompare(b.sourceRecordId)).map((item) => ({ source_record_id: item.sourceRecordId, activity_date: item.date, description: item.description, calculation_method_id: item.methodId, activity_value: item.quantity, activity_unit: item.unit, factor: item.factor, factor_year: item.factorYear, factor_version: item.factorVersion, factor_source: item.factorSource, kg_co2e: item.kgCo2e, evidence_reference: item.evidence, lineage: item.lineage || {}, review_status: item.status })),
  };
}

async function sha256(text) {
  return CORE.sha256(text);
}

async function generateReport() {
  if (!["analyst", "approver"].includes(currentRole()) || state.pilot.stage === "locked") return showToast("Report snapshots are controlled by D-carbN before release.");
  const checks = reportChecks();
  const payload = stableReportPayload();
  const serialised = JSON.stringify(payload);
  const previousVersion = state.report?.version || 0;
  state.report = {
    version: previousVersion + 1,
    generatedAt: new Date().toISOString(),
    status: checks.every((check) => check.ok) ? "Assurance-ready prototype" : "Draft — controls outstanding",
    hash: await sha256(serialised),
    payload,
  };
  addAudit(`Report snapshot v${state.report.version} generated (${state.report.status})`);
  saveState();
  renderAll();
  showToast("Report snapshot generated with a deterministic hash.");
}

function exportWorkspace() {
  if (currentRole() !== "analyst") return showToast("The controlled workspace export is restricted to the D-carbN Analyst.");
  exportPilotSession();
}

async function exportPilotSession() {
  if (!sessionPassphrase) return showToast("Unlock the local pilot session before exporting it.");
  try {
    const envelope = await CORE.encryptPayload(CORE.createSessionBundle(structuredClone(state)), sessionPassphrase, "portable-session-export");
    download("new-era-group-2025-encrypted-pilot-session.json", JSON.stringify(envelope, null, 2), "application/json");
    showToast("Encrypted pilot session exported. Keep the passphrase separately.");
  } catch (error) {
    showToast(error.message || "The encrypted export could not be created.");
  }
}

async function restorePilotSession(file) {
  const passphrase = prompt("Enter the passphrase used to encrypt this exported pilot session. It will not be stored.");
  if (!passphrase) return;
  try {
    const envelope = JSON.parse(await file.text());
    const bundle = await CORE.decryptPayload(envelope, passphrase, "portable-session-export");
    state = normalisePilotState(CORE.validateSessionBundle(bundle));
    addAudit("Encrypted pilot session restored and integrity checksum verified", "Local pilot");
    saveState();
    renderAll();
    navigate("dashboard");
    showToast("Encrypted session restored with calculations, lineage, audit and report state intact.");
  } catch (error) {
    showToast(error.message || "The encrypted session could not be restored.");
  }
}

function emptyPilotState() {
  const cleared = defaultState();
  cleared.organisation = "Local pilot";
  cleared.activities = [];
  cleared.batches = [];
  cleared.profile = {
    reportingPeriodStart: "2025-01-01", reportingPeriodEnd: "2025-12-31",
    fullTimeEquivalentEmployees: null, headcount: null, revenueGbp: null,
    completedBy: "", evidenceReference: "", notes: "",
    organisationalBoundary: "", reportingScopes: "", responsibleContributorRole: "", evidenceCompletenessConfirmed: false,
  };
  cleared.audit = [{ id: uid("audit"), at: new Date().toISOString(), action: "All local customer data cleared", actor: "Local pilot" }];
  cleared.report = null;
  cleared.intake = { organisationValidated: false, validatedScopes: { 1: false, 2: false, 3: false }, unresolvedRecords: [], duplicateChecksPassed: false, confirmations: { complete: false, duplicates: false } };
  cleared.pilot = { stage: "draft", activeRole: "contributor", submittedAt: null, reviewedAt: null, lockedAt: null };
  return cleared;
}

function clearLocalCustomerData() {
  const confirmed = confirm("Clear all uploaded activities, calculations, organisation details, audit history and reports stored by this pilot in this browser? This cannot be undone unless you exported the session first.");
  if (!confirmed) return;
  CORE.clearPilotStorage(localStorage, [STORAGE_KEY, LEGACY_STORAGE_KEY]);
  state = emptyPilotState();
  sessionPassphrase = "";
  clearUploadSelection();
  showSecurityGate("setup", "All local customer data and encrypted storage were removed. Create a new passphrase to begin an empty 2025 pilot session.");
}

function showSecurityGate(mode, message = "") {
  const gate = document.querySelector("#security-gate");
  document.querySelector(".app-frame").inert = true;
  gate.dataset.mode = mode;
  gate.classList.remove("hidden");
  document.querySelector("#security-title").textContent = mode === "unlock" ? "Unlock local pilot session" : "Protect this pilot session";
  document.querySelector("#security-message").textContent = message || (mode === "unlock" ? "Enter the passphrase for the encrypted data stored in this browser." : "Create a passphrase to encrypt all pilot data held on this computer.");
  document.querySelector("#security-confirm-label").classList.toggle("hidden", mode === "unlock");
  document.querySelector("#security-passphrase-confirm").required = mode !== "unlock";
  document.querySelector("#security-submit").textContent = mode === "unlock" ? "Unlock session" : "Create encrypted session";
  document.querySelector("#security-passphrase").value = "";
  document.querySelector("#security-passphrase-confirm").value = "";
  document.querySelector("#security-passphrase").focus();
}

function lockLocalSession() {
  state = emptyPilotState();
  sessionPassphrase = "";
  renderAll();
  showSecurityGate("unlock", "The encrypted pilot locked. Enter its passphrase to continue.");
}

async function handleSecuritySubmit(event) {
  event.preventDefault();
  const mode = document.querySelector("#security-gate").dataset.mode;
  const passphrase = document.querySelector("#security-passphrase").value;
  const confirmation = document.querySelector("#security-passphrase-confirm").value;
  try {
    if (passphrase.length < 12) throw new Error("Use a passphrase of at least 12 characters.");
    if (mode === "setup") {
      if (passphrase !== confirmation) throw new Error("The passphrase confirmation does not match.");
      sessionPassphrase = passphrase;
      state = normalisePilotState(pendingInitialState || emptyPilotState());
      pendingInitialState = null;
      localStorage.removeItem(LEGACY_STORAGE_KEY);
      saveState();
    } else {
      const envelope = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      const bundle = await CORE.decryptPayload(envelope, passphrase, "persistent-session");
      state = normalisePilotState(CORE.validateSessionBundle(bundle));
      sessionPassphrase = passphrase;
    }
    lastActivityAt = Date.now();
    document.querySelector("#security-passphrase").value = "";
    document.querySelector("#security-passphrase-confirm").value = "";
    document.querySelector(".app-frame").inert = false;
    document.querySelector("#security-gate").classList.add("hidden");
    renderAll();
    navigate("dashboard");
  } catch (error) {
    document.querySelector("#security-message").textContent = error.message || "The encrypted session could not be opened.";
  }
}

function initialiseSecurePilot() {
  const encrypted = localStorage.getItem(STORAGE_KEY);
  if (encrypted) return showSecurityGate("unlock");
  const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
  if (legacy) {
    try { pendingInitialState = normalisePilotState(JSON.parse(legacy)); } catch (_error) { pendingInitialState = emptyPilotState(); }
    return showSecurityGate("setup", "A previous unencrypted local session was found. Create a passphrase to migrate it into encrypted storage; the old copy will then be removed.");
  }
  pendingInitialState = defaultState();
  showSecurityGate("setup");
}

function configureActivityForm() {
  const select = document.querySelector("#method-select");
  select.innerHTML = METHODS.map((method) => `<option value="${escapeHtml(method.id)}">Scope ${method.scope}${method.category ? ` · Cat. ${method.category}` : ""} · ${escapeHtml(method.label)}</option>`).join("");
  const syncUnit = () => {
    const method = METHOD_BY_ID.get(select.value);
    document.querySelector("#method-unit").value = method?.unit || "";
    const equipmentFields = document.querySelector("#equipment-lineage-fields");
    const supplierFields = document.querySelector("#supplier-lineage-fields");
    const isRefrigerant = method?.id === "scope1.refrigerant.r410a.service_top_up.kg.uk_2025.v1";
    equipmentFields.classList.toggle("hidden", !isRefrigerant);
    supplierFields.classList.toggle("hidden", !method?.directResult);
    equipmentFields.querySelectorAll("input").forEach((input) => { input.required = isRefrigerant; });
    supplierFields.querySelectorAll("input, select").forEach((input) => { input.required = Boolean(method?.directResult); });
  };
  select.onchange = syncUnit;
  syncUnit();
}

function submitActivity(event) {
  event.preventDefault();
  if (!contributorCanEdit()) return showToast("Customer records can only be added before submission.");
  const form = new FormData(event.currentTarget);
  const method = METHOD_BY_ID.get(form.get("calculation_method_id"));
  const quantity = Number(form.get("activity_value"));
  if (!method || !Number.isFinite(quantity) || quantity <= 0) return showToast("Enter a positive governed activity value.");
  const lineage = {};
  if (method.id === "scope1.refrigerant.r410a.service_top_up.kg.uk_2025.v1") {
    lineage.equipment_reference = String(form.get("equipment_reference")).trim();
    lineage.service_performed = true;
  }
  if (method.directResult) {
    lineage.supplier_name = String(form.get("supplier_name")).trim();
    lineage.supplier_methodology = String(form.get("supplier_methodology")).trim();
    lineage.supplier_methodology_version = String(form.get("supplier_methodology_version")).trim();
    lineage.boundary_description = String(form.get("boundary_description")).trim();
    lineage.assurance_status = String(form.get("assurance_status")).trim();
  }
  const sourceRecordId = `NEG-MANUAL-${String(state.activities.length + 1).padStart(3, "0")}`;
  state.activities.push({
    id: uid("activity"), sourceRecordId, date: form.get("activity_date"), description: String(form.get("description")).trim(),
    methodId: method.id, quantity, unit: method.unit, factor: method.factor,
    factorYear: method.factorYear, factorVersion: method.factorVersion, factorSource: method.factorSource,
    kgCo2e: method.directResult ? quantity : quantity * method.factor,
    evidence: String(form.get("evidence_reference")).trim(), lineage, status: "ready",
    validation: "Exact governed method and compatible unit confirmed.", source: "Manual local entry", createdAt: new Date().toISOString(),
  });
  addAudit(`Manual activity added: ${sourceRecordId}`);
  state.report = null;
  saveState();
  event.currentTarget.reset();
  document.querySelector("#activity-form-panel").classList.add("hidden");
  configureActivityForm();
  renderAll();
  showToast("Activity added and queued for review.");
}

function resetDemo() {
  if (!confirm("Reset the local New Era Group demo and discard browser-only changes?")) return;
  state = defaultState();
  uploadRows = [];
  uploadKind = "activity";
  selectedFile = null;
  saveState();
  renderAll();
  navigate("dashboard");
  showToast("Demo restored to its original sample state.");
}

function setReportDetailVisible(visible) {
  const detail = document.querySelector("#report-detail");
  detail.classList.toggle("hidden", !visible);
  if (visible) detail.scrollIntoView({ behavior: "smooth", block: "start" });
}

function changePilotRole(role) {
  if (!ROLE_DEFINITIONS[role]) return;
  state.pilot.activeRole = role;
  saveState();
  const activeView = document.querySelector(".view.active")?.id.replace("view-", "") || "dashboard";
  renderAll();
  if (!canAccessView(activeView)) navigate("dashboard");
  showToast(`Prototype switched to ${ROLE_DEFINITIONS[role].label}.`);
}

async function performPilotAction(action) {
  const summary = totals();
  if (action === "submit") {
    if (!contributorCanEdit()) return showToast("Only the customer contributor can submit the draft inventory.");
    const blockers = CORE.submissionBlockers(state);
    if (blockers.length || summary.attention > 0) return showToast(blockers[0] || "Resolve validation issues before submitting to D-carbN.");
    state.pilot.stage = "analyst_review";
    state.pilot.submittedAt = new Date().toISOString();
    state.pilot.activeRole = "analyst";
    state.report = null;
    addAudit("Customer inventory submitted to D-carbN for analyst review", "New Era Contributor");
    saveState();
    renderAll();
    navigate("review");
    return showToast("Submission received. Switched to the D-carbN Analyst view for this demonstration.");
  }
  if (action === "review") {
    if (!analystCanReview()) return showToast("Only the D-carbN Analyst can complete this stage.");
    if (summary.ready > 0 || summary.attention > 0) return showToast("Every submitted activity needs a completed analyst decision.");
    state.pilot.stage = "ready_for_approval";
    state.pilot.reviewedAt = new Date().toISOString();
    state.pilot.activeRole = "approver";
    addAudit("Analyst review completed and inventory sent for final approval", "D-carbN Analyst");
    saveState();
    renderAll();
    navigate("reports");
    return showToast("Analyst review complete. Switched to the D-carbN Approver view.");
  }
  if (action === "lock") {
    if (currentRole() !== "approver" || state.pilot.stage !== "ready_for_approval") return showToast("Only the D-carbN Approver can lock this report.");
    const blockers = CORE.reportLockBlockers(state);
    if (blockers.length) return showToast(`Report cannot be locked: ${blockers[0]}`);
    const openControl = reportChecks().find((check) => !check.ok);
    if (openControl) return showToast(`Report cannot be locked: ${openControl.title} — ${openControl.helper}`);
    const payload = stableReportPayload();
    const previousVersion = state.report?.version || 0;
    state.report = { version: previousVersion + 1, generatedAt: new Date().toISOString(), status: "Locked customer release", hash: await sha256(JSON.stringify(payload)), payload };
    state.pilot.stage = "locked";
    state.pilot.lockedAt = state.report.generatedAt;
    addAudit(`Report v${state.report.version} locked and released to New Era Group`, "D-carbN Approver");
    saveState();
    renderAll();
    navigate("reports");
    return showToast("The immutable customer report is locked and released.");
  }
}

function attachEvents() {
  document.querySelectorAll(".nav-link").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.view)));
  document.querySelector("#mobile-menu").addEventListener("click", () => document.querySelector("#sidebar").classList.toggle("open"));
  document.querySelector("#reset-demo").addEventListener("click", resetDemo);
  document.querySelector("#role-select").addEventListener("change", (event) => changePilotRole(event.target.value));
  document.querySelector("#download-template").addEventListener("click", downloadCompleteTemplatePack);
  document.querySelectorAll("[data-template-download]").forEach((button) => {
    button.addEventListener("click", () => downloadTemplate(button.dataset.templateDownload));
  });
  document.querySelectorAll("[data-scope-download]").forEach((button) => {
    button.addEventListener("click", () => downloadScopeTemplate(button.dataset.scopeDownload));
  });
  document.querySelector("#export-pilot-session").addEventListener("click", exportPilotSession);
  document.querySelector("#restore-pilot-session").addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (file) restorePilotSession(file);
    event.target.value = "";
  });
  document.querySelector("#lock-local-session").addEventListener("click", lockLocalSession);
  document.querySelector("#clear-local-customer-data").addEventListener("click", clearLocalCustomerData);
  document.querySelector("#validate-upload").addEventListener("click", validateSelectedFile);
  document.querySelector("#load-sample").addEventListener("click", () => { uploadRows = sampleUploadRows(); renderUploadPreview(); showToast("Sample rows loaded: two valid and one intentionally flagged."); });
  document.querySelector("#accept-valid-rows").addEventListener("click", acceptValidRows);
  document.querySelector("#clear-upload").addEventListener("click", clearUploadSelection);
  document.querySelector("#approve-all-ready").addEventListener("click", approveAllReady);
  document.querySelector("#export-results").addEventListener("click", exportResults);
  document.querySelector("#export-workspace").addEventListener("click", exportWorkspace);
  document.querySelector("#generate-report").addEventListener("click", generateReport);
  document.querySelector("#print-report").addEventListener("click", () => window.print());
  document.querySelector("#inspect-output").addEventListener("click", () => setReportDetailVisible(true));
  document.querySelector("#close-output").addEventListener("click", () => setReportDetailVisible(false));
  document.querySelector("#activity-form").addEventListener("submit", submitActivity);
  document.querySelector("#open-activity-form").addEventListener("click", () => document.querySelector("#activity-form-panel").classList.remove("hidden"));
  ["#close-activity-form", "#cancel-activity-form"].forEach((selector) => document.querySelector(selector).addEventListener("click", () => document.querySelector("#activity-form-panel").classList.add("hidden")));
  ["#activity-search", "#scope-filter", "#status-filter"].forEach((selector) => document.querySelector(selector).addEventListener("input", () => { renderActivities(); bindDynamicActions(); }));

  const input = document.querySelector("#file-input");
  const dropZone = document.querySelector("#drop-zone");
  input.addEventListener("change", () => {
    selectedFile = input.files[0] || null;
    document.querySelector("#validate-upload").disabled = !selectedFile;
    if (selectedFile) { dropZone.querySelector("strong").textContent = selectedFile.name; dropZone.querySelector("small").textContent = `${formatNumber(selectedFile.size / 1024, 1)} KB selected`; }
  });
  ["dragenter", "dragover"].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.remove("dragging"); }));
  dropZone.addEventListener("drop", (event) => {
    selectedFile = event.dataTransfer.files[0] || null;
    document.querySelector("#validate-upload").disabled = !selectedFile;
    if (selectedFile) { dropZone.querySelector("strong").textContent = selectedFile.name; dropZone.querySelector("small").textContent = `${formatNumber(selectedFile.size / 1024, 1)} KB selected`; }
  });
}

configureActivityForm();
attachEvents();
document.querySelector("#security-form").addEventListener("submit", handleSecuritySubmit);
["pointerdown", "keydown", "touchstart"].forEach((name) => document.addEventListener(name, () => { if (sessionPassphrase) lastActivityAt = Date.now(); }, { passive: true }));
setInterval(() => {
  if (sessionPassphrase && Date.now() - lastActivityAt >= 15 * 60 * 1000) lockLocalSession();
}, 30000);
initialiseSecurePilot();
