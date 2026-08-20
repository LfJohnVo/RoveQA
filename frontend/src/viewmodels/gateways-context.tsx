/**
 * Handing the gateways to React.
 *
 * The provider and the hook only. What they carry, and how the real ones are built,
 * lives in `gateways.ts` — so a ViewModel importing the type never pulls in React, and
 * this file stays a component module.
 */

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { buildGateways, type Gateways } from "@viewmodels/gateways";

const GatewaysContext = createContext<Gateways | null>(null);

export function GatewaysProvider({
  children,
  gateways,
}: {
  children: ReactNode;
  /** Supplied by tests; built from configuration in the real app. */
  gateways?: Gateways;
}) {
  const value = useMemo(() => gateways ?? buildGateways(), [gateways]);
  return <GatewaysContext.Provider value={value}>{children}</GatewaysContext.Provider>;
}

/* A hook belongs with the context it reads. Splitting them to satisfy fast refresh
   would mean exporting the context object itself, which is a wider surface than the
   hook and invites someone to consume it directly. */
// eslint-disable-next-line react-refresh/only-export-components
export function useGateways(): Gateways {
  const gateways = useContext(GatewaysContext);
  if (gateways === null) {
    // Louder than a silent undefined: a ViewModel rendered outside the provider would
    // otherwise fail somewhere deep in a fetch with no hint of the real cause.
    throw new Error("useGateways was called outside GatewaysProvider");
  }
  return gateways;
}
