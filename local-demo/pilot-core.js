(function initialisePilotCore(global) {
  "use strict";

  const FACTOR_PACK = Object.freeze({
    id: "desnz-uk-ghg-2025.v1",
    year: 2025,
    version: "2025.1",
    source: "DESNZ UK Government GHG Conversion Factors for Company Reporting 2025",
    sourceUrl: "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025",
    published: "2025-06-10",
  });

  const method = (id, label, short, scope, category, unit, factor, factorLabel, extra = {}) => Object.freeze({
    id, label, short, scope, category, unit, factor, factorLabel,
    factorYear: FACTOR_PACK.year,
    factorPackId: FACTOR_PACK.id,
    factorVersion: FACTOR_PACK.version,
    factorSource: FACTOR_PACK.source,
    ...extra,
  });

  const METHODS = Object.freeze([
    method("scope1.stationary_natural_gas.gross_cv.kwh.uk_2025.v1", "Natural gas · gross CV · kWh", "Natural gas", 1, null, "kWh (Gross CV)", 0.18296, "Fuels / Gaseous fuels / Natural gas"),
    method("scope1.stationary_natural_gas.cubic_metres.uk_2025.v1", "Natural gas · cubic metres", "Natural gas", 1, null, "cubic metres", 2.06672, "Fuels / Gaseous fuels / Natural gas"),
    method("scope1.mobile_combustion.diesel.litres.uk_2025.v1", "Owned fleet diesel · litres", "Fleet diesel", 1, null, "litres", 2.57082, "Fuels / Liquid fuels / Diesel (average biofuel blend)"),
    method("scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2025.v1", "Owned Class I diesel van · kilometres", "Diesel van", 1, null, "km", 0.15738, "Delivery vehicles / Vans / Class I (up to 1.305 tonnes) / Diesel"),
    method("scope1.mobile_combustion.average_car.petrol.km.uk_2025.v1", "Average petrol car · kilometres", "Petrol fleet", 1, null, "km", 0.16272, "Passenger vehicles / Cars / Average car / Petrol"),
    method("scope1.refrigerant.r410a.service_top_up.kg.uk_2025.v1", "R410A service top-up · kg", "R410A top-up", 1, null, "kg", 1924, "Refrigerant & other / Blends / R410A"),
    method("scope2.location_electricity.kwh.uk_2025.v1", "UK electricity · location-based · kWh", "Electricity", 2, null, "kWh", 0.177, "UK electricity / Electricity generated / Electricity: UK"),
    method("scope3.category3.diesel_wtt.litres.uk_2025.v1", "Category 3 · Diesel well-to-tank · litres", "Diesel WTT", 3, 3, "litres", 0.61101, "WTT fuels / Liquid fuels / Diesel"),
    method("scope3.category5.commercial_waste.closed_loop.tonnes.uk_2025.v1", "Category 5 · Commercial waste · closed-loop · tonnes", "Closed-loop waste", 3, 5, "tonnes", null, "Waste disposal / Commercial and industrial waste / Closed-loop", { unavailableReason: "The official 2025 flat factor pack does not publish a numeric closed-loop factor for this material grouping. Select a supported material-specific route; calculation is blocked." }),
    method("scope3.category5.commercial_waste.landfill.tonnes.uk_2025.v1", "Category 5 · Commercial waste · landfill · tonnes", "Landfill waste", 3, 5, "tonnes", 520.5327, "Waste disposal / Commercial and industrial waste / Landfill"),
    method("scope3.category5.commercial_waste.combustion.tonnes.uk_2025.v1", "Category 5 · Commercial waste · incineration with energy recovery · tonnes", "Waste incineration", 3, 5, "tonnes", 4.68568, "Waste disposal / Commercial and industrial waste / Incineration with energy recovery"),
    method("scope3.category4.diesel_van.tonne_km.uk_2025.v1", "Category 4 · Upstream diesel van freight · tonne-km", "Upstream van freight", 3, 4, "tonne.km", 0.87423, "Freighting goods / Vans / Class I (up to 1.305 tonnes) / Diesel"),
    method("scope3.category6.domestic_air.with_rf.passenger_km.uk_2025.v1", "Category 6 · Domestic air · passenger-km · with RF", "Domestic air", 3, 6, "passenger.km", 0.22928, "Business travel - air / Domestic, to/from UK / Average passenger / With RF"),
    method("scope3.category6.national_rail.passenger_km.uk_2025.v1", "Category 6 · National rail · passenger-km", "National rail", 3, 6, "passenger.km", 0.03546, "Business travel - land / Rail / National rail"),
    method("scope3.category6.average_ferry_passenger.passenger_km.uk_2025.v1", "Category 6 · Average ferry passenger · passenger-km", "Ferry travel", 3, 6, "passenger.km", 0.1127, "Business travel - sea / Ferry / Average passenger"),
    method("scope3.category6.uk_hotel.room_night.uk_2025.v1", "Category 6 · UK hotel · room night", "UK hotel", 3, 6, "Room per night", 10.4, "Hotel stay / Hotel stay / UK"),
    method("scope3.category7.average_car.unknown_fuel.km.uk_2025.v1", "Category 7 · Average car commute · kilometres", "Employee commuting", 3, 7, "km", 0.16725, "Business travel - land / Cars / Average car / Unknown fuel"),
    method("scope3.category9.average_diesel_van.tonne_km.uk_2025.v1", "Category 9 · Downstream average diesel van · tonne-km", "Downstream van freight", 3, 9, "tonne.km", 0.6313, "Freighting goods / Vans / Average (up to 3.5 tonnes) / Diesel"),
    method("scope3.category9.average_non_refrigerated_hgv.average_laden.tonne_km.uk_2025.v1", "Category 9 · Downstream average-laden HGV · tonne-km", "Downstream HGV freight", 3, 9, "tonne.km", 0.10163, "Freighting goods / HGV (non-refrigerated, all diesel) / Average laden"),
    method("scope3.category9.rail_freight.tonne_km.uk_2025.v1", "Category 9 · Downstream rail freight · tonne-km", "Downstream rail freight", 3, 9, "tonne.km", 0.02779, "Freighting goods / Rail / Freight train"),
    method("scope3.category1.supplier_specific.reported_kgco2e.ghgp.v1", "Category 1 · Supplier-specific reported result", "Purchased goods", 3, 1, "kgCO2e", null, "GHG Protocol supplier-specific lifecycle result", { directResult: true, methodology: "GHG Protocol Scope 3 supplier-specific method" }),
    method("scope3.category2.supplier_specific.reported_kgco2e.ghgp.v1", "Category 2 · Supplier-specific capital goods result", "Capital goods", 3, 2, "kgCO2e", null, "GHG Protocol supplier-specific lifecycle result", { directResult: true, methodology: "GHG Protocol Scope 3 supplier-specific method" }),
  ]);

  const METHOD_BY_ID = new Map(METHODS.map((item) => [item.id, item]));
  const textEncoder = new TextEncoder();
  const textDecoder = new TextDecoder();
  const ENVELOPE_VERSION = 1;
  const SESSION_SCHEMA = "dcarbn-browser-pilot-session";
  const SESSION_VERSION = 1;

  function requireWebCrypto() {
    if (!global.crypto?.subtle || !global.crypto?.getRandomValues) throw new Error("Secure WebCrypto is unavailable. The pilot cannot store, export or lock customer data safely in this browser.");
    return global.crypto;
  }

  function bytesToBase64(bytes) {
    if (typeof Buffer !== "undefined") return Buffer.from(bytes).toString("base64");
    let binary = "";
    bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
    return btoa(binary);
  }

  function base64ToBytes(value) {
    if (typeof Buffer !== "undefined") return new Uint8Array(Buffer.from(value, "base64"));
    return Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
  }

  async function sha256(value) {
    const digest = await requireWebCrypto().subtle.digest("SHA-256", textEncoder.encode(value));
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  async function deriveKey(passphrase, salt, usages) {
    if (typeof passphrase !== "string" || passphrase.length < 12) throw new Error("Use a passphrase of at least 12 characters.");
    const crypto = requireWebCrypto();
    const material = await crypto.subtle.importKey("raw", textEncoder.encode(passphrase), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt, iterations: 250000 }, material, { name: "AES-GCM", length: 256 }, false, usages);
  }

  async function encryptPayload(payload, passphrase, purpose = "persistent-session") {
    const crypto = requireWebCrypto();
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const serialised = JSON.stringify(payload);
    const protectedPayload = JSON.stringify({ checksum: await sha256(serialised), payload });
    const key = await deriveKey(passphrase, salt, ["encrypt"]);
    const cipher = await crypto.subtle.encrypt({ name: "AES-GCM", iv, additionalData: textEncoder.encode(`${SESSION_SCHEMA}:${purpose}:${ENVELOPE_VERSION}`) }, key, textEncoder.encode(protectedPayload));
    return {
      schema: SESSION_SCHEMA,
      version: ENVELOPE_VERSION,
      purpose,
      encryption: { algorithm: "AES-GCM", keyDerivation: "PBKDF2-SHA-256", iterations: 250000, salt: bytesToBase64(salt), iv: bytesToBase64(iv) },
      ciphertext: bytesToBase64(new Uint8Array(cipher)),
    };
  }

  async function decryptPayload(envelope, passphrase, expectedPurpose) {
    if (!envelope || envelope.schema !== SESSION_SCHEMA || envelope.version !== ENVELOPE_VERSION) throw new Error("This session file uses an incompatible or unsupported format.");
    if (expectedPurpose && envelope.purpose !== expectedPurpose) throw new Error("This encrypted file is not the expected pilot-session type.");
    if (envelope.encryption?.algorithm !== "AES-GCM" || envelope.encryption?.keyDerivation !== "PBKDF2-SHA-256" || envelope.encryption?.iterations !== 250000) throw new Error("This session file uses an unsupported encryption configuration.");
    try {
      const salt = base64ToBytes(envelope.encryption.salt);
      const iv = base64ToBytes(envelope.encryption.iv);
      const key = await deriveKey(passphrase, salt, ["decrypt"]);
      const plain = await requireWebCrypto().subtle.decrypt({ name: "AES-GCM", iv, additionalData: textEncoder.encode(`${SESSION_SCHEMA}:${envelope.purpose}:${ENVELOPE_VERSION}`) }, key, base64ToBytes(envelope.ciphertext));
      const protectedPayload = JSON.parse(textDecoder.decode(plain));
      const serialised = JSON.stringify(protectedPayload.payload);
      if (await sha256(serialised) !== protectedPayload.checksum) throw new Error("checksum");
      return protectedPayload.payload;
    } catch (error) {
      if (error instanceof Error && error.message.includes("incompatible")) throw error;
      throw new Error("The passphrase is incorrect or the encrypted session file is corrupted.");
    }
  }

  function resolveMethod(methodId, reportingYear) {
    const selected = METHOD_BY_ID.get(methodId);
    if (!selected) throw new Error(`Unsupported governed method: ${methodId}`);
    if (selected.factorYear !== reportingYear) throw new Error(`Method ${methodId} belongs to factor year ${selected.factorYear}, not reporting year ${reportingYear}.`);
    if (!selected.directResult && (!Number.isFinite(selected.factor) || selected.unavailableReason)) throw new Error(selected.unavailableReason || `Method ${methodId} has no numeric factor.`);
    return selected;
  }

  function isValidIsoDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value))) return false;
    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  }

  function submissionBlockers(state) {
    const blockers = [];
    const intake = state.intake || {};
    const profile = state.profile || {};
    if (!intake.organisationValidated) blockers.push("Upload and validate the organisation-information CSV.");
    [1, 2, 3].forEach((scope) => { if (!intake.validatedScopes?.[scope]) blockers.push(`Upload and validate a Scope ${scope} CSV.`); });
    if (intake.unresolvedRecords?.length) blockers.push(`Correct and re-upload ${intake.unresolvedRecords.length} unresolved record(s).`);
    if (!intake.duplicateChecksPassed) blockers.push("Resolve duplicate source IDs and complete a clean duplicate check.");
    if (!intake.confirmations?.complete) blockers.push("Confirm the submitted files are complete for the stated sources.");
    if (!intake.confirmations?.duplicates) blockers.push("Confirm records are not duplicated elsewhere.");
    if (!state.activities?.length) blockers.push("Add at least one validated activity record.");
    if (!String(state.organisation || "").trim()) blockers.push("Add the reporting organisation name.");
    if (!profile.reportingPeriodStart || !profile.reportingPeriodEnd) blockers.push("Add the reporting-period start and end dates.");
    return blockers;
  }

  function reportLockBlockers(state) {
    const blockers = submissionBlockers(state);
    const profile = state.profile || {};
    if (!String(profile.organisationalBoundary || "").trim()) blockers.push("Define the organisational boundary.");
    if (!String(profile.reportingScopes || "").trim()) blockers.push("Confirm the reporting scopes.");
    if (!String(profile.responsibleContributorRole || "").trim()) blockers.push("Identify the responsible contributor role.");
    if (!profile.evidenceCompletenessConfirmed) blockers.push("Confirm evidence completeness.");
    if (!String(profile.completedBy || "").trim()) blockers.push("Record the contributing organisation contact or role.");
    if (!state.activities?.every((item) => item.status === "approved")) blockers.push("Complete analyst approval for every activity.");
    if (!state.activities?.every((item) => item.evidence && item.factorYear === 2025 && item.factorVersion && item.factorSource)) blockers.push("Complete evidence and 2025 methodology lineage for every activity.");
    return [...new Set(blockers)];
  }

  function createSessionBundle(state) {
    return { schema: SESSION_SCHEMA, version: SESSION_VERSION, exportedAt: new Date().toISOString(), state };
  }

  function clearPilotStorage(storage, keys) {
    keys.forEach((key) => storage.removeItem(key));
  }

  function validateSessionBundle(bundle) {
    if (!bundle || bundle.schema !== SESSION_SCHEMA || bundle.version !== SESSION_VERSION || !bundle.state || !Array.isArray(bundle.state.activities)) throw new Error("The decrypted session has an incompatible or incomplete structure.");
    if (!bundle.state.profile || !Array.isArray(bundle.state.audit) || !bundle.state.pilot || !bundle.state.intake) throw new Error("The decrypted session is missing required profile, workflow or audit state.");
    if (bundle.state.activities.some((activity) => !METHOD_BY_ID.has(activity.methodId) || !Number.isFinite(activity.quantity) || activity.quantity <= 0 || !activity.sourceRecordId || !activity.evidence)) throw new Error("The decrypted session contains an unsupported or incomplete activity record.");
    return bundle.state;
  }

  const api = Object.freeze({ FACTOR_PACK, METHODS, METHOD_BY_ID, SESSION_SCHEMA, SESSION_VERSION, sha256, encryptPayload, decryptPayload, resolveMethod, isValidIsoDate, submissionBlockers, reportLockBlockers, createSessionBundle, validateSessionBundle, clearPilotStorage });
  global.DCARBN_PILOT_CORE = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
