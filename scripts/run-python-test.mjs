import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const testScript = path.join(repoRoot, "scripts", "test_asset_sheet_first_generation.py");

const candidates = [
  process.env.PYTHON,
  process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, "Programs", "Python", "Python314", "python.exe"),
  "python",
  "python3",
  "py"
].filter(Boolean);

let lastResult = null;

for (const candidate of candidates) {
  const isPath = candidate.includes("\\") || candidate.includes("/");
  if (isPath && !existsSync(candidate)) {
    continue;
  }

  const args = candidate === "py" ? ["-3", testScript] : [testScript];
  const result = spawnSync(candidate, args, {
    cwd: repoRoot,
    stdio: "inherit",
    shell: false,
  });
  lastResult = result;

  if (!result.error) {
    process.exit(result.status ?? 0);
  }
}

console.error(lastResult?.error?.message || "No Python interpreter found.");
process.exit(1);
