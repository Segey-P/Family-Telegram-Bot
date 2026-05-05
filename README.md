# Project Template

This is a template for new projects in the workspace. Copy this directory when starting a new project and customize the files below.

---

## For New Projects

When creating a new project, follow these steps:

1. **Copy this template:**
   ```bash
   cp -r _template new-project-name
   cd new-project-name
   git init
   ```

2. **Update project files:**
   - `CLAUDE.md` — Fill in [Project Name], repo slug, stack, etc.
   - `README.md` — Describe your project (user-facing)
   - `TODO.md` — Add your first tasks

3. **Create specs/ files:**
   - Start with `context-agent-instructions.md` (how to work on the project)
   - Then `spec-requirements.md` (what to build)
   - Then `plan-phases.md` (how to break it into phases)
   - Finally `ref-decisions.md` (track decisions made)

4. **Push to GitHub:**
   ```bash
   git add -A
   git commit -m "Initialize [Project Name] from template"
   git remote add origin https://github.com/Segey-P/repo-slug.git
   git push -u origin main
   ```

5. **Update workspace:**
   - Add the new project to `projects.json` in Project Management Hub
   - Update the workspace-level `CLAUDE.md` if needed

---

## Template Contents

| File | Purpose | Customize |
|------|---------|-----------|
| `CLAUDE.md` | Agent instructions | Yes — fill in your project details |
| `README.md` | User-facing overview | Yes — describe your project |
| `TODO.md` | Current tasks | Yes — add your first tasks |
| `specs/context-*.md` | Agent instructions (detailed) | Yes — fill in your tech stack |
| `specs/spec-*.md` | Requirements & definitions | Yes — define your features |
| `specs/plan-*.md` | Phases & roadmap | Yes — break into phases |
| `specs/ref-*.md` | Decisions & reference | Yes — log decisions made |
| `.gitignore` | Exclude from git | Optional — add project-specific items |

---

## Key Principles

1. **Keep TODO.md clean:** Delete completed items immediately. Only show active/next tasks.
2. **Read specs first:** Any agent starting work should read `specs/context-*.md` first.
3. **No secrets in code:** Use environment variables or Streamlit Cloud secrets.
4. **Push to main:** Feature branches only for large/risky changes.
5. **Update specs as you go:** Specs are the source of truth for requirements.

---

## For Reference

See `/Users/sergeypochikovskiy/AI_workspace/CLAUDE.md` for comprehensive workspace-level guidance on:
- Code quality standards
- Git workflow
- Streamlit patterns
- Database design decisions
- Deployment procedures
- Security checklist

---

**Template Version:** 1.0  
**Last Updated:** 2026-04-28  
**Maintained By:** Segey-P
