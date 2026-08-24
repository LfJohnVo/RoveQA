"""Append one archetype's result to the smoke's JSON file.

A separate file rather than a heredoc inside the shell script: `python - <<PY` reads the
program from stdin, so anything piped in is swallowed by the heredoc. The report arrives
on stdin here precisely because nothing else is competing for it.
"""

import json
import pathlib
import sys

out, label, origin, consent, run_id, elapsed = sys.argv[1:7]
report = json.load(sys.stdin)

path = pathlib.Path(out)
existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

criteria = report.get("criteria", [])
sweep = [c for c in criteria if c.get("source") == "sweep"]
story = [c for c in criteria if c.get("source") == "plan"]

existing.append(
    {
        "archetype": label,
        "origin": origin,
        "consent": consent,
        "run_id": run_id,
        "seconds": int(elapsed),
        "verdict": report.get("verdict"),
        "pages_checked": len(sweep),
        "pages_answered": sum(1 for c in sweep if c["outcome"] == "met"),
        "story_criteria": len(story),
        "not_met": [c["criterion_id"] for c in sweep if c["outcome"] == "not_met"],
        "unverified": [c["criterion_id"] for c in sweep if c["outcome"] == "unverified"],
        "observed_failures": len(report.get("observed_failures", [])),
        "routes": sorted(c["criterion_id"].removeprefix("page:") for c in sweep),
    }
)
path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

last = existing[-1]
print(
    f"  verdict {last['verdict']}  pages {last['pages_answered']}/{last['pages_checked']}"
    f"  observed {last['observed_failures']}  {last['seconds']}s",
    file=sys.stderr,
)
