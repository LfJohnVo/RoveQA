/**
 * Light or dark, and who decides.
 *
 * A deliberate choice outlives the operating system's: someone who switched to dark at
 * 2am did so knowing what their OS preferred. So a stored value always wins, and the OS
 * preference is only the opening bid.
 *
 * The class lands on `<html>` rather than on a React root because the ground behind the
 * app is painted before React mounts — `index.html` applies the same rule inline so a
 * dark-theme user never sees a white flash on load. This hook keeps the two in step
 * afterwards; it does not own the initial paint.
 */

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "dark";
const DARK_CLASS = "theme-dark";

export interface ThemeViewModel {
  isDark: boolean;
  toggle: () => void;
}

function prefersDark(): boolean {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored !== null) return JSON.parse(stored) === true;
  } catch {
    // Private browsing, a blocked origin, a corrupted value: none of them is a reason
    // to fail to render. Fall through to what the OS says.
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function useTheme(): ThemeViewModel {
  const [isDark, setIsDark] = useState(prefersDark);

  useEffect(() => {
    document.documentElement.classList.toggle(DARK_CLASS, isDark);
  }, [isDark]);

  const toggle = useCallback(() => {
    setIsDark((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // The class still flips; only the memory of it is lost.
      }
      return next;
    });
  }, []);

  return { isDark, toggle };
}
