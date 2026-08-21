# The frontend adopts Windmill Dashboard, and Tailwind with it

Status: Accepted

## Context
The console was styled with about 500 lines of hand-written CSS over a small token file.
It was coherent, and it was ours — which is the problem it solved and also its cost: every
new surface needed a designer's decision, and the decisions were being made by whoever
wrote the component.

Windmill Dashboard (Estevan Maito, MIT) is a finished dashboard design system: palette,
type scale, shell, cards, tables, badges, forms, modals, and a dark theme for all of it.
Adopting it answers the recurring question — *what should this look like* — with a
reference rather than an opinion.

Windmill ships as Tailwind markup. That leaves two ways to adopt it, and they are not the
same decision:

1. **Port the visual system into the existing CSS.** No new dependency, small diff, and the
   token file survives. But every component Windmill already solved has to be
   re-implemented, and the next one copied from the template has to be translated by hand.
   The design system stops being a reference and becomes a thing we maintain.
2. **Adopt Tailwind and use the template's classes verbatim.** A new build dependency and a
   rewrite of the markup in six pages and three components. In exchange the template stays
   usable as a source: a card from `cards.html` is paste-and-go, and the classes in this
   repository are the same strings as in its documentation.

This was put to the user, who chose (2) — literal fidelity over the smaller diff.

## Decision
The frontend uses **Tailwind 4** and the **Windmill Dashboard** design language.

- Windmill's Tailwind 1 JS config is ported to Tailwind 4's CSS configuration in
  `frontend/src/views/styles/theme.css`. The palette values are Windmill's, unchanged.
- Dark mode follows a `.theme-dark` class on `<html>`, as Windmill does, rather than the OS
  preference alone — the toggle has to be able to disagree with the OS, and a stored choice
  outlives it. `index.html` applies the class before first paint so a dark-theme reader
  never sees a white flash.
- `shadow-outline-*` (Windmill's focus ring) and the `form-*` classes are reproduced:
  the first as `@utility` declarations, the second through `@tailwindcss/forms` with the
  **class** strategy, which is the same contract Tailwind 1's `custom-forms` gave.
- `frontend/src/views/components/ui.tsx` holds the component vocabulary — card, badge,
  button, table, field, notice — with the template's class strings. Pages compose those
  rather than retyping the strings, because a card that is `rounded-lg shadow-xs` in five
  places and `rounded-md shadow-sm` in the sixth is how a borrowed look stops looking
  borrowed.
- The old `tokens.css` and `app.css` are deleted. Two styling systems side by side is the
  option that ages worst, and keeping the dead one would guarantee it.

**Semantic colour is not remapped onto Windmill's names.** A verdict is the reason someone
opened the screen. `--color-pass`, `--color-fail`, `--color-no-answer` and `--color-stopped`
stay named for what they mean, and `VerdictBadge` keeps mapping the domain's own
`VerdictTone` onto a badge tone. `green-500` would let a component quietly paint something
green that was never a pass, and the taxonomy exists precisely so `inconclusive` cannot be
shown as a failure (docs/00).

## Consequences
**Attribution.** Windmill is MIT and its copyright notice is reproduced in
`frontend/THIRD-PARTY.md`. Adopting a design system is not a licence to drop the licence.

**A build dependency the frontend did not have.** `tailwindcss` and `@tailwindcss/vite` are
dev dependencies; nothing ships to the browser but CSS. `CLAUDE.md` forbids new
infrastructure without a documented need — this is that document.

**The template is Tailwind 1; we are on 4.** The class names are mostly stable, but not
entirely: `whitespace-no-wrap` is now `whitespace-nowrap`, `flex-shrink-0` is `shrink-0`,
and `bg-opacity-50` is `bg-black/50`. Copying from the template is paste-then-check, not
paste.

**Two tests changed, and both were right to.** One queried the timeline by CSS class
(`.timeline__row`) and broke the moment the timeline became a table; it now asks for a
table by accessible name, which is what a reader looks for too. The other could not find a
label, because the field's hint had been rendered *inside* the `<label>` and became part of
the control's accessible name. Restyling is a decent way to find out which tests were
testing the markup rather than the interface.

**No new dependency for icons.** Eight inline SVG paths from the template, in
`views/components/icons.tsx`.
