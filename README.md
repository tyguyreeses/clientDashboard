# Client Dashboard

## Run

Install dependencies and configure the environment before starting the backend:

```bash
.venv/bin/python -m pip install -e .
cp .env.example .env.local
```

For local development, set these values in `.env.local`:

```env
APP_ENV=development
FRONTEND_ORIGIN=http://localhost:5173
GOOGLE_CALLBACK_URL=http://localhost:5173/api/auth/google/callback
GOOGLE_ALLOWED_EMAIL=heymaddie@hairbymaddieee.com
AUTH_BOOTSTRAP_ENABLED=true
```

Set a real Google OAuth client ID and secret, and generate a random `SESSION_SECRET` of at least 32 bytes. Add this exact URI to the Google OAuth client's authorized redirect URIs:

```text
http://localhost:5173/api/auth/google/callback
```

The application uses a server-side OAuth callback; an authorized JavaScript origin is not required.

Terminal 1:

```bash
set -a
source .env.local
set +a
PYTHONPATH=src .venv/bin/alembic upgrade head
PYTHONPATH=src .venv/bin/python -m uvicorn client_dashboard.main:app --reload --port 8000
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. After the first successful admin login, set `AUTH_BOOTSTRAP_ENABLED=false` in `.env.local` and restart the backend. Never leave bootstrap mode enabled after initial provisioning.

For development or test data, a destructive reset and reseed is also available:

```bash
PYTHONPATH=src .venv/bin/python -m client_dashboard.scripts.init_db
```

The reset drops all application tables and permanently deletes their data. Do not use it against production data.

The production frontend check must also run from `frontend/`:

```bash
npm run build
```

Database schema and migration documentation is in [`src/client_dashboard/README.md`](src/client_dashboard/README.md).

## Public bridal inquiries

Visitors can open `/inquiry` or submit anonymously to `POST /api/inquiry`; no admin session, CSRF token, email provider, or email configuration is involved. Apply migrations with `alembic upgrade head` before deployment. The API requires name, email, social profile, wedding date, getting-ready address, service counts (brides defaults to 1), ready-by time and firmness, home/venue, makeup and bridal-trial choices, planning stage, referral source, and contact consent. Phone, recommendations, referral name, and additional notes are optional; choosing Other requires a source name. Consent is not stored. Wedding dates must be after today and no later than the same calendar date next year in America/Denver (Feb. 29 anniversaries use Feb. 28); farther-out dates prompt visitors to contact Maddie on Instagram.

Successful inquiries create a Client, an Inquired Wedding, initial status progress, and service-party records atomically. Counts map to B (bride), P (bridesmaids/MOB/MOG), and J (flowergirls/junior bridesmaids); source Other maps only to `Client.source` (maximum 100 characters). Optional notes are limited to 2,000 characters; home/venue, time firmness, and trial context are appended to `Client.notes`. Planning choices are stored as `looking`, `invoice`, or `book`. `Client.inquiry_date` uses the America/Denver calendar date.

Outside `APP_ENV=development`, the API permits three submissions per client IP in a rolling 60-minute window. Development is exempt. Keep the API behind the configured Nginx proxy: it replaces forwarded client IP headers with the connected remote address, and Uvicorn must only be reachable through that trusted local proxy. Do not expose Uvicorn directly or trust client-supplied forwarding headers.

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

