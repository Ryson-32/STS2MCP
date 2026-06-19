#!/usr/bin/env node

const { spawnSync } = require("node:child_process");

const scriptArgs = process.argv.slice(2);

if (scriptArgs.length === 0) {
  console.error("Usage: node .codex/hooks/run-python.cjs <script.py> [args...]");
  process.exit(64);
}

const candidates = [
  { command: "python3", args: ["-X", "utf8"], label: "python3" },
  { command: "python", args: ["-X", "utf8"], label: "python" },
  { command: "py", args: ["-3", "-X", "utf8"], label: "py -3" },
];

for (const candidate of candidates) {
  const result = spawnSync(candidate.command, [...candidate.args, ...scriptArgs], {
    stdio: "inherit",
    windowsHide: true,
  });

  if (result.error?.code === "ENOENT") {
    continue;
  }

  if (result.error) {
    console.error(`Failed to run ${candidate.label}: ${result.error.message}`);
    process.exit(1);
  }

  if (result.signal) {
    console.error(`${candidate.label} exited due to signal ${result.signal}`);
    process.exit(1);
  }

  process.exit(result.status ?? 0);
}

console.error("Could not find a Python interpreter. Tried: python3, python, py -3.");
process.exit(127);
