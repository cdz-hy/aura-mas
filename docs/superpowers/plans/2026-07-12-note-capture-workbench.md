# Note Capture Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the global note sidebar into a learning capture workbench with quick/excerpt/question modes, automatic learning-page sources, pending/organized grouping, and AI organization.

**Architecture:** Keep `useNoteDraft` as the single owner of autosave and draft recovery. Add a focused `useNoteCapture` composable for capture mode/source/excerpt state, pass selected text through a small Pinia capture store, and extend the existing Java note contract with optional metadata. Reuse the existing Python SSE note formatter for organization, adapting its result into the sidebar's organizing/error states.

**Tech Stack:** Vue 3 + TypeScript + Pinia + Tailwind CSS; Spring Boot/MyBatis-Plus Java backend; FastAPI SSE note formatter; Vitest and Playwright.

## Global Constraints

- Only plan modules, resource details, knowledge-tree nodes, and Tutor conversations create automatic sources.
- Home, settings, note-list, and utility pages do not create automatic sources.
- The sidebar remains a lightweight capture surface; full Markdown editing stays in `NoteDetailView`.
- Existing notes without capture metadata must remain readable and editable with frontend defaults.
- Preserve existing autosave sequencing and draft recovery in `useNoteDraft`.
- Do not add folders, smart tag clustering, knowledge-graph recommendations, or a new full editor in this slice.

---

### Task 1: Define the note capture contract across frontend and Java backend

**Files:**
- Modify: `Vue-frontend/src/types/note.ts`
- Modify: `Vue-frontend/src/api/note.ts`
- Modify: `Java-backend/src/main/java/com/learning/entity/Note.java`
- Modify: `Java-backend/src/main/java/com/learning/dto/NoteCreateRequest.java`
- Modify: `Java-backend/src/main/java/com/learning/controller/NoteController.java`
- Modify: `Java-backend/src/main/java/com/learning/service/NoteService.java`
- Modify: `Java-backend/src/main/resources/schema.sql`
- Test: `Vue-frontend/src/api/note.test.ts`
- Test: `Java-backend/src/test/java/com/learning/controller/NoteControllerTest.java`

**Interfaces:**
- `Note` gains optional `noteType`, `organizeStatus`, `sourceType`, `sourceId`, `sourceTitle`, `sourceRoute`, and `excerpt` fields.
- `NoteCreateRequest` accepts the same optional fields while keeping `noteName` and `content` validation compatible with existing full-note creation.
- `createNote(data: NoteCreateRequest)` and `updateNote(noteId, data)` continue returning `{ data: Note }`.
- Add `organizeNote(noteId, data)` only if the backend persists the organized result; otherwise the frontend uses the existing SSE formatter and updates through `updateNote`.

- [x] **Step 1: Write failing frontend contract tests**

Add tests asserting that create/update payloads preserve capture metadata and that list responses deserialize fields without transformation:

```ts
it('sends capture metadata when creating an excerpt note', async () => {
  await createNote({
    noteName: '无标题笔记',
    content: '我的理解',
    noteType: 'excerpt',
    organizeStatus: 'pending',
    sourceType: 'resource',
    sourceId: 12,
    sourceTitle: '极限的定义',
    sourceRoute: '/plans/1/resources/12',
    excerpt: '当 x 趋近于 a 时',
  })
  expect(requestMock.post).toHaveBeenCalledWith('/note', expect.objectContaining({ noteType: 'excerpt', excerpt: '当 x 趋近于 a 时' }))
})
```

- [x] **Step 2: Run the focused frontend test and verify it fails**

Run: `cd Vue-frontend; npm run test -- src/api/note.test.ts`

Expected: FAIL because the `NoteCreateRequest` type and fixture do not yet include capture fields.

- [x] **Step 3: Add optional fields and Java persistence mapping**

Add nullable columns with defaults for old records. Use enum-like string values at the API boundary (`excerpt|quick|question` and `pending|organizing|organized|error`) and map them as strings in MyBatis-Plus. Do not make existing note creation reject an empty excerpt.

