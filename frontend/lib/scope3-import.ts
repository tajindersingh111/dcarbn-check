export type AccountingSourceSystem =
  | "csv"
  | "quickbooks"
  | "xero"
  | "sage"
  | "api";

export interface AccountingTemplate {
  schema_version: string;
  supported_source_systems: AccountingSourceSystem[];
  required_columns: string[];
  optional_columns: string[];
  governed_methods: Record<string, string>;
}

export type ImportRow = Record<string, string>;

export interface ValidatedImportRow {
  index: number;
  values: ImportRow;
  errors: Record<string, string>;
  valid: boolean;
}

const supportedCategories = new Set(["1", "2", "8", "10", "11", "12", "13", "14", "15"]);

function finishCell(row: string[], value: string): void {
  row.push(value.trim());
}

export function parseCsv(csv: string): { headers: string[]; rows: string[][] } {
  const records: string[][] = [];
  let row: string[] = [];
  let value = "";
  let quoted = false;

  for (let index = 0; index < csv.length; index += 1) {
    const character = csv[index];
    if (character === '"') {
      if (quoted && csv[index + 1] === '"') {
        value += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === "," && !quoted) {
      finishCell(row, value);
      value = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && csv[index + 1] === "\n") index += 1;
      finishCell(row, value);
      value = "";
      if (row.some((cell) => cell.length > 0)) records.push(row);
      row = [];
    } else {
      value += character;
    }
  }

  finishCell(row, value);
  if (row.some((cell) => cell.length > 0)) records.push(row);
  if (quoted) throw new Error("The CSV contains an unclosed quoted value.");
  if (records.length === 0) throw new Error("The CSV is empty.");

  const [headers, ...rows] = records;
  if (new Set(headers).size !== headers.length) {
    throw new Error("The CSV contains duplicate column headings.");
  }
  return { headers, rows };
}

export function initialColumnMapping(
  headers: string[],
  targetColumns: string[]
): Record<string, string> {
  return Object.fromEntries(
    targetColumns.map((target) => [
      target,
      headers.find(
        (header) =>
          header.trim().toLowerCase().replace(/[\s-]+/g, "_") === target
      ) ?? ""
    ])
  );
}

export function mapCsvRows(
  headers: string[],
  rows: string[][],
  mapping: Record<string, string>
): ImportRow[] {
  const indexes = new Map(headers.map((header, index) => [header, index]));
  return rows.map((row) =>
    Object.fromEntries(
      Object.entries(mapping).map(([target, source]) => [
        target,
        source ? row[indexes.get(source) ?? -1] ?? "" : ""
      ])
    )
  );
}

function isDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value));
}

function isDateTime(value: string): boolean {
  return value.length > 0 && !Number.isNaN(Date.parse(value));
}

export function validateImportRow(
  values: ImportRow,
  requiredColumns: string[],
  index: number
): ValidatedImportRow {
  const errors: Record<string, string> = {};

  for (const column of requiredColumns) {
    if (!values[column]?.trim()) errors[column] = "Required";
  }
  if (values.scope_3_category && !supportedCategories.has(values.scope_3_category)) {
    errors.scope_3_category = "Use 1, 2, 8 or 10–15";
  }
  for (const field of ["reported_kg_co2e", "allocation_percentage"]) {
    const number = Number(values[field]);
    if (values[field] && (!Number.isFinite(number) || number <= 0)) {
      errors[field] = "Enter a positive number";
    }
  }
  const allocation = Number(values.allocation_percentage);
  if (Number.isFinite(allocation) && allocation > 100) {
    errors.allocation_percentage = "Maximum 100%";
  }
  for (const field of [
    "transaction_date",
    "supplier_reporting_period_start",
    "supplier_reporting_period_end"
  ]) {
    if (values[field] && !isDate(values[field])) errors[field] = "Use YYYY-MM-DD";
  }
  if (
    values.supplier_result_calculated_at &&
    !isDateTime(values.supplier_result_calculated_at)
  ) {
    errors.supplier_result_calculated_at = "Use an ISO date and time";
  }
  if (
    isDate(values.supplier_reporting_period_start) &&
    isDate(values.supplier_reporting_period_end) &&
    values.supplier_reporting_period_end < values.supplier_reporting_period_start
  ) {
    errors.supplier_reporting_period_end = "Must follow the start date";
  }

  return { index, values, errors, valid: Object.keys(errors).length === 0 };
}

export function toApiRecord(row: ImportRow): Record<string, unknown> {
  const optionalNumber = (value: string | undefined) =>
    value?.trim() ? value.trim() : null;

  return {
    ...row,
    source_account_code: row.source_account_code || null,
    source_account_name: row.source_account_name || null,
    currency_code: row.currency_code || null,
    net_amount: optionalNumber(row.net_amount),
    scope_3_category: Number(row.scope_3_category),
    reported_kg_co2e: row.reported_kg_co2e,
    allocation_percentage: row.allocation_percentage,
    source_document_reference: row.source_document_reference || null,
    source_record_version: row.source_record_version || null
  };
}
