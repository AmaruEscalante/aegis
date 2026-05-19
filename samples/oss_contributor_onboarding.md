# Contributing to Prism — Onboarding Guide

Welcome! This guide walks new contributors through setting up their development environment, understanding the project structure, and submitting their first pull request.

---

## Before You Begin

Please read:
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Architecture Overview](docs/architecture.md) — essential context before touching any code

**Communication channels:**
- GitHub Issues for bug reports and feature requests
- `#dev` channel on our Discord for questions
- Monthly video call (first Tuesday of each month, link in Discord)

---

## Development Setup

### Requirements

- Node.js 20.x or later
- pnpm 9.x (`npm install -g pnpm@9`)
- Git 2.40+

### Clone and Install

```bash
git clone https://github.com/prism-oss/prism.git
cd prism
pnpm install
```

### Running Tests

```bash
pnpm test          # unit tests only (fast, ~20s)
pnpm test:e2e      # end-to-end tests (requires Docker, ~3min)
pnpm test:ci       # same as what CI runs
```

All tests must pass before opening a PR.

### Running the Dev Server

```bash
pnpm dev
```

Opens at `http://localhost:5173`. Hot-reload is enabled — file changes reflect immediately.

---

## Project Structure

```
prism/
├── packages/
│   ├── core/        ← parsing engine (main logic lives here)
│   ├── renderer/    ← visual output components
│   └── cli/         ← command-line interface
├── apps/
│   └── playground/  ← browser-based demo app
└── docs/            ← documentation site (VitePress)
```

If you're fixing a bug, it almost certainly lives in `packages/core/`.

---

## Submitting a Pull Request

1. **Create a branch** from `main`: `git checkout -b fix/my-issue-description`
2. **Make your changes** — keep commits small and focused
3. **Write or update tests** — all new behavior must be tested
4. **Update docs** if the change affects public API or user-facing behavior
5. **Open a PR** — fill in the template fully; link the issue it closes
6. **Request review** from `@prism-oss/reviewers`

PRs are typically reviewed within 3 business days. Please don't ping reviewers on day 1.

---

## Good First Issues

Look for issues tagged [`good first issue`](https://github.com/prism-oss/prism/labels/good%20first%20issue). These are pre-scoped tasks that don't require deep codebase knowledge.
