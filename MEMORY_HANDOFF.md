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

## 2026-09-27 Curated Walkthrough Expansion

Current workspace: `C:\Users\mattp\Documents\ChatGPT\Rocket Surgery` on `main`.
GitHub pushes auto-deploy to Render. Do not use OpenAI Sites for this project.

- `research/next_50_video_candidates.json` holds 50 distinct home DIY/lifestyle topics, one relevant YouTube source per topic, observed view counts, and candidate-pool popularity ranks. This is a curated set, not YouTube's global top 50. The requested ceiling-fan receiver, windshield chip, variable-speed pool pump, pool heater, lanai screen, and cloudy headlamp topics are included. Two sampled YouTube transcript exports were unavailable; do not claim these drafts used transcripts.
- Production inventory is 92 stored walkthroughs as of this note: 88 preexisting plus four curated drafts. The four are `how-do-i-small-chip-in-my-car-windshield` (`order_and_visuals_checked`), `how-do-i-restore-cloudy-car-headlights` (`visual_review_needed`), `how-do-i-torn-screen-panel-in-my-lanai` (`visual_review_needed`), and `how-do-i-leaky-outdoor-faucet` (`visual_review_needed`). None is approved. A mistaken generic `repair-leaky-faucet` draft created during this session was deleted after the exact outdoor-faucet draft saved.
- New curated generation creates a structured locked visual plan, then an asset sheet, then asset-sheet-edited step images. Sheet and step visual reviews can retry once. A review that reports discrepancies cannot be marked passed even if its booleans are true. Visual-review API calls have bounded timeouts. Curated queries now retain their exact wording and storage identity instead of being collapsed onto a broader taxonomy match.
- Human visual QA remains essential. The lanai sheet and panels still show a removable screen frame/tabletop setup in places; this is not a fixed enclosure bay. The faucet draft changes handle geometry and its reassembly panel misdraws the faucet. The headlamp sheet needs a context review; step 3's earlier off-target sanding image was repaired. Do not approve or bulk-generate more from these patterns without repairing them.
- `scripts/create_curated_video_walkthroughs.mjs` has vetted briefs for catalog IDs 2, 3, 5, 6, and 10. ID 3 (variable-speed pool pump) is prepared but not generated; its electrical and bonding work is assigned to a qualified installer. ID 4 (pool heater) remains a candidate because gas versus heat-pump installation needs a specific equipment branch and professional requirements. Catalog ID 1 interprets the fan request as a remote-control receiver, not a motor assembly; confirm that intent before generating.
- The long-running creation POST can exceed the client/proxy timeout. The script checks production for a completed save after disconnect. Never assume a timed-out request failed or issue a duplicate paid generation without checking the exact saved query/storage ID. The faucet run eventually saved after its client disconnected. Future scaling would benefit from a persistent server-side job queue and checkpointed creation.
- Focused tests: `scripts/test_new_walkthrough_generation.py` and `scripts/test_asset_sheet_first_generation.py`. Both passed locally on 2026-09-27.

