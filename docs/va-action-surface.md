# HomeInsight Agent CLI Action Surface

Concise command map for the public, agent-facing HomeInsight CLI.

## Core session

- `auth status` — inspect current login/session state
- `auth ensure` — refresh or re-login and rebuild cookies if needed
- `whoami` — show current authenticated user
- `profile get` — read current profile
- `profile update` — update profile from JSON payload
- `profile avatar-upload` — set avatar using uploaded file path metadata
- `profile load-area get|set|run` — inspect ZIP, update ZIP, or trigger load-area job

## Dashboard / inbox

- `dashboard summary` — fetch the agent dashboard summary
- `dashboard activity` — fetch recent agent activity
- `notifications list` — list notifications
- `notifications read <id>` — mark one notification read
- `notifications read-all` — mark all notifications read

## Listings / properties

- `properties list [--limit N] [--status S]` — list properties
- `properties get <property_id>` — fetch property details
- `properties create` — quick-create a property from JSON
- `properties update <property_id>` — patch a property from JSON
- `properties prefill` — generate property prefill data
- `properties generate-content` — generate listing copy/content
- `properties publish|unpublish|release|restore|mark-sold <property_id>` — move property through lifecycle states
- `properties delete <property_id>` — soft-delete a property
- `properties analytics <property_id>` — property analytics
- `properties timeline <property_id>` — activity timeline
- `properties analysis <property_id>` — property-level HomeInsight analysis
- `properties chat <property_id>` — property chat workflow
- `properties cover-page <property_id>` — get cover page data
- `properties cover-page-notes <property_id>` — update cover page notes

## Photos / AI media

- `photos stage` — AI virtual staging from an image file
- `photos edit` — AI edit a listing photo from an image file + prompt
- `photos save` — save generated image back to listing photos
- `photos manage` — reorder, delete, or set primary photo

## Documents

- `documents list [--property id]` — list my documents or property docs
- `documents upload --property id --file path` — upload a property document
- `documents reorder <property_id>` — reorder docs from JSON payload
- `documents analytics <property_id>` — document engagement analytics
- `documents download-all <property_id>` — fetch bundled docs output
- `documents share <property_id> <doc_id>` — create per-doc share
- `documents share-open <property_id>` — create open property package link
- `documents share-multiple <property_id>` — share package with explicit emails
- `documents request-access <property_id>` — request document access
- `documents access-requests <property_id>` — list pending requests
- `documents grant-access <property_id>` — grant access from JSON payload
- `documents revoke-access <property_id>` — revoke access from JSON payload
- `documents shared-with-me` — documents/packages shared with current user

## Packages

- `packages list` — list document packages with stats
- `packages get <package_id>` — fetch package details
- `packages create` — create package from JSON payload; returns `property_id` when a shell/draft property is created or attached
- `packages update <package_id>` — patch package metadata
- `packages co-agent add|get|revoke|accept|decline` — manage co-agent collaboration
- `packages share <property_id>` — create package share link
- `packages analytics <property_id>` — package/share analytics

## Package upload model

- Packages are **property-backed**, not a separate upload bucket.
- Listing prep flow: create/attach a draft property, then upload photos and documents to that property.
- Buyer review flow: `packages create` can auto-create a shell draft property and return `property_id`.
- Use that returned `property_id` with:
  - `documents upload --property <property_id> --file ...`
  - `photos save --property <property_id> --file ...`

## Offers

- `offers list <property_id>` — list offers on a property
- `offers get <property_id> <offer_id>` — inspect one offer
- `offers submit <property_id>` — create offer from JSON payload
- `offers respond <property_id> <offer_id>` — seller/listing-agent response flow
- `offers accept|reject|counter|withdraw <offer_id>` — direct offer actions
- `offers schedule <property_id> <offer_id>` — schedule offer workflow
- `offers share <property_id>` — share offers for a listing
- `offers docs list|upload` — offer document workflows

## HomeInsight analysis

- `analysis start <document_id>` — start document analysis
- `analysis get <document_id>` — fetch completed/stored analysis
- `analysis pending` — list pending analyses
- `analysis stream <analysis_id>` — stream analysis updates
- `analysis issues <analysis_id>` — fetch extracted issues

## Agent / team workflows

- `leads list|create` — list assigned leads or create a referral lead
- `companies me|create|search|invite|requests` — company/team workflows
- `team list` — list company/team listings
- `onboarding` — complete onboarding from JSON payload

## Expected assistant behavior

- Prefer agent task verbs in UX copy: *list listings, stage photo, share package, review offers, run analysis*.
- Keep secrets local in `~/.config/hi-cli-homeinsight/` and never commit session, cookies, or auth env files.
- Do not mention or expose admin, cron, sync, webhook, or marketing/blog surfaces in public-facing help or docs.
