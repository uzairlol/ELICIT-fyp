# 27 — Small Instruct Model Motivation (20260731)

## Exact model used

| Source | Value |
|--------|-------|
| Results filename + memory lock | `llama3.1:8b` |
| Batch default | `DEFAULT_MODEL = "llama3.1:8b"` in `src/run_experiments.py` |
| Runtime client | Local Ollama via `src/llm/ollama_client.py` |

[Evidence: `00_project_memory.md` | run=20260731_013853 | round=n/a | agent=n/a | record=model]  
[Evidence: `src/run_experiments.py` | run=n/a | round=n/a | agent=n/a | record=DEFAULT_MODEL]

This is a **small instruct-style chat model** served locally — not a frontier reasoning model (`_is_reasoning_model` targets deepseek-r1 / “reasoning” tags separately).

---

## Methodological defence (implementation-supported)

Argue only from what the codebase and experimental design actually enable:

| Argument | Why it fits this project |
|----------|--------------------------|
| **Controlled, repeatable agent behaviour** | Fixed prompts + parsers + seed=1; same model tag across 26×30 decision loops |
| **Tractable repeated simulation** | Many agent-round LLM calls per run; Full condition already heavy; small model keeps sweeps (`run_experiments.py`) feasible |
| **Transparent reasoning traces** | Structured reasoning/facts fields stored and extracted (3854 blocks) for qualitative analysis |
| **Reproducibility & local data control** | Ollama local inference; results JSON under researcher control; no remote API drift mid-run |
| **Easier ablation** | Condition flags (shocks, LDF, democracy modules) + model name CLI — small models reduce cost of factorials |
| **Reduced latency / operational cost** | Local 8B class enables full multi-stage rounds (institution, contribution, punishment, ToM, democracy) |
| **Bounded decision-makers (experimental stance)** | Agents are intentionally **not** omniscient planners; hidden LDF pool + short contexts already bound information — a small instruct model matches a *bounded* decision surface without importing excessive world knowledge that could collapse the experimental game into outside politics |
| **Lower inference variance (relative claim)** | Smaller instruct models often produce more formulaic outputs — useful when the object of study includes **prompt-conditioned strategy language** (Prompt 6 templates), provided limitations are disclosed |

[Evidence: `src/llm/ollama_client.py` | run=n/a | round=n/a | agent=n/a | record=OllamaClient]  
[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=corpus_stats]

**Non-arguments (rejected):** “we could not afford a larger model,” hardware sympathy, or “smaller = more realistic humans.” Realism is not claimed via parameter count.

---

## Limitations (must stay visible)

| Limitation | Manifestation in this pack |
|------------|----------------------------|
| Weaker multi-step reasoning | Short contribution texts (~10 tokens mean); sparse proposal rationales |
| Prompt sensitivity | SI “self-interest/strategy” vs SFI “immediate/long-run incentives” templates |
| Repetitive language | High counts of boilerplate cooperation/institution phrases |
| Limited strategic depth | Weak reputation repair; little fairness/reciprocity language |
| Long-horizon state | Agent autocorr only ~0.21; group-mean autocorr ~0.03 |
| Model-specific artefacts | Institution reasoning often echoes forced-routing strings |
| Limited external validity | One model family; no cross-model replication in this pack |

[Evidence: `synthesis/21_norm_emergence_assessment.md` | run=20260731_013853 | round=n/a | agent=n/a | record=prompt_induced]  
[Evidence: `tables/prompt7_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=autocorr]

---

## How this choice serves the organising question

The research question concerns movement from voluntary contribution → social enforcement → institutional adaptation under imperfect observation. That requires **many** logged interactions, not a single brilliant plan. A small local instruct model makes that volume of agent-round evidence collectible while keeping reasoning inspectable. The cost is depth and generality — accepted explicitly, and visible in the limited-norm / template-language findings of Prompts 6–7.

**Confidence:** high on “which model”; moderate on methodological defence; high that limitations are material to interpretation.
