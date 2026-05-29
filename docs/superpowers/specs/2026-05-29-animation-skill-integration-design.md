# Animation Skill Integration Design

## Overview

Integrate the `jacky-motion-main` animation skill into the AURA LangGraph pipeline as a new dedicated node. When a user requests animation generation for an existing learning resource, the system reads skill files from disk, constructs a prompt with CSS DNA from style templates, calls an LLM to generate a self-contained HTML animation, and returns it via SSE for iframe playback.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Communication path | SSE synchronous | Same as mindmap/summary/code; user waits on page for result |
| Prompt loading | Dynamic from skill directory | Flexible; changing prompts doesn't require code changes |
| Skill loader | Generic `app/skills/loader.py` | Reusable for future skills |
| Node architecture | New independent node | Different prompt construction, output format, and post-processing than resource_type_generator |

## Architecture

### New Files

1. **`Python-backend/app/skills/loader.py`** — Generic skill loader
2. **`Python-backend/app/agents/animation_skill_generator.py`** — Animation generation node
3. **`Python-backend/app/prompts/animation_skill.py`** — Prompt assembly from skill files (optional; may be inlined in the node)

### Modified Files

4. **`Python-backend/app/agents/schemas.py`** — Add `NODE_ANIMATION_SKILL_GENERATOR` constant
5. **`Python-backend/app/graph/learning_graph.py`** — Register node, add edges, add to controller mapping
6. **`Python-backend/app/api/v1/endpoints/resource_chat.py`** — Add `type=animation` routing branch

### Data Flow

```
Frontend: GET /api/ai/resource/generate?type=animation&moduleId=X&planId=Y
  → resource_chat.py: intent="generate_animation", next_node=NODE_ANIMATION_SKILL_GENERATOR
  → controller: routes to animation_skill_generator
  → skill loader: reads skills/jacky-motion-main/ files
  → prompt assembly: SKILL.md + CSS DNA + quality checklist
  → LLM call: generates HTML + animationSpec JSON
  → output validation: html non-empty, animationSpec present
  → returns generated_content via SSE stream
  → Frontend: iframe srcdoc rendering on user click
```

No RabbitMQ involvement. No changes to Java backend or database schema.

## Skill Loader

**Location:** `Python-backend/app/skills/loader.py`

**Convention directory structure:**
```
Python-backend/skills/<skill-name>/
├── SKILL.md                          # Required: skill description and instructions
├── references/                       # Optional: reference documents
│   └── *.md
├── styles/                           # Optional: style definitions
│   └── *.md
└── assets/templates/                 # Optional: template files
    └── *.html
```

**API:**
```python
from dataclasses import dataclass

@dataclass
class SkillBundle:
    name: str
    skill_md: str                          # SKILL.md raw content
    references: dict[str, str]             # {filename_without_ext: content}
    styles: dict[str, str]                 # {filename_without_ext: content}
    templates: dict[str, str]              # {filename_without_ext: content}

def load_skill(skill_name: str) -> SkillBundle:
    """Load all files from skills/<skill_name>/ following the convention above."""
```

The loader reads files and organizes them by subdirectory. It does not interpret or transform content — prompt construction is the caller's responsibility.

## Animation Skill Generator Node

**Location:** `Python-backend/app/agents/animation_skill_generator.py`

**Function signature:**
```python
def animation_skill_generator_node(state: AgentState) -> dict[str, Any]:
```

**Steps:**

1. Extract from state: `source_resource_content`, `user_profile`, `plan_id`, `module_id`, `task_breakdown` (for title/description)
2. Call `load_skill("jacky-motion-main")`
3. Select style template (default: `apple-tech-gradient`) from `skill.templates`
4. Assemble system prompt:
   - `skill.skill_md` — full SKILL.md as base instructions
   - `skill.templates[selected_style]` — CSS DNA injection
   - `skill.references["quality-check"]` — 27-point self-check checklist
