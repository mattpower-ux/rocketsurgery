const API_URL = (process.env.ROCKETSURGERY_API_URL || "https://rocketsurgery-api.onrender.com").replace(/\/$/, "");
const ADMIN_TOKEN = process.env.ADMIN_API_TOKEN || "";
const action = process.argv[2] || "report";
const limit = Number(process.argv[3] || 10);

function usage() {
  console.log("Usage:");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs report");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs prepare 10");
  console.log("  ADMIN_API_TOKEN=... node scripts/run_visual_migration.mjs asset-sheets 3");
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

  usage();
  throw new Error(`Unknown action: ${action}`);
}

run().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
