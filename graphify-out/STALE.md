# This graph is stale, and specifically so

`graphify-out/` was regenerated from the code as it stood **before Phase 15**. A commit
named `grafiphy` was made on a `main` that had not yet pulled the Phase 15 and Phase 16
merges, so what is committed here describes the architecture without any of that work:
without the generated decision union, without the page text in the observation, without the
action trace, without `PageProblems`.

Do not use it for orientation without refreshing it first. It will confidently describe
call flows that no longer exist and miss the ones that matter.

## Refreshing it

```bash
uv tool install graphifyy     # or see .claude/skills/graphify/SKILL.md
make graphify-refresh         # graphify update .
```

Neither `graphify` nor `uv` was installed on the machine that wrote this note, and `pip`
there pointed at the system Python, so installing a tool would have been a change nobody
asked for. That is the only reason this file exists instead of a fresh graph.

## Commit it on its own

A refresh is roughly 360,000 lines. Mixed into a functional change it buries the review;
the diff that matters becomes invisible among regenerated JSON. One commit, nothing else in
it.
