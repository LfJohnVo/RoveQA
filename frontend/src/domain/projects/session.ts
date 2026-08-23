/**
 * A borrowed browser session, as the console needs it.
 *
 * Deliberately without the session itself. There is no field for it here and no endpoint
 * behind one: a stored session goes in and never comes back out, and a type with a place
 * to put it would be the first step to a screen that shows it (ADR 0019).
 *
 * The console reads and revokes; it does not register. Pasting a credential into a web
 * form routes it through another surface — browser memory, autofill, a screenshot — for
 * no gain over `roveqa session register <file>`, which reads it once and sends it once.
 */

export interface EnvironmentSession {
  sessionId: string;
  environmentId: string;
  label: string;
  establishedAt: string;
  /** Absent when nobody stated one. Different from an expiry in the past: one is
   *  unknown, the other is known to be over. */
  validUntil: string | null;
  establishedBy: string;
}

export interface Environment {
  environmentId: string;
  projectId: string;
  name: string;
  defaultRunPolicyId: string | null;
}

/** Whether the stated validity is over. Unknown validity is not expiry. */
export function hasExpired(session: EnvironmentSession, now: Date): boolean {
  if (session.validUntil === null) return false;
  return new Date(session.validUntil).getTime() <= now.getTime();
}

/**
 * The session a run of this environment would borrow, or null.
 *
 * Newest first is what the server returns, so this is the head — but it is written as a
 * function rather than `sessions[0]` because "which one is current" is a rule, and a rule
 * that lives in an index expression is one nobody can find later.
 */
export function currentSession(
  sessions: readonly EnvironmentSession[],
): EnvironmentSession | null {
  return sessions[0] ?? null;
}
