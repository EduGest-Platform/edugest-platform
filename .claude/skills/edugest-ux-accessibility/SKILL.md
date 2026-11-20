---
name: edugest-ux-accessibility
description: UX, accessibility and human tone for EduGest screens, forms, errors and empty states. Use when designing or changing anything people see or type into.
---

# EduGest UX, accessibility and human tone

Our users may have little digital experience and may be in a vulnerable situation. The site must be easy, clear and kind.

## Accessibility (WCAG 2.2 AA)

- Every field has a visible `<label>` (use `Field` from `ui.tsx`). Placeholders are examples, never the label.
- Required fields say so in words, not only with `*`.
- Keyboard: everything works with Tab, Enter and Escape. The focus is always visible (global `:focus-visible` style in `src/index.css`).
- When a screen or modal opens with important news (for example "no access"), move the focus to its heading (`tabIndex={-1}` + `focus()`).
- Errors and important messages are read aloud: `Notice live="assertive"` for errors, `live="polite"` for normal updates.
- Never use colour as the only signal. Every status has a word, and an icon where it helps.
- Good contrast: use the app's tokens and the `Status`/`Notice` colour families.

## Human tone (Spanish UI)

- Plain Spanish, talking to the person with *tú*. Short sentences.
- Errors say what happened and what to do next: "Revisa tu correo", never "Error 422". Use `describeApiError` from `src/shared/api/errors.ts`.
- 401/403 never show technical details. 403 uses the `AccessDenied` screen with a way back.
- Every list has a friendly empty state (`Empty`), a loading state, and an error state. No dead ends.
- Words about people: never "rechazado/excluido" as an automatic result. Say "necesita una decisión del equipo".

## Human decisions (EU AI Act)

- AI, ranking and risk outputs are labelled as suggestions.
- Admission, waiting list and no admission are confirmed by authorised people, with their signature and date.

## Quick check before a PR

1. Tab through the whole screen. Can you reach and use everything?
2. Is every error, empty and loading state there and in plain Spanish?
3. Is any status shown only by colour?
4. Does anything sound like the platform decided about a person?
