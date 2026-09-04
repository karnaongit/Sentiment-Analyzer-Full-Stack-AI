# Agent Instructions for Sentiment Analyzer

Welcome. You are working on the **Sentiment Analyzer** project (React + FastAPI + LangGraph + PostgreSQL).

At the beginning of a new task, first consult `PROJECT_CONTEXT.md` and the relevant source files before implementing.

## Core Rules

1. **Read `PROJECT_CONTEXT.md`** before making non-trivial changes. It is the single source of truth for this project's architecture, LangGraph workflow, and database schema.
2. **Verify against code**: Treat `PROJECT_CONTEXT.md` as project knowledge, but always verify against actual code when necessary.
3. **Preserve Architecture**: Maintain the React → FastAPI → LangGraph → PostgreSQL separation of concerns. Do not rewrite working architecture unnecessarily.
4. **PostgreSQL is the Source of Truth**: Use PostgreSQL via SQLAlchemy for persistent storage. Never add Redis or external caching unless explicitly requested.
5. **Deterministic KPIs**: Keep numeric KPI calculations strictly deterministic; never use an LLM or probabilistic model for math.
6. **Keep Agents Simple**: Do not invent unnecessary subagents or microservices. Maintain the streamlined LangGraph StateGraph workflow.
7. **Inspect before modifying**: Before modifying a feature, inspect its existing implementation and dependencies closely.
8. **Minimal, Targeted Changes**: Prefer minimal changes over broad refactoring.
9. **Update Context**: After significant architecture or feature changes, update `PROJECT_CONTEXT.md` to reflect the new reality.
10. **Keep README Synchronized**: Keep user-facing documentation aligned with actual setup and commands.
11. **No Hallucinations**: Never invent APIs, components, models, or configurations that do not exist.
12. **Test Affected Flows**: Test the affected flow after changes (using API tests and browser verification).

## Standard Project Commands

```bash
# Start PostgreSQL Database
docker compose up -d

# Start Application (Backend + Frontend concurrently)
npm run dev
```
