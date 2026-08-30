# RocketSurgery Memory Handoff - 2026-08-24

## Project Location

Current local working folder:

`C:\Users\mattp\Documents\ChatGPT\Rocket Surgery`

GitHub repository:

`https://github.com/mattpower-ux/rocketsurgery`

Live Render URLs:

- Frontend: `https://rocketsurgery.onrender.com`
- API: `https://rocketsurgery-api.onrender.com`

Current branch:

`main`, tracking `origin/main`

## Latest Pushed Commits

- `9f53391` - `Regenerate walkthrough images from asset sheet`
- `1d66948` - `Isolate image direction modal keystrokes`
- `1ef96a1` - `Add walkthrough visual asset sheets`
- `92db2fc` - `Rebuild stale drafts with chimney cap scaffold`
- `e74ceaf` - `Apply visual continuity to initial generation`
- `aec245c` - `Add QC visual consistency templates`
- `e3ff273` - `Move QC image directions into modal editor`
- Earlier related stabilization commits: `0116f29`, `8f4cfac`, `4fe43aa`, `901a16a`, `6de8f37`

All listed work was pushed to `origin/main`.

## Main Strategic Change

Walkthrough image generation is moving from independent one-off step images toward a pre-production visual asset workflow.

The desired pipeline is now:

`query -> classify/taxonomy -> plan steps -> create visual asset sheet -> generate step images using that asset sheet -> QC review -> save/approve`

The asset sheet is intended to function as the walkthrough's visual bible. It defines the product/object, environment, worker, tools, materials, and key views before step images are generated.

## Visual Asset Sheet Workflow

Added in `1ef96a1` and expanded in `9f53391`.

New walkthrough generation now creates:

- `visual_template`
- `visual_assets`
- `visual_assets.asset_sheet_url`
- `visual_assets.asset_key`
- `visual_assets.primary_object`
- `visual_assets.product`
- `visual_assets.environment`
- `visual_assets.worker`
- `visual_assets.tools`
- `visual_assets.views`
- `visual_assets.asset_sheet_prompt`

For chimney cap walkthroughs, the asset key is:

`taxonomy-chimney-cap-single-flue-brick-chimney`

The generated asset sheet is cached by taxonomy-style asset key so future compatible walkthroughs can reuse the visual component sheet.

## Reference-Based Step Regeneration

Before `9f53391`, step image prompts only said "use the asset sheet as the visual bible." That helped, but it was still prompt-only.

Now:

- `backend/app/image_generator.py` includes `generate_step_image_from_asset_sheet`.
- It locates a local `/static/images/...` asset sheet.
- It calls `client.images.edit(...)` with the asset sheet as a reference image.
- It uses `input_fidelity="high"` when generating the new step panel.
- It falls back to normal `generate_step_image` if the asset sheet file is unavailable.

This should make step images follow the approved asset sheet more tightly than text prompting alone.

## Admin: Regenerate All Images

Added in `9f53391`.

New backend endpoint:

`POST /admin/qc/regenerate-all-images`

New frontend button:

`Regenerate All Images`

Scope:

- It affects only the currently expanded walkthrough in Admin QC.
- It does not batch-regenerate existing walkthroughs globally.
- It stages regenerated images in the QC draft.
- The user must click `Save All` to persist the regenerated images.

Individual `Generate New Image` also now uses the asset sheet reference path when available.

## QC Image Direction UX Fixes

The inline "Image direction" textarea caused page jumping, cursor jumps, vanished text, and row rerenders.

Fixes:

- Replaced inline image-direction textarea with an `Add/Edit image direction` button.
- Editing now happens in a fixed modal: `QcImageDirectionModal`.
- Modal has `Apply` and `Apply + Generate`.
- Text state is owned locally inside the modal, not the whole Admin page.
- Keystrokes and pointer events are stopped from bubbling out of the modal.
- Commit `1d66948` specifically fixed Return/Enter causing the Admin page to jump while editing in the popup.

Known expectation:

- After deployment, hard refresh Admin if old JS is still loaded.

## QC Metadata And Persistence

Added/stabilized:

- `visual_template` field in the QC metadata editor.
- `visual_template` is sent through Save All.
- `visual_assets` is displayed in QC when present.
- QC shows the asset sheet image preview if `visual_assets.asset_sheet_url` exists.
- Step text corrections and image directions are staged and persisted through Save All.

