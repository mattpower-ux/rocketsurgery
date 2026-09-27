const API_URL = (process.env.ROCKETSURGERY_API_URL || "https://rocketsurgery-api.onrender.com").replace(/\/$/, "");
const ADMIN_TOKEN = process.env.ADMIN_API_TOKEN || "";
const action = process.argv[2] || "report";
const limit = Number(process.argv[3] || 10);

function usage() {
  console.log("Usage:");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs report");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs prepare 10");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs asset-sheets 3");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs images 1");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs images-dry-run 1");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs images-all");
  console.log("  Optional for images-all: ROCKETSURGERY_MIGRATION_IDS=id-1,id-2");
}

async function request(path, options = {}) {
  if (!ADMIN_TOKEN) {
    throw new Error("ADMIN_API_TOKEN is required for visual migration API calls.");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": ADMIN_TOKEN,
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = { raw: text };
  }

  if (!response.ok) {
    throw new Error(data.detail || data.error || `HTTP ${response.status}`);
  }
  return data;
}

const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function migrationReport() {
  for (let attempt = 1; attempt <= 5; attempt++) {
    try {
      return await request("/admin/qc/visual-migration-report?limit=10000&review_status=all");
    } catch (error) {
      if (attempt === 5) throw error;
      await pause(10000);
    }
  }
}

async function verifyRegeneratedWalkthrough(walkthroughId) {
  const data = await request(`/admin/walkthroughs/${encodeURIComponent(walkthroughId)}`);
  const walkthrough = data.walkthrough || {};
  const steps = walkthrough.steps || [];
  const failures = steps.filter((step) =>
    step.imageGenerationMode !== "asset_sheet_edit" || !step.imageUrl ||
    !step.imageRegeneratedAt || step.imageGenerationFallbackError
  );
  if (!walkthrough.visual_step_images_regenerated_at || failures.length || !steps.length) {
    throw new Error(`${walkthroughId}: saved images failed asset-sheet verification`);
  }
  return steps.length;
}

async function runAllImages() {
  const allowedIds = new Set(
    (process.env.ROCKETSURGERY_MIGRATION_IDS || "").split(",").map((id) => id.trim()).filter(Boolean)
  );
  while (true) {
    const report = await migrationReport();
    const candidate = (report.items || []).find((item) =>
      item.step_image_calls_needed > 0 && (!allowedIds.size || allowedIds.has(item.walkthrough_id))
    );
    if (!candidate) {
      console.log(JSON.stringify(report.summary, null, 2));
      return;
    }

    const walkthroughId = candidate.walkthrough_id;
    const body = JSON.stringify({
      limit: 1,
      review_status: "all",
      dry_run: false,
      generate_asset_sheets: false,
      walkthrough_ids: [walkthroughId],
    });
    let disconnected = false;
    try {
      await request("/admin/qc/regenerate-visual-migration-images", { method: "POST", body });
    } catch (error) {
      if (error.message !== "fetch failed") throw error;
      disconnected = true;
      console.log(`WAIT ${walkthroughId}: connection dropped; checking saved steps`);
    }

    if (disconnected) {
      let savedStepCount = candidate.regenerated_step_count || 0;
      let lastProgressAt = Date.now();
      while (true) {
        await pause(20000);
        const latest = await migrationReport();
        const item = (latest.items || []).find((entry) => entry.walkthrough_id === walkthroughId);
        if (item?.step_images_regenerated) break;
        if ((item?.regenerated_step_count || 0) > savedStepCount) {
          savedStepCount = item.regenerated_step_count;
          lastProgressAt = Date.now();
        }
        if (Date.now() - lastProgressAt > 300000) {
          throw new Error(`${walkthroughId}: no saved image progress for five minutes`);
        }
      }
    }

    const stepCount = await verifyRegeneratedWalkthrough(walkthroughId);
    const latest = await migrationReport();
    console.log(`DONE ${walkthroughId}: ${stepCount} asset-sheet edits; ${latest.summary.remaining_step_image_walkthrough_count} walkthroughs remain`);
  }
}

async function run() {
  if (action === "help" || action === "--help" || action === "-h") {
    usage();
    return;
  }

  if (action === "report") {
    const data = await request("/admin/qc/visual-migration-report?limit=10000&review_status=all");
    console.log(JSON.stringify(data.summary || data, null, 2));
    return;
  }

  if (action === "images-all") {
    await runAllImages();
    return;
  }

  if (action === "prepare" || action === "asset-sheets") {
    const data = await request("/admin/qc/prepare-visual-migration", {
      method: "POST",
      body: JSON.stringify({
        limit,
        review_status: "all",
        dry_run: false,
        generate_asset_sheets: action === "asset-sheets",
      }),
    });
    console.log(JSON.stringify({
      status: data.status,
      processed_count: data.processed_count,
      generated_asset_sheet_count: data.generated_asset_sheet_count,
      estimated_asset_sheet_costs: data.estimated_asset_sheet_costs,
      items: data.items,
    }, null, 2));
    return;
  }

  if (action === "images" || action === "images-dry-run") {
    const data = await request("/admin/qc/regenerate-visual-migration-images", {
      method: "POST",
      body: JSON.stringify({
        limit,
        review_status: "all",
        dry_run: action === "images-dry-run",
        generate_asset_sheets: false,
      }),
    });
    console.log(JSON.stringify({
      status: data.status,
      processed_count: data.processed_count,
      generated_step_image_count: data.generated_step_image_count,
      estimated_step_image_costs: data.estimated_step_image_costs,
      items: data.items,
    }, null, 2));
    return;
  }

  usage();
  throw new Error(`Unknown action: ${action}`);
}

run().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
