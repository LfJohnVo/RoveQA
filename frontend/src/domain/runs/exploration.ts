/**
 * What a traversal reached, as the UI needs it.
 *
 * In the domain rather than beside the port it travels through, because that is what it
 * is: a fact about a run, not a detail of how the run is fetched. The boundary test made
 * the point before this file existed — a view drawing the map imported the type from
 * `@application/ports`, which views may not reach, and the fix was not an exception to
 * the rule but the type being in the wrong place.
 */

export interface ExploredState {
  signature: string;
  route: string;
  url: string;
  title: string;
  /** Normalised `role:name` keys, which is what the signature was built from. Enough to
   *  see what a page offers; never the page's text, which belongs in evidence. */
  affordances: readonly string[];
}

export interface ExplorationMap {
  runId: string;
  states: readonly ExploredState[];
  stopReason: string | null;
  /**
   * Whether this is the whole application or as far as the run got.
   *
   * A map of twelve states that ran out of actions and one that ran out of places to go
   * look identical, and only the second can support "this page is gone" next time.
   */
  complete: boolean;
  statesDiscovered: number;
  actionsTaken: number;
  declined: number;
}