5. Assemble user message:
   - Source resource title and content (truncated to fit context)
   - User profile Felder-Silverman preferences (visual_verbal, sequential_global)
   - Target duration (default 60s)
6. Call LLM via `get_resource_type_generator_llm().chat_json(messages, max_tokens=16384)`
7. Validate output: `html` field non-empty, `animationSpec` present
8. Return:
   ```python
   {
       "generated_content": {
           "module_type": "animation",
           "title": result["title"],
           "description": result["description"],
           "html": result["html"],
           "content": result["html"],  # same as html, backward compat
           "animationSpec": result["animationSpec"],
           "metadata": result.get("metadata", {}),
       },
       "current_step": "动画生成完成",
       "stream_events": [...]
   }
   ```

**LLM:** Reuse `get_resource_type_generator_llm()` (mimo-v2.5-pro), `max_tokens=16384` for longer HTML output.

**Error handling:** On failure, return `{"error": ..., "current_step": ..., "stream_events": [...]}` — same pattern as other nodes. The route function sends the graph back to controller on error.

## Graph Integration

### schemas.py
```python
NODE_ANIMATION_SKILL_GENERATOR = "animation_skill_generator"
```

### learning_graph.py

**Import and register:**
```python
from app.agents.animation_skill_generator import animation_skill_generator_node
graph.add_node(NODE_ANIMATION_SKILL_GENERATOR, animation_skill_generator_node)
```

**Route function:**
```python
def route_after_animation_skill_generator(state: AgentState) -> str:
    anomaly = _route_if_anomaly(state)
    if anomaly:
        return anomaly
    if state.get("error"):
        return NODE_CONTROLLER
    return END
```

**Conditional edges:**
```python
graph.add_conditional_edges(
    NODE_ANIMATION_SKILL_GENERATOR,
    route_after_animation_skill_generator,
    {NODE_CONTROLLER: NODE_CONTROLLER, END: END}
)
```

**Controller mapping** (line ~545-555) — add one entry:
```python
NODE_ANIMATION_SKILL_GENERATOR: NODE_ANIMATION_SKILL_GENERATOR,
```

### resource_chat.py

Add `is_animation` branch before the `is_type_resource` check (around line 632):
```python
is_animation = (type == "animation")

if is_quiz:
    intent = "generate_quiz"
    next_node = "quiz_generator"
elif is_animation:
    intent = "generate_animation"
    next_node = NODE_ANIMATION_SKILL_GENERATOR
elif is_type_resource:
    intent = "generate_type_resource"
    next_node = NODE_RESOURCE_TYPE_GENERATOR
else:
    intent = "generate_resource"
    next_node = "rag_retriever"
```

## Frontend Integration

No new API endpoints needed. The existing SSE flow handles animation the same as other resource types.

**Rendering:** When `generated_content.module_type == "animation"`, render with:
```html
<iframe
  :srcdoc="generatedContent.html"
  sandbox="allow-scripts"
  style="width:100%; aspect-ratio:16/9; border:none;"
/>
```

**Interaction model:** Generation and playback are separate:
- Generation: SSE stream returns the result; a new resource card with animation icon appears in the left sidebar module list
- Playback: User clicks the card; center panel loads the iframe

**Security:** `sandbox="allow-scripts"` matches the skill's constraint — JS can run (for beat navigation and CSS animations) but cannot access parent page, localStorage, cookies, or make network requests.

## State Changes

None. `generated_content` is `Dict[str, Any]` — animation adds `html`, `animationSpec`, `metadata` fields to the existing dict without schema changes. This follows the same pattern as mindmap (which adds `nodeData`).

## What This Does NOT Change

- Java backend — no schema changes, no new endpoints
- RabbitMQ — animation does not use the async queue
- Database — `moduleData` stores the same `generated_content` dict; `moduleType="animation"` is just a string value
- Existing resource_type_generator — untouched; mindmap/summary/code continue working as before
- Controller logic — only the mapping table gets one new entry; no routing logic changes
