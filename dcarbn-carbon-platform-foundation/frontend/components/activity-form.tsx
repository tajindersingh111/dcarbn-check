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

const blankValues: ActivityFormValues = {
  organisationId: "",
  inventoryId: "",
  activityType: "mobile_combustion",
  scope: "scope_1",
  scope2Method: "not_applicable",
  scope3Category: "",
  activityDate: new Date().toISOString().slice(0, 10),
  description: "",
  activityValue: "",
  activityUnit: "litres",
  geographyCode: "GB",
  factorLevel1: "Fuels",
  factorLevel2: "Liquid fuels",
  factorLevel3: "Diesel",
  lifecycleBoundary: "direct",
  evidenceReference: "",
  sourceRecordId: ""
};

export function ActivityForm() {
  const organisations = useApiQuery<ListResponse<Organisation>>(
    "/organisations?limit=200"
  );
  const inventories = useApiQuery<ListResponse<Inventory>>(
    "/inventories?limit=200"
  );
  const [values, setValues] = useState(blankValues);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
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

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
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
            activity_value: values.activityValue,
            activity_unit: values.activityUnit,
            geography_code: values.geographyCode,
            factor_level_1: values.factorLevel1,
            factor_level_2: values.factorLevel2 || null,
            factor_level_3: values.factorLevel3 || null,
            lifecycle_boundary: values.lifecycleBoundary || null,
            allocation_percentage: "100.00",
            data_quality_level: "primary",
            data_quality_score: 90,
            source_system: "carbon-platform",
            source_record_id: values.sourceRecordId,
            evidence_reference: values.evidenceReference || null
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
          <label>
            Activity type
            <select
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
            </select>
          </label>
          <label>
            Scope
            <select
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
          {values.scope === "scope_3" ? (
            <label>
              Scope 3 category
              <select
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
          <label>
            Unit
            <select
              onChange={(event) => update("activityUnit", event.target.value)}
              value={values.activityUnit}
            >
              <option value="litres">Litres</option>
              <option value="kWh">kWh</option>
              <option value="tonne-km">Tonne-km</option>
              <option value="vehicle-km">Vehicle-km</option>
              <option value="kg">kg</option>
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
              onChange={(event) => update("factorLevel1", event.target.value)}
              required
              value={values.factorLevel1}
            />
          </label>
          <label>
            Level 2
            <input
              onChange={(event) => update("factorLevel2", event.target.value)}
              value={values.factorLevel2}
            />
          </label>
          <label>
            Level 3
            <input
              onChange={(event) => update("factorLevel3", event.target.value)}
              value={values.factorLevel3}
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
