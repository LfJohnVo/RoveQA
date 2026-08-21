/**
 * Windmill's component vocabulary, as React.
 *
 * The class strings are the template's, unchanged. They live here rather than being
 * retyped per page for the reason any design system exists: a card that is
 * `rounded-lg shadow-xs` in five places and `rounded-md shadow-sm` in the sixth is how a
 * borrowed look stops looking borrowed.
 *
 * Nothing here knows what a run or a project is. These are surfaces; the pages supply
 * the meaning.
 */

import type { ReactNode } from "react";

export function PageTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="my-6 text-2xl font-semibold text-gray-700 dark:text-gray-200">{children}</h2>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h3 className="mb-4 text-lg font-semibold text-gray-600 dark:text-gray-300">{children}</h3>
  );
}

export function Lede({ children }: { children: ReactNode }) {
  return <p className="mb-6 text-sm text-gray-600 dark:text-gray-400">{children}</p>;
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={[
        "min-w-0 rounded-lg bg-white p-4 shadow-xs dark:bg-gray-800",
        className ?? "",
      ].join(" ")}
    >
      {children}
    </div>
  );
}

/** A number worth reading at a glance, with the word that says what it counts. */
export function StatCard({
  label,
  value,
  tone = "purple",
  icon,
}: {
  label: string;
  value: ReactNode;
  tone?: "purple" | "green" | "red" | "yellow" | "blue";
  icon?: ReactNode;
}) {
  const tones = {
    purple: "text-purple-500 bg-purple-100 dark:text-purple-100 dark:bg-purple-500",
    green: "text-green-500 bg-green-100 dark:text-green-100 dark:bg-green-500",
    red: "text-red-500 bg-red-100 dark:text-red-100 dark:bg-red-500",
    yellow: "text-yellow-500 bg-yellow-100 dark:text-yellow-100 dark:bg-yellow-500",
    blue: "text-blue-500 bg-blue-100 dark:text-blue-100 dark:bg-blue-500",
  } as const;

  return (
    <Card className="flex items-center">
      {icon === undefined ? null : (
        <div className={`mr-4 rounded-full p-3 ${tones[tone]}`}>{icon}</div>
      )}
      <div>
        <p className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-400">{label}</p>
        <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">{value}</p>
      </div>
    </Card>
  );
}

const BADGE_TONES = {
  /* Windmill's four badge colours, mapped onto what a run can answer. Green only ever
     means the product was checked and held; yellow is the run admitting it could not
     tell, which is a different thing from failure and must not look like one. */
  pass: "text-green-700 bg-green-100 dark:bg-green-700 dark:text-green-100",
  fail: "text-red-700 bg-red-100 dark:bg-red-700 dark:text-red-100",
  unsure: "text-yellow-700 bg-yellow-100 dark:bg-yellow-700 dark:text-yellow-100",
  neutral: "text-gray-700 bg-gray-100 dark:bg-gray-700 dark:text-gray-100",
} as const;

export type BadgeTone = keyof typeof BADGE_TONES;

export function Badge({
  tone,
  dataTone,
  children,
}: {
  tone: BadgeTone;
  /** The domain's own name for what this colour means, on the element carrying the word.
   *  A test that asserts a verdict is not painted as a failure has to read it off the
   *  thing the reader sees, not off a wrapper that could drift away from it. */
  dataTone?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={`rounded-full px-2 py-1 text-xs font-semibold leading-tight ${BADGE_TONES[tone]}`}
      {...(dataTone === undefined ? {} : { "data-tone": dataTone })}
    >
      {children}
    </span>
  );
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
  block?: boolean;
};

