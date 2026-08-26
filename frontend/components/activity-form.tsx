"use client";

import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type {
  ActivityFormValues,
  Inventory,
  ListResponse,
  Organisation
} from "@/lib/types";

export interface GovernedMethodOption {
  id: string;
  label: string;
  activityType: string;
  scope: string;
  scope3Category: string;
  activityUnit: string;
  factorLevel1: string;
  factorLevel2: string;
  factorLevel3: string;
  factorLevel4: string;
  factorColumnText: string;
  lifecycleBoundary: string;
  specialist?: boolean;
  reportingYear?: string;
}

const supplierSpecificScope3Categories = [
  [1, "Purchased goods and services"],
  [2, "Capital goods"],
  [8, "Upstream leased assets"],
  [10, "Processing of sold products"],
  [11, "Use of sold products"],
  [12, "End-of-life treatment of sold products"],
  [13, "Downstream leased assets"],
  [14, "Franchises"],
  [15, "Investments"],
] as const;

export const governedMethods: GovernedMethodOption[] = [
  {
    id: "scope1.mobile_combustion.hvo.litres.uk_2023.v1",
    label: "Scope 1 · HVO combustion · litres · UK 2023 · 0.03558",
    activityType: "mobile_combustion",
    scope: "scope_1",
    scope3Category: "",
    activityUnit: "litres",
    factorLevel1: "Bioenergy",
    factorLevel2: "Biofuel",
    factorLevel3: "Biodiesel HVO",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "direct",
    specialist: true,
    reportingYear: "2023",
  },
  {
    id: "scope3.category3.hvo_wtt.litres.uk_2023.v1",
    label: "Scope 3 category 3 · HVO well-to-tank · litres · UK 2023 · 0.27844",
    activityType: "mobile_combustion",
    scope: "scope_3",
    scope3Category: "3",
    activityUnit: "litres",
    factorLevel1: "WTT- bioenergy",
    factorLevel2: "WTT- biofuel",
    factorLevel3: "Biodiesel HVO",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "well_to_tank",
    specialist: true,
    reportingYear: "2023",
  },
  {
    id: "scope1.mobile_combustion.hvo.litres.uk_2024.v1",
    label: "Scope 1 · HVO combustion · litres · UK 2024 · 0.03558",
    activityType: "mobile_combustion",
    scope: "scope_1",
    scope3Category: "",
    activityUnit: "litres",
    factorLevel1: "Bioenergy",
    factorLevel2: "Biofuel",
    factorLevel3: "Biodiesel HVO",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "direct",
    specialist: true,
    reportingYear: "2024",
  },
  {
    id: "scope3.category3.hvo_wtt.litres.uk_2024.v1",
    label: "Scope 3 category 3 · HVO well-to-tank · litres · UK 2024 · 0.55900",
    activityType: "mobile_combustion",
    scope: "scope_3",
    scope3Category: "3",
    activityUnit: "litres",
    factorLevel1: "WTT- bioenergy",
    factorLevel2: "WTT- biofuel",
    factorLevel3: "Biodiesel HVO",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "well_to_tank",
    specialist: true,
    reportingYear: "2024",
  },
  {
    id: "scope1.mobile_combustion.hvo.litres.uk_2025.v1",
    label: "Scope 1 · HVO combustion · litres · UK 2025 · 0.03558",
    activityType: "mobile_combustion",
    scope: "scope_1",
    scope3Category: "",
    activityUnit: "litres",
    factorLevel1: "Bioenergy",
    factorLevel2: "Biofuel",
    factorLevel3: "Biodiesel HVO",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "direct",
    specialist: true,
    reportingYear: "2025",
  },
  {
    id: "scope3.category3.hvo_wtt.litres.uk_2025.v1",
    label: "Scope 3 category 3 · HVO well-to-tank · litres · UK 2025 · 0.56439",
    activityType: "mobile_combustion",
    scope: "scope_3",
    scope3Category: "3",
    activityUnit: "litres",
    factorLevel1: "WTT- bioenergy",
    factorLevel2: "WTT- biofuel",
    factorLevel3: "Biodiesel HVO",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "well_to_tank",
    specialist: true,
    reportingYear: "2025",
  },
  {
    id: "scope1.mobile_combustion.hvo.litres.uk_2026.v1",
    label: "Scope 1 · HVO combustion · litres · UK 2026 · 0.03558",
    activityType: "mobile_combustion",
    scope: "scope_1",
    scope3Category: "",
    activityUnit: "litres",
    factorLevel1: "Bioenergy",
    factorLevel2: "Biofuel",
    factorLevel3: "Biodiesel HVO",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "direct",
    specialist: true,
    reportingYear: "2026",
  },
  {
    id: "scope3.category3.hvo_wtt.litres.uk_2026.v1",
    label: "Scope 3 category 3 · HVO well-to-tank · litres · UK 2026 · 0.56439",
    activityType: "mobile_combustion",
    scope: "scope_3",
    scope3Category: "3",
    activityUnit: "litres",
    factorLevel1: "WTT- bioenergy",
    factorLevel2: "WTT- biofuel",
    factorLevel3: "Biodiesel HVO",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "well_to_tank",
    specialist: true,
    reportingYear: "2026",
  },
  {
    id: "scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2026.v1",
    label: "Scope 1 · Class I diesel delivery van · km · 0.15833",
    activityType: "mobile_combustion",
    scope: "scope_1",
    scope3Category: "",
    activityUnit: "km",
    factorLevel1: "Delivery vehicles",
    factorLevel2: "Vans",
    factorLevel3: "Class I (up to 1.305 tonnes)",
    factorLevel4: "",
    factorColumnText: "Diesel",
    lifecycleBoundary: "",
  },
  {
    id: "scope1.stationary_diesel.litres.uk_2026.v1",
    label: "Scope 1 · Stationary diesel · litres",
    activityType: "stationary_combustion",
    scope: "scope_1",
    scope3Category: "",
    activityUnit: "litres",
    factorLevel1: "Fuels",
    factorLevel2: "Liquid fuels",
    factorLevel3: "Diesel (average biofuel blend)",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "",
  },
  {
    id: "scope2.location_electricity.kwh.uk_2026.v1",
    label: "Scope 2 · UK electricity · location-based · kWh",
    activityType: "purchased_electricity",
    scope: "scope_2",
    scope3Category: "",
    activityUnit: "kWh",
    factorLevel1: "UK electricity",
    factorLevel2: "Electricity generated",
    factorLevel3: "Electricity: UK",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "purchased_energy",
  },
  {
    id: "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1",
    label: "Scope 1 · HFC-134a · mass balance · kg",
    activityType: "refrigerant",
    scope: "scope_1",
    scope3Category: "",
    activityUnit: "kg",
    factorLevel1: "Refrigerant & other",
    factorLevel2: "Kyoto protocol products",
    factorLevel3: "HFC-134a",
    factorLevel4: "",
    factorColumnText: "Emissions including only Kyoto products",
    lifecycleBoundary: "direct",
  },
  {
    id: "scope3.category3.diesel_wtt.litres.uk_2026.v1",
    label: "Scope 3 category 3 · Diesel well-to-tank · litres · 0.61101",
    activityType: "stationary_combustion",
    scope: "scope_3",
    scope3Category: "3",
    activityUnit: "litres",
    factorLevel1: "WTT- fuels",
    factorLevel2: "Liquid fuels",
    factorLevel3: "Diesel (average biofuel blend)",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "well_to_tank",
  },
  {
    id: "scope3.category5.commercial_waste.landfill.tonnes.uk_2026.v1",
    label: "Scope 3 category 5 · Commercial waste to landfill · tonnes · 520.58023",
    activityType: "waste_generated",
    scope: "scope_3",
    scope3Category: "5",
    activityUnit: "tonnes",
    factorLevel1: "Waste disposal",
    factorLevel2: "Refuse",
    factorLevel3: "Commercial and industrial waste",
    factorLevel4: "",
    factorColumnText: "Landfill",
    lifecycleBoundary: "indirect_value_chain",
  },
  {
    id: "scope3.category7.average_car.unknown_fuel.km.uk_2026.v1",
    label: "Scope 3 category 7 · Average car commuting · km · 0.16591",
    activityType: "employee_commuting",
    scope: "scope_3",
    scope3Category: "7",
    activityUnit: "km",
    factorLevel1: "Business travel- land",
    factorLevel2: "Cars (by size)",
    factorLevel3: "Average car",
    factorLevel4: "",
    factorColumnText: "Unknown",
    lifecycleBoundary: "indirect_value_chain",
  },
  {
    id: "scope3.category9.average_diesel_van.tonne_km.uk_2026.v1",
    label: "Scope 3 category 9 · Average diesel van · tonne-km · 0.63511",
    activityType: "freight_transport",
    scope: "scope_3",
    scope3Category: "9",
    activityUnit: "tonne.km",
    factorLevel1: "Freighting goods",
    factorLevel2: "Vans",
    factorLevel3: "Average (up to 3.5 tonnes)",
    factorLevel4: "",
    factorColumnText: "Diesel",
    lifecycleBoundary: "indirect_value_chain",
  },
  {
    id: "scope3.category9.average_non_refrigerated_hgv.average_laden.tonne_km.uk_2026.v1",
    label: "Scope 3 category 9 · Average diesel HGV · average laden · tonne-km · 0.10356",
    activityType: "freight_transport",
    scope: "scope_3",
    scope3Category: "9",
    activityUnit: "tonne.km",
    factorLevel1: "Freighting goods",
    factorLevel2: "HGV (non-refrigerated, all diesel)",
    factorLevel3: "Average non-refrigerated HGVs",
    factorLevel4: "",
    factorColumnText: "Average laden",
    lifecycleBoundary: "indirect_value_chain",
  },
  {
    id: "scope3.category9.rail_freight.tonne_km.uk_2026.v1",
    label: "Scope 3 category 9 · Rail freight · tonne-km · 0.02583",
    activityType: "freight_transport",
    scope: "scope_3",
    scope3Category: "9",
    activityUnit: "tonne.km",
    factorLevel1: "Freighting goods",
    factorLevel2: "Rail",
    factorLevel3: "Freight train",
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "indirect_value_chain",
  },
  {
    id: "scope3.category4.diesel_van.tonne_km.uk_2026.v1",
    label: "Scope 3 category 4 · Class I diesel van · tonne-km",
    activityType: "freight_transport",
    scope: "scope_3",
    scope3Category: "4",
    activityUnit: "tonne.km",
    factorLevel1: "Freighting goods",
    factorLevel2: "Vans",
    factorLevel3: "Class I (up to 1.305 tonnes)",
    factorLevel4: "",
    factorColumnText: "Diesel",
    lifecycleBoundary: "",
  },
  {
    id: "scope3.category6.domestic_air.with_rf.passenger_km.uk_2026.v1",
    label: "Scope 3 category 6 · Domestic air with RF · passenger-km",
    activityType: "business_travel",
    scope: "scope_3",
    scope3Category: "6",
    activityUnit: "passenger.km",
    factorLevel1: "Business travel- air",
    factorLevel2: "Flights",
    factorLevel3: "Domestic, to/from UK",
    factorLevel4: "Average passenger",
    factorColumnText: "With RF",
    lifecycleBoundary: "",
  },
  ...supplierSpecificScope3Categories.map(([category, label]) => ({
    id: `scope3.category${category}.supplier_specific.reported_kgco2e.ghgp.v1`,
    label: `Scope 3 category ${category} · ${label} · supplier-specific kgCO₂e`,
    activityType: "value_chain_result",
    scope: "scope_3",
    scope3Category: String(category),
    activityUnit: "kgCO2e",
    factorLevel1: "Supplier-specific lifecycle result",
    factorLevel2: `Category ${category}`,
    factorLevel3: label,
    factorLevel4: "",
    factorColumnText: "",
    lifecycleBoundary: "indirect_value_chain",
  })),
];

