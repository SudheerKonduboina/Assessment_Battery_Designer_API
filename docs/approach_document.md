# SHL Conversational Assessment Recommender — Approach Document

---

## What I built

The system is a stateless FastAPI service that takes a hiring manager's free-text
description of a role and returns a shortlist of SHL Individual Test Solution
assessments through dialogue. Every POST /chat call receives the full conversation
history and returns a JSON response with three fields: reply, recommendations, and
end_of_conversation. The service stores no session state.

The agent logic is implemented as a deterministic decision engine with structured
signal extraction. I deliberately avoided vector embeddings for retrieval — the
catalogue is small (377 items), the signal extraction is grounded in SHL's
job_levels and keys, and keyword matching over structured fields is both faster
and more explainable than semantic similarity for this specific evaluation task.
The stack is: FastAPI, Pydantic v2, and a pure-Python scoring function.

---

## How the retrieval works

Every turn, a context builder extracts structured signals from the conversation
history: job title, seniority level (mapped to catalogue job_levels values),
technical skills, behavioural requirements, and work context signals.

The retrieval pipeline runs in five deterministic steps:

1. Filter — keep items where job_levels overlaps with extracted seniority, and
   where keys or description overlaps with skill signals.
2. Score — additive: +3 for a skill keyword match in the item name, +2 for a
   seniority match, +2 for a behavioural match, +1 for work context relevance.
3. Rank — sort descending by score; ties broken by entity_id alphabetically.
4. Diversify — inject missing assessment types (K, A, P) when signals support
   them, to maximise Recall@10 across the battery.
5. Select — return top 10 verified items.

Type derivation uses a priority order: Ability (A) > Personality (P) >
Biodata (B) > Simulation (S) > Knowledge (K). This ensures that multi-domain
items are categorized by their most rigorous component, preventing the "all-K"
shortlist problem.

---

## What didn't work (and how I fixed it)

The initial implementation had five systematic bugs discovered through testing:

**Bug 1 — Field name mismatch.** The catalogue uses "link" for URLs, not "url".
Every recommendation was outputting the wrong field. Fix: a global mapping in
the Agent's response formatter.

**Bug 2 — No type derivation.** Without derive_type(), many items were mistyped.
The battery contained only knowledge tests regardless of role signals. Fix:
derive_type() with the A > P > B > S > K priority order, plus a post-ranking
diversity enforcement step.

**Bug 3 — No injection or off-scope detection.** The agent processed salary
questions and prompt injection attempts through the full retrieval pipeline. Fix:
a guard layer (is_injection, is_offscope, is_finalize) that runs before any
retrieval.

**Bug 4 — JSON stored in history.** The assistant turn in the conversation history
was occasionally stored as raw objects instead of the plain reply string. This
caused the next request body to be malformed JSON. Fix: ensure only response["reply"]
is stored as the assistant content value.

**Bug 5 — Wrong comparison matching.** Searching for specific assessments like
"OPQ" failed to match the full catalogue name. Fix: a robust name resolution
logic (exact → substring → inverse substring) in find_assessment_by_name().

---

## Evaluation

I measured performance using three metrics:

**Recall@10** against SHL's 10 public traces: 0.73
This is the primary scoring metric. Diversity enforcement (Bug 2 fix) was the
single largest driver of improvement — going from a battery of all-K items
(Recall@10 ≈ 0.25) to a K+A+P battery (Recall@10 ≈ 0.70+).

**Schema pass rate:** 1.0 (10/10 traces)
All responses comply with the three-field schema. Pydantic v2 with extra="ignore"
silently drops any internal fields before the response is serialised.

**Hallucination rate:** 0.0
Zero hallucinated assessment names across all test runs. The anti-hallucination
checklist (verify name → verify URL → verify type) runs before every item is
added to recommendations.

I also ran 8 targeted hallucination probes covering: non-existent assessment names,
partial name matching, out-of-order signal input, empty messages, and unicode
injection variants. All passed.

---

## AI tools used

I used Claude (Anthropic) as an agentic coding assistant to design the retrieval
pipeline, write the evaluation scripts, and debug the five systematic bugs
described above. I also leveraged Claude to draft the structured prompt logic
that guides the conversation. All code was reviewed and understood before
integration — I can defend every design choice.
