# Note Capture Workbench Design

## Context

The global note sidebar is a 360px panel with search, drag-and-drop capture,
an inline editor, autosave, and links to full note pages. It currently feels
like a small note list with a detached editor. The goal is to make it a fast
learning capture surface while keeping long-form editing in `NoteDetailView`.

The first release follows the Learning Capture Workbench direction: quick
capture first, lightweight retrieval second, and learning context preserved
automatically.

## Goals

- Capture a thought or selected passage without leaving a learning page.
- Automatically associate captures with supported learning content pages.
- Separate raw captures from notes that have been organized.
- Make recent notes easy to scan and reopen.
- Reuse the existing autosave, note, resource, flashcard, and AI formatting
  capabilities where possible.

## Non-goals

- No complex folders, smart tag clustering, or knowledge-graph automation.
- No replacement of the full note editor or Markdown preview in the sidebar.
- No automatic source association on home, settings, note-list, or other
  non-learning pages.

## Data Model

Existing `Note` records remain readable and editable. New optional metadata is
added for captures:

```text
noteType: excerpt | quick | question
organizeStatus: pending | organizing | organized | error
sourceType: plan | resource | knowledge-node | tutor
sourceId: optional identifier
sourceTitle: optional display title
sourceRoute: optional deep-link route
excerpt: optional selected source text
```

`content` stores the user's own note. `excerpt` stores source material and is
never silently merged into user-authored content. A source can be removed from
the capture without deleting the user's note.

New notes default to `noteType=quick` and `organizeStatus=pending`. A note
becomes `organizing` while AI formatting runs, `organized` on success, and
`error` on failure. Editing an organized note returns it to `pending`.

The source model is structured rather than embedded in Markdown so it can be
filtered, rendered, and navigated independently. Existing notes without these
fields use quick/pending defaults in the frontend.

## Sidebar Interaction

### Collapsed state

The top of the panel shows a single-line capture entry:

```text
[+ 记一条笔记]          当前来源：极限的定义
```

It is collapsed by default. Clicking it expands the capture editor. Dropping
content onto the panel also expands it and switches to excerpt mode.

### Expanded editor

The editor contains three mutually exclusive modes: `摘录`, `速记`, and
`问题`. Quick is the default. The expanded state includes:

- the current source badge, with a remove action;
- an excerpt block when capture came from selected or dropped content;
- an optional title;
- the user-authored content field;
- save state and a save action;
- `整理成笔记` when there is content to organize;
- a collapse action that preserves the draft.

Selecting text on a supported learning page and invoking “添加到笔记” opens
the sidebar, switches to excerpt mode, places the selection in the excerpt
block, and focuses the user's content field. Drag-and-drop follows the same
flow. Saving keeps the editor mounted long enough to show the saved state, then
collapses it so repeated captures remain fast.

### Note list

The list below the editor is grouped into `待整理` and `已整理`. Each item
shows its mode icon, title or first line, source, excerpt preview when present,
updated time, and flashcard count when available. Hover actions expose pin,
archive/delete, and open-full-editor actions without adding permanent visual
noise. Search and lightweight filters (`最近`, `置顶`, `有来源`) operate on the
same list.

The sidebar does not render a full Markdown preview. Long-form editing,
formatting, and deep AI operations continue in `NoteDetailView`.

## Context Association

Only learning-content routes create automatic source metadata:

- plan modules and resource detail pages;
- knowledge-tree nodes;
- Tutor conversations.

Home, settings, note-list, and other utility pages do not create a source.
When a source target no longer exists, its title and excerpt remain visible;
the navigation control is disabled instead of deleting context.

The frontend normalizes all supported source types into one source contract and
passes it to the capture composable. A global `note-capture` event or Pinia
state carries selected text from learning pages to the sidebar without
coupling those pages to sidebar internals.

## Components and Responsibilities

- `NoteSidebar`: layout, list rendering, mode controls, drag/drop, and capture
  events.
- `useNoteCapture`: mode, source, excerpt, expanded state, filters, and capture
  transitions.
- `useNoteDraft`: existing autosave, draft recovery, save sequencing, and
  status handling.
- Note API layer: CRUD, source metadata, and AI organize requests.
- Full note detail view: long-form editing and existing formatting/flashcard
  workflows.

The new composable must not duplicate save sequencing already owned by
`useNoteDraft`.

## AI Organization

The organization action accepts a saved note ID. It returns a structured title,
body, key knowledge points, and optional flashcard candidates. The sidebar
shows an organizing state and supports retry after errors. Raw excerpt and
user-authored content remain available throughout the operation.

## Error Handling

- Autosave failures keep the draft editable and expose retry.
- AI failures set `organizeStatus=error`, preserve all input, and expose retry.
- A stale or deleted source keeps display metadata but disables navigation.
- Refresh recovery restores an unsaved new capture, including mode, source,
  excerpt, and content.
- Older notes with missing capture metadata render with safe defaults.

## Verification

Frontend tests cover mode-to-field mapping, supported-route source creation,
selection and drag capture, grouping/filtering, autosave recovery, organize
status transitions, and source removal. API tests cover backward-compatible
note payloads and organize responses. End-to-end coverage verifies that a
selection on a learning page opens the sidebar in excerpt mode, saves with
source metadata, and appears in the correct group.

Responsive checks must confirm that the expanded editor does not obscure the
main content or cause the note list to resize unpredictably at the existing
sidebar width and supported small-screen layouts.

## Rollout Boundary

The implementation should begin with the frontend capture contract and
sidebar states, then add backend persistence and AI organization integration.
Knowledge graph recommendations, advanced tagging, and cross-note discovery
remain follow-up work after this workflow proves useful.
