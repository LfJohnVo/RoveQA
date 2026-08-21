/**
 * The icon set, lifted from Windmill Dashboard (MIT, Estevan Maito).
 *
 * Inline rather than a package: eight paths do not justify a dependency, and an icon
 * that ships with the markup cannot fail to load. All are 20×20 `currentColor`, so they
 * take the colour of whatever they sit in and need no dark-theme handling of their own.
 *
 * Every one is `aria-hidden`. These sit beside a text label in every place they are
 * used; announcing them again would only make a screen reader say everything twice.
 */

import type { ReactNode } from "react";

export type IconProps = { className?: string };

function icon(path: ReactNode, defaultClass = "h-5 w-5") {
  return function Icon({ className }: IconProps) {
    return (
      <svg
        className={className ?? defaultClass}
        aria-hidden="true"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        {path}
      </svg>
    );
  };
}

export const ProjectsIcon = icon(
  <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />,
);

export const StoriesIcon = icon(
  <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />,
);

export const RunIcon = icon(
  <path
    fillRule="evenodd"
    d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
    clipRule="evenodd"
  />,
);

export const MemoryIcon = icon(
  <path
    fillRule="evenodd"
    d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
    clipRule="evenodd"
  />,
);

export const MoonIcon = icon(
  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />,
);

export const SunIcon = icon(
  <path
    fillRule="evenodd"
    d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
    clipRule="evenodd"
  />,
);

export const MenuIcon = icon(
  <path
    fillRule="evenodd"
    d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
    clipRule="evenodd"
  />,
  "h-6 w-6",
);

export const PlusIcon = icon(
  <path
    fillRule="evenodd"
    d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
    clipRule="evenodd"
  />,
);
