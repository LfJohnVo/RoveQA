/**
 * Parse a `--timeout` value.
 *
 * The flag has always meant milliseconds, and every example we published got it
 * wrong: `--timeout 300` reads as five minutes and lasts three tenths of a second.
 * The CI example asked for `1800` — half an hour, it thought — and gave up after
 * 1.8 seconds. It fails safe (exit 7, the run keeps going) and it is useless.
 *
 * So a unit is now allowed and encouraged: `300s`, `5m`, `1h`. A bare number is
 * still milliseconds, because changing what existing scripts mean would be worse
 * than the trap itself. Garbage is rejected instead of becoming NaN, which used to
 * silently mean "no timeout at all".
 */

import { CliError } from "./errors.js";

const UNITS: Record<string, number> = { ms: 1, s: 1_000, m: 60_000, h: 3_600_000 };

const MAX_MS = 24 * 3_600_000;
/** A client-side wait longer than a day is a script nobody is watching. */

export function parseDurationMs(raw: string | undefined, fallbackMs: number): number {
  if (raw === undefined) {
    return fallbackMs;
  }

  const match = /^(\d+)(ms|s|m|h)?$/.exec(raw.trim());
  if (match === null) {
    throw new CliError("USAGE_ERROR", `--timeout ${raw} is not a duration`, {
      nextAction: "Use a unit: --timeout 300s, --timeout 5m. A bare number is milliseconds.",
    });
  }

  const value = Number(match[1]) * UNITS[match[2] ?? "ms"]!;
  if (value < 1 || value > MAX_MS) {
    throw new CliError("USAGE_ERROR", `--timeout ${raw} is out of range`, {
      nextAction: `Choose between 1ms and 24h.`,
    });
  }
  return value;
}