- [x] **Step 4: Run frontend and backend focused tests**

Run: `cd Vue-frontend; npm run test -- src/api/note.test.ts`

Run: `cd Java-backend; mvn -q -Dtest=NoteControllerTest test`

Expected: PASS, with old payload tests still passing.

- [x] **Step 5: Commit the contract slice**

```bash
git add Vue-frontend/src/types/note.ts Vue-frontend/src/api/note.ts Vue-frontend/src/api/note.test.ts Java-backend/src/main/java/com/learning/entity/Note.java Java-backend/src/main/java/com/learning/dto/NoteCreateRequest.java Java-backend/src/main/java/com/learning/controller/NoteController.java Java-backend/src/main/java/com/learning/service/NoteService.java Java-backend/src/main/resources/schema.sql Java-backend/src/test/java/com/learning/controller/NoteControllerTest.java
git commit -m "feat: add note capture metadata contract"
```

### Task 2: Add capture state and learning-page source propagation

**Files:**
- Create: `Vue-frontend/src/stores/noteCapture.ts`
- Create: `Vue-frontend/src/components/note/useNoteCapture.ts`
- Modify: `Vue-frontend/src/components/note/useNoteDraft.ts`
- Test: `Vue-frontend/src/stores/noteCapture.test.ts`
- Test: `Vue-frontend/src/components/note/useNoteCapture.test.ts`
- Modify: `Vue-frontend/src/router/index.ts`
- Modify: `Vue-frontend/src/views/PlanDetailView.vue`
- Modify: `Vue-frontend/src/views/NoteDetailView.vue`
- Modify: `Vue-frontend/src/components/chat/TutorChatPanel.vue`

**Interfaces:**
- `NoteCaptureMode = 'excerpt' | 'quick' | 'question'`.
- `NoteCaptureSource = { sourceType: 'plan'|'resource'|'knowledge-node'|'tutor'; sourceId?: number|string; sourceTitle: string; sourceRoute: string }`.
- Pinia action `requestCapture(payload: { mode?: NoteCaptureMode; source?: NoteCaptureSource; excerpt?: string }): void`.
- `useNoteCapture()` exposes `mode`, `source`, `excerpt`, `expanded`, `pendingFilter`, `openCapture()`, `removeSource()`, `consumeRequest()`.

- [x] **Step 1: Write failing state tests**

Cover default quick mode, request consumption, source removal, and route filtering. Assert that a request from a supported page contains source metadata while a note-list route produces no source.

- [x] **Step 2: Run tests to verify they fail**

Run: `cd Vue-frontend; npm run test -- src/stores/noteCapture.test.ts src/components/note/useNoteCapture.test.ts`

Expected: FAIL because the store and composable do not exist.

- [x] **Step 3: Implement the store and composable**

Keep capture state separate from draft persistence. `useNoteCapture` must convert a consumed request into draft seed fields without calling the API itself. `useNoteDraft` should accept a seed containing mode/source/excerpt and serialize it into local recovery storage.

- [x] **Step 4: Emit capture requests from learning content**

Add a small “添加到笔记” action to supported content surfaces. It sends the current selection and normalized route source through `requestCapture`; do not emit from home, settings, or note-list views.

- [x] **Step 5: Run the focused state tests**

Run: `cd Vue-frontend; npm run test -- src/stores/noteCapture.test.ts src/components/note/useNoteCapture.test.ts src/components/note/useNoteDraft.test.ts`

Expected: PASS.

- [x] **Step 6: Commit source propagation**

```bash
git add Vue-frontend/src/stores/noteCapture.ts Vue-frontend/src/stores/noteCapture.test.ts Vue-frontend/src/components/note/useNoteCapture.ts Vue-frontend/src/components/note/useNoteCapture.test.ts Vue-frontend/src/components/note/useNoteDraft.ts Vue-frontend/src/components/note/useNoteDraft.test.ts Vue-frontend/src/router/index.ts Vue-frontend/src/views/PlanDetailView.vue Vue-frontend/src/views/NoteDetailView.vue Vue-frontend/src/components/chat/TutorChatPanel.vue
git commit -m "feat: propagate learning context into note capture"
```

