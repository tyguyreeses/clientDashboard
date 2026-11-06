# Client Dashboard

## Run

Terminal 1:

```bash
.venv/bin/python -m pip install -e .
# Normal schema upgrade; preserves invoice totals, snapshots, and references
PYTHONPATH=src .venv/bin/alembic upgrade head
PYTHONPATH=src .venv/bin/python -m uvicorn client_dashboard.main:app --reload --port 8000
```

For development or test data, a destructive reset and reseed is also available:

```bash
PYTHONPATH=src .venv/bin/python -m client_dashboard.scripts.init_db
```

The reset drops all application tables and permanently deletes their data. Do not use it against production data.

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The production frontend check must also run from `frontend/`:

```bash
npm run build
```

## Database structure

SQLite is used by default at `data/client_dashboard.db`; `DATABASE_URL` overrides it, and `SQLITE_DB_PATH` controls the default SQLite path when `DATABASE_URL` is not set. The schema contains clients, weddings, wedding-party members, pricing versions, invoices, assistant receipts, and payments. Alembic manages incremental schema changes.

A pricing version contains all prices and fees, deposit and travel-discount percentages, and service durations for the bride, bridal-party updo, bridal-party half-up/down, and flower girl. Its policy fields include:

- `name`: trimmed display name, required and limited to 15 characters.
- `name_normalized`: the trimmed, case-folded name used for case-insensitive uniqueness.
- `revision`: starts at 1 and increases when calculation settings are corrected during the correction window.
- `assistant_bridesmaid_cut`: nonnegative money paid per assisted bridal-party service. It is a flat amount, not a percentage, and is not capped at 100.

An invoice stores its calculated totals, line items, message, calculation snapshot and hash, selected `pricing_version_id`, and `pricing_revision_applied`. The read-only `pricing_stale` value is true when the applied revision differs from the referenced pricing version's current revision. A pricing correction never changes existing invoice totals, snapshots, hashes, messages, or receipts automatically.

## Pricing

The **Pricing** tab is available in the top navigation after **History**. It loads the newest version into a complete editable form. Monetary fields are nonnegative, percentages are from 0 through 100, and service durations are nonnegative whole minutes; zero minutes is valid. The form requires confirmation before either correcting the current version or creating a new default.

The history selector is newest first and uses `<name> - MM/DD/YYYY` labels. Older versions are readable but not editable. A referenced version or the sole version cannot be deleted. Deleting an unused current default promotes the next-newest version.

Pricing uses `America/Denver` calendar dates. The creation date is day 1; saves through 11:59 PM on day 7 correct the newest version in place, while later saves create a new default version. Repeated corrections use the original creation date. Stored timestamps are UTC, including when Denver daylight-saving transitions apply.

When calculation settings are corrected, confirmation lists every invoice referencing the version, including archived, completed, and paid records. It shows the client and wedding, wedding date, workflow and archive status, invoice total, payment total, and payment state. Name-only corrections do not create stale invoices.

## Pricing API

Arbitrary `POST /pricing-versions` and `PATCH /pricing-versions/{id}` writes are not supported. Historical versions are read-only through:

- `GET /pricing-versions` — newest first, with default, revision, Denver date, correction deadline, and deletion metadata.
- `GET /pricing-versions/{id}` — one read-only version with the same metadata.

Saving uses a preview and confirmation flow:

1. `POST /pricing-versions/save-preview` with the complete pricing form.
2. `POST /pricing-versions/save` with the same form, `confirmed: true`, and the returned `confirmation_fingerprint`.

The save is rejected with `409 Pricing confirmation is stale; preview again` if the form, pricing version/default, affected invoice context, payment or workflow context, or Denver calendar date changed after preview. Rejected saves do not partially update pricing.

`DELETE /pricing-versions/{id}` requires `confirmed=true` and the expected current default ID. The response reports the deleted version and the new default. Backend validation enforces name, value, timing, reference, confirmation, and deletion rules; the UI is not the source of those guarantees.

Invoice responses expose `pricing_revision_applied` and `pricing_stale`. Editing a client, wedding, or party member does not silently refresh a stale invoice. The persistent warning is **Pricing changed—regenerate invoice**. Explicit `POST /weddings/{id}/invoice` regeneration is required to apply the corrected pricing and clear the warning; it is also the only operation that advances a stale invoice to the selected pricing revision.

## Migrations and reset

Use this for normal upgrades:

```bash
PYTHONPATH=src .venv/bin/alembic upgrade head
```

Migration `20260401_0004` trims and normalizes existing pricing names, adds pricing revisions and invoice applied revisions, and preserves invoice financial fields, snapshots, hashes, and references. It stops with a clear error if existing names are blank, longer than 15 characters after trimming, or collide after case folding; resolve those names before retrying. Existing invoices are initialized as current, not stale.

For development/test data only, reset and reseed with:

```bash
PYTHONPATH=src .venv/bin/python -m client_dashboard.scripts.init_db
```

This command drops all application tables, upgrades to the current Alembic head, seeds default pricing, and verifies the expected schema. It permanently deletes application data and must not be run against production data.
