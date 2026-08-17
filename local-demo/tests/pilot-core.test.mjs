import assert from "node:assert/strict";
await import("../pilot-core.js");
const core = globalThis.DCARBN_PILOT_CORE;

assert.equal(core.FACTOR_PACK.year, 2025);
assert.equal(core.FACTOR_PACK.version, "2025.1");
assert.equal(core.METHODS.length, 22);
assert.ok(core.METHODS.every((method) => method.factorYear === 2025 && method.factorVersion && method.factorSource));

const gas = core.resolveMethod("scope1.stationary_natural_gas.gross_cv.kwh.uk_2025.v1", 2025);
const electricity = core.resolveMethod("scope2.location_electricity.kwh.uk_2025.v1", 2025);
const rail = core.resolveMethod("scope3.category6.national_rail.passenger_km.uk_2025.v1", 2025);
assert.ok(Math.abs(10000 * gas.factor - 1829.6) < 1e-9);
assert.equal(50000 * electricity.factor, 8850);
assert.equal(1000 * rail.factor, 35.46);
assert.throws(() => core.resolveMethod(gas.id, 2024), /factor year 2025/);
assert.throws(() => core.resolveMethod("scope3.category5.commercial_waste.closed_loop.tonnes.uk_2025.v1", 2025), /does not publish a numeric/);
assert.throws(() => core.resolveMethod("unknown", 2025), /Unsupported/);

assert.equal(core.isValidIsoDate("2025-02-28"), true);
assert.equal(core.isValidIsoDate("2025-02-30"), false);

const validState = {
  organisation: "Fictional Logistics Ltd",
  profile: {
    reportingPeriodStart: "2025-01-01", reportingPeriodEnd: "2025-12-31",
    organisationalBoundary: "Operational control", reportingScopes: "Scope 1, Scope 2 and Scope 3",
    responsibleContributorRole: "Sustainability Coordinator", completedBy: "Fictional Coordinator",
    evidenceCompletenessConfirmed: true,
  },
  intake: { organisationValidated: true, validatedScopes: { 1: true, 2: true, 3: true }, unresolvedRecords: [], duplicateChecksPassed: true, confirmations: { complete: true, duplicates: true } },
  pilot: { stage: "locked", activeRole: "approver" },
  activities: [{ sourceRecordId: "FICTIONAL-1", methodId: gas.id, quantity: 10000, status: "approved", evidence: "FICTIONAL-EVIDENCE", factorYear: 2025, factorVersion: "2025.1", factorSource: core.FACTOR_PACK.source }],
  audit: [{ action: "Fictional activity approved" }],
  report: { hash: "a".repeat(64) },
};
assert.deepEqual(core.submissionBlockers(validState), []);
assert.deepEqual(core.reportLockBlockers(validState), []);

for (const mutation of [
  (state) => { state.intake.validatedScopes[1] = false; },
  (state) => { state.intake.validatedScopes[2] = false; },
  (state) => { state.intake.validatedScopes[3] = false; },
  (state) => { state.intake.organisationValidated = false; },
  (state) => { state.intake.unresolvedRecords = [{ row: 2 }]; },
  (state) => { state.intake.duplicateChecksPassed = false; },
  (state) => { state.intake.confirmations.complete = false; },
  (state) => { state.intake.confirmations.duplicates = false; },
]) {
  const changed = structuredClone(validState);
  mutation(changed);
  assert.ok(core.submissionBlockers(changed).length > 0);
}

for (const mutation of [
  (state) => { state.profile.organisationalBoundary = ""; },
  (state) => { state.profile.reportingScopes = ""; },
  (state) => { state.profile.responsibleContributorRole = ""; },
  (state) => { state.profile.completedBy = ""; },
  (state) => { state.profile.evidenceCompletenessConfirmed = false; },
  (state) => { state.activities[0].status = "ready"; },
  (state) => { state.activities[0].factorVersion = ""; },
]) {
  const changed = structuredClone(validState);
  mutation(changed);
  assert.ok(core.reportLockBlockers(changed).length > 0);
}

const passphrase = "fictional-passphrase-2025";
const bundle = core.createSessionBundle(validState);
const envelope = await core.encryptPayload(bundle, passphrase, "portable-session-export");
const serialisedEnvelope = JSON.stringify(envelope);
assert.equal(serialisedEnvelope.includes("Fictional Logistics Ltd"), false);
assert.equal(serialisedEnvelope.includes("FICTIONAL-EVIDENCE"), false);
const restoredBundle = await core.decryptPayload(envelope, passphrase, "portable-session-export");
assert.deepEqual(core.validateSessionBundle(restoredBundle), validState);
await assert.rejects(core.decryptPayload(envelope, "wrong-passphrase-value", "portable-session-export"), /incorrect or.*corrupted/);
const corrupted = structuredClone(envelope);
corrupted.ciphertext = `${corrupted.ciphertext.slice(0, -4)}AAAA`;
await assert.rejects(core.decryptPayload(corrupted, passphrase, "portable-session-export"), /incorrect or.*corrupted/);
const incompatible = { ...envelope, version: 999 };
await assert.rejects(core.decryptPayload(incompatible, passphrase, "portable-session-export"), /incompatible/);

const persistent = await core.encryptPayload(bundle, passphrase);
assert.equal(persistent.purpose, "persistent-session");
assert.equal((await core.decryptPayload(persistent, passphrase)).state.report.hash, "a".repeat(64));

const fakeStorage = new Map([["encrypted", "cipher"], ["legacy", "plain"], ["unrelated", "keep"]]);
core.clearPilotStorage({ removeItem: (key) => fakeStorage.delete(key) }, ["encrypted", "legacy"]);
assert.deepEqual([...fakeStorage.entries()], [["unrelated", "keep"]]);

console.log("pilot-core: 2025 factor, blockers, SHA-256 and AES-GCM session tests passed");
