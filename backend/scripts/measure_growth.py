"""Measure what grows, and print it.

Run inside the gates container:

    docker compose --profile gates run --rm backend-tests python scripts/measure_growth.py

The numbers land in `docs/status/PERFORMANCE_PROFILE.md`. They are a snapshot, not a
gate: the gate is `tests/test_growth_profile.py`, which asserts the *shape* of the
growth and survives rewording. These say how big the shapes actually are.
"""

import asyncio
import os
import pickle

from sqlalchemy import text

from agentic_qa.application.ports.models import PlanningRequest
from agentic_qa.domain.agent.state import AgentState, EpisodeSummary, StepOutcome, StepRecord
from agentic_qa.infrastructure.inference.prompts import build_planning_prompt
from agentic_qa.infrastructure.persistence.postgres.engine import create_engine

DEFAULT_TEST_DSN = "postgresql+asyncpg://agentic:agentic@postgres:5432/agentic_qa_test"


def test_dsn() -> str:
    # Its own database, like the suite: this script reads sizes, and pointing it at
    # the application's would report whatever a developer happens to be running.
    return os.environ.get("POSTGRES_TEST_DSN", DEFAULT_TEST_DSN)


def run_for(episodes: int, steps: int = 30) -> AgentState:
    agent = AgentState(run_id="run-measure", goal="exercise the whole application")
    for episode in range(episodes):
        for step in range(steps):
            agent.record_step(
                StepRecord(
                    index=step,
                    intent=f"do the thing {step}",
                    outcome=StepOutcome.SUCCEEDED,
                    detail="it worked as expected",
                )
            )
        agent.close_episode(
            EpisodeSummary(
                episode_index=episode,
                goal=f"episode {episode}",
                steps_taken=steps,
                succeeded=True,
                summary="everything the episode did, in one line",
            )
        )
    return agent


def prompt_for(agent: AgentState) -> str:
    return build_planning_prompt(
        PlanningRequest(
            goal=agent.goal,
            observation="a page with some controls on it" * 20,
            recent_steps=agent.recent_steps,
            episode_summaries=agent.episode_summaries,
            folded_episodes=agent.folded_episodes,
        )
    )


async def table_sizes() -> list[tuple[str, str, int]]:
    engine = create_engine(test_dsn())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT c.relname,
                           pg_size_pretty(pg_total_relation_size(c.oid)) AS pretty,
                           coalesce(s.n_live_tup, 0) AS rows
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
                    WHERE n.nspname = 'public' AND c.relkind = 'r'
                    ORDER BY pg_total_relation_size(c.oid) DESC
                    LIMIT 8
                    """
                )
            )
            return [(row[0], row[1], row[2]) for row in result]
    finally:
        await engine.dispose()


def main() -> None:
    print("episodes  state_bytes  prompt_chars  summaries  folded")
    for episodes in (1, 10, 20, 200, 1000):
        agent = run_for(episodes)
        print(
            f"{episodes:>8}  {len(pickle.dumps(agent)):>11}  {len(prompt_for(agent)):>12}  "
            f"{len(agent.episode_summaries):>9}  {agent.folded_episodes:>6}"
        )

    print("\nsteps  state_bytes (one episode)")
    for steps in (10, 100, 5_000):
        print(f"{steps:>5}  {len(pickle.dumps(run_for(1, steps))):>11}")

    print("\nlargest tables in the test database")
    for name, pretty, rows in asyncio.run(table_sizes()):
        print(f"  {name:<28} {pretty:>10}  {rows:>8} rows")


if __name__ == "__main__":
    main()
