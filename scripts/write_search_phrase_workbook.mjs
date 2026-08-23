import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";


async function loadArtifactTool() {
  try {
    return await import("@oai/artifact-tool");
  } catch (error) {
    if (process.env.ARTIFACT_TOOL_MODULE) {
      const configured = process.env.ARTIFACT_TOOL_MODULE;
      const moduleUrl = configured.startsWith("file:")
        ? configured
        : pathToFileURL(configured).href;
      return import(moduleUrl);
    }

    for (const moduleDir of (process.env.NODE_PATH || "").split(path.delimiter).filter(Boolean)) {
      const candidate = path.join(moduleDir, "@oai", "artifact-tool", "dist", "artifact_tool.mjs");
      try {
        await fs.access(candidate);
        return import(pathToFileURL(candidate).href);
      } catch {
        continue;
      }
    }

    throw error;
  }
}


const { SpreadsheetFile, Workbook } = await loadArtifactTool();


const __filename = fileURLToPath(import.meta.url);
const root = path.resolve(path.dirname(__filename), "..");
const outputDir = path.join(root, "outputs", "search_phrase_taxonomy");
const dataPath = path.join(outputDir, "workbook_data.json");
const workbookPath = path.join(outputDir, "rocket_surgery_actionable_walkthrough_taxonomy.xlsx");


const data = JSON.parse(await fs.readFile(dataPath, "utf8"));
const workbook = Workbook.create();


function writeSheet(sheetName, headers, rows, tableName, widths = []) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;

  const values = [headers, ...rows];
  const range = sheet.getRangeByIndexes(0, 0, values.length, headers.length);
  range.values = values;
  range.format.wrapText = true;
  range.format.font = { name: "Aptos", size: 10, color: "#111827" };
  range.format.borders = { preset: "all", style: "thin", color: "#E5E7EB" };

  const header = sheet.getRangeByIndexes(0, 0, 1, headers.length);
  header.format = {
    fill: "#123C69",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
  };

  sheet.freezePanes.freezeRows(1);

  if (rows.length > 0) {
    const tableRange = sheet.getRangeByIndexes(0, 0, values.length, headers.length);
    const table = sheet.tables.add(tableRange.address, true, tableName);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
  }

  widths.forEach((width, index) => {
    if (width) {
      sheet.getRangeByIndexes(0, index, values.length, 1).format.columnWidth = width;
    }
  });

  sheet.getRangeByIndexes(0, 0, Math.min(values.length, 250), headers.length).format.autofitRows();
  return sheet;
}


const generatedAtLabel = data.summary.generated_at.replace("T", " ").replace("Z", " UTC");

const summaryRows = [
  ["Source file", data.summary.source_file],
  ["Generated at", generatedAtLabel],
  ["Source phrases reviewed", data.summary.source_phrase_count],
  ["Kept actionable phrase variants", data.summary.kept_actionable_phrase_count],
  ["Removed non-walkthrough phrases", data.summary.removed_phrase_count],
  ["Canonical walkthrough groups", data.summary.canonical_walkthrough_count],
  ["Refinement rule", data.summary.rule],
  ["GitHub taxonomy file", "backend/app/search_phrase_taxonomy.json"],
  ["Review status", "All canonical groups are marked DRAFT until approved in QC."],
];

const summary = workbook.worksheets.add("Summary");
summary.showGridLines = false;
summary.getRange("A1:B1").values = [["RocketSurgery Actionable Walkthrough Taxonomy", ""]];
summary.getRange("A1:B1").merge();
summary.getRange("A1:B1").format = {
  fill: "#123C69",
  font: { bold: true, color: "#FFFFFF", size: 14 },
};
summary.getRangeByIndexes(2, 0, summaryRows.length, 2).values = summaryRows;
summary.getRange("A3:A11").format = {
  fill: "#EAF2F8",
  font: { bold: true, color: "#123C69" },
};
summary.getRange("A3:B11").format.borders = { preset: "all", style: "thin", color: "#D1D5DB" };
summary.getRange("A:B").format.columnWidth = 38;
summary.getRange("B:B").format.columnWidth = 92;
summary.freezePanes.freezeRows(2);

writeSheet(
  "Clean Actionable Phrases",
  [
    "Canonical ID",
    "Canonical Query",
    "Canonical Title",
    "Category",
    "Safety Level",
    "Query Variant",
    "Original Rank",
    "Source Cluster",
    "Priority Score",
    "Search Intent",
    "Review Status",
  ],
  data.kept_phrases.map((item) => [
    item.canonical_id,
    item.canonical_query,
    item.canonical_title,
    item.category,
    item.safety_level,
    item.query_variant,
    item.original_rank,
    item.source_cluster,
    item.priority_score,
    item.search_intent,
    item.review_status,
  ]),
  "CleanActionablePhrases",
  [26, 36, 36, 20, 24, 46, 14, 26, 14, 30, 16],
);

writeSheet(
  "Taxonomy Index",
  [
    "Walkthrough ID",
    "Canonical Query",
    "Title",
    "Category",
    "Safety Level",
    "Review Status",
    "Alias Count",
    "Kept Phrases",
    "Removed From Cluster",
    "Source Clusters",
    "Trigger Aliases",
  ],
  data.taxonomy_entries.map((item) => [
    item.walkthrough_id,
    item.canonical_query,
    item.title,
    item.category,
    item.safety_level,
    item.review_status,
    item.alias_count,
    item.kept_phrase_count,
    item.removed_phrase_count_from_cluster,
    item.source_clusters.join(", "),
    item.aliases.join(" | "),
  ]),
  "TaxonomyIndex",
  [32, 38, 38, 20, 24, 16, 12, 14, 18, 30, 90],
);

writeSheet(
  "Removed Non-Actionable",
  [
    "Search Phrase",
    "Original Rank",
    "Source Cluster",
    "Drop Reason",
    "Priority Score",
    "Search Intent",
  ],
  data.removed_phrases.map((item) => [
    item.search_phrase,
    item.original_rank,
    item.source_cluster,
    item.drop_reason,
    item.priority_score,
    item.search_intent,
  ]),
  "RemovedNonActionable",
  [50, 14, 28, 34, 14, 30],
);

writeSheet(
  "Methodology",
  ["Rule", "Detail"],
  [
    ["Keep", "Queries that directly ask RocketSurgery to perform a specific repair, installation, removal, cleaning, or build walkthrough."],
    ["Group", "Multiple phrasings that produce the same practical walkthrough are grouped under one canonical walkthrough ID."],
    ["Drop", "Near-me service searches, contractor hiring, cost research, permits, tool lists, timelines, tips, mistakes, signs, prevention, and broad home improvement topics."],
    ["Review status", "All canonical groups are drafts. Approval should happen through the QC workflow before a walkthrough is promoted."],
    ["GitHub connection", "The source taxonomy is written to backend/app/search_phrase_taxonomy.json so it can be used by the app index layer."],
  ],
  "MethodologyRules",
  [28, 110],
);

await fs.mkdir(outputDir, { recursive: true });

for (const sheetName of ["Summary", "Taxonomy Index", "Clean Actionable Phrases", "Removed Non-Actionable"]) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  const fileName = `${sheetName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.png`;
  await fs.writeFile(path.join(outputDir, fileName), new Uint8Array(await preview.arrayBuffer()));
}

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(workbookPath);

console.log(JSON.stringify({
  workbookPath,
  previewDir: outputDir,
  sheets: workbook.worksheets.items.map((sheet) => sheet.name),
}, null, 2));
