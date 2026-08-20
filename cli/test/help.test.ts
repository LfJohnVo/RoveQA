/**
 * `roveqa --help`, from the point of view of somebody who just installed the binary.
 *
 * Asking for help and succeeding is not a usage error, so it comes back as an ordinary
 * success envelope: an agent reads the command list the way it reads every other answer,
 * and a person can find out what the tool does without reading the source.
 */

import { describe, expect, it } from "vitest";

import { parseSingleJson, runCli } from "./helpers.js";

describe("discovering the commands", () => {
  it("lists them as a success, not as an error", async () => {
    const result = await runCli(["--help", "--output", "json"]);

    expect(result.code).toBe(0);
    const envelope = parseSingleJson(result.stdout) as {
      data?: { commands?: { name: string }[] };
    };
    const names = (envelope.data?.commands ?? []).map((command) => command.name);
    expect(names).toContain("doctor");
    expect(names).toContain("run wait");
    expect(names).toContain("run failure");
  });

  it("prints something a person can read in text mode", async () => {
    const result = await runCli(["--help"]);

    expect(result.code).toBe(0);
    expect(result.stdout).toMatch(/Usage: roveqa <command>/);
    expect(result.stdout).toMatch(/plan lint/);
  });

  it("still refuses an empty invocation, and points at help", async () => {
    // Different from asking for help: nothing was requested, so there is nothing to do.
    const result = await runCli([]);

    expect(result.code).not.toBe(0);
    // Either stream: which one carries a text-mode error is the envelope suite's
    // business, and this test is about whether a newcomer is pointed anywhere at all.
    expect(result.stdout + result.stderr).toMatch(/roveqa --help/);
  });
});
