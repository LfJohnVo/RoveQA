/**
 * The Windmill Dashboard shell: a fixed sidebar, a header bar, and a scrolling main.
 *
 * The nav lists what exists and nothing else. A sidebar entry that leads nowhere is a
 * worse interface than a small one that works — and in a control plane it is a support
 * call, because the reader assumes the feature is there and broken rather than absent.
 * So the project group appears only once a project is open, since that is the only
 * moment Stories, Runs and Memory have a subject.
 */

import type { ComponentType, ReactNode } from "react";
import { useState } from "react";
import { NavLink, useMatch } from "react-router";

import { useTheme } from "@viewmodels/theme/use-theme";

import type { IconProps } from "./icons";
import {
  MemoryIcon,
  MenuIcon,
  MoonIcon,
  ProjectsIcon,
  RunIcon,
  StoriesIcon,
  SunIcon,
} from "./icons";

type NavEntry = { to: string; label: string; Icon: ComponentType<IconProps> };

function NavItem({ to, label, Icon, end }: NavEntry & { end?: boolean }) {
  return (
    <li className="relative px-6 py-3">
      <NavLink
        to={to}
        end={end ?? false}
        className={({ isActive }) =>
          [
            "inline-flex w-full items-center text-sm font-semibold transition-colors duration-150",
            isActive
              ? "text-gray-800 dark:text-gray-100"
              : "hover:text-gray-800 dark:hover:text-gray-200",
          ].join(" ")
        }
      >
        {({ isActive }) => (
          <>
            {isActive ? (
              // The purple bar is the only thing marking the current page in this design,
              // so it is drawn from the same state the link colour uses — two sources
              // would eventually disagree and leave the sidebar lying about where you are.
              <span
                className="absolute inset-y-0 left-0 w-1 rounded-tr-lg rounded-br-lg bg-purple-600"
                aria-hidden="true"
              />
            ) : null}
            <Icon />
            <span className="ml-4">{label}</span>
          </>
        )}
      </NavLink>
    </li>
  );
}

function Nav({ projectId }: { projectId: string | null }) {
  return (
    <div className="py-4 text-gray-500 dark:text-gray-400">
      <NavLink className="ml-6 text-lg font-bold text-gray-800 dark:text-gray-200" to="/projects">
        RoveQA
      </NavLink>

      <ul className="mt-6">
        <NavItem to="/projects" label="Projects" Icon={ProjectsIcon} end />
      </ul>

      {projectId === null ? null : (
        <>
          <p className="mt-6 px-6 text-xs font-semibold tracking-wide text-gray-400 uppercase dark:text-gray-500">
            This project
          </p>
          <ul className="mt-2">
            <NavItem to={`/projects/${projectId}`} label="Overview" Icon={ProjectsIcon} end />
            <NavItem to={`/projects/${projectId}/stories`} label="Stories" Icon={StoriesIcon} />
            <NavItem to={`/projects/${projectId}/runs/new`} label="New run" Icon={RunIcon} />
            <NavItem to={`/projects/${projectId}/memory`} label="Memory" Icon={MemoryIcon} />
          </ul>
        </>
      )}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { isDark, toggle } = useTheme();
  const [isSideMenuOpen, setSideMenuOpen] = useState(false);

  // The one route parameter the shell itself cares about, read here rather than passed
  // down so no page has to remember to tell the sidebar where it is. Both patterns are
  // matched unconditionally: `??` between two hook calls would skip the second whenever
  // the first matched, and a hook that runs only sometimes is a hook order that changes.
  const nested = useMatch("/projects/:projectId/*");
  const exact = useMatch("/projects/:projectId");
  const projectId = (nested ?? exact)?.params.projectId ?? null;

  return (
    <div
      className={[
        "flex h-screen bg-gray-50 dark:bg-gray-900",
        isSideMenuOpen ? "overflow-hidden" : "",
      ].join(" ")}
    >
      <aside className="z-20 hidden w-64 shrink-0 overflow-y-auto bg-white md:block dark:bg-gray-800">
        <Nav projectId={projectId} />
      </aside>

      {isSideMenuOpen ? (
        <>
          <div
            className="fixed inset-0 z-10 flex items-end bg-black/50 sm:items-center sm:justify-center"
            onClick={() => setSideMenuOpen(false)}
            aria-hidden="true"
          />
          <aside
            className="fixed inset-y-0 z-20 mt-16 w-64 shrink-0 overflow-y-auto bg-white md:hidden dark:bg-gray-800"
            onKeyDown={(event) => {
              if (event.key === "Escape") setSideMenuOpen(false);
            }}
          >
            <Nav projectId={projectId} />
          </aside>
        </>
      ) : null}

      <div className="flex w-full flex-1 flex-col">
        <header className="z-10 bg-white py-4 shadow-md dark:bg-gray-800">
          <div className="container mx-auto flex h-full items-center justify-between px-6 text-purple-600 dark:text-purple-300">
            <button
              type="button"
              className="-ml-1 mr-5 rounded-md p-1 focus:shadow-outline-purple focus:outline-none md:hidden"
              onClick={() => setSideMenuOpen((open) => !open)}
              aria-label="Menu"
              aria-expanded={isSideMenuOpen}
            >
              <MenuIcon />
            </button>

            <div className="flex flex-1 justify-center lg:mr-32" />

            <ul className="flex flex-shrink-0 items-center space-x-6">
              <li className="flex">
                <button
                  type="button"
                  className="rounded-md focus:shadow-outline-purple focus:outline-none"
                  onClick={toggle}
                  aria-label="Toggle color mode"
                  aria-pressed={isDark}
                >
                  {isDark ? <SunIcon /> : <MoonIcon />}
                </button>
              </li>
            </ul>
          </div>
        </header>

        <main className="h-full overflow-y-auto">
          <div className="container mx-auto grid px-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