Important: staged image regenerations are not final until `Save All` is clicked.

## Chimney Cap Test

The first chimney cap prototype exposed problems:

- Images had inconsistent chimneys.
- Step order was unclear.
- Initial image prompting did not use the asset sheet process yet.
- The first generated draft was cached, so old bad results stayed visible until deleted or force-refreshed.

Fixes made:

- Added `chimney_cap` category detection.
- Added a deterministic chimney-cap scaffold instead of relying fully on LLM step ordering.
- Added generator schema versioning.
- Old non-approved drafts rebuild when the generator schema version changes.
- `/walkthrough` now supports `force_refresh`.

Current chimney cap scaffold:

1. Confirm Cap Fit and Gather Tools
2. Access Chimney Safely
3. Inspect Crown and Flue
4. Clean Chimney Crown
5. Dry-Fit Chimney Cap
6. Mark and Drill Fastener Points
7. Secure Chimney Cap
8. Seal and Inspect Installation

The regenerated chimney cap walkthrough returned:

- `generator_schema_version: 5`
- `visual_assets.asset_status: generated`
- `step_sequence_validation.category: chimney_cap`
- `step_sequence_validation.status: passed`
- latency around 366 seconds for asset sheet plus 8 images

## YouTube Research / Transcript Status

Current code does not yet parse YouTube transcripts.

Existing module:

`backend/app/source_research.py`

Current behavior:

- Uses YouTube API metadata if `YOUTUBE_API_KEY` or `GOOGLE_YOUTUBE_API_KEY` exists.
- Synthesizes planning/image guidance from public video titles/descriptions.
- Stores derived research lessons, not transcripts.

Important limitation:

- True transcript ingestion is not implemented yet.
- For chimney cap, source research reported `skipped_no_youtube_api_key`.

Recommended future work:

- Add transcript fetching/parsing when a suitable video source is selected.
- Store derived sequence/visual guidance, not raw transcript text.
- Feed transcript-derived step order and visual cues into the planner and asset sheet brief.

## Known Limitations

Image generation is still expensive:

- Chimney cap full generation took roughly 5-6 minutes.
- Asset sheet workflow adds one image generation up front, then step panels.

Asset sheet reference use is new:

- It now uses `images.edit` with the asset sheet as an image reference.
- Needs real-world QA on whether consistency improves enough.
- If step images still drift, next step is a stronger component library / cutout reuse / reference set per object angle.

Existing walkthroughs are not automatically regenerated:

- This was intentional.
- Use Admin QC's per-walkthrough `Regenerate All Images` button when you want to upgrade a specific walkthrough.

## Useful Commands

Build frontend:

```powershell
npm run build
```

Compile backend files with installed Python:

```powershell
& 'C:\Users\mattp\AppData\Local\Programs\Python\Python314\python.exe' -m py_compile backend\main.py backend\app\image_generator.py backend\app\generator.py backend\app\step_sequence_validator.py
```

Create a walkthrough through deployed API:

```powershell
$body = @{ query = 'How do I install a chimney cap?'; force_refresh = $true } | ConvertTo-Json
Invoke-RestMethod -Uri 'https://rocketsurgery-api.onrender.com/walkthrough' -Method Post -ContentType 'application/json' -Body $body
```

## Next Best Steps

1. Wait for Render deploy of `9f53391`.
2. Open Admin QC and hard refresh.
3. Inspect the regenerated chimney cap walkthrough and its asset sheet.
4. Use `Regenerate All Images` on that one walkthrough to test reference-based regeneration from the asset sheet.
5. Compare visual consistency before/after reference-based regeneration.
6. Add YouTube transcript parsing if narration/sequence quality still needs stronger external grounding.
7. Generalize deterministic scaffolds for other taxonomy families where step order should not be left to open-ended planning.

## Update - 2026-08-30 Visual Consistency Migration Start

Commit `bdcec0c` starts the existing-walkthrough migration process.

Added backend endpoints:

- `GET /admin/qc/visual-migration-report`
- `POST /admin/qc/prepare-visual-migration`

Added Admin panel:

