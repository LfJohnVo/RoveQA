/**
 * Windmill's input classes.
 *
 * Separated from `ui.tsx` because they are functions rather than components, and a module
 * that exports both breaks React Fast Refresh — the editor stops hot-reloading and nobody
 * connects the two facts.
 */

/** The input class Windmill uses everywhere, including its red variant. */
export function inputClass(invalid = false): string {
  return [
    "form-input mt-1 block w-full rounded-md text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 focus:outline-none",
    invalid
      ? "border-red-600 focus:border-red-400 focus:shadow-outline-red"
      : "focus:border-purple-400 focus:shadow-outline-purple dark:focus:shadow-outline-gray",
  ].join(" ");
}

export function selectClass(): string {
  return "form-select mt-1 block w-full rounded-md text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 focus:border-purple-400 focus:shadow-outline-purple focus:outline-none dark:focus:shadow-outline-gray";
}

export function checkboxClass(): string {
  return "form-checkbox rounded text-purple-600 focus:border-purple-400 focus:shadow-outline-purple focus:outline-none dark:focus:shadow-outline-gray";
}
