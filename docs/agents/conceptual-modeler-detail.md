# Conceptual modeler: detail

The long form behind `agents/conceptual-modeler-agent.md`, which carries the short form and points
here: the atom-mode spinoff rules with two worked examples (Step 5a), and the error table.

## Spinoff detection, atom mode (Step 5a)

A **spinoff candidate** is a concept the source treats as an **independently atomic topic** —
one with its own definition, distinct exposition, or that the source itself refers to as a
separate vault-worthy idea. Spinoff candidates are **not**:

- **Steps or stages of the primary concept.** If the concept appears in
  `mental_model.description` as a node, edge, or stage of the primary's cascade, it belongs in
  the primary note. It is **not** a spinoff.
- **Supporting evidence, examples, or analogies.** Those compress into `why_it_matters` or
  `boundary`, or they live as labels in `mental_model.description`.
- **Vocabulary mentioned in passing without elaboration.** A concept that gets a sentence and
  no more is a term, not an atom.

**Necessity test** — for each potential spinoff, ask:

> *"If I remove this concept entirely from the primary note (no mention in Definition, no
> appearance in Mental Model, no bullet in Why or Boundary), would the primary concept's
> exposition still hold together?"*

- **NO** (removal damages the primary) → **NOT a spinoff.** Keep it embedded. It is part of
  this atom.
- **YES** (the primary stands on its own without this concept) → **Eligible.** Proceed to
  the cross-check.

**Worked example.** Source: a video explaining how websites scale from 1 user to 1M users
using a bubble tea franchise metaphor. Primary concept: *Demand-Driven Scaling*. Concepts
mentioned: Cache, Docker, CI/CD, Load Balancer, Read Replica, Microservice, CDN, Rate Limiter,
Queue.

- Each of these 9 is a **stage in the cascade** the primary concept describes. Removing any
  one gutts the Mental Model. → **0 atom-mode spinoffs.** All 9 live in
  `mental_model.description`.

  (Note: this exact source, when actually classified, would likely be `note_mode = thesis`
  with the 9 stages distributed across themes — see 5b. The atom-mode worked example here is
  hypothetical, illustrating the necessity test rather than recommending a classification.)

- Contrast: a source *specifically about cache eviction policies* mentions LRU, LFU, FIFO each
  with its own taxonomy. Primary is "Cache Eviction Policy". The three algorithms each have
  their own atomic structure. Removing LFU does not damage the primary. → **2 atom-mode
  spinoffs** (LFU, FIFO; LRU might be the worked example in the primary).

## Error handling, full table

| Issue | Action | Terminal Output |
|-------|--------|-----------------|
| (atom only) Concept un-distillable to ≤ 50 chars | Abort with suggestion to refine concept name upstream (the discover-layer concept may be too broad — split via spinoff). Applies only when `note_mode = atom`; thesis mode does not produce a one-line definition. | `echo -e "${RED}✗ ABORT:${RESET} Atom concept cannot fit in 50-char definition\n${DIM}  Refine concept name upstream or split via spinoff${RESET}"` |
| (atom only) Budget > 500 after compression and optional-section demotion | Abort — concept is too dense to fit in one atom note. Caller should re-run with a narrower concept or consider whether the source is actually thesis-shaped. | `echo -e "${RED}✗ ABORT:${RESET} Atom concept cannot fit in 500-char budget — likely needs splitting via spinoff or reclassification to thesis${RESET}"` |
| (thesis only) Cannot identify a coherent macro thesis from source | Abort with suggestion to reclassify as atom instead. If the source has no macro claim, the modeler is likely mis-classifying a glossary-style source as thesis. | `echo -e "${RED}✗ ABORT:${RESET} No coherent macro thesis identifiable\n${DIM}  Reclassify as atom or refine source selection${RESET}"` |
| (thesis only) Zero supporting themes pass the one-atom-per-chapter rule | Abort — thesis without supporting structure is just a claim. Recommend reclassification to atom or selection of a richer source. | `echo -e "${RED}✗ ABORT:${RESET} Thesis has no supporting themes — reclassify as atom${RESET}"` |
| (thesis only) Every chapter < 200 chars after authoring | Abort — chapters are too thin to constitute a thesis; source is probably atom-shaped. | `echo -e "${RED}✗ ABORT:${RESET} All thesis chapters under-budget (<200) — reclassify as atom${RESET}"` |
| `modality_hint = structural-bullets` but can produce only one component | Warn and emit a single Definition (atom) / executive summary (thesis) without Mental Model; signal diagram-agent will receive an empty hint | `echo -e "${YELLOW}⚠${RESET} Insufficient components for Structural Bullets\n${DIM}  diagram-agent will receive empty hint${RESET}"` |
| Source has no extractable mental model at all | Warn, set `modality_hint = structural-bullets`, attempt component extraction; if still empty, escalate to the row above | `echo -e "${YELLOW}⚠${RESET} No extractable mental model from source${RESET}"` |
| `discover_output` missing required fields | Abort — caller (skill orchestrator) must supply complete discover-layer output | `echo -e "${RED}✗ ABORT:${RESET} discover_output missing required fields${RESET}"` |

---
