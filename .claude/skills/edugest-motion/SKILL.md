---
name: edugest-motion
description: Animations and transitions for EduGest. Use only when a change adds motion (modals, toasts, cards moving, loading).
---

# EduGest motion

Small animations that help people understand what changed. Optional: only if there is time before the freeze.

## Rules

- Use Tailwind or CSS transitions first (`transition-colors`, `transition-opacity`, 150–250 ms). Do not add an animation library unless a screen really needs it and the team agrees.
- Always respect "reduce motion": use Tailwind's `motion-safe:` / `motion-reduce:` variants, or `@media (prefers-reduced-motion: reduce)`. Some people get dizzy with animations.
- Use motion only where it helps:
  - opening and closing a modal (`Modal`);
  - a toast appearing;
  - a card moving between columns on a board;
  - loading skeletons instead of spinners for lists.
- Never animate text people are reading, and never block a click while something animates.
- Motion never replaces a message: the result is always said in text too.