### Task 3: Rebuild the sidebar around the capture workbench

**Files:**
- Modify: `Vue-frontend/src/components/note/NoteSidebar.vue`
- Modify: `Vue-frontend/src/components/note/notePresentation.ts`
- Test: `Vue-frontend/src/components/note/notePresentation.test.ts`
- Create: `Vue-frontend/src/components/note/NoteCaptureEditor.vue`
- Create: `Vue-frontend/src/components/note/NoteListItem.vue`
- Test: `Vue-frontend/e2e/note-sidebar.spec.ts`

**Interfaces:**
- `NoteCaptureEditor` accepts `draft`, `mode`, `source`, `excerpt`, and save/organize callbacks; emits `update:mode`, `update:fields`, `remove-source`, `collapse`, and `organize`.
- `NoteListItem` accepts a `Note` plus `sourceLabel`, `flashcardCount`, and `onOpen` callback.
- `notePresentation` adds `noteTypeLabel`, `organizeStatusLabel`, and `noteGroup(note): 'pending'|'organized'` helpers.

- [x] **Step 1: Write presentation tests**

Assert stable labels, safe defaults for legacy notes, two-group classification, and excerpt-first preview behavior.

- [x] **Step 2: Run presentation tests to verify they fail**

Run: `cd Vue-frontend; npm run test -- src/components/note/notePresentation.test.ts`

Expected: FAIL for the new helpers.

- [x] **Step 3: Implement the presentation helpers and focused child components**

Keep child components presentational. Put API calls, list loading, request consumption, and draft wiring in `NoteSidebar`.

- [x] **Step 4: Replace the permanent drop zone with the collapsed capture row**

The row expands on click or drag-over/drop. In expanded mode render mode tabs, source badge with remove action, excerpt block, title/content fields, save status, organize action, and collapse control. Preserve the existing 800ms autosave behavior.

- [x] **Step 5: Add grouped list and filters**

Render `待整理` and `已整理` sections, with `最近`, `置顶`, and `有来源` filters. Keep search debounced and retain existing resource-label fallback for legacy notes.

- [x] **Step 6: Run unit and browser tests**

Run: `cd Vue-frontend; npm run test -- src/components/note/notePresentation.test.ts src/components/note/useNoteDraft.test.ts`

Run: `cd Vue-frontend; npx playwright test e2e/note-sidebar.spec.ts`

Expected: PASS; browser coverage must verify collapsed row, mode switching, drag capture, grouped rendering, and source removal.

- [x] **Step 7: Commit the sidebar slice**

```bash
git add Vue-frontend/src/components/note/NoteSidebar.vue Vue-frontend/src/components/note/NoteCaptureEditor.vue Vue-frontend/src/components/note/NoteListItem.vue Vue-frontend/src/components/note/notePresentation.ts Vue-frontend/src/components/note/notePresentation.test.ts Vue-frontend/e2e/note-sidebar.spec.ts
git commit -m "feat: build learning capture note sidebar"
```

### Task 4: Connect AI organization and organized-state transitions

**Files:**
- Modify: `Vue-frontend/src/api/noteAgent.ts`
- Modify: `Vue-frontend/src/components/note/NoteSidebar.vue`
- Modify: `Vue-frontend/src/components/note/useNoteCapture.ts`
- Modify: `Python-backend/app/api/v1/endpoints/note_agent.py`
- Test: `Vue-frontend/src/api/noteAgent.test.ts`
- Test: `Python-backend/tests/test_note_agent.py`

**Interfaces:**
- `formatNoteSSE(ticket, content, handlers, instruction?, context?)` accepts optional `excerpt`, `sourceTitle`, and `noteType` context while remaining compatible with existing callers.
- Sidebar action `organizeCurrentNote(): Promise<void>` sets `organizing`, streams the formatter result, updates the saved note content, then sets `organized`; errors set `error` and keep the draft editable.

- [x] **Step 1: Write failing SSE/context tests**