const BUTTON_VARIANTS = {
  primary:
    "text-white bg-purple-600 border border-transparent active:bg-purple-600 hover:bg-purple-700 focus:shadow-outline-purple",
  secondary:
    "text-gray-600 border border-gray-300 dark:text-gray-400 active:bg-transparent hover:border-gray-500 focus:border-gray-500 active:text-gray-500 focus:shadow-outline-gray dark:border-gray-600 dark:hover:border-gray-400",
  danger:
    "text-white bg-red-600 border border-transparent active:bg-red-600 hover:bg-red-700 focus:shadow-outline-red",
} as const;

export function Button({ variant = "primary", block, className, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      className={[
        "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium leading-5 transition-colors duration-150 focus:outline-none",
        // A disabled control that still looks pressable is a click that silently does
        // nothing, which reads as the app being broken rather than busy.
        "disabled:cursor-not-allowed disabled:opacity-60",
        BUTTON_VARIANTS[variant],
        block === true ? "w-full" : "",
        className ?? "",
      ].join(" ")}
    />
  );
}

/**
 * A message that is not content: loading, empty, or something went wrong.
 *
 * `error` is announced. Everything else is not — a screen reader interrupting to say
 * "Loading projects…" is noise, while a failure the reader cannot see otherwise is not.
 */
export function Notice({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "info" | "error" | "warning";
}) {
  const tones = {
    info: "text-gray-600 bg-white dark:text-gray-400 dark:bg-gray-800",
    error: "text-red-700 bg-red-50 dark:text-red-100 dark:bg-red-800",
    warning: "text-yellow-700 bg-yellow-50 dark:text-yellow-100 dark:bg-yellow-800",
  } as const;

  return (
    <p
      className={`mb-4 rounded-lg px-4 py-3 text-sm shadow-xs ${tones[tone]}`}
      {...(tone === "error" ? { role: "alert" as const } : {})}
    >
      {children}
    </p>
  );
}

/** A field label with its control underneath, the way Windmill's forms are built. */
export function Field({
  label,
  hint,
  error,
  htmlFor,
  children,
}: {
  label: string;
  hint?: ReactNode;
  error?: string | undefined;
  htmlFor?: string;
  children: ReactNode;
}) {
  // The hint and the error sit *outside* the label on purpose. Inside, they become part
  // of the control's accessible name — "Application origin The only place that knows
  // which application this tests…" — which is both unusable to hear and impossible to
  // query by. The label element wraps only its own words and the control.
  return (
    <div className="mt-4">
      <label className="block text-sm" htmlFor={htmlFor}>
        <span className="text-gray-700 dark:text-gray-400">{label}</span>
        {children}
      </label>
      {hint === undefined ? null : (
        <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{hint}</p>
      )}
      {error === undefined ? null : (
        <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}

/**
 * A table in Windmill's card: rounded, clipped, and able to scroll on its own.
 *
 * `label` is required. A page here can show two tables at once — evidence and timeline —
 * and an unnamed table is one a screen reader announces as "table" twice, with no way to
 * tell which is which.
 */
export function TableCard({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-8 w-full overflow-hidden rounded-lg shadow-xs">
      <div className="w-full overflow-x-auto">
        <table className="w-full whitespace-nowrap" aria-label={label}>
          {children}
        </table>
      </div>
    </div>
  );
}

export function TableHead({ children }: { children: ReactNode }) {
  return (
    <thead>
      <tr className="border-b bg-gray-50 text-left text-xs font-semibold tracking-wide text-gray-500 uppercase dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
        {children}
      </tr>
    </thead>
  );
}

export function TableBody({ children }: { children: ReactNode }) {
  return (
    <tbody className="divide-y bg-white dark:divide-gray-700 dark:bg-gray-800">{children}</tbody>
  );
}

export function Th({ children }: { children: ReactNode }) {
  return <th className="px-4 py-3">{children}</th>;
}

export function Td({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={["px-4 py-3 text-sm", className ?? ""].join(" ")}>{children}</td>;
}

export function Tr({ children }: { children: ReactNode }) {
  return <tr className="text-gray-700 dark:text-gray-400">{children}</tr>;
}