- `Visual Consistency Migration`
- `Load Report`
- `Prepare Missing Templates`
- `Generate 3 Asset Sheets`

The migration deliberately starts with an inventory and template-prep phase. It does not blindly regenerate all 80+ walkthroughs. The intended production flow is:

1. Load the visual migration report.
2. Prepare missing visual templates and visual asset metadata.
3. Generate visual asset sheets in small capped batches.
4. Open individual walkthroughs in Step Order QC.
5. Use `Regenerate All Images` only after the visual template and asset sheet look right.
6. Save and approve one walkthrough at a time.

Cost guardrails:

- The report estimates image calls and low/medium/high output-only costs.
- `Prepare Missing Templates` does not create paid images.
- `Generate 3 Asset Sheets` is intentionally capped to avoid an accidental expensive batch.

Important implementation detail:

- During legacy migration, non-chimney walkthroughs get per-walkthrough asset sheet keys when no sheet already exists. This avoids unrelated older walkthroughs accidentally sharing a broad generic category sheet.

## Update - 2026-08-30 Asset Sheet First Is Mandatory

The generator pipeline has been hardened so new walkthrough generation creates or resolves the visual template and visual asset sheet before step-by-step images are created.

Code changes:

- `backend/app/generator.py` now uses `generate_step_image_from_asset_sheet` for first-pass step images.
- `GENERATOR_SCHEMA_VERSION` is now `6`, so stale non-approved cached drafts rebuild under the stricter visual pipeline.
- Generated manifests include `image_generation_pipeline.requires_asset_sheet_before_step_images = true`.
- Each step records `imageGenerationMode`, usually `asset_sheet_reference`.
- If asset sheet generation fails, new paid step images are not created from one-off prompts; the step is left with `imageStale: true` for QC.
- Added stronger templates/assets for attic insulation, plumbing sinks, and door/window walkthroughs.
- Fixed the duplicate API-side category classifier so chimney cap is recognized consistently during QC and migration.
- `backend/app/image_generator.py` now uses stricter wording when deriving step images from an asset sheet.

Verification:

- Added `scripts/test_asset_sheet_first_generation.py`.
- Added `npm test`, backed by `scripts/run-python-test.mjs`, to verify asset-sheet-first sequencing without spending image-generation calls.

## Update - 2026-08-30 Production Migration Inventory

After `c47eec8` deployed, the live Render API was checked from this workspace.

Read-only production inventory:

- Active walkthroughs found: `87`
- Walkthroughs missing visual templates: `86`
- Walkthroughs missing asset sheets: `86`
- Estimated full rebuild image calls: `722`
- Estimated medium-quality output-only rebuild cost: about `$30.32`

Protected migration writes could not be started from this Codex process because `ADMIN_API_TOKEN` was not available locally and the in-app browser session did not already have an admin token saved.

Follow-up tooling:

- `npm run visual:migration:report`
- `npm run visual:migration:prepare`
- `npm run visual:migration:asset-sheets`

These commands use `ADMIN_API_TOKEN` from the environment and call the deployed Render API.

## Update - 2026-08-30 Missing Templates Prepared In Production

Commit `68caaea` fixed visual migration batch targeting before production writes were run.

Why this mattered:

- `Prepare Missing Templates` now selects only walkthroughs missing visual templates.
- `Generate 3 Asset Sheets` selects only walkthroughs missing asset sheets.
- The Visual Consistency Migration buttons preserve scroll from the click moment to reduce admin panel jumpiness.

Production action completed:

- The admin UI token was saved in the controllable in-app browser session.
- `Prepare Missing Templates` was run in batches against the live Render app.
- Missing visual templates dropped from `86` to `0`.
- No paid asset-sheet or step-image generation was run as part of this template-prep phase.

Current production migration state after the final report:

- Active walkthroughs: `87`
- Missing visual templates: `0`
- Missing asset sheets: `86`
- Estimated full-regeneration image calls: `722`
- Estimated medium-quality full image pass: about `$30.32`

Next migration phase:

1. Generate asset sheets in capped batches, starting with a small group.
2. Review the asset sheets for visual consistency before regenerating step images.
3. Regenerate images one walkthrough at a time using the per-walkthrough `Regenerate All Images` control.
4. Save and approve only after the visual template, asset sheet, narration order, and generated step images look coherent.