const blankValues: ActivityFormValues = {
  organisationId: "",
  inventoryId: "",
  calculationMethodId: "",
  activityType: "mobile_combustion",
  scope: "scope_1",
  scope2Method: "not_applicable",
  scope3Category: "",
  activityDate: new Date().toISOString().slice(0, 10),
  description: "",
  activityValue: "",
  openingStockKg: "",
  purchasesKg: "",
  closingStockKg: "",
  recoveredKg: "",
  scope2InstrumentType: "supplier_specific",
  scope2SupplierOrIssuer: "",
  scope2InstrumentReference: "",
  scope2FactorSource: "",
  scope2FactorValue: "",
  scope2ValidFrom: "",
  scope2ValidTo: "",
  scope2QualityCriteriaAttested: false,
  supplierName: "",
  supplierMethodology: "",
  supplierMethodologyVersion: "",
  supplierReportingPeriod: "",
  supplierBoundaryDescription: "",
  supplierAssuranceStatus: "not_assured",
  activityUnit: "litres",
  geographyCode: "GB",
  factorLevel1: "Fuels",
  factorLevel2: "Liquid fuels",
  factorLevel3: "Diesel",
  factorLevel4: "",
  factorColumnText: "",
  lifecycleBoundary: "direct",
  evidenceReference: "",
  sourceRecordId: ""
};

