/**
 * The map a traversal produced, drawn.
 *
 * A table of routes answers "what did it reach". The shape answers "what is this site" —
 * a hub with twelve leaves and a chain of twelve pages are the same twelve rows and very
 * different applications, and the difference is the thing worth seeing at a glance.
 *
 * Laid out by depth from the entry point, which the map itself records by order: the
 * frontier is breadth-first, so a state's position in the list is its distance from the
 * start. Nothing here needs a layout engine, and adding one would be a dependency to
 * animate a dozen circles.
 */

import type { ExploredState } from "@domain/runs/exploration";

const NODE_RADIUS = 7;
const COLUMN_WIDTH = 190;
const ROW_HEIGHT = 34;
const MARGIN = 16;

/** Depth from the entry point, read off the route rather than stored.
 *
 * `/domains/root/db` is three from `/`. The frontier records depth internally and the
 * map does not carry it, and re-deriving it from the path is both close enough and
 * honest about being derived — a wrong depth here mislabels a picture, it does not
 * mislabel a verdict. */
function depthOf(route: string): number {
  return route.split("/").filter(Boolean).length;
}

export function StateMap({ states }: { states: readonly ExploredState[] }) {
  if (states.length === 0) return null;

  const byDepth = new Map<number, ExploredState[]>();
  for (const state of states) {
    const depth = depthOf(state.route);
    byDepth.set(depth, [...(byDepth.get(depth) ?? []), state]);
  }

  const depths = [...byDepth.keys()].sort((first, second) => first - second);
  const tallest = Math.max(...depths.map((depth) => byDepth.get(depth)?.length ?? 0));
  const width = MARGIN * 2 + Math.max(1, depths.length) * COLUMN_WIDTH;
  const height = MARGIN * 2 + Math.max(1, tallest) * ROW_HEIGHT;

  const placed = new Map<string, { x: number; y: number; state: ExploredState }>();
  depths.forEach((depth, column) => {
    (byDepth.get(depth) ?? []).forEach((state, row) => {
      placed.set(state.signature, {
        x: MARGIN + column * COLUMN_WIDTH + NODE_RADIUS,
        y: MARGIN + row * ROW_HEIGHT + NODE_RADIUS,
        state,
      });
    });
  });

  const nodes = [...placed.values()];

  return (
    <div className="mb-8 w-full overflow-x-auto rounded-lg bg-white p-4 shadow-xs dark:bg-gray-800">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        role="img"
        aria-label={`Map of ${states.length} states this run reached`}
        className="max-w-none"
      >
        {/* Edges are drawn to the nearest shallower state rather than to the affordance
            that was actually taken: the stored map keeps routes and affordance keys, not
            which link led where. Drawn dashed and faint so the picture does not claim a
            precision the data does not have. */}
        {nodes.map((node) => {
          const parent = nodes
            .filter((other) => other.x < node.x)
            .sort((a, b) => Math.abs(a.y - node.y) - Math.abs(b.y - node.y))[0];
          if (parent === undefined) return null;
          return (
            <line
              key={`edge-${node.state.signature}`}
              x1={parent.x}
              y1={parent.y}
              x2={node.x}
              y2={node.y}
              className="stroke-gray-300 dark:stroke-gray-600"
              strokeWidth={1}
              strokeDasharray="3 3"
            />
          );
        })}

        {nodes.map(({ x, y, state }) => (
          <g key={state.signature}>
            <circle
              cx={x}
              cy={y}
              r={NODE_RADIUS}
              className="fill-purple-500 dark:fill-purple-400"
            >
              <title>
                {state.url} — {state.affordances.length} affordances
              </title>
            </circle>
            <text
              x={x + NODE_RADIUS + 6}
              y={y + 4}
              className="fill-gray-700 text-xs dark:fill-gray-300"
            >
              {state.route}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
