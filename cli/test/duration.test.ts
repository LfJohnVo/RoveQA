/**
 * `--timeout` units.
 *
 * Every example we shipped read `--timeout 1800` as half an hour. It is 1.8 seconds,
 * and the CI adapter therefore gave up before any run could finish.
 */

import { describe, expect, it } from "vitest";

import { parseDurationMs } from "../src/duration.js";
import { CliError } from "../src/errors.js";

describe("parseDurationMs", () => {
  it("keeps a bare number as milliseconds", () => {
    // Not what most people mean, but changing it would silently redefine what every
    // existing script asked for. The units below are the way out, not a rewrite.
    expect(parseDurationMs("1800", 0)).toBe(1800);
  });

  it.each([
    ["500ms", 500],
    ["300s", 300_000],
    ["5m", 300_000],
    ["1h", 3_600_000],
  ])("reads %s", (raw, expected) => {
    expect(parseDurationMs(raw, 0)).toBe(expected);
  });

  it("uses the fallback when the flag is absent", () => {
    expect(parseDurationMs(undefined, 300_000)).toBe(300_000);
  });

  it.each(["", "soon", "5 minutes", "-1", "3.5s", "10d"])("refuses %s", (raw) => {
    // Number("soon") is NaN, and a NaN timeout used to mean "wait forever" — the one
    // outcome a client asking for a bound never wants.
    expect(() => parseDurationMs(raw, 0)).toThrow(CliError);
  });

  it("refuses a wait longer than a day", () => {
    expect(() => parseDurationMs("25h", 0)).toThrow(/out of range/);
  });
});