export function ActivityForm() {
  const organisations = useApiQuery<ListResponse<Organisation>>(
    "/organisations?limit=200"
  );
  const inventories = useApiQuery<ListResponse<Inventory>>(
    "/inventories?limit=200&scope_2_headline_basis=location_based"
  );
  const [values, setValues] = useState(blankValues);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isSupplierSpecificResult = values.calculationMethodId.includes(
    ".supplier_specific.reported_kgco2e."
  );
  const [submitting, setSubmitting] = useState(false);

  const filteredInventories = useMemo(
    () =>
      (inventories.data?.items ?? []).filter(
        (inventory) =>
          !values.organisationId ||
          inventory.organisation_id === values.organisationId
      ),
    [inventories.data, values.organisationId]
  );

  useEffect(() => {
    if (!values.organisationId && organisations.data?.items[0]) {
      setValues((current) => ({
        ...current,
        organisationId: organisations.data!.items[0].id
      }));
    }
  }, [organisations.data, values.organisationId]);

  useEffect(() => {
    if (
      filteredInventories.length > 0 &&
      !filteredInventories.some(
        (inventory) => inventory.id === values.inventoryId
      )
    ) {
      setValues((current) => ({
        ...current,
        inventoryId: filteredInventories[0].id
      }));
    }
  }, [filteredInventories, values.inventoryId]);

  function update(field: keyof ActivityFormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function selectGovernedMethod(methodId: string) {
    const method = governedMethods.find((item) => item.id === methodId);
    if (!method) {
      update("calculationMethodId", "");
      return;
    }
    setValues((current) => ({
      ...current,
      calculationMethodId: method.id,
      activityType: method.activityType,
      scope: method.scope,
      scope2Method: method.scope === "scope_2" ? "location_based" : "not_applicable",
      scope3Category: method.scope3Category,
      activityUnit: method.activityUnit,
      factorLevel1: method.factorLevel1,
      factorLevel2: method.factorLevel2,
      factorLevel3: method.factorLevel3,
      factorLevel4: method.factorLevel4,
      factorColumnText: method.factorColumnText,
      lifecycleBoundary: method.lifecycleBoundary,
    }));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      const isRefrigerantMassBalance =
        values.calculationMethodId ===
        "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1";
      const refrigerantEmittedKg = isRefrigerantMassBalance
        ? String(
            Number(values.openingStockKg) +
            Number(values.purchasesKg) -
            Number(values.closingStockKg) -
            Number(values.recoveredKg)
          )
        : values.activityValue;
      if (isRefrigerantMassBalance && Number(refrigerantEmittedKg) < 0) {
        throw new Error("Refrigerant mass balance cannot produce negative emissions.");
      }
      await apiRequest(
        `/inventories/${values.inventoryId}/activities`,
        {
          method: "POST",
          body: JSON.stringify({
            organisation_id: values.organisationId,
            activity_type: values.activityType,
            scope: values.scope,
            scope_2_method: values.scope2Method,
            scope_3_category:
              values.scope === "scope_3"
                ? Number(values.scope3Category)
                : null,
            activity_date: values.activityDate,
            description: values.description,
            activity_value: refrigerantEmittedKg,
            activity_unit: values.activityUnit,
            geography_code: values.geographyCode,
            factor_level_1: values.factorLevel1,
            factor_level_2: values.factorLevel2 || null,
            factor_level_3: values.factorLevel3 || null,
            factor_level_4: values.factorLevel4 || null,
            factor_column_text: values.factorColumnText || null,
            lifecycle_boundary: values.lifecycleBoundary || null,
            allocation_percentage: "100.00",
            data_quality_level: "primary",
            data_quality_score: 90,
            source_system: "carbon-platform",
            source_record_id: values.sourceRecordId,
            evidence_reference: values.evidenceReference || null,
            metadata_json: {
              ...(values.calculationMethodId
                ? { calculation_method_id: values.calculationMethodId }
                : {}),
              ...(isRefrigerantMassBalance
                ? {
                    opening_stock_kg: values.openingStockKg,
                    purchases_kg: values.purchasesKg,
                    closing_stock_kg: values.closingStockKg,
                    recovered_kg: values.recoveredKg
                  }
                : {}),
              ...(values.scope2Method === "market_based"
                ? {
                    instrument_type: values.scope2InstrumentType,
                    supplier_or_issuer: values.scope2SupplierOrIssuer,
                    instrument_reference: values.scope2InstrumentReference,
                    factor_source: values.scope2FactorSource,
                    factor_value: values.scope2FactorValue,
                    factor_unit: "kg CO2e/kWh",
                    valid_from: values.scope2ValidFrom,
                    valid_to: values.scope2ValidTo,
                    geography_code: values.geographyCode,
                    quality_criteria_attested:
                      values.scope2QualityCriteriaAttested
                  }
                : {}),
              ...(isSupplierSpecificResult
                ? {
                    supplier_name: values.supplierName,
                    supplier_methodology: values.supplierMethodology,
                    supplier_methodology_version: values.supplierMethodologyVersion,
                    supplier_reporting_period: values.supplierReportingPeriod,
                    boundary_description: values.supplierBoundaryDescription,
                    assurance_status: values.supplierAssuranceStatus
                  }
                : {})
            }
          })
        }
      );
      setMessage("Activity saved and validated.");
      setValues((current) => ({
        ...blankValues,
        organisationId: current.organisationId,
        inventoryId: current.inventoryId
      }));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Activity could not be saved."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (organisations.loading || inventories.loading) {
    return <LoadingState label="Loading activity form" />;
  }
  if (organisations.error || inventories.error) {
    return (
      <ErrorState
        message={organisations.error ?? inventories.error ?? "Unknown error"}
        onRetry={() => {
          void organisations.refresh();
          void inventories.refresh();
        }}
      />
    );
  }

  return (
    <form className="form-card" onSubmit={submit}>
      <section className="form-section">
        <div className="form-section-heading">
          <span>1</span>
          <div>
            <h2>Reporting context</h2>
            <p>Select the organisation and inventory receiving this activity.</p>
          </div>
        </div>
        <div className="form-grid">
          <label>
            Organisation
            <select
              aria-label="Organisation"
              onChange={(event) => update("organisationId", event.target.value)}
              required
              value={values.organisationId}
            >
              {(organisations.data?.items ?? []).map((organisation) => (
                <option key={organisation.id} value={organisation.id}>
                  {organisation.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Inventory
            <select
              aria-label="Inventory"
              onChange={(event) => update("inventoryId", event.target.value)}
              required
              value={values.inventoryId}
            >
              {filteredInventories.map((inventory) => (
                <option key={inventory.id} value={inventory.id}>
                  {inventory.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Activity date
            <input
              onChange={(event) => update("activityDate", event.target.value)}
              required
              type="date"
              value={values.activityDate}
            />
          </label>
        </div>
      </section>

      <section className="form-section">
        <div className="form-section-heading">
          <span>2</span>
          <div>
            <h2>Activity classification</h2>
            <p>Define the GHG scope and activity type.</p>
          </div>
        </div>
        <div className="form-grid">
          <label className="field-span-2">
            Governed calculation method
            <select
              aria-label="Governed calculation method"
              onChange={(event) => selectGovernedMethod(event.target.value)}
              value={values.calculationMethodId}
            >
              <option value="">Manual / method not yet governed</option>
              <optgroup label="Standard governed methods">
                {governedMethods.filter((method) => !method.specialist).map((method) => (
                  <option key={method.id} value={method.id}>{method.label}</option>
                ))}
              </optgroup>
              <optgroup label="Specialist bioenergy methods — evidence required">
                {governedMethods.filter((method) => method.specialist).map((method) => (
                  <option key={method.id} value={method.id}>{method.label}</option>
                ))}
              </optgroup>
            </select>
          </label>
          <div className="lineage-card">
            <strong>{values.calculationMethodId ? "Governed method selected" : "Draft method"}</strong>
            <p>{values.calculationMethodId
              ? "Scope, category, unit and factor selectors are locked to the approved method contract."
              : "Manual methods remain draft and may not be eligible for customer reporting."}</p>
          </div>
          <label>
            Activity type
            <select
              disabled={Boolean(values.calculationMethodId)}
              onChange={(event) => update("activityType", event.target.value)}
              value={values.activityType}
            >
              <option value="mobile_combustion">Mobile combustion</option>
              <option value="stationary_combustion">Stationary combustion</option>
              <option value="refrigerant">Refrigerant</option>
              <option value="purchased_electricity">Purchased electricity</option>
              <option value="purchased_heat_steam_cooling">Purchased heat, steam and cooling</option>
              <option value="freight_transport">Freight transport</option>
              <option value="business_travel">Business travel</option>
              <option value="employee_commuting">Employee commuting</option>
              <option value="waste_generated">Waste generated in operations</option>
              <option value="value_chain_result">Supplier-specific value-chain result</option>
            </select>
          </label>
          <label>
            Scope
            <select
              disabled={Boolean(values.calculationMethodId)}
              onChange={(event) => {
                const scope = event.target.value;
                update("scope", scope);
                update(
                  "scope2Method",
                  scope === "scope_2" ? "location_based" : "not_applicable"
                );
              }}
              value={values.scope}
            >
              <option value="scope_1">Scope 1</option>
              <option value="scope_2">Scope 2</option>
              <option value="scope_3">Scope 3</option>
            </select>
          </label>
          {values.scope === "scope_2" ? (
            <label>
              Scope 2 method
              <select
                onChange={(event) => update("scope2Method", event.target.value)}
                value={values.scope2Method}
              >
                <option value="location_based">Location-based</option>
                <option value="market_based">Market-based</option>
              </select>
            </label>
          ) : null}
          {values.scope === "scope_2" && values.scope2Method === "market_based" ? (
            <>
              <label>
                Contractual instrument
                <select onChange={(event) => update("scope2InstrumentType", event.target.value)} value={values.scope2InstrumentType}>
                  <option value="supplier_specific">Supplier-specific</option>
                  <option value="energy_attribute_certificate">Energy attribute certificate</option>
                  <option value="direct_contract">Direct contract</option>
                  <option value="residual_mix">Residual mix</option>
                </select>
              </label>
              <label>Supplier or issuer<input onChange={(event) => update("scope2SupplierOrIssuer", event.target.value)} required value={values.scope2SupplierOrIssuer} /></label>
              <label>Instrument reference<input onChange={(event) => update("scope2InstrumentReference", event.target.value)} required value={values.scope2InstrumentReference} /></label>
              <label>Factor source<input onChange={(event) => update("scope2FactorSource", event.target.value)} required value={values.scope2FactorSource} /></label>
              <label>Contractual factor (kg CO₂e/kWh)<input inputMode="decimal" min="0" onChange={(event) => update("scope2FactorValue", event.target.value)} required value={values.scope2FactorValue} /></label>
              <label>Valid from<input onChange={(event) => update("scope2ValidFrom", event.target.value)} required type="date" value={values.scope2ValidFrom} /></label>
              <label>Valid to<input onChange={(event) => update("scope2ValidTo", event.target.value)} required type="date" value={values.scope2ValidTo} /></label>
              <label className="checkbox-field">
                <input
                  checked={values.scope2QualityCriteriaAttested}
                  onChange={(event) => setValues((current) => ({
                    ...current,
                    scope2QualityCriteriaAttested: event.target.checked
                  }))}
                  required
                  type="checkbox"
                />
                Instrument meets the Scope 2 quality criteria
              </label>
            </>
          ) : null}
          {values.scope === "scope_3" ? (
            <label>
              Scope 3 category
              <select
                disabled={Boolean(values.calculationMethodId)}
                onChange={(event) => update("scope3Category", event.target.value)}
                required
                value={values.scope3Category}
              >
                <option value="">Select category</option>
                {Array.from({ length: 15 }, (_, index) => index + 1).map(
                  (category) => (
                    <option key={category} value={category}>
                      Category {category}
                    </option>
                  )
                )}
              </select>
            </label>
          ) : null}
          {isSupplierSpecificResult ? (
            <>
              <div className="lineage-card field-span-2">
                <strong>Supplier-specific lifecycle result</strong>
                <p>Enter the reported kgCO₂e and retain the supplier methodology, boundary and evidence. The platform will not substitute a generic government factor.</p>
              </div>
              <label>Supplier or investee<input onChange={(event) => update("supplierName", event.target.value)} required value={values.supplierName} /></label>
              <label>Methodology<input onChange={(event) => update("supplierMethodology", event.target.value)} required value={values.supplierMethodology} /></label>
              <label>Methodology version<input onChange={(event) => update("supplierMethodologyVersion", event.target.value)} required value={values.supplierMethodologyVersion} /></label>
              <label>Supplier reporting period<input onChange={(event) => update("supplierReportingPeriod", event.target.value)} required value={values.supplierReportingPeriod} /></label>
              <label className="field-span-2">Lifecycle boundary description<input onChange={(event) => update("supplierBoundaryDescription", event.target.value)} required value={values.supplierBoundaryDescription} /></label>
              <label>Assurance status<select onChange={(event) => update("supplierAssuranceStatus", event.target.value)} value={values.supplierAssuranceStatus}><option value="not_assured">Not assured</option><option value="limited_assurance">Limited assurance</option><option value="reasonable_assurance">Reasonable assurance</option><option value="third_party_verified">Third-party verified</option></select></label>
            </>
          ) : null}
        </div>
      </section>

      <section className="form-section">
        <div className="form-section-heading">
          <span>3</span>
          <div>
            <h2>Activity data</h2>
            <p>Enter the measured quantity and supporting evidence.</p>
          </div>
        </div>
        <div className="form-grid">
          <label className="field-span-2">
            Description
            <input
              onChange={(event) => update("description", event.target.value)}
              placeholder="Diesel consumed by owned HGV fleet"
              required
              value={values.description}
            />
          </label>
{values.calculationMethodId ===
          "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1" ? (
            <>
              <label>Opening stock (kg)<input inputMode="decimal" min="0" onChange={(event) => update("openingStockKg", event.target.value)} required value={values.openingStockKg} /></label>
              <label>Purchases/additions (kg)<input inputMode="decimal" min="0" onChange={(event) => update("purchasesKg", event.target.value)} required value={values.purchasesKg} /></label>
              <label>Closing stock (kg)<input inputMode="decimal" min="0" onChange={(event) => update("closingStockKg", event.target.value)} required value={values.closingStockKg} /></label>
              <label>Recovered/returned (kg)<input inputMode="decimal" min="0" onChange={(event) => update("recoveredKg", event.target.value)} required value={values.recoveredKg} /></label>
              <div className="lineage-card">
                <strong>Calculated refrigerant emitted</strong>
                <p>{String(
                  Number(values.openingStockKg || 0) +
                  Number(values.purchasesKg || 0) -
                  Number(values.closingStockKg || 0) -
                  Number(values.recoveredKg || 0)
                )} kg</p>
              </div>
            </>
          ) : (
            <label>
              Activity value
              <input
                inputMode="decimal"
                onChange={(event) => update("activityValue", event.target.value)}
                placeholder="1250.50"
                required
                value={values.activityValue}
              />
            </label>
          )}
          <label>
            Unit
            <select
              disabled={Boolean(values.calculationMethodId)}
              onChange={(event) => update("activityUnit", event.target.value)}
              value={values.activityUnit}
            >
              <option value="litres">Litres</option>
              <option value="kWh">kWh</option>
              <option value="tonne.km">Tonne-km</option>
              <option value="passenger.km">Passenger-km</option>
              <option value="vehicle-km">Vehicle-km</option>
              <option value="kg">kg</option>
              <option value="kgCO2e">kgCO₂e</option>
              <option value="tonnes">Tonnes</option>
              <option value="km">km</option>
            </select>
          </label>
          <label>
            Geography
            <input
              onChange={(event) => update("geographyCode", event.target.value)}
              required
              value={values.geographyCode}
            />
          </label>
          <label>
            Evidence reference
            <input
              onChange={(event) => update("evidenceReference", event.target.value)}
              placeholder="Invoice or document reference"
              required
              value={values.evidenceReference}
            />
          </label>
          <label>
            Source record ID
            <input
              onChange={(event) => update("sourceRecordId", event.target.value)}
              placeholder="fuel-statement-2026-08"
              required
              value={values.sourceRecordId}
            />
          </label>
        </div>
      </section>

      <section className="form-section">
        <div className="form-section-heading">
          <span>4</span>
          <div>
            <h2>Emission-factor matching</h2>
            <p>Provide the governed category hierarchy used for resolution.</p>
          </div>
        </div>
        <div className="form-grid">
          <label>
            Level 1
            <input
              disabled={Boolean(values.calculationMethodId)}
              onChange={(event) => update("factorLevel1", event.target.value)}
              required
              value={values.factorLevel1}
            />
          </label>
          <label>
            Level 2
            <input
              disabled={Boolean(values.calculationMethodId)}
              onChange={(event) => update("factorLevel2", event.target.value)}
              value={values.factorLevel2}
            />
          </label>
          <label>
            Level 3
            <input
              disabled={Boolean(values.calculationMethodId)}
              onChange={(event) => update("factorLevel3", event.target.value)}
              value={values.factorLevel3}
            />
          </label>
          <label>
            Level 4
            <input
              disabled={Boolean(values.calculationMethodId)}
              onChange={(event) => update("factorLevel4", event.target.value)}
              value={values.factorLevel4}
            />
          </label>
          <label>
            Column text
            <input
              disabled={Boolean(values.calculationMethodId)}
              onChange={(event) => update("factorColumnText", event.target.value)}
              value={values.factorColumnText}
            />
          </label>
          <label>
            Lifecycle boundary
            <select
              onChange={(event) => update("lifecycleBoundary", event.target.value)}
              value={values.lifecycleBoundary}
            >
              <option value="direct">Direct</option>
              <option value="purchased_energy">Purchased energy</option>
              <option value="well_to_tank">Well-to-tank</option>
              <option value="indirect_value_chain">Indirect value chain</option>
            </select>
          </label>
        </div>
      </section>

      <div className="form-footer">
        <MutationMessage error={error} success={message} />
        <div className="button-row">
          <button className="button button-secondary" type="reset">
            Reset
          </button>
          <button
            className="button button-primary"
            disabled={submitting || !values.inventoryId}
            type="submit"
          >
            {submitting ? "Saving…" : "Save and validate"}
          </button>
        </div>
      </div>
    </form>
  );
}
