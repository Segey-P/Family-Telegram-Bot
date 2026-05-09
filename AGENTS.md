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

## Specialized Agents (15 Available)

| # | Agent | Purpose | Default Model |
|---|---|---|---|
| 1 | Code Simplifier | Code quality, reuse, efficiency | Qwen3 Coder (Free) |
| 2 | Security Reviewer | Vulnerabilities, CVE, OWASP Top 10 | Qwen3 Coder (Free) |
| 3 | Tech Lead / Solution Architect | Architecture trade-offs, scalability | Qwen3 Coder (Free) |
| 4 | UX Reviewer | UI/UX, accessibility, mobile | Qwen3 Coder (Free) |
| 5 | Agent Coach | Meta-optimization of agent instructions | Nemotron 3 Super |
| 6 | Product Manager | Feature utility, MVP scope, prioritization | Gemini 3 Flash |
| 7 | Models Manager | Dynamic model routing and cost audits | Qwen3 Coder (Free) |
| 8 | Compliance & SecOps | PIPEDA, Bill C-27, banking standards | Liquid LFM 2.5 Thinking |
| 9 | Database Architect | Schema, migrations, ACID, indexing | DeepSeek-V4 Flash |
| 10 | Refactor & Code Cleanup | Dead code, DRY, over-engineering | Qwen3 Coder (Free) |
| 11 | Documentation Writer | README, inline docs, API docs | Qwen3 Coder (Free) |
| 12 | Testing Specialist | Unit/integration tests, edge cases | Qwen3 Coder (Free) |
| 13 | DevOps & Release Engineer | CI/CD, GitHub Actions, Streamlit Cloud | Qwen3 Coder (Free) |
| 14 | Performance Optimizer | Streamlit, DB, API bottlenecks | Qwen3 Coder (Free) |
| 15 | API Design Reviewer | Endpoints, contracts, REST patterns | Qwen3 Coder (Free) |

## Model Switching

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
