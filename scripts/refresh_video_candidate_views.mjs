import { readFile, writeFile } from "node:fs/promises";

const catalogPath = new URL("../research/next_50_video_candidates.json", import.meta.url);
const catalog = JSON.parse(await readFile(catalogPath, "utf8"));
const items = catalog.items || [];
let next = 0;

async function check(item) {
  const video = item.source_video || {};
  if (!video.url) return;
  try {
    const response = await fetch(video.url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; RocketSurgeryResearch/1.0)" },
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const html = await response.text();
    const views = html.match(/"viewCount":"(\d+)"/);
    if (!views) throw new Error("No video view count in page metadata");
    video.observed_views = Number(views[1]);
    video.view_count_checked_at = new Date().toISOString();
    const published = html.match(/"publishDate":"([^\"]+)"/);
    if (published) video.publish_date = published[1];
    delete video.metadata_error;
    console.log(`${item.id}: ${video.observed_views.toLocaleString()} views`);
  } catch (error) {
    video.metadata_error = String(error.message || error);
    console.log(`${item.id}: view count unavailable (${video.metadata_error})`);
  }
}

async function worker() {
  while (next < items.length) {
    const item = items[next++];
    await check(item);
  }
}

await Promise.all(Array.from({ length: 3 }, worker));
const ranked = items.filter((item) => item.source_video?.view_count_checked_at)
  .sort((a, b) => b.source_video.observed_views - a.source_video.observed_views);
ranked.forEach((item, index) => { item.popularity_rank_within_candidates = index + 1; });
catalog.view_count_checked_at = new Date().toISOString();
catalog.verified_count = ranked.length;
await writeFile(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`);
console.log(`Verified ${ranked.length}/${items.length} video view counts.`);
