# Design system

## Brand foundation

- Product name: **D-carbN Carbon Platform**.
- Primary typeface: **Lato**, weights 400 and 700.
- Voice: clear, factual, calm, non-accusatory and evidence-led.
- Carbon terms use CO₂ for carbon dioxide and CO₂e for greenhouse-gas equivalence.
- Use “Other” rather than “Unknown” when the classification is a valid residual group.

## Tokens

The code-level source of truth is `frontend/app/styles/globals.css`. Components must consume named tokens, not introduce isolated hex values. Maintain token groups for brand, text, surface, border, status, focus, spacing, radius, shadow, type scale and layout width.

Before production brand sign-off, record approved accessible values for:
- primary/secondary/neutral colours;
- success, warning, error and information states;
- focus ring and link states;
- chart categorical and sequential palettes.

All text/background combinations must meet WCAG 2.2 AA contrast. Charts require labels/tooltips and must not rely on colour alone.

## Typography

- Page title: one H1 per page.
- Section titles: hierarchical H2/H3; do not skip levels for styling.
- Body copy: Lato 400; emphasis/headings: Lato 700.
- Numeric emissions values use tabular alignment where supported.
- Units stay adjacent to values and remain explicit.

## Components

Required reusable components: application shell, navigation item, page header, panel/card, primary/secondary/destructive/text buttons, form fields, select, textarea, date/numeric inputs, status badge, metric card, data table, pagination, modal/confirmation, toast/inline message, loading state, empty state, error state, file upload, evidence link, reconciliation summary and report/chart container.

### Button hierarchy
- Primary: one dominant page action.
- Secondary: reversible supporting action.
- Destructive: explicit confirmation and consequence.
- Text/link: navigation or low-emphasis action.
- Disabled controls explain the prerequisite nearby.

### Forms
Labels are persistent; placeholder text is not a label. Errors identify the field and correction. Preserve user input on recoverable errors. Required status, accepted format, unit and evidence expectations are stated before submission.

### Tables and charts
Tables support accessible headers, sensible responsive overflow and export context. Emissions charts display scope/category, period, unit, basis and factor/method context. Empty charts use an explanatory state, not an empty frame.

## Layout and responsive behaviour

Use the existing sidebar/topbar shell. At smaller breakpoints, navigation becomes an accessible overlay. Maintain logical reading order and touch targets. Avoid horizontal scrolling except within deliberate data-table containers.

## Governance

New components need documented purpose, variants, states, keyboard behaviour and tests. Design changes require visual regression consideration and user-guide screenshot updates.
