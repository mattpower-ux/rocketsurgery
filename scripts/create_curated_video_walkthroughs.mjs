import { readFile } from "node:fs/promises";

const API_URL = (process.env.ROCKETSURGERY_API_URL || "https://rocketsurgery-api.onrender.com").replace(/\/$/, "");
const ADMIN_TOKEN = process.env.ADMIN_API_TOKEN || "";
if (!ADMIN_TOKEN) throw new Error("ADMIN_API_TOKEN is required.");

const catalog = JSON.parse(await readFile(new URL("../research/next_50_video_candidates.json", import.meta.url), "utf8"));
const ids = process.argv.slice(2).map(Number);
if (!ids.length) throw new Error("Pass one or more catalog IDs, for example: 6 2 5");

const curated = {
  6: {
    brief: {
      required_steps: [
        "Inspect exterior lens oxidation; damaged lenses or internal condensation need a different repair",
        "Wash and dry the lens, then mask surrounding painted trim",
        "Wet-sand the oxidized lens evenly using one kit's specified abrasive progression",
        "Rinse and refine the surface using the same kit's finishing steps",
        "Apply the kit-compatible UV-protective clear coat and allow its stated cure time",
        "Inspect clarity and confirm the headlamp functions normally",
      ],
      common_mistakes: ["Sanding painted trim", "Mixing incompatible restoration systems", "Skipping UV protection"],
      image_guidance: ["Use one silver sedan and the same left polycarbonate headlamp in every panel", "Show only the lens changing from cloudy to clear"],
      tools_and_materials: ["matched headlamp restoration kit", "masking tape", "water", "clean cloth", "kit-compatible UV coating"],
      branch_questions: ["Is the haze on the outer lens rather than inside a cracked or leaking assembly?"],
    },
    reference_urls: [
      "https://www.3m.com/3M/en_US/collision-repair-us/applications/paint-finishing-and-detail-shop/",
      "https://www.3m.com/3M/en_US/p/d/b40072114/",
    ],
  },
  2: {
    brief: {
      required_steps: [
        "Check whether the small outer-layer chip is suitable for a DIY resin kit; refer unsafe, spreading, edge, or vision-obstructing damage to a professional",
        "Clean and thoroughly dry the chip and surrounding windshield",
        "Center the kit applicator over the chip and apply resin according to its directions",
        "Use the kit's specified pressure and release cycle to fill the chip",
        "Apply the curing strip and cure the resin as directed",
        "Remove the strip, level excess cured resin as directed, and inspect the repair",
      ],
      common_mistakes: ["Attempting to repair multi-layer damage", "Trapping moisture or dirt beneath resin", "Driving before cure is complete"],
      image_guidance: ["Same silver sedan windshield, same single small chip on the passenger side in every panel", "Keep the windshield curve and surrounding hood consistent"],
      tools_and_materials: ["windshield chip repair kit", "clean cloth", "curing strip"],
      branch_questions: ["Is the damage a small eligible chip rather than a long crack or damaged inner layer?"],
    },
    reference_urls: [
      "https://www.rainx.com/product/rain-x-windshield-repair-kit/",
      "https://www.rainx.com/wp-content/uploads/2013/05/RX600001WindshieldRepairInst_v2.pdf",
    ],
  },
  5: {
    brief: {
      required_steps: [
        "Inspect the torn lanai screen panel and confirm safe access to its frame",
        "Measure the opening and select matching screen mesh and spline",
        "Remove the old spline and damaged mesh without bending the frame",
        "Lay a single oversized mesh panel flat across the opening",
        "Roll spline into the frame channel while keeping the mesh evenly taut",
        "Trim excess mesh and inspect the perimeter for gaps or wrinkles",
      ],
      common_mistakes: ["Changing mesh color between panels", "Stretching the mesh unevenly", "Working on a high enclosure panel without safe access"],
      image_guidance: ["Same white aluminum lanai frame and charcoal screen mesh in every panel", "Show the same one damaged panel from removal through finished replacement"],
      tools_and_materials: ["matching screen mesh", "matching spline", "spline roller", "utility knife", "tape measure"],
      branch_questions: ["Is the damaged panel reachable without working at unsafe height?"],
    },
    reference_urls: [],
  },
};

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Admin-Token": ADMIN_TOKEN, ...(options.headers || {}) },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

async function findByQuery(query) {
  const data = await request("/admin/walkthroughs?limit=1000");
  return (data.walkthroughs || []).find((item) => item.query === query || item.title === `PLANNED WALKTHROUGH: ${query}`);
}

async function verify(walkthroughId) {
  const data = await request(`/admin/walkthroughs/${encodeURIComponent(walkthroughId)}`);
  const manifest = data.walkthrough || {};
  const steps = manifest.steps || [];
  if (manifest.visual_assets?.asset_status !== "generated" || !manifest.visual_assets?.asset_sheet_url) {
    throw new Error(`${walkthroughId}: asset sheet missing`);
  }
  if (steps.length < 4 || steps.some((step) => !step.imageUrl || step.imageGenerationMode !== "asset_sheet_edit")) {
    throw new Error(`${walkthroughId}: missing or non-reference step image`);
  }
  console.log(`VERIFIED ${walkthroughId}: asset sheet and ${steps.length} asset-sheet edits; draft for editorial review`);
}

for (const id of ids) {
  const item = (catalog.items || []).find((candidate) => candidate.id === id);
  if (!item || !curated[id]) throw new Error(`Catalog ID ${id} has no vetted research brief`);
  const existing = await findByQuery(item.query);
  if (existing) {
    console.log(`EXISTS ${id}: ${existing.storage_walkthrough_id || existing.walkthrough_id}`);
    continue;
  }
  const body = {
    query: item.query,
    video_url: item.source_video.url,
    video_title: item.source_video.title,
    video_views: item.source_video.observed_views,
    ...curated[id],
  };
  console.log(`GENERATING ${id}: ${item.query}`);
  let result;
  try {
    result = await request("/admin/create-curated-video-walkthrough", {
      method: "POST",
      body: JSON.stringify(body),
    });
  } catch (error) {
    console.log(`Connection interrupted for ${id}: ${error.message}. Checking for completed save.`);
    for (let attempt = 0; attempt < 20 && !result; attempt++) {
      await wait(30000);
      const saved = await findByQuery(item.query);
      if (saved) result = { status: "created_after_disconnect", walkthrough_id: saved.storage_walkthrough_id || saved.walkthrough_id };
    }
    if (!result) throw error;
  }
  await verify(result.walkthrough_id);
}
