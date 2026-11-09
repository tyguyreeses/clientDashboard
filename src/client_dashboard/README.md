# Client Dashboard Database

SQLite is used by default at `data/client_dashboard.db`; `DATABASE_URL` overrides it, and `SQLITE_DB_PATH` controls the default SQLite path when `DATABASE_URL` is not set. The schema contains clients, weddings, wedding-party members, pricing versions, invoices, assistant receipts, payments, and server-side authentication records. Alembic manages incremental schema changes. A fresh migration upgrade seeds the default pricing version when no pricing records exist.

A pricing version contains all prices and fees, deposit and travel-discount percentages, and service durations for the bride, bridal-party updo, bridal-party half-up/down, and flower girl. Its policy fields include:

- `name`: trimmed display name, required and limited to 15 characters.
- `name_normalized`: the trimmed, case-folded name used for case-insensitive uniqueness.
- `revision`: starts at 1 and increases when calculation settings are corrected during the correction window.
- `assistant_bridesmaid_cut`: nonnegative money paid per assisted bridal-party service. It is a flat amount, not a percentage, and is not capped at 100.

An invoice stores its calculated totals, line items, message, calculation snapshot and hash, selected `pricing_version_id`, and `pricing_revision_applied`. The read-only `pricing_stale` value is true when the applied revision differs from the referenced pricing version's current revision. A pricing correction never changes existing invoice totals, snapshots, hashes, messages, or receipts automatically.

## Migrations and reset

Use this for normal upgrades:

```bash
PYTHONPATH=src .venv/bin/alembic upgrade head
```

Migration `20260401_0004` trims and normalizes existing pricing names, adds pricing revisions and invoice applied revisions, and preserves invoice financial fields, snapshots, hashes, and references. Migration `20260401_0008` seeds the default pricing version on an empty pricing table without replacing existing pricing data. It stops with a clear error if existing names are blank, longer than 15 characters after trimming, or collide after case folding; resolve those names before retrying. Existing invoices are initialized as current, not stale.

For development/test data only, reset and reseed with:

```bash
PYTHONPATH=src .venv/bin/python -m client_dashboard.scripts.init_db
```

This command drops all application tables, upgrades to the current Alembic head, seeds default pricing, and verifies the expected schema. It permanently deletes application data and must not be run against production data.
