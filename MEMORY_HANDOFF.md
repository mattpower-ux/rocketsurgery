# RocketSurgery Memory Handoff

Saved: 2026-08-22 23:24 -04:00

## Project Location

Local working folder:

`C:\Users\mattp\Desktop\RocketSurgery Working Folder`

GitHub repository:

`https://github.com/mattpower-ux/rocketsurgery`

Live Render URLs:

- Frontend: `https://rocketsurgery.onrender.com`
- API: `https://rocketsurgery-api.onrender.com`

## Current Persistent Storage State

The live API reported:

- 86 total stored walkthrough manifests
- 86 marked `draft`
- 86 marked `unvalidated`
- 0 approved/other statuses returned by the walkthrough manifest index

Important caveat: this counts indexed walkthrough manifests in persistent storage. It does not count loose/orphaned image files that are not tied to a manifest.

## Recent Commits Pushed

- `fafd55d` - `Fix QC delete storage id resolution`
- `33084a0` - `Add walkthrough library taxonomy view`

Both were pushed to `origin/main`.

## What Was Fixed

### QC Delete

The QC delete failure was caused by a mismatch between the UI's display/title-style walkthrough id and the actual persistent disk folder id.

Fixes made:

- Backend now resolves a display id, title, manifest id, or storage id to the actual storage folder before loading or deleting.
- QC delete now removes the actual walkthrough folder and index entry.
- UI uses `storage_walkthrough_id` for QC row actions when available.
- Removed a stray `stepId` reference in `loadAdminStatus()` that caused a console error.

### Admin Token

The admin token is stored in browser `localStorage` under:

`rocketsurgery_admin_token`

This lets the admin page reuse the token across sessions until local browser storage is cleared or the token fails.

## New Walkthrough Library Layer

A new admin-protected endpoint was added:

`GET /admin/walkthrough-library`

It returns:

- stored walkthroughs
- taxonomy match state
- unmatched stored walkthroughs
- prospective taxonomy walkthroughs
- branch-selection flags
- count summaries

A new Admin section was added:

`Walkthrough Library`

It includes:

- Stored / Prospective toggle
- filters for All, Draft, Matched, Unmatched, Branch Needed
- search by title, query, alias, taxonomy id, and category
- inventory stats
- Repair button for stored walkthroughs

After Render redeploys, refresh Admin and click:

`Rebuild Index`

This updates the live persistent disk's walkthrough index using stable storage ids.

## Strategic Direction

The goal is to scale from 86 walkthroughs toward about 1,000 stored walkthroughs while avoiding duplicate near-identical responses.

Recommended lifecycle:

`candidate query -> taxonomy cluster -> branch selection -> generated draft -> QC edit -> approved canonical walkthrough -> reusable response`

Important principle:

The approved walkthrough is the asset, not the query. Many query phrasings should map to one approved walkthrough unless the physical process actually differs.

Examples:

- `fix a leaky faucet`, `repair a faucet leak`, `stop a leaking faucet`, `fix a faucet leak` should generally map to one walkthrough.
- `replace dishwasher`, `install dishwasher`, `dishwasher replacement`, `dishwasher installation` should generally map to one walkthrough.
- `replace shower` needs branches such as acrylic shower kit, tile shower, shower pan, or shower cartridge.
- `install window` needs branches such as standard window, replacement insert, storm window, or egress window.

## Next Best Steps

1. Wait for Render to redeploy commit `33084a0`.
2. Open Admin and load the new `Walkthrough Library`.
3. Click `Rebuild Index`.
4. Review the stored list and identify unmatched walkthroughs.
5. Start approving/deleting the 86 draft walkthroughs through QC.
6. Use the library's Prospective view to choose the next batch of walkthroughs to generate.
7. Add edit logging/rules so your QC corrections become reusable generation guidance.
8. Add a queue screen for batch generation from taxonomy candidates.
9. Add duplicate detection before generation.
10. Scale in batches: 86 -> 150 -> 250 -> 500 -> 1,000.

## Verification From Last Work Session

Passed:

- Backend syntax parse
- Temporary storage delete test
- Temporary library/index test
- Frontend production build using `dist-check`

Temporary build output was removed after verification.

