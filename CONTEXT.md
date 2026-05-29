# Aura MAS Learning Context

This context describes the learning-resource language used by the system. It keeps product, frontend, Java backend, and Python AI workflow terms aligned.

## Language

**Learning Resource**:
A user-facing learning artifact attached to a learning plan module.
_Avoid_: content blob, article record

**Supplementary Learning Resource**:
A learning resource generated from the current module context without replacing the primary resource.
_Avoid_: overwrite, variant

**Teaching Animation Resource**:
A supplementary learning resource that visually demonstrates a concept or process from the current module.
_Avoid_: loading animation, UI animation

**Animation Source Context**:
The selected resource title and body, plus learning-style preferences used to shape a teaching animation.
_Avoid_: whole plan context, unrelated chat history

## Relationships

- A **Learning Resource** belongs to exactly one learning plan module.
- A **Supplementary Learning Resource** is added alongside existing resources in the same module.
- A **Teaching Animation Resource** is a kind of **Supplementary Learning Resource**.
- A **Teaching Animation Resource** is derived from the **Animation Source Context** of the currently selected resource.

## Example dialogue

> **Dev:** "When the learner clicks generate animation from a text resource, should we replace the text?"
> **Domain expert:** "No — create a **Teaching Animation Resource** next to the existing **Learning Resource** so the learner can switch between explanation formats."

> **Dev:** "Should the animation generator read the whole plan?"
> **Domain expert:** "No — use the selected resource as the **Animation Source Context**, then adapt the presentation using the learner's visual and sequential preferences."

## Flagged ambiguities

- "animation" can mean either a UI loading effect or a learning artifact — resolved: use **Teaching Animation Resource** for the learning artifact.
