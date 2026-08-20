/**
 * The gateways an app run is wired with, and how the real ones are built.
 *
 * Separate from the provider component so each module exports one kind of thing: a
 * file that exports both a component and helpers defeats fast refresh, and the lint
 * rule that says so is right — mixing them is also how a "small helper" ends up
 * importing React for no reason.
 */

import type {
  MemoryGateway,
  ProjectGateway,
  RunEventStream,
  RunGateway,
  StoryGateway,
} from "@application/ports/gateways";
import {
  ApiClient,
  HttpMemoryGateway,
  HttpProjectGateway,
  HttpRunGateway,
  HttpStoryGateway,
} from "@infrastructure/api/client";
import { WebSocketRunEventStream } from "@infrastructure/realtime/run-events";

export interface Gateways {
  projects: ProjectGateway;
  runs: RunGateway;
  events: RunEventStream;
  memory: MemoryGateway;
  stories: StoryGateway;
}

/** The composition root: the one place that names a concrete adapter. */
export function buildGateways(baseUrl = ""): Gateways {
  const client = new ApiClient({ baseUrl });
  return {
    projects: new HttpProjectGateway(client),
    runs: new HttpRunGateway(client),
    // Only pass the option when there is one: with exactOptionalPropertyTypes an
    // explicit `undefined` is a different thing from an absent key.
    events: new WebSocketRunEventStream(baseUrl === "" ? {} : { baseUrl }),
    memory: new HttpMemoryGateway(client),
    stories: new HttpStoryGateway(client),
  };
}
