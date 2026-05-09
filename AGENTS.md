# Agent Context — [Project Name]

Mirrors `CLAUDE.md` for non-Claude agents.

## What This Project Is

[One sentence description.]

## Rules

1. Read `TODO.md` before starting — it is the source of truth for next actions.
2. Never commit secrets or credentials.
3. Push to `main` directly.
4. `TODO.md` is read by the Project Hub dashboard — keep it current and updated throughout the session.
5. Prefer editing existing files over creating new ones.
6. Keep dependencies minimal.
7. Update specs in `specs/` at the end of every session and after any major change in requirements or behaviour.

---

## Specialized Agents (15 Active)

| # | Agent | Purpose | Default Model |
|---|---|---|---|
| 1 | Code Refiner | Code quality, refactoring, cleanup | Qwen3 Coder (Free) |
| 2 | Security & Compliance Officer | Vulnerabilities, PIPEDA, OWASP, banking | Liquid LFM 2.5 Thinking |
| 3 | Tech Lead / Solution Architect | Architecture trade-offs, scalability | Gemini 3 Flash |
| 4 | UX Reviewer | UI/UX, accessibility, mobile | Qwen3 Coder (Free) |
| 5 | Agent Coach | Meta-optimization of agent instructions | Gemini 3 Flash |
| 6 | Product Manager | Feature utility, MVP scope, prioritization | Gemini 3 Flash |
| 7 | Models Manager | Dynamic model routing and cost audits | Qwen3 Coder (Free) |
| 8 | Database Architect | Schema, migrations, ACID, indexing | DeepSeek-V4 Flash |
| 9 | Documentation Writer | README, inline docs, API docs | Qwen3 Coder (Free) |
| 10 | Testing Specialist | Unit/integration tests, edge cases | Qwen3 Coder (Free) |
| 11 | DevOps & Release Engineer | CI/CD, GitHub Actions, Streamlit Cloud, Vercel | Qwen3 Coder (Free) |
| 12 | Performance Optimizer | Streamlit/React/DB/API bottlenecks | Qwen3 Coder (Free) |
| 13 | API Design Reviewer | Endpoints, contracts, REST patterns | Qwen3 Coder (Free) |
| 14 | GitHub Ops | PRs, issues, branches, repo scaffolding | Qwen3 Coder (Free) |
| 15 | Streamlit Pro | Dashboard architecture, caching, Streamlit-specific | Qwen3 Coder (Free) |

## Model Pool

| Model | Best For | Limitations |
|---|---|---|
| **Qwen3 Coder (Free)** | Fast lookups, small edits, structured output | Limited reasoning depth |
| **Gemini 3 Flash** | Large context, history analysis, multi-file reads | Higher latency |
| **NVIDIA Nemotron 3 Super** | Cross-document reasoning, long-form writing | Slower than free models |
| **Liquid LFM 2.5 Thinking** | Regulatory analysis, security audits, complex logic | Token-heavy |
| **DeepSeek-V4 Flash** | SQL/NoSQL schemas, precise data tasks | Narrow focus |

**Rules:**
1. Start with cheapest capable model unless context is large (>50k tokens) or task is reasoning-heavy.
2. If output quality degrades, escalate to next tier.
3. Log model switches in commit messages: `[model: Gemini 3 Flash]`

---

## Execution Protocol (All Agents)

For every multi-file or multi-step task:

1. **Plan first** — identify dependencies. Group by independent units.
2. **Estimate** — give time + model choice upfront before starting.
3. **Parallelize** — run independent tasks concurrently. Different models if justified.
4. **Sequential only** — when outputs feed into next steps.

| Phase | Parallel? | Model |
|---|---|---|
| Read + analyze | Sequential (once) | Qwen3 Coder (Free) |
| Write / edit files | Parallel (no dependencies) | Qwen3 or Gemini 3 Flash |
| Git operations | Parallel (repos are independent) | Qwen3 Coder (Free) |

**Rule:** Never batch unrelated work sequentially just because it's the same tool. Parallelize whenever safe.

Full definitions: `/Users/sergeypochikovskiy/AI_workspace/AGENTS.md`