Assert the request body includes excerpt/source context and that progress, done, and error events map to the expected callbacks.

- [x] **Step 2: Run focused tests to verify failure**

Run: `cd Vue-frontend; npm run test -- src/api/noteAgent.test.ts`

Expected: FAIL because the context argument is not yet serialized.

- [x] **Step 3: Extend the formatter request and prompt context**

Preserve the existing annotation protocol and Markdown output. Add explicit instructions that excerpt is source material and content is the learner's own thinking; do not overwrite the source excerpt.

- [x] **Step 4: Implement sidebar organization state**

Require a saved note ID. Disable the action while organizing, expose retry after error, and mark edited organized notes as pending through the draft update path.

- [x] **Step 5: Run frontend and Python tests**

Run: `cd Vue-frontend; npm run test -- src/api/noteAgent.test.ts src/components/note/useNoteDraft.test.ts`

Run: `cd Python-backend; pytest tests/test_note_agent.py -q`

Expected: PASS.

- [x] **Step 6: Commit AI organization**

```bash
git add Vue-frontend/src/api/noteAgent.ts Vue-frontend/src/api/noteAgent.test.ts Vue-frontend/src/components/note/NoteSidebar.vue Vue-frontend/src/components/note/useNoteCapture.ts Python-backend/app/api/v1/endpoints/note_agent.py Python-backend/tests/test_note_agent.py
git commit -m "feat: organize captured notes with AI"
```

### Task 5: Verify compatibility, responsive behavior, and end-to-end workflow

**Files:**
- Modify: `Vue-frontend/e2e/note-sidebar.spec.ts`
- Modify: `Vue-frontend/src/components/note/NoteSidebar.vue`
- Modify: `Vue-frontend/src/components/note/NoteCaptureEditor.vue`
- Modify: `Vue-frontend/src/components/note/NoteListItem.vue`
- Test: `Vue-frontend/src/api/note.test.ts`
- Test: `Java-backend/src/test/java/com/learning/controller/NoteControllerTest.java`

- [x] **Step 1: Add the full workflow browser test**

Verify: supported learning page -> select text -> open sidebar in excerpt mode -> source badge and excerpt visible -> save -> note appears under `待整理` -> organize -> note moves to `已整理` -> edit returns it to `待整理`.

- [x] **Step 2: Add legacy-record compatibility assertions**

Use a note fixture with only `id`, `noteName`, `content`, and timestamps. Assert it renders as quick/pending with no source and remains editable.

- [x] **Step 3: Run the complete frontend verification**

Run: `cd Vue-frontend; npm run test; npm run build; npx playwright test e2e/note-sidebar.spec.ts`

Expected: PASS with no TypeScript errors and no layout overflow at desktop and supported small-screen viewports.

- [x] **Step 4: Run backend verification**

Run: `cd Java-backend; mvn -q test`

Expected: PASS with note controller/service regressions covered.

- [x] **Step 5: Review the final diff and commit verification fixes**

```bash
git diff --check
git status --short
git add Vue-frontend/e2e/note-sidebar.spec.ts Vue-frontend/src/components/note/NoteSidebar.vue Vue-frontend/src/components/note/NoteCaptureEditor.vue Vue-frontend/src/components/note/NoteListItem.vue Vue-frontend/src/api/note.test.ts Java-backend/src/test/java/com/learning/controller/NoteControllerTest.java
git commit -m "test: verify note capture workflow compatibility"
```

## Self-Review

- Spec coverage: data fields and legacy defaults are covered by Task 1; source scope and selection flow by Task 2; collapsed editor, modes, grouping, filters, and responsive behavior by Tasks 3 and 5; AI state transitions by Task 4; errors and retries by Tasks 2 and 4.
- Placeholder scan: every step contains concrete files, interfaces, commands, and expected outcomes.
- Type consistency: `NoteCaptureMode`, `NoteCaptureSource`, the optional `Note` fields, and `formatNoteSSE` context are defined before consumers.
- Scope check: all tasks stay within the approved workbench slice; advanced graph/tag discovery remains explicitly out of scope.
