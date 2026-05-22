"""
Curated training data for Aegis privacy classifier — handwritten by Claude
to avoid the pattern collapse observed in SLM-generated content (where every
README shared an identical skeleton, every NDA the same WHEREAS clauses, etc.).

50 examples per class × 4 classes = 200 examples. Each example targets a
specific scenario from train/prompts.py but is written with deliberate
structural / stylistic variety: different lengths, voices, formats, industries.

Run as a script to dump to train/dataset.jsonl:

    python train/curated_data.py
"""

import json
from pathlib import Path


CLASSIFY_SAFE = [
    # 0. README.md for an open-source Python utility library (string manipulation)
    """# strutil

Lightweight string utilities. No deps, no surprises.

```python
from strutil import dedent, slugify, ngrams

dedent("    hello\\n    world")    # "hello\\nworld"
slugify("Hello, World!")            # "hello-world"
list(ngrams("banana", 2))           # ["ba", "an", "na", "an", "na"]
```

## Install

    pip install strutil

## Why

I kept rewriting the same five string helpers in every project. Now they live here.

Tested on CPython 3.9+ and PyPy. No C extensions. ~400 lines total.
""",

    # 1. README.md for an open-source JavaScript date-formatting library
    """## chronoscript

A 3kb date formatter for the browser. Built because moment.js is 70kb and I needed sub-page-weight.

### Install

`npm i chronoscript` or `<script src="https://unpkg.com/chronoscript">`

### Use

    format(new Date(), 'YYYY-MM-DD HH:mm')   // "2024-03-14 09:42"
    format(new Date(), 'ddd, MMM Do YYYY')    // "Thu, Mar 14th 2024"
    parse('2024-03-14', 'YYYY-MM-DD')          // Date

### Tokens

| Token | Output |
| YYYY | 2024 |
| MM | 03 |
| DD | 14 |
| HH | 09 (24-hour) |
| hh | 09 (12-hour) |
| mm | 42 |
| ddd | Thu |
| MMM | Mar |
| Do | 14th |

PRs welcome. Tests must pass on Node 18+ and the last 2 versions of Chrome/Firefox/Safari.
""",

    # 2. MIT LICENSE file
    """The MIT License (MIT)

Copyright (c) 2023 Lila Brookman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
""",

    # 3. CONTRIBUTING.md for an open-source library
    """# Contributing

Glad you're here. Couple of quick things before you open a PR.

**Open an issue first** if your change is more than ~50 lines or touches public API. Saves both of us the heartbreak of a closed PR after you've done the work.

**Style**: we use `ruff` for linting and `ruff format` for formatting. Run `make lint` before pushing. CI will reject anything ruff complains about.

**Tests**: pytest. New behavior gets a new test. Bug fixes get a regression test. Run `make test` locally; CI runs the same on 3.9, 3.10, 3.11, 3.12.

**Commits**: use conventional commits if you can (`feat:`, `fix:`, `docs:`, `refactor:`). Doesn't have to be perfect. Squash before merging is fine.

**Don't worry about**: typos in docs, formatting fixes, dropping a `print` someone left in. Just send the PR.

**Do think about**: backward compatibility. We follow semver strictly on minor releases. If you're proposing a breaking change, that's a conversation for an issue, not a PR.

Feel free to ask questions. There are no dumb ones.
""",

    # 4. CHANGELOG.md fragment for a CLI tool
    """## [2.4.0] - 2024-08-12

### Added
- `--json` output mode for all subcommands. Pipes cleanly to `jq`.
- `cfg list --since <date>` — show config entries modified after a given date.
- Shell completion for fish (zsh and bash were already supported).

### Changed
- `cfg validate` now exits 2 instead of 1 on schema errors, matching the convention in `jsonschema`. Exit code 1 is reserved for "validation passed but warnings present."
- Default timeout for `cfg push` raised from 5s to 15s after several reports of flaky CI runners.

### Fixed
- Crash when `~/.config/foo` is a broken symlink (regression introduced in 2.3.4).
- `cfg diff` no longer emits ANSI color codes when stdout is redirected.

### Deprecated
- `--legacy-format` flag will be removed in 3.0. Use `--format=v1` instead.

### Internal
- Migrated from `setup.py` to `pyproject.toml`. No user-facing change.
""",

    # 5. B2B SaaS marketing one-pager (analytics platform)
    """**Pulse Analytics: Product Analytics That Actually Answer Questions**

Most analytics tools tell you what happened. Pulse tells you why.

Built for product teams at scale, Pulse combines event-level data with native cohort analysis and an SQL-first query layer that doesn't make you wait 90 seconds for a dashboard to load.

**What you get**

Funnel analysis without the upfront schema work. Drop in events, ask questions in plain English or SQL, get answers under a second.

Retention curves with cohort drill-down. Slice by acquisition channel, plan tier, or any custom property without re-running pipelines.

Auto-anomaly detection on every chart you save. We notify you when a metric drifts more than 2 standard deviations from its trailing 30-day mean — no manual alert configuration.

**How it's different**

Most tools sample your data. Pulse doesn't — we run every query against the full event log. That's why our P95 latency is 800ms even on multi-billion-row datasets.

**Pricing**

Starts at $499/month for up to 5M events. Volume tiers from there. No per-seat fees, no upsell to "enterprise tier" for basic features like SSO.

Try it free for 14 days — no credit card.
""",

    # 6. Consumer app marketing copy for a meditation app
    """**Quiet — A Meditation App That Doesn't Try Too Hard**

You don't need another app screaming at you to "Start Your Mindfulness Journey." Quiet is just meditations. Press play, sit, breathe.

**What's in here**

- 200+ guided sessions from 6-30 minutes, recorded in a studio (not on a phone)
- Sleep stories — slow-paced narration designed to put you under, not entertain you
- Bare-bones timer with bells, if you already know what you're doing
- Daily check-in, optional, no streak guilt

**What's not in here**

- Push notifications begging you to come back
- "Wellness coaches" trying to upsell you to a coaching subscription
- Social features
- Ads of any kind

**Pricing**

$4.99/month. $39/year. 7-day free trial. Cancel from the iOS / Android settings page, not through us.

**A word from the founder**

I built Quiet because every meditation app I tried felt like a marketing funnel with breathing exercises bolted on. If you want to meditate, the app should get out of your way. That's the whole idea.

— Maya
""",

    # 7. Press release — product launch
    """FOR IMMEDIATE RELEASE

Threshold Robotics Unveils Atlas Mark IV, Doubling Payload Capacity for Warehouse Automation

PITTSBURGH, PA — September 18, 2024 — Threshold Robotics today announced the commercial availability of Atlas Mark IV, its fourth-generation autonomous mobile robot platform, designed for high-throughput fulfillment centers and cross-docking operations.

The Mark IV doubles the payload capacity of its predecessor to 1,200 kilograms while reducing average pick-to-station cycle times by 34 percent in Threshold's internal benchmarks. The system retains the same 1.4-meter footprint, allowing operators to upgrade existing Mark III fleets without aisle reconfiguration.

"Our customers told us they were hitting throughput ceilings, not space ceilings," said Daniel Whitman, CEO of Threshold Robotics. "Mark IV is our answer: more capacity, same physical envelope, same fleet management tooling."

The platform integrates with major warehouse management systems and is shipping today to early-access partners in North America and Europe. General availability is expected in Q1 2025.

About Threshold Robotics
Threshold Robotics designs and manufactures autonomous mobile robots for material handling and fulfillment operations. Founded in 2017, the company is headquartered in Pittsburgh, with engineering offices in Munich and Singapore.

Press contact: press@thresholdrobotics.com
""",

    # 8. Public case study (aggregate ROI from an anonymized B2B customer)
    """## Case Study: Mid-Market Retailer Cuts Database Costs 38% with TimescaleDB

A North American specialty retailer (revenue $400-600M) running 14 stores plus an e-commerce channel was facing exponential cost growth on its analytics infrastructure. Inventory telemetry, point-of-sale events, and supply-chain data were accumulating in a managed Postgres instance that had been vertically scaled three times in 18 months.

The team migrated their time-series workload to TimescaleDB and consolidated 11 different reporting jobs onto a single materialized view layer.

### Results, six months in

- **38%** reduction in monthly database spend (combined Postgres + ETL pipeline costs)
- **6.2x** faster average query time on the analytics dashboard set
- **94%** reduction in storage footprint for raw event data via compression
- Operational headcount unchanged (the existing team absorbed the migration over a quarter)

### What they kept

The company continued using their existing Postgres instance for transactional workloads. The migration was scoped narrowly to time-series and analytical queries, which had been the cost driver.

### What surprised them

The compression ratio. The team had budgeted for ~30% storage savings; they got 94%. Most of that came from columnar compression on the high-cardinality event tables.

Full technical details, including schema diagrams and benchmark methodology, are available on request.
""",

    # 9. Public API reference page for a payments SDK
    """### POST /v1/charges

Create a charge against a saved payment method.

**Request body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| amount | integer | yes | smallest currency unit (e.g. cents) |
| currency | string | yes | ISO-4217 |
| source | string | yes | payment method ID |
| description | string | no | up to 500 chars |
| metadata | object | no | key/value, both strings, max 50 keys |

**Example**

    curl -X POST https://api.payd.dev/v1/charges \\
      -H "Authorization: Bearer YOUR_PUBLIC_TEST_KEY" \\
      -d amount=2500 \\
      -d currency=usd \\
      -d source=pm_test_4242

**Response**

    {
      "id": "ch_1ABC...",
      "amount": 2500,
      "currency": "usd",
      "status": "succeeded",
      "created": 1726502400
    }

**Status codes**

- 200: charge succeeded
- 402: card declined; see `decline_code` in response body
- 422: validation error
- 429: rate limited; retry with backoff
- 5xx: server error; safe to retry idempotently if you provide an `Idempotency-Key` header
""",

    # 10. Step-by-step tutorial: how to deploy a Next.js app to Vercel
    """# Deploying Your First Next.js App to Vercel

If you've never deployed anything before, this'll take about 8 minutes start to finish.

## Prerequisites

- A Next.js project that runs locally (`npm run dev` works)
- A GitHub account
- A Vercel account (free tier is fine)

## Step 1: Push to GitHub

Create a repo on GitHub, then from your project directory:

    git init
    git add -A
    git commit -m "initial commit"
    git remote add origin <your repo URL>
    git push -u origin main

## Step 2: Import to Vercel

Go to vercel.com/new, click "Import Git Repository," and select the repo you just pushed.

Vercel will auto-detect Next.js. You don't need to change anything in the "Configure Project" page unless you have a specific reason.

Click "Deploy."

## Step 3: Wait ~90 seconds

You'll see the build log scroll past. When it's done you'll get a URL like `your-project-abc123.vercel.app`.

## What just happened

Vercel cloned your repo, ran `next build`, and deployed the output to their edge network. Every time you push to `main`, this happens again automatically. PRs get their own preview URLs.

## What's next

- Add a custom domain in Vercel project settings
- Set environment variables (if your app needs them) under Settings → Environment Variables
- Read about Edge Functions if you want to ship serverless code that runs close to your users
""",

    # 11. FAQ page for a developer tool
    """# Frequently Asked Questions

**Is foo free?**
The CLI is free and open source under Apache 2.0. The hosted dashboard has a free tier (up to 3 projects); paid tiers start at $19/month.

**Does foo work on Windows?**
Yes. We test on Windows 10/11, macOS 12+, and Ubuntu 22.04 LTS. WSL is supported but native Windows works fine too.

**What about ARM Macs (M1/M2/M3)?**
Native ARM64 builds since v0.8. If you installed via Homebrew before v0.8, run `brew reinstall foo` to pick up the native binary.

**How does foo compare to bar?**
Different goals. Foo focuses on local development workflows; bar is a CI-first tool. Many people use both. We've published a side-by-side comparison at /compare-bar.

**Can I use foo without the hosted dashboard?**
Yes. The CLI works fully offline; the dashboard is optional for collaboration and history.

**Is there a way to self-host the dashboard?**
Yes, on the Team and Enterprise plans. Docker Compose setup, takes about 15 minutes.

**How do I report a bug?**
Open an issue on GitHub with output from `foo doctor` attached. We triage within 2 business days.

**Where can I ask questions?**
Discord (link in the README) or GitHub Discussions. We don't monitor Twitter for support.
""",

    # 12. Public product spec for an open-source DB extension
    """## pg_search — Postgres Extension for Full-Text Search

### Status
Stable. Released to public registries as of v0.6.0 (June 2024). Tested on Postgres 14, 15, and 16.

### What it does
Adds BM25-scored full-text search to Postgres, with phrase queries, fuzzy matching, and field-weighted scoring, exposed as standard SQL operators.

### What it isn't
Not a replacement for Elasticsearch when you need cross-cluster search at petabyte scale. It's for the 95% of cases where your search data fits in a Postgres database and you'd rather not run a second piece of infrastructure.

### Usage

    CREATE EXTENSION pg_search;

    CREATE INDEX idx_articles_search ON articles USING pgs (title, body);

    SELECT id, title FROM articles
    WHERE search('quick brown fox')
    ORDER BY rank() DESC
    LIMIT 10;

### Roadmap
- v0.7: synonym dictionaries
- v0.8: per-language stemmers (currently English-only)
- v1.0: stability commitment for SQL surface, semantic versioning thereafter

### Non-goals
We don't plan to add vector search; that's pgvector's job. We're not building our own storage layer; we rely on Postgres heap and indexes throughout.
""",

    # 13. Excerpt from a public annual report (aggregate numbers only)
    """### Financial Highlights — Fiscal Year 2023

Total revenue for the fiscal year ended December 31, 2023 was $2.84 billion, an increase of 19 percent compared to fiscal 2022. Growth was driven primarily by expansion in our subscription business, which now represents 71 percent of total revenue.

Gross margin improved to 64 percent from 61 percent in the prior year, reflecting continued infrastructure efficiency gains and a more favorable revenue mix.

Operating income was $412 million, or 14.5 percent of revenue, compared to $268 million, or 11.2 percent, in fiscal 2022. The improvement reflects operating leverage from revenue growth and disciplined cost management.

We ended the fiscal year with 4,820 full-time employees globally, up from 4,150 a year earlier. Our team is now distributed across 14 countries.

Cash and cash equivalents totaled $1.1 billion at year-end. During the year we repurchased $180 million of common stock under our existing authorization, with $320 million remaining authorized at year-end.

Free cash flow for the year was $487 million, representing a free-cash-flow margin of 17 percent, up from 12 percent in fiscal 2022.

We continue to invest in research and development at approximately 20 percent of revenue, consistent with our long-term commitment to product innovation.
""",

    # 14. Public market research report excerpt (EV adoption)
    """## Global EV Adoption: 2024 Mid-Year Update

Electric vehicle sales reached an estimated 8.4 million units globally in the first half of 2024, up 27 percent year-over-year. This places full-year 2024 on track to exceed 18 million units, representing roughly 22 percent of new passenger vehicle sales worldwide.

China continues to lead in absolute volume, accounting for approximately 58 percent of global EV sales in H1. The Chinese market reached a 38 percent EV share of new passenger vehicle sales in June 2024, the highest monthly share recorded in any major market.

Europe (EU + UK + EFTA) represents the second-largest market by volume, with 1.7 million EVs sold in H1. EV share has plateaued at approximately 21 percent of new vehicle sales after rapid growth in 2020-2022, with affordability cited as the primary barrier to further share gains.

The United States lags both regions in share but is growing in volume, with approximately 720,000 EVs sold in H1, representing 9.4 percent of new vehicle sales.

Charging infrastructure deployment continues to accelerate, with an estimated 12 million public charging points globally as of June 2024, a 41 percent increase from June 2023.

This report draws on public registration data, industry trade publications, and IEA databases. All figures are estimates and subject to revision.
""",

    # 15. tsconfig.json with strict mode, paths
    """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "lib": ["DOM", "DOM.Iterable", "ES2022"],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@lib/*": ["./src/lib/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx"],
  "exclude": ["node_modules", "dist", "build"]
}
""",

    # 16. .eslintrc.json with rules
    """{
  "root": true,
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": 2022,
    "sourceType": "module",
    "project": "./tsconfig.json"
  },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  "plugins": ["@typescript-eslint", "react"],
  "rules": {
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "@typescript-eslint/no-explicit-any": "warn",
    "no-console": ["warn", { "allow": ["error", "warn"] }],
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off"
  },
  "settings": {
    "react": { "version": "detect" }
  },
  "ignorePatterns": ["dist/", "build/", "*.config.js"]
}
""",

    # 17. package.json without secrets
    """{
  "name": "metrics-collector",
  "version": "1.4.2",
  "description": "Lightweight metrics collection for Node.js services",
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src --ext .ts",
    "format": "prettier --write \\"src/**/*.ts\\"",
    "prepublishOnly": "npm run build && npm test"
  },
  "dependencies": {
    "prom-client": "^15.1.0"
  },
  "devDependencies": {
    "@types/node": "^20.10.0",
    "@typescript-eslint/eslint-plugin": "^6.13.0",
    "@typescript-eslint/parser": "^6.13.0",
    "eslint": "^8.55.0",
    "prettier": "^3.1.0",
    "typescript": "^5.3.2",
    "vitest": "^1.0.0"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/sonsa/metrics-collector.git"
  },
  "license": "MIT"
}
""",

    # 18. Public CSV: weather station readings
    """station_id,observation_date,observation_time_utc,temperature_celsius,humidity_percent,wind_speed_kmh,pressure_hpa
KSEA,2024-09-14,00:00,14.2,82,8,1015.3
KSEA,2024-09-14,03:00,12.8,86,5,1015.1
KSEA,2024-09-14,06:00,11.4,89,3,1014.8
KSEA,2024-09-14,09:00,13.1,84,7,1014.9
KSEA,2024-09-14,12:00,16.7,71,12,1015.4
KSEA,2024-09-14,15:00,18.9,62,14,1015.2
KSEA,2024-09-14,18:00,17.6,68,11,1014.6
KSEA,2024-09-14,21:00,15.3,76,8,1014.2
KDEN,2024-09-14,00:00,8.1,45,6,1018.9
KDEN,2024-09-14,03:00,6.4,52,4,1019.1
KDEN,2024-09-14,06:00,4.8,58,3,1019.2
KDEN,2024-09-14,09:00,9.7,41,8,1019.4
KDEN,2024-09-14,12:00,16.2,28,11,1019.0
KDEN,2024-09-14,15:00,19.4,21,14,1018.5
KDEN,2024-09-14,18:00,17.1,29,12,1018.1
KDEN,2024-09-14,21:00,12.6,38,9,1018.4
""",

    # 19. Public CSV: city population statistics
    """city,country,population_2010,population_2015,population_2020,population_2023_estimate
Tokyo,Japan,37100000,38000000,37400000,37200000
Delhi,India,21900000,25700000,30300000,32900000
Shanghai,China,20300000,23700000,27100000,29200000
Sao Paulo,Brazil,19700000,21000000,22000000,22600000
Mexico City,Mexico,20100000,21000000,21800000,22200000
Cairo,Egypt,16900000,18800000,20900000,22600000
Mumbai,India,19400000,19500000,20400000,20900000
Beijing,China,15500000,18200000,20400000,21800000
Dhaka,Bangladesh,14700000,17600000,21000000,23200000
Osaka,Japan,19500000,19300000,19200000,19000000
New York,United States,18400000,18600000,18800000,18900000
Karachi,Pakistan,13100000,15400000,16100000,16800000
Buenos Aires,Argentina,14200000,14900000,15200000,15400000
Chongqing,China,11200000,13300000,15900000,17000000
Istanbul,Turkey,13400000,14200000,15200000,15800000
""",

    # 20. Recipe blog post
    """# The Easiest Roasted Tomato Pasta

This is the dinner I make when I haven't been to the grocery store, when I'm tired, when I've been promising myself "I'll cook something real this week" and have not.

You need:

- A pint of cherry tomatoes
- A whole head of garlic
- Olive oil
- A box of pasta — whatever shape, doesn't matter
- Salt, pepper
- Basil if you have it. Don't go buy it specially.

Heat the oven to 425°F. Put the tomatoes whole in a baking dish. Slice the top off the head of garlic so the cloves peek out. Nestle it in among the tomatoes. Pour over a generous glug of olive oil — maybe 3-4 tablespoons. Salt liberally.

Into the oven for 35 minutes. You're looking for the tomatoes to burst and the garlic to go golden and soft.

Meanwhile, boil pasta. Use plenty of salt in the water. Drain a minute before the package says, keeping a cup of pasta water.

When the tomatoes are out, smush the garlic cloves out of their papery skins into the dish with a fork. Mash everything together. It should look like a chunky sauce now.

Add the pasta and a splash of the pasta water. Toss. Black pepper. Basil if applicable.

That's it. Serves 2 generously or 3 modestly. Leftovers are excellent cold the next day.
""",

    # 21. Travel blog post about Tokyo
    """## Three Days in Tokyo Without Trying

Most Tokyo guides will tell you to organize your visit by neighborhood: a day for Shibuya, a day for Asakusa, etc. I think that's tiring and you end up never feeling like you understand where you are. Here's what I'd do differently.

Pick one neighborhood. Walk for hours in it. Eat at three random places. Take the train home.

That's it.

If pressed for a more structured suggestion: stay in Yanaka. It's quiet, low-rise, mostly residential, and surrounded by some of the easiest-to-love parts of the city. From there, walk to Nezu Shrine in the morning (mosquitoes if it's summer; bring repellent). Lunch at any of the tonkatsu places along Yanaka Ginza. Afternoon: take a 30-minute train ride to Ginza, but pick one street and walk it slowly.

A few practical notes:

- Cash is still useful, especially for smaller restaurants. Konbini ATMs accept foreign cards.
- The trains are fantastic but rush hour is real. Avoid 7:30-9:30 and 17:00-19:00 if you can.
- Vending machines are everywhere and the canned coffee is unironically great.
- Almost no one will speak English in smaller restaurants. They'll be patient and you'll be fine.

Last thing: don't try to "see" Tokyo. You can't. Just be there.
""",

    # 22. Tech blog post explaining B-trees
    """## Why Your Database Is Faster Than It Has Any Right to Be

If you've ever wondered how Postgres can find a single row among a hundred million in under a millisecond, the answer is: B-trees.

A B-tree is just a balanced search tree where every node has many children — typically dozens or hundreds — rather than the strict two of a binary tree. This bushiness is the whole trick.

Suppose you have 100 million rows and you want to find one. With a binary tree, you'd need about log₂(100,000,000) ≈ 27 comparisons. That's not bad, but each of those comparisons might be a disk read (or at least a cache miss), and 27 disk reads is slow.

A B-tree with a fan-out of, say, 200 children per node only needs log₂₀₀(100,000,000) ≈ 3.5 levels — call it 4 disk reads. That's nearly 7x fewer reads. Doesn't sound like much, but at scale and over billions of queries, it's the difference between a snappy database and an unusable one.

The fan-out also has a friendly relationship with how disks work. A "page" in most databases is 8KB or 16KB. If you size your B-tree nodes to fit in one page, then loading a node is one I/O operation, and you've packed as much branching information as possible into each I/O.

The "B" in B-tree, by the way, doesn't officially stand for anything. Bayer (one of the inventors) said in an interview that "you can think of it as 'balanced' if you like."
""",

    # 23. Tech blog post comparing two JS frameworks
    """## React vs. Solid: A Tale of Two Reactivity Models

Both React and Solid let you write component-based UIs. The surface APIs look similar — JSX, components as functions, hooks. Where they fundamentally diverge is in how they detect what to update.

React, by default, re-runs your entire component function whenever a state variable inside it changes. The virtual DOM is then diffed against the previous render to figure out the actual DOM changes. This is conceptually clean — your function is the description of what should be rendered — but the cost is that you're potentially doing a lot of work per state change.

Solid takes the opposite approach. It compiles your JSX into imperative DOM operations at build time, and uses fine-grained reactivity (signals) to track exactly which DOM nodes need to update when which state changes. There is no re-render. Your component function runs once, when the component is created. After that, only the specific DOM bindings that depend on a changed signal get updated.

Practical implications:

- React's mental model is simpler: state changes → component re-runs → DOM updates.
- Solid's mental model is more nuanced: state changes → specific DOM bindings re-execute.
- React benefits enormously from libraries like react-compiler that automate the memoization most React apps end up needing.
- Solid doesn't need memoization because it never does unnecessary work.

Neither is "better" in a vacuum. React has the larger ecosystem; Solid has the better default performance. Pick based on what your team can maintain.
""",

    # 24. Tutorial: Docker for local development
    """# Setting Up Docker for Local Development

This guide assumes you've installed Docker Desktop and can run `docker --version` successfully.

## What we're building

A development environment with three services: a Node.js app, a Postgres database, and a Redis cache. All three will run in containers and talk to each other over a private Docker network.

## docker-compose.yml

In the root of your project, create `docker-compose.yml`:

    services:
      app:
        build: .
        ports:
          - "3000:3000"
        environment:
          DATABASE_URL: postgres://dev:dev@db:5432/myapp
          REDIS_URL: redis://cache:6379
        depends_on:
          - db
          - cache
        volumes:
          - ./src:/app/src

      db:
        image: postgres:16
        environment:
          POSTGRES_USER: dev
          POSTGRES_PASSWORD: dev
          POSTGRES_DB: myapp
        volumes:
          - postgres_data:/var/lib/postgresql/data

      cache:
        image: redis:7-alpine

    volumes:
      postgres_data:

## Why this layout

Each service gets its own container, but they all share a network. The hostnames `db` and `cache` resolve to the right containers automatically.

The volume mount on `./src:/app/src` means your local code edits show up in the container immediately — no rebuild needed for most changes.

## Daily use

`docker compose up` starts everything. Ctrl-C to stop.
`docker compose down` removes the containers but keeps the postgres volume.
`docker compose down -v` also removes the postgres volume, giving you a clean slate.

That's it. Spend a day with it. You won't want to go back.
""",

    # 25. Open-source code: array manipulation utility module
    """// arr-utils.ts — small, dependency-free array helpers
// MIT licensed. See LICENSE.

export function chunk<T>(arr: readonly T[], size: number): T[][] {
  if (size <= 0) throw new RangeError("chunk size must be positive");
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) {
    out.push(arr.slice(i, i + size));
  }
  return out;
}

export function unique<T>(arr: readonly T[]): T[] {
  return [...new Set(arr)];
}

export function groupBy<T, K extends string | number>(
  arr: readonly T[],
  key: (item: T) => K
): Record<K, T[]> {
  const out = {} as Record<K, T[]>;
  for (const item of arr) {
    const k = key(item);
    (out[k] ||= []).push(item);
  }
  return out;
}

export function zip<A, B>(a: readonly A[], b: readonly B[]): Array<[A, B]> {
  const len = Math.min(a.length, b.length);
  const out: Array<[A, B]> = [];
  for (let i = 0; i < len; i++) out.push([a[i], b[i]]);
  return out;
}

export function partition<T>(
  arr: readonly T[],
  predicate: (item: T) => boolean
): [T[], T[]] {
  const truthy: T[] = [];
  const falsy: T[] = [];
  for (const item of arr) {
    (predicate(item) ? truthy : falsy).push(item);
  }
  return [truthy, falsy];
}
""",

    # 26. Open-source code: Python class implementing a sorted set
    """\"\"\"sorted_set.py

A minimal sorted set backed by a sorted list. O(log n) membership tests,
O(n) inserts and removes. Not as fast as the `sortedcontainers` library,
but has no dependencies and fits in 60 lines.

Suitable for collections up to maybe 10k items. For larger, use blist or
sortedcontainers.SortedList.
\"\"\"

from bisect import insort, bisect_left
from typing import Iterable, TypeVar

T = TypeVar("T")


class SortedSet:
    \"\"\"A set that maintains its elements in sorted order.\"\"\"

    def __init__(self, items: Iterable[T] = ()):
        self._items: list[T] = []
        for item in items:
            self.add(item)

    def add(self, item: T) -> None:
        idx = bisect_left(self._items, item)
        if idx < len(self._items) and self._items[idx] == item:
            return
        insort(self._items, item)

    def remove(self, item: T) -> None:
        idx = bisect_left(self._items, item)
        if idx < len(self._items) and self._items[idx] == item:
            del self._items[idx]
        else:
            raise KeyError(item)

    def discard(self, item: T) -> None:
        idx = bisect_left(self._items, item)
        if idx < len(self._items) and self._items[idx] == item:
            del self._items[idx]

    def __contains__(self, item: T) -> bool:
        idx = bisect_left(self._items, item)
        return idx < len(self._items) and self._items[idx] == item

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __repr__(self) -> str:
        return f\"SortedSet({self._items!r})\"
""",

    # 27. Open-source code: a small React Button component
    """import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { clsx } from "clsx";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary: "bg-slate-900 text-white hover:bg-slate-800 active:bg-slate-700",
  secondary: "bg-slate-100 text-slate-900 hover:bg-slate-200 active:bg-slate-300",
  ghost: "bg-transparent text-slate-900 hover:bg-slate-100",
  danger: "bg-red-600 text-white hover:bg-red-700 active:bg-red-800",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-base",
  lg: "px-6 py-3 text-lg",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, leftIcon, rightIcon, disabled, children, className, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center gap-2 rounded-md font-medium transition disabled:opacity-50 disabled:pointer-events-none",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...rest}
    >
      {loading ? <span className="animate-spin">⠋</span> : leftIcon}
      {children}
      {rightIcon}
    </button>
  );
});
""",

    # 28. Code-of-conduct
    """# Community Code of Conduct

We want this project to be a place where people learn, build, and have fun together. To make that possible, we ask everyone — contributors, maintainers, and users — to read and honor this code.

**Be kind.** Approach disagreements with patience. Assume good faith. Remember that the person on the other side of the screen is a human being with their own context.

**Be specific.** When critiquing, critique the work, not the person. "This function is hard to follow" is fine. "You write bad code" is not.

**Be honest.** Don't say things you don't believe. Don't say things to score points. If you're wrong, say so.

**Help newcomers.** Everyone was a beginner once. If someone is asking a question that seems obvious to you, remember that it isn't obvious to them yet, and answering carefully is a gift you give them.

**Don't.** Harassment, slurs, threats, sexually explicit content, and personal attacks have no place here. Neither does sustained disruption of discussions, dismissive responses ("read the docs"), or any conduct that would be inappropriate in a professional setting.

If you experience or witness behavior that violates this code, report it to coc@example-project.org. Reports are confidential and will be reviewed by at least two maintainers. We act, including removal of contributors, when warranted.

This document is adapted from the Contributor Covenant, with modifications. We update it as we learn.
""",

    # 29. Public roadmap document
    """## Q1 2025 Roadmap

This is a public, best-effort plan. Priorities can shift; this isn't a commitment. We'll update this doc monthly.

### Themes for the quarter

1. **Stability over features.** We shipped a lot in Q4. This quarter is about consolidation — fixing the bugs we accumulated, tightening tests, and reducing flakiness.
2. **Improved onboarding.** New users tell us the first 10 minutes are confusing. We want to make the install-to-first-success path much shorter.
3. **Plugin system.** Community has asked for extensibility. We're going to ship a small, well-defined plugin API.

### Concrete planned work

- Migrate the test suite off the old fixture system (tracked in #1842)
- Fix the slow startup time on Windows (#1901)
- Write a "5-minute getting started" guide and rework the home page to lead with it (#1934)
- Design and ship the plugin API; we'll publish an RFC by end of January (#1966)
- Triage and fix or close the issues older than 6 months that don't have a clear path forward

### Out of scope this quarter

- Major new features in the CLI surface
- Marketing pushes / conference talks (back next quarter)
- Multi-language client libraries (still on the longer roadmap, not Q1)
""",

    # 30. Stack Overflow answer (CSS grid)
    """The reason your two columns aren't equal height is that `display: grid` on the parent only stretches its direct children, and you've wrapped each column in an extra `<div>` that doesn't have explicit grid placement.

Here's the minimal fix:

    .container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    .container > * {
      display: flex;
      flex-direction: column;
    }

Now every direct child of `.container` will stretch to the height of the tallest child, and each becomes a flex column itself, so content inside can use `margin-top: auto` to push to the bottom.

If you actually want the inner content of each column to be vertically centered, change the second rule to:

    .container > * {
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

A couple of things to watch out for:

1. If you set `align-items: start` on the grid container, children won't stretch and you'll be back where you started.
2. If the children themselves have `height: 100%` set somewhere, that can interact strangely with the grid stretch behavior. Strip it out and rely on grid stretching.

I've been bitten by both of these. Grid is great once it clicks but the interaction with descendant flex/sizing rules is genuinely confusing.
""",

    # 31. GitHub issue: dark mode toggle
    """**Feature request: dark mode toggle in settings**

Hi! Love this app. One thing that would make it a daily-driver for me: a dark mode toggle in the settings page.

Currently the app respects the OS-level color scheme preference (which is great), but I'd love to be able to override it from within the app. Specifically:

- Light (always light, regardless of OS)
- Dark (always dark, regardless of OS)
- System (current behavior — follow OS)

Use case: I have my OS set to "light during the day, dark at night" via macOS's auto setting, but for this particular app I always want it dark because I use it mostly in dim rooms.

I poked around the codebase and it looks like the theme is already a CSS variable that gets set based on a `prefers-color-scheme` media query. Plumbing this through to a settings toggle should be straightforward — happy to take a stab at a PR if you'd accept one.

Let me know how you'd want this surfaced in the UI. I was thinking a three-way segmented control in Settings → Appearance, but you might prefer a different placement.

Thanks for the great work!
""",

    # 32. Public meetup announcement
    """**Python Pittsburgh — September Meetup**

When: Tuesday, September 24, 2024, 6:30 PM — 8:30 PM
Where: WeWork US Steel Tower, 600 Grant Street, 28th floor

Topic: "Async Python in 2024: What Actually Works"

Our speaker is Aisha Patel, a backend engineer at a local fintech who spends most of her time wrangling asyncio in production. She'll walk through the patterns that have served her well and the ones she's learned to avoid the hard way. There'll be a Q&A after.

This is a casual meetup. No pre-reading required. We'll have pizza and drinks. Bring a friend.

Free to attend, but please RSVP at meetup.com/pittsburgh-python so we order enough pizza. If you signed up and can't make it, no worries — just unRSVP so someone on the waitlist gets a spot.

Note: the WeWork lobby has a metal-detector security check, so plan a couple of extra minutes. Once you check in at the front desk, take the elevator to 28.

See you there.
""",

    # 33. Public job description (backend engineer)
    """## Backend Engineer (Mid / Senior)

We're a 35-person infrastructure-tools company hiring our 8th engineer. The team is fully remote across US time zones, with quarterly in-person retreats.

### What you'd work on

Our product is a distributed scheduler that runs millions of jobs a day for our customers. You'd be on the team responsible for the scheduling kernel: scheduling correctness, failure recovery, and performance.

Concrete projects on our near-term roadmap that you might pick up:
- Rewriting the priority-queue implementation to support backpressure
- Designing the v2 of our retry/timeout/circuit-breaker semantics
- Investigating P99 latency regressions across customer fleets

### What we look for

- Comfortable in Go (we'd happily teach you if you're strong in another systems language)
- Some experience with distributed systems — doesn't have to be deep
- A bias toward writing clear, debuggable code over clever code
- Strong opinions, held loosely

### Compensation

We publish exact salary bands. This role is $165k-$210k base + equity. We don't negotiate the band; we negotiate where within the band based on your experience.

### How to apply

Send a resume and a paragraph about an interesting bug you debugged to jobs@example-co.dev. We respond to every application within 5 business days.
""",

    # 34. Public docs: command reference for a CLI tool
    """### foo — command reference

    foo [global-options] <subcommand> [subcommand-options] [args...]

**Global options**

| Flag | Description |
| `--config <path>` | Use a config file at the given path. Default: `~/.config/foo/config.toml`. |
| `--verbose` | Show debug output. |
| `--quiet` | Suppress non-error output. |
| `--no-color` | Disable ANSI color codes. Useful when piping. |
| `--version` | Print version and exit. |
| `--help` | Print help. |

**Subcommands**

`init` — Create a new foo project in the current directory.
`build` — Compile the project. Output goes to `./dist` unless `--out` is given.
`test` — Run the test suite. Forwards extra args to the underlying test runner.
`run` — Build and run the project in development mode.
`deploy` — Push the latest build to a deployment target. Requires login.
`login` — Authenticate against the registry. Saves credentials to your OS keychain.
`logout` — Clear stored credentials.

Run `foo <subcommand> --help` for subcommand-specific options.

**Examples**

    foo init --template=ts-library
    foo build --out=./build --release
    foo test -- --grep "edge case"
    foo deploy production --confirm
""",

    # 35. Public docs: error code reference for an API
    """## Error Code Reference

When the API returns an error, the response body has the form:

    {
      "error": {
        "code": "INVALID_PARAMETER",
        "message": "Human-readable explanation",
        "param": "name_of_field_with_problem"
      }
    }

The HTTP status code reflects the broad category; the `code` field tells you the specific reason.

### 4xx codes

`INVALID_PARAMETER` (400) — One or more fields had bad values. The `param` field identifies which.
`MISSING_PARAMETER` (400) — A required field was absent.
`UNAUTHORIZED` (401) — Your API key is missing or wrong. Get a new one if you've rotated.
`FORBIDDEN` (403) — You authenticated but lack permission for this resource.
`NOT_FOUND` (404) — The resource ID you provided doesn't exist or is hidden from you.
`CONFLICT` (409) — The request would create a duplicate or violate a constraint. Inspect `details`.
`RATE_LIMITED` (429) — Slow down. The `Retry-After` header tells you when to retry.

### 5xx codes

`INTERNAL_ERROR` (500) — Something broke on our side. We see these and triage. Safe to retry with backoff.
`SERVICE_UNAVAILABLE` (503) — We're degraded. Retry with backoff. We may publish a status page banner.
`GATEWAY_TIMEOUT` (504) — A downstream service took too long. Retry with backoff.

All 5xx responses are safe to retry if you pass an `Idempotency-Key` header.
""",

    # 36. Public benchmark report: HTTP libraries
    """## Benchmarking Three Open-Source HTTP Client Libraries

We measured throughput and latency of three Rust HTTP clients — `reqwest`, `hyper` (lower-level), and `ureq` — against a local echo server, varying request size and concurrency.

### Setup

- Hardware: AWS c6i.4xlarge (16 vCPU, 32 GB RAM), Ubuntu 22.04
- Server: a minimal hyper-based echo server on the same machine
- Workload: 100,000 requests per run, 30-second steady-state sample, three runs averaged

### Results — small requests (256-byte bodies, GET)

| Library | Throughput (req/s) | P50 (ms) | P95 (ms) | P99 (ms) |
| reqwest | 88,400 | 0.42 | 0.71 | 1.34 |
| hyper (raw) | 124,600 | 0.31 | 0.52 | 1.02 |
| ureq | 31,200 | 1.18 | 1.71 | 2.46 |

### Results — large requests (1 MB bodies, POST)

| Library | Throughput (req/s) | P50 (ms) | P95 (ms) | P99 (ms) |
| reqwest | 1,290 | 18.4 | 24.7 | 38.1 |
| hyper (raw) | 1,380 | 17.2 | 23.1 | 36.4 |
| ureq | 1,240 | 19.6 | 26.3 | 41.7 |

### Reading the numbers

For small-request workloads, the gap between hyper and the higher-level libraries is real. For large bodies, the wire and serialization costs dominate; the library choice is mostly irrelevant.

ureq's synchronous design has higher per-request overhead but its simpler API is often worth it for tools that aren't request-throughput-bound.

This is a microbenchmark. Your workload will differ. Reproducing repo: github.com/example/http-bench.
""",

    # 37. Public design system documentation
    """### Color Tokens

Our design system organizes colors into semantic tokens. Components should always reference tokens, never raw hex values. This lets us adjust themes (light/dark, brand variants) without touching component code.

**Background tokens**
- `--bg-canvas` — The page background
- `--bg-surface` — Cards, modals, anything that sits on the canvas
- `--bg-elevated` — Tooltips, dropdowns, anything that sits on a surface
- `--bg-inset` — Inputs, sunken regions

**Text tokens**
- `--text-primary` — Body text
- `--text-secondary` — Captions, helper text
- `--text-disabled` — Disabled states
- `--text-on-brand` — Text on top of brand-colored backgrounds (white in our light theme)

**Border tokens**
- `--border-subtle` — Default borders, dividers
- `--border-strong` — Inputs that need emphasis
- `--border-focus` — The focus ring, applied via `outline`

### Spacing Scale

Use only these values. 4px base unit.

    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-6: 24px;
    --space-8: 32px;
    --space-12: 48px;
    --space-16: 64px;

### Typography

Two font families:
- `--font-sans` — Inter, fallback to system-ui
- `--font-mono` — JetBrains Mono, fallback to monospace

Size scale follows a modular ratio of 1.2, anchored at 16px body text. See `tokens/typography.css` for the full ladder.
""",

    # 38. Public conference abstract
    """**Abstract: Cooperative Schedulers for Heterogeneous Edge Devices**

PerfCon 2024, Track 3, Tuesday 11:15 AM

Edge deployments increasingly span heterogeneous hardware: some nodes have GPUs, others don't; some have abundant memory, others are RAM-constrained; some sit on 5G, others on flaky LTE. Most scheduling systems either assume homogeneity or push the complexity to the workload definitions, neither of which scales.

This talk presents the design and operational experience of a cooperative scheduler that exposes node capabilities as a structured constraint vocabulary and asks workloads to declare their requirements at the same level. The result is a placement algorithm that runs in linear time in the number of (workload, node) pairs and handles the heterogeneity without exploding configuration surface.

We'll cover:
- The constraint language we landed on after three iterations
- The placement algorithm (a modified greedy bin-packing with backtracking)
- Operational lessons from running this in production on ~12,000 nodes over 18 months
- Two failure modes we hit and how we now defend against them

This is an experience talk. No prior knowledge of distributed scheduling required, but it'll help if you've written or operated a job scheduler before.

Speaker: David Park is a staff engineer on the platform team at a logistics company. Prior: Google, MIT CSAIL.
""",

    # 39. Public newsletter issue
    """**Bytes Weekly #47 — Friday, October 4, 2024**

A short roundup of what caught my eye this week.

**1. The Go team published their proposal for a new iter package in the stdlib.**
This is a big deal. Range-over-func, which landed in 1.23, gets a lot more useful when there's a community-blessed set of helpers. I'm particularly interested in the proposed `iter.Map` and `iter.Filter`. Link in the proposal: golang.org/cl/proposal/iter.

**2. A nice deep-dive on how Cloudflare implements DNS over QUIC at scale.**
The honest writeups about *why* a particular trick was needed (rather than just "here's our cool architecture") are the best kind of engineering blog post. blog.cloudflare.com — search "doq scale."

**3. SQLite 3.47 shipped with the new vector-search extension as a first-class member of the build.**
Locally-runnable vector search, no external dependencies. I tried it Wednesday for a side project. Index build was slower than pgvector but query time was faster on my dataset (small, ~50k vectors). Worth a look if you're allergic to running another piece of infrastructure.

**4. Something non-tech: a podcast episode worth your time.**
"What Even Is Money?" — Planet Money's episode from September 27 on the history of the gold standard. The pacing in the second half is exceptional.

That's it for this week. As always, reply with anything you'd like me to cover. — Sam
""",

    # 40. Public glossary of ML terms
    """# A Small Glossary of Machine Learning Terms

For people who've heard these words used in meetings but want a quick refresher.

**Backpropagation.** The algorithm for computing how each weight in a neural network should change to reduce a loss value. Walks the chain rule backwards through the network from output to input.

**Embedding.** A learned representation of something (a word, an image, a user) as a vector of real numbers. Similar things end up with similar vectors. Used as input to other models or for retrieval.

**Fine-tuning.** Taking a model that's already been trained on some general task and adjusting its weights on a smaller, task-specific dataset.

**Gradient.** The partial derivatives of the loss function with respect to each weight. Tells you which direction in weight-space lowers the loss.

**Inference.** Running a trained model to get predictions, as opposed to training the model.

**Loss function.** A scalar that measures how wrong the model's predictions are on the training data. Training minimizes this.

**Overfitting.** When the model has learned the training data too literally, including its noise, and doesn't generalize to new examples.

**Token.** The unit of text that a language model operates on. Roughly a word or piece of a word — modern tokenizers chop language into ~4-character subwords on average.

**Zero-shot.** Asking a model to do a task it wasn't explicitly trained on, relying on the generality of what it learned during pre-training.
""",

    # 41. Public whitepaper excerpt — consensus algorithms
    """### Selected Trade-offs in Modern Consensus Algorithms

Three families of consensus algorithms dominate practical use today: Paxos and its descendants, Raft, and the BFT (Byzantine Fault Tolerant) family typified by PBFT. Each is correct, and each has been deployed at meaningful scale. The differences are in operational characteristics.

**Paxos and Multi-Paxos** are the oldest of the three. The basic Paxos protocol agrees on a single value; Multi-Paxos extends this to a sequence. The algorithm is correct and proven, but the original Lamport paper is famously difficult to follow, and most production implementations are descendant variants with their own subtleties. Operators report higher initial learning curve but solid steady-state behavior.

**Raft** was designed explicitly for understandability. It separates leader election, log replication, and safety into three subproblems that can each be reasoned about in isolation. Operationally, Raft is more sensitive to network partitions than Multi-Paxos and tends to have more leader-election churn under unstable conditions. The trade-off is that ops teams can debug it without a PhD.

**PBFT and BFT variants** tolerate Byzantine faults — that is, nodes that lie or behave maliciously, not just nodes that crash. The cost is a higher message complexity (typically O(n²) per consensus round) and stricter requirements on the number of replicas needed (3f+1 to tolerate f Byzantine failures). Most non-blockchain systems don't need BFT and pay the performance cost without benefit; most blockchain systems need it and gladly pay.

These algorithms are different points in the same trade-off surface. Pick the one whose properties match your operational model.
""",

    # 42. Public coding-bootcamp curriculum outline
    """## Full-Stack Web Development Bootcamp — Curriculum

**Duration**: 12 weeks, full-time, in-person
**Cohort size**: 24 students max, 3 instructors

### Week 1-2: Foundations

- Computers, networks, the web (what actually happens when you type a URL)
- HTML semantics, CSS layout (Flexbox, Grid)
- JavaScript fundamentals — values, types, control flow, functions, scope
- Tooling: VS Code, git basics, the command line

### Week 3-4: Modern JavaScript

- ES6+ syntax, modules, destructuring, spread/rest
- Promises, async/await, the event loop
- DOM manipulation, events
- Fetch and JSON

### Week 5-7: Frontend with React

- Components, props, state, lifecycle
- Hooks (useState, useEffect, useReducer, custom hooks)
- Routing (React Router)
- State management patterns (when you need it, when you don't)
- Capstone-1: a personal-projects portfolio in React

### Week 8-10: Backend with Node and Express

- HTTP request/response model
- REST API design, validation, error handling
- Persistent storage — SQL with Postgres, ORM with Prisma
- Authentication — sessions, JWTs, OAuth
- Capstone-2: a small full-stack app with auth and a database

### Week 11-12: Production and Job Search

- Deployment to Vercel (frontend) and Railway/Fly (backend)
- Testing — Jest for unit, Playwright for E2E
- CI/CD basics with GitHub Actions
- Mock interviews, portfolio review, job-search workshops

### Outcomes

Students leave with a portfolio of 3 projects, including one full-stack application, and a resume ready for entry-level positions.
""",

    # 43. Public sample test suite for a string parser
    """import { describe, it, expect } from "vitest";
import { parseQueryString } from "../src/qs";

describe("parseQueryString", () => {
  it("parses an empty string to an empty object", () => {
    expect(parseQueryString("")).toEqual({});
  });

  it("strips a leading question mark", () => {
    expect(parseQueryString("?a=1")).toEqual({ a: "1" });
  });

  it("parses a single key=value pair", () => {
    expect(parseQueryString("name=alice")).toEqual({ name: "alice" });
  });

  it("parses multiple key=value pairs", () => {
    expect(parseQueryString("a=1&b=2&c=3")).toEqual({ a: "1", b: "2", c: "3" });
  });

  it("decodes URL-encoded values", () => {
    expect(parseQueryString("q=hello%20world")).toEqual({ q: "hello world" });
    expect(parseQueryString("q=caf%C3%A9")).toEqual({ q: "caf\\u00e9" });
  });

  it("treats keys without an equals sign as empty-string values", () => {
    expect(parseQueryString("flag")).toEqual({ flag: "" });
    expect(parseQueryString("a&b&c")).toEqual({ a: "", b: "", c: "" });
  });

  it("collapses repeated keys, keeping the last", () => {
    expect(parseQueryString("a=1&a=2&a=3")).toEqual({ a: "3" });
  });

  it("preserves whitespace and formatting", () => {
    expect(parseQueryString("note=line%201%0Aline%202")).toEqual({
      note: "line 1\\nline 2",
    });
  });

  it("ignores trailing ampersands", () => {
    expect(parseQueryString("a=1&")).toEqual({ a: "1" });
    expect(parseQueryString("a=1&&b=2")).toEqual({ a: "1", b: "2" });
  });
});
""",

    # 44. Public hackathon submission README
    """# Composti

**Built for**: AI Hack Weekend 2024
**Team**: 2 people (Mira and Yusuf)
**Time**: 36 hours

## What it does

Composti turns a photo of your kitchen into a list of recipes you can make with what's in it, plus a shopping list for what's missing. Aimed at the "I'm hungry and don't want to think" use case.

## How

- Frontend: a single-page web app in Svelte
- Backend: a Node service that calls a vision model (we used the local gemma3-vision via Ollama for the hack — see notes)
- Recipe retrieval: a small Postgres database we seeded with ~500 recipes from a public CC-BY recipe corpus

## Demo

Working hosted demo (will be down 30 days after submission): composti-demo.fly.dev

## Stack notes

We deliberately kept this local-first because we weren't going to pay for hosted vision API credits during a hackathon. The whole thing runs on a laptop with Ollama plus a Postgres docker container.

## What we'd do with more time

- Better prompt for the vision step — currently fails ~20% of the time on cluttered counters
- Dietary-restriction filters (vegetarian, gluten-free, etc.)
- Save-the-list functionality with email export

## License

MIT. Use the code freely.

## Team

Mira Saito (frontend), Yusuf Ahmed (backend + ML wrangling). GitHub handles on the team page in the repo.
""",

    # 45. Public RFC
    """# RFC: Add `--exclude` flag to the `prune` subcommand

**Status**: Draft
**Author**: @qlk
**Discussion**: #2104

## Summary

Add a `--exclude <pattern>` flag to the `foo prune` subcommand that prevents matching artifacts from being deleted, even if they would otherwise qualify.

## Motivation

Currently `foo prune` deletes any cached artifact older than the configured TTL. This is great in the common case but problematic in two specific scenarios users have reported:

1. CI runners that share a cache directory between jobs. One job's recent artifacts can be sibling to another job's stale ones, and there's no way to say "leave these specific files alone."
2. Cached files that users have explicitly pinned via the `pin` command. The pinned status is respected by `gc` but not by `prune`. (Arguably this is a separate bug, but the proposed mechanism would fix it too.)

## Detailed design

Add a repeatable `--exclude <glob>` flag. Patterns are tested against the artifact's relative path. Files matching any provided pattern are skipped during prune.

    foo prune --older-than 7d --exclude "ci-build-*" --exclude "important/**"

Combine with `--dry-run` to verify exclusions before destructive runs.

## Alternatives considered

A config-file-based exclusion list. Rejected because it complicates the per-invocation case; the flag form is composable with config-defined defaults.

## Open questions

Should exclusions persist across runs (e.g., in a hidden marker file inside excluded directories)? My current preference is no — keep `--exclude` purely a per-invocation flag — but this could change based on user feedback.
""",

    # 46. Public release notes for a Linux distribution
    """## Foobian 14.3 Release Notes

**Released**: 2024-08-21
**Kernel**: 6.10.4-foobian1
**Estimated upgrade time**: 30-45 minutes

### Highlights

- Long-term support extended through April 2028
- Wayland is the default session for new installs (X11 still available)
- Default Python is now 3.12; 3.10 remains available via the foobian-python3.10 package

### Package upgrades

Notable packages updated in this release:
- glibc 2.39
- systemd 254
- gcc 14.2
- llvm 18
- openssl 3.3
- firefox-esr 128
- libreoffice 24.2
- gnome 46

### Removed packages

- `xorg-modular-server-deprecated` (replaced by `wayland-compositor`)
- `python2.7` (end of life since 2020)

### Known issues

- On systems with NVIDIA proprietary drivers older than 535, the upgrade may render Wayland sessions unstable. Workaround: install the latest NVIDIA driver before upgrading, or fall back to the X11 session at the login screen.
- The new GRUB 2.12 has a regression that affects systems booted via ZFS-on-root. A workaround patch is available via the `grub-zfs-patch` package.

### How to upgrade

Existing 14.x systems: `sudo foobian-upgrade --release=14.3`. Reboot when prompted.

Older releases (13.x): upgrade to 14.0 first, then to 14.3.
""",

    # 47. Public Terraform module example
    """# Example Terraform module: a small EC2 instance behind a security group

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

provider "aws" {
  region = var.region
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]   # Canonical's public account

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_security_group" "demo" {
  name        = "demo-instance-sg"
  description = "Allow inbound HTTP and SSH from anywhere (demo only)"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "demo" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.demo.id]

  tags = {
    Name = "demo-instance"
  }
}

output "public_ip" {
  value = aws_instance.demo.public_ip
}
""",

    # 48. Public Postman collection example (JSON, no API key)
    """{
  "info": {
    "name": "Weather API — Public Example",
    "description": "Example calls to a public weather API. Substitute your own API key into the collection variables before running.",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    { "key": "base_url", "value": "https://api.example-weather.dev/v1" },
    { "key": "api_key", "value": "YOUR_API_KEY_HERE" }
  ],
  "item": [
    {
      "name": "Current conditions by lat/lon",
      "request": {
        "method": "GET",
        "url": {
          "raw": "{{base_url}}/current?lat=47.6062&lon=-122.3321&units=metric&key={{api_key}}"
        }
      }
    },
    {
      "name": "5-day forecast by city",
      "request": {
        "method": "GET",
        "url": {
          "raw": "{{base_url}}/forecast?city=Seattle&units=metric&key={{api_key}}"
        }
      }
    },
    {
      "name": "Historical observation",
      "request": {
        "method": "GET",
        "url": {
          "raw": "{{base_url}}/history?station=KSEA&date=2024-08-15&key={{api_key}}"
        }
      }
    }
  ]
}
""",

    # 49. Public ETL pipeline tutorial — CSV to BigQuery
    """## Loading a Public CSV Into BigQuery

This walks through loading a public dataset (NOAA weather station readings) into BigQuery using the bq CLI. Total time: about 10 minutes.

### Prerequisites

- A Google Cloud project with billing enabled (the free tier includes 1 TB of BigQuery query and 10 GB of storage per month; the example fits comfortably under both)
- `gcloud` and `bq` installed locally
- Authenticated: `gcloud auth login`

### Step 1: Create a dataset

    bq mk --dataset --location=US weather_public

### Step 2: Download the source data

NOAA publishes daily summary CSVs at noaa.gov/public/data/global-hourly. For this example we'll grab one year of one station's data:

    curl -O "https://www.ncei.noaa.gov/data/global-hourly/access/2023/72793524234.csv"

### Step 3: Define the schema

The CSV has a fixed set of fields. Save this as `schema.json`:

    [
      { "name": "station", "type": "STRING" },
      { "name": "date", "type": "TIMESTAMP" },
      { "name": "source", "type": "STRING" },
      { "name": "latitude", "type": "FLOAT" },
      { "name": "longitude", "type": "FLOAT" },
      { "name": "elevation", "type": "FLOAT" }
    ]

### Step 4: Load

    bq load \\
      --source_format=CSV \\
      --skip_leading_rows=1 \\
      --allow_jagged_rows \\
      weather_public.station_72793524234 \\
      ./72793524234.csv \\
      ./schema.json

### Step 5: Query

    bq query --use_legacy_sql=false \\
      'SELECT EXTRACT(MONTH FROM date) as month, AVG(elevation) FROM weather_public.station_72793524234 GROUP BY month ORDER BY month'

That's the whole pipeline. Productionize by writing a small script to crawl the NOAA listing pages and load each station-year on a schedule.
""",
    # 50. .env.example with "your-*" placeholder values throughout
    """# Example environment configuration
# Copy to .env and replace placeholders with real values.

DATABASE_URL=postgresql://your-db-user:your-db-password@your-db-host:5432/your-db-name
REDIS_URL=redis://your-redis-host:6379/0
SECRET_KEY=your-secret-key-min-32-characters
JWT_SECRET=your-jwt-secret-min-32-characters

# Third-party API keys (sign up at the provider to obtain these)
STRIPE_SECRET_KEY=sk_test_your-stripe-test-key-here
SENDGRID_API_KEY=your-sendgrid-api-key
OPENAI_API_KEY=your-openai-api-key

# Feature flags (true/false)
ENABLE_BETA_FEATURES=false
""",
    # 51. .env.dist with explicit CHANGEME markers
    """# .env.dist — checked-in template. Copy to .env before running.

# Database
PG_HOST=localhost
PG_USER=app
PG_PASSWORD=CHANGEME
PG_DB=app_dev

# Auth
SESSION_SECRET=CHANGEME-AT-LEAST-32-CHARS
ADMIN_BOOTSTRAP_TOKEN=CHANGEME

# External services
SMTP_HOST=smtp.example.com
SMTP_USER=CHANGEME
SMTP_PASS=CHANGEME
""",
    # 52. .env.template with empty KEY= placeholders and inline documentation
    """# Production environment template
# Populate every key below before deploying.
# DO NOT commit a filled-in copy.

# Required: Postgres connection
DATABASE_HOST=
DATABASE_PORT=5432
DATABASE_USER=
DATABASE_PASSWORD=
DATABASE_NAME=

# Required: Redis (for sessions + job queue)
REDIS_HOST=
REDIS_PORT=6379

# Required: AWS S3 (for asset uploads)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=

# Optional: Sentry error tracking
SENTRY_DSN=
""",
]


FLAG_PII: list[str] = [
    # 0. customers.csv with 10 rows: full_name, email, phone, address
    """full_name,email,phone,address,signup_date
Mireille Okonkwo,mireille.o@gmail.com,(415) 555-0123,2418 Folsom Street San Francisco CA 94110,2023-04-12
Tomas Belmonte,t.belmonte@yahoo.com,(312) 555-0144,755 N Wells Avenue Chicago IL 60654,2022-11-04
Aiyana Whitewater,aiyana.ww@protonmail.com,(602) 555-0177,1409 W Lincoln Drive Phoenix AZ 85007,2024-01-21
Ruben Castellanos,rcastel@hotmail.com,(305) 555-0199,632 Brickell Avenue Miami FL 33131,2023-09-30
Hannelore Friedrich,h.friedrich@outlook.com,(212) 555-0156,180 Riverside Drive New York NY 10024,2023-02-14
Kwabena Mensah,kmensah@gmail.com,(404) 555-0188,2255 Peachtree Road Atlanta GA 30309,2024-03-08
Aisha Saraswati,aisha.s@gmail.com,(206) 555-0166,1450 NW Market Street Seattle WA 98107,2023-07-19
Lena Krasinski,lena.k@yahoo.com,(617) 555-0143,392 Commonwealth Avenue Boston MA 02215,2022-12-29
Devon Whitfield,d.whitfield@gmail.com,(303) 555-0122,1640 Pearl Street Boulder CO 80302,2024-02-11
Yuki Nakamura,yuki.n@icloud.com,(503) 555-0188,2125 SE Hawthorne Boulevard Portland OR 97214,2023-08-04
""",

    # 1. patient_records.csv with DOB, SSN, MRN, diagnosis
    """patient_id,first_name,last_name,date_of_birth,ssn,mrn,primary_diagnosis,attending_physician
P-10042,Margaret,Cho,1958-03-14,521-44-9087,MRN-00104201,Type 2 diabetes mellitus,Dr. Patel
P-10043,Hiroshi,Tanaka,1972-11-22,634-22-1198,MRN-00104230,Essential hypertension,Dr. Walsh
P-10044,Solange,Mbeki,1989-07-09,388-71-4502,MRN-00104265,Migraine without aura,Dr. Patel
P-10045,Boris,Yelchin,1965-01-28,512-91-3344,MRN-00104299,COPD stage II,Dr. Reyes
P-10046,Catalina,Reyes,1991-09-15,609-12-7723,MRN-00104330,Anxiety disorder NOS,Dr. Walsh
P-10047,Thomas,Yablokov,1949-05-03,287-44-8819,MRN-00104358,Coronary artery disease,Dr. Reyes
P-10048,Faiza,Al-Mahmoud,1983-12-19,711-33-2206,MRN-00104389,Gestational diabetes,Dr. Patel
P-10049,Eduardo,Penha,1978-04-30,499-66-1147,MRN-00104412,Major depressive disorder,Dr. Walsh
""",

    # 2. employees.json — 12 employees with name, email, phone, address, employee_id
    """[
  {"employee_id": "E04412", "name": "Anika Volkova", "email": "a.volkova@cnstrct.com", "phone": "(415) 555-2031", "address": "3429 22nd Street San Francisco CA 94110", "department": "Engineering", "salary_band": "L4"},
  {"employee_id": "E04413", "name": "Marcus Otieno", "email": "marcus.o@cnstrct.com", "phone": "(415) 555-2042", "address": "521 Lake Street San Francisco CA 94118", "department": "Engineering", "salary_band": "L5"},
  {"employee_id": "E04414", "name": "Priyanka Sundaresan", "email": "priya.s@cnstrct.com", "phone": "(510) 555-2089", "address": "1402 Stuart Street Berkeley CA 94703", "department": "Product", "salary_band": "L4"},
  {"employee_id": "E04415", "name": "Tobias Lindqvist", "email": "tobias.l@cnstrct.com", "phone": "(415) 555-2114", "address": "988 Page Street San Francisco CA 94117", "department": "Engineering", "salary_band": "L3"},
  {"employee_id": "E04416", "name": "Yolanda Becerra", "email": "yolanda.b@cnstrct.com", "phone": "(510) 555-2156", "address": "2218 Telegraph Avenue Berkeley CA 94704", "department": "Design", "salary_band": "L4"},
  {"employee_id": "E04417", "name": "Chinedu Achebe", "email": "chinedu.a@cnstrct.com", "phone": "(415) 555-2188", "address": "1801 Bush Street San Francisco CA 94109", "department": "Engineering", "salary_band": "L5"},
  {"employee_id": "E04418", "name": "Sevda Petrosyan", "email": "sevda.p@cnstrct.com", "phone": "(650) 555-2231", "address": "324 Lytton Avenue Palo Alto CA 94301", "department": "Engineering", "salary_band": "L6"},
  {"employee_id": "E04419", "name": "Jonas Wirtanen", "email": "jonas.w@cnstrct.com", "phone": "(415) 555-2267", "address": "676 Cole Street San Francisco CA 94117", "department": "Marketing", "salary_band": "L3"},
  {"employee_id": "E04420", "name": "Adaeze Eze", "email": "adaeze.e@cnstrct.com", "phone": "(415) 555-2289", "address": "2401 Octavia Street San Francisco CA 94109", "department": "Engineering", "salary_band": "L4"},
  {"employee_id": "E04421", "name": "Renzo Calabrese", "email": "renzo.c@cnstrct.com", "phone": "(510) 555-2301", "address": "5104 Telegraph Avenue Oakland CA 94609", "department": "Operations", "salary_band": "L3"},
  {"employee_id": "E04422", "name": "Lakshmi Narayan", "email": "lakshmi.n@cnstrct.com", "phone": "(415) 555-2334", "address": "1430 Filbert Street San Francisco CA 94109", "department": "Product", "salary_band": "L5"},
  {"employee_id": "E04423", "name": "Mateusz Zielinski", "email": "mat.z@cnstrct.com", "phone": "(415) 555-2356", "address": "2901 California Street San Francisco CA 94115", "department": "Engineering", "salary_band": "L4"}
]
""",

    # 3. hr_payroll.csv
    """name,ssn,address,gross_pay_ytd,net_pay_ytd,bank_account_last4,direct_deposit_routing
Hsu-Lien Wang,478-92-1100,4012 Cathedral Avenue NW Washington DC 20016,142500.00,98744.21,4422,031176110
Kwame Achiampong,512-77-3349,1881 Park Road NW Washington DC 20010,178200.00,121887.55,8819,031176110
Marielle Pereira,389-21-5547,2110 16th Street NW Washington DC 20009,98200.00,71422.18,5503,031176110
Otto Spengler,601-44-2287,3401 38th Street NW Washington DC 20016,210000.00,141502.66,9931,031176110
Aaliyah Ferguson,422-91-8843,1234 Quincy Street NE Washington DC 20017,87400.00,64118.92,7702,031176110
Yusuf Karadeniz,548-33-1190,4711 Connecticut Avenue NW Washington DC 20008,124800.00,89665.40,3318,031176110
""",

    # 4. mailing_list.csv — name, email, signup_date (20 rows)
    """name,email,signup_date,source
Dimitri Kalogeropoulos,dimitri.k@gmail.com,2024-01-04,homepage
Sora Tanigawa,sora.tani@yahoo.com,2024-01-06,instagram_ad
Beatriz Salgado,beatriz.salgado@outlook.com,2024-01-09,referral
Femi Ogundimu,femi.o@gmail.com,2024-01-11,newsletter_signup_modal
Anya Vasilyeva,anya.v@protonmail.com,2024-01-14,homepage
Tomasz Wojcik,tomasz.w@gmail.com,2024-01-15,podcast_ad
Mireille Bouchard,mireille.b@icloud.com,2024-01-18,homepage
Kenji Suzuki,k.suzuki@gmail.com,2024-01-19,twitter_ad
Aaliyah Robinson,aaliyah.r@gmail.com,2024-01-22,homepage
Stefano Marchetti,stefano.m@gmail.com,2024-01-23,referral
Indira Krishnaswamy,indira.k@gmail.com,2024-01-25,blog_signup
Olufemi Adeyemi,olufemi.a@gmail.com,2024-01-27,homepage
Magdalena Schaeffer,magda.s@gmail.com,2024-01-28,referral
Hyo-Jin Park,h.park@gmail.com,2024-01-30,instagram_ad
Reza Tabrizi,reza.t@gmail.com,2024-02-01,homepage
Aurore Lefebvre,aurore.l@gmail.com,2024-02-02,podcast_ad
Ngozi Okeke,ngozi.o@gmail.com,2024-02-04,referral
Lucia Bianchi,lucia.b@gmail.com,2024-02-05,homepage
Pawel Nowakowski,pawel.n@gmail.com,2024-02-07,homepage
Marisol Quintanilla,marisol.q@gmail.com,2024-02-09,instagram_ad
""",

    # 5. support_tickets.json — customer name, email, account_number, address
    """[
  {
    "ticket_id": "T-88412",
    "opened": "2024-08-14T09:14:22Z",
    "customer_name": "Lior Ben-David",
    "customer_email": "lior.bd@gmail.com",
    "customer_phone": "(310) 555-0144",
    "account_number": "AC-4477-2218",
    "shipping_address": "2014 Rose Avenue Venice CA 90291",
    "issue_category": "billing",
    "subject": "Was charged twice for August invoice",
    "body": "Hi — I see two charges on my card for $89.00 this month. The order numbers are O-1182 and O-1183 but I only placed one order. Can you refund the duplicate?"
  },
  {
    "ticket_id": "T-88413",
    "opened": "2024-08-14T09:18:01Z",
    "customer_name": "Saanvi Ramaswamy",
    "customer_email": "saanvi.r@yahoo.com",
    "customer_phone": "(469) 555-0188",
    "account_number": "AC-4488-9981",
    "shipping_address": "4108 McKinney Avenue Dallas TX 75204",
    "issue_category": "shipping",
    "subject": "Package marked delivered but not received",
    "body": "Tracking says delivered Aug 11 but nothing was at my door. Camera footage doesn't show any delivery that day. Order O-1144."
  },
  {
    "ticket_id": "T-88414",
    "opened": "2024-08-14T09:31:55Z",
    "customer_name": "Hakim Touré",
    "customer_email": "hakim.toure@gmail.com",
    "customer_phone": "(404) 555-0119",
    "account_number": "AC-4421-1106",
    "shipping_address": "1502 Boulevard SE Atlanta GA 30317",
    "issue_category": "product",
    "subject": "Defective unit — possibly battery",
    "body": "Bought the Model X3 two weeks ago. Won't hold a charge for more than 20 minutes now. Order O-1098, serial number SN-X3-2244187."
  },
  {
    "ticket_id": "T-88415",
    "opened": "2024-08-14T10:02:14Z",
    "customer_name": "Esperanza del Castillo",
    "customer_email": "esperanza.dc@hotmail.com",
    "customer_phone": "(786) 555-0177",
    "account_number": "AC-4408-3349",
    "shipping_address": "2422 Coral Way Miami FL 33145",
    "issue_category": "account",
    "subject": "Can't login — password reset email never arrived",
    "body": "Tried reset three times. Nothing in inbox or spam. My account email is esperanza.dc@hotmail.com."
  },
  {
    "ticket_id": "T-88416",
    "opened": "2024-08-14T10:14:38Z",
    "customer_name": "Tobias Reinholt",
    "customer_email": "tobias.r@protonmail.com",
    "customer_phone": "(206) 555-0188",
    "account_number": "AC-4399-0021",
    "shipping_address": "1820 N 50th Street Seattle WA 98103",
    "issue_category": "return",
    "subject": "Return label expired",
    "body": "The return label you sent on Aug 1 expired. Need a new one for order O-1066."
  }
]
""",

    # 6. survey_responses.csv with name, age, email, zip, free-text feedback
    """respondent_name,age,email,zip_code,nps_score,feedback
Ines Capucci,34,ines.c@gmail.com,11217,9,"Love the app. Wish the export to CSV worked on iPad."
Akim Maziq,29,akim.maziq@yahoo.com,10314,7,"Good overall. The signup flow is confusing — took me 3 tries."
Heloise Fontaine,41,heloise.f@gmail.com,11211,10,"Switched from a competitor 6 months ago. Never looking back."
Wojciech Kowalski,52,w.kowalski@outlook.com,11375,5,"Way too many notifications by default. Had to disable everything."
Ndidi Ezenwa,38,n.ezenwa@gmail.com,11201,8,"Solid product. Customer service responded within an hour when I had a question."
Ramazan Yetisken,26,ramazan.y@gmail.com,11104,9,"Easy to use. Pricing feels fair compared to what I paid before."
Sofia Lindholm,33,sofia.l@gmail.com,11215,4,"Crashes on the latest iOS. Three times in two weeks."
Ezekiel Hatfield,47,zeke.hatfield@gmail.com,11103,10,"Best decision I made this year. Pays for itself."
Yumiko Iijima,31,y.iijima@gmail.com,11225,7,"Mostly happy. The dashboard could be faster."
Talal Saghir,28,talal.s@gmail.com,11237,8,"Good. Wish there was a way to share specific views without sharing the whole workspace."
Aleksandra Pavlova,36,a.pavlova@gmail.com,11206,9,"Excellent. The new search update made everything faster."
Marcus Whitehorse,44,marcus.w@gmail.com,11220,6,"It's fine. Nothing wrong, nothing remarkable."
""",

    # 7. order_history.json — customer name, shipping address, phone, items, total
    """[
  {
    "order_id": "O-2024-08144",
    "customer_name": "Magdalena Rodriguez-Ortiz",
    "phone": "(303) 555-2241",
    "shipping_address": "1620 N Ogden Street Denver CO 80218",
    "items": [
      {"sku": "BK-CLI-1023", "name": "Linen Sheet Set Queen", "qty": 1, "price": 124.00},
      {"sku": "BK-PIL-2104", "name": "Down Pillow Standard", "qty": 2, "price": 48.00}
    ],
    "total_paid": 220.00,
    "ordered_at": "2024-08-14T19:42:11Z"
  },
  {
    "order_id": "O-2024-08145",
    "customer_name": "Tariq Abulafia",
    "phone": "(929) 555-1018",
    "shipping_address": "488 9th Avenue Apt 12B New York NY 10018",
    "items": [
      {"sku": "BK-CLI-1024", "name": "Linen Sheet Set King", "qty": 1, "price": 154.00}
    ],
    "total_paid": 154.00,
    "ordered_at": "2024-08-14T19:55:32Z"
  },
  {
    "order_id": "O-2024-08146",
    "customer_name": "Hisako Yamamoto",
    "phone": "(206) 555-3349",
    "shipping_address": "904 N 36th Street Seattle WA 98103",
    "items": [
      {"sku": "BK-DUV-3019", "name": "Heavyweight Duvet Insert King", "qty": 1, "price": 218.00},
      {"sku": "BK-PIL-2104", "name": "Down Pillow Standard", "qty": 2, "price": 48.00}
    ],
    "total_paid": 314.00,
    "ordered_at": "2024-08-14T20:11:08Z"
  },
  {
    "order_id": "O-2024-08147",
    "customer_name": "Bayo Akingbade",
    "phone": "(404) 555-0944",
    "shipping_address": "2241 Highland Avenue NE Atlanta GA 30317",
    "items": [
      {"sku": "BK-CLI-1023", "name": "Linen Sheet Set Queen", "qty": 1, "price": 124.00}
    ],
    "total_paid": 124.00,
    "ordered_at": "2024-08-14T20:32:44Z"
  }
]
""",

    # 8. school_enrollment.csv — student name, dob, parent contact info
    """student_id,student_first_name,student_last_name,date_of_birth,grade,parent_first_name,parent_last_name,parent_phone,parent_email,home_address
S-44120,Imani,Goldberg,2015-04-21,3,Yael,Goldberg,(773) 555-1144,yael.goldberg@gmail.com,3422 N Hoyne Avenue Chicago IL 60618
S-44121,Diego,Velasquez,2014-11-08,4,Carmen,Velasquez,(312) 555-1188,c.velasquez@yahoo.com,1502 W Cullerton Street Chicago IL 60608
S-44122,Astrid,Hartmann,2016-02-15,2,Bjorn,Hartmann,(847) 555-1233,bjorn.h@gmail.com,4108 Lake Avenue Wilmette IL 60091
S-44123,Kavi,Subramanian,2015-09-30,3,Rohini,Subramanian,(630) 555-1255,rohini.s@gmail.com,2218 Greenfield Court Naperville IL 60540
S-44124,Olamide,Adesanya,2013-06-14,5,Tunde,Adesanya,(773) 555-1288,t.adesanya@gmail.com,5230 N Sheridan Road Chicago IL 60640
S-44125,Mariella,Ferrara,2014-08-22,4,Lucia,Ferrara,(708) 555-1311,lucia.ferrara@gmail.com,910 N Oak Park Avenue Oak Park IL 60302
S-44126,Beau,Whitlock,2016-12-04,2,Marshall,Whitlock,(312) 555-1344,m.whitlock@gmail.com,1840 N Hudson Avenue Chicago IL 60614
S-44127,Saoirse,O'Connell,2015-03-19,3,Riley,O'Connell,(773) 555-1377,riley.oc@gmail.com,2105 W Belden Avenue Chicago IL 60647
S-44128,Eitan,Levy,2014-07-26,4,Daniela,Levy,(312) 555-1411,dlevy@gmail.com,420 W Belmont Avenue Chicago IL 60657
S-44129,Yumi,Watanabe,2016-05-11,2,Kenji,Watanabe,(847) 555-1444,kenji.w@gmail.com,815 Forest Avenue Evanston IL 60202
""",

    # 9. insurance_claims.json — claimant name, policy number, dob, diagnosis, amount
    """[
  {
    "claim_id": "CLM-2024-091122",
    "claimant_first_name": "Beverly",
    "claimant_last_name": "Hu-Ramos",
    "date_of_birth": "1971-08-04",
    "policy_number": "BCBS-IL-44128-7",
    "diagnosis_code": "M17.11",
    "diagnosis_description": "Unilateral primary osteoarthritis, right knee",
    "claim_amount_usd": 8450.00,
    "service_date": "2024-09-04",
    "provider_npi": "1992733410",
    "claimant_address": "1422 Asbury Avenue Evanston IL 60202",
    "claimant_phone": "(847) 555-3340"
  },
  {
    "claim_id": "CLM-2024-091123",
    "claimant_first_name": "Yannick",
    "claimant_last_name": "Bertrand",
    "date_of_birth": "1955-03-22",
    "policy_number": "AETNA-NY-22188-3",
    "diagnosis_code": "I25.10",
    "diagnosis_description": "Atherosclerotic heart disease of native coronary artery",
    "claim_amount_usd": 12200.00,
    "service_date": "2024-09-06",
    "provider_npi": "1881772290",
    "claimant_address": "240 W 73rd Street Apt 5C New York NY 10023",
    "claimant_phone": "(212) 555-4419"
  },
  {
    "claim_id": "CLM-2024-091124",
    "claimant_first_name": "Khadija",
    "claimant_last_name": "Diallo",
    "date_of_birth": "1988-12-15",
    "policy_number": "CIGNA-NJ-90021-1",
    "diagnosis_code": "O80",
    "diagnosis_description": "Encounter for full-term uncomplicated delivery",
    "claim_amount_usd": 14800.00,
    "service_date": "2024-09-01",
    "provider_npi": "1773344229",
    "claimant_address": "618 Bergen Avenue Jersey City NJ 07304",
    "claimant_phone": "(201) 555-2218"
  }
]
""",

    # 10. donor_list.csv — donor name, email, phone, donation amount, donation date (15 rows)
    """donor_name,donor_email,donor_phone,donation_amount_usd,donation_date,donation_method
Adina Rosenfeld,a.rosenfeld@gmail.com,(415) 555-7711,500.00,2024-06-04,credit_card
Yusef Khoury,yusef.k@gmail.com,(415) 555-7723,250.00,2024-06-04,bank_transfer
Mavis Okonkwo,mavis.ok@gmail.com,(510) 555-7745,1000.00,2024-06-05,credit_card
Demetrius Papadopoulos,dpap@gmail.com,(415) 555-7757,100.00,2024-06-05,credit_card
Sigrid Halvorsen,sigrid.h@gmail.com,(415) 555-7779,5000.00,2024-06-06,bank_transfer
Aarush Bhattacharya,aarush.b@gmail.com,(650) 555-7782,250.00,2024-06-06,credit_card
Liesel Mannheim,liesel.m@gmail.com,(415) 555-7794,750.00,2024-06-07,credit_card
Tahir Reza,tahir.r@gmail.com,(510) 555-7811,100.00,2024-06-07,paypal
Ofelia Quesada,ofelia.q@gmail.com,(415) 555-7823,2500.00,2024-06-08,bank_transfer
Kwame Asantehene,kwame.a@gmail.com,(415) 555-7836,500.00,2024-06-08,credit_card
Inken Sorensen,inken.s@gmail.com,(415) 555-7849,300.00,2024-06-09,credit_card
Vihaan Acharya,vihaan.a@gmail.com,(415) 555-7853,1000.00,2024-06-09,bank_transfer
Bronisław Dobrowolski,b.dobrowolski@gmail.com,(415) 555-7867,150.00,2024-06-10,paypal
Selene Vazquez,selene.v@gmail.com,(415) 555-7879,400.00,2024-06-10,credit_card
Aroha Tipene,aroha.t@gmail.com,(415) 555-7882,200.00,2024-06-11,credit_card
""",

    # 11. volunteer_signups.json — name, email, phone, emergency contact
    """[
  {"name": "Alaric Strathearn", "email": "alaric.s@gmail.com", "phone": "(720) 555-1101", "t_shirt_size": "L", "emergency_contact_name": "Fiona Strathearn", "emergency_contact_phone": "(720) 555-1102", "dietary_restrictions": "none"},
  {"name": "Bisrat Tewelde", "email": "bisrat.t@gmail.com", "phone": "(720) 555-1112", "t_shirt_size": "M", "emergency_contact_name": "Selam Tewelde", "emergency_contact_phone": "(720) 555-1113", "dietary_restrictions": "vegetarian"},
  {"name": "Catalina Mendez", "email": "c.mendez@gmail.com", "phone": "(720) 555-1124", "t_shirt_size": "S", "emergency_contact_name": "Hector Mendez", "emergency_contact_phone": "(720) 555-1125", "dietary_restrictions": "gluten-free"},
  {"name": "Dilnoza Yusupova", "email": "dilnoza.y@gmail.com", "phone": "(720) 555-1136", "t_shirt_size": "M", "emergency_contact_name": "Bekzod Yusupov", "emergency_contact_phone": "(720) 555-1137", "dietary_restrictions": "halal"},
  {"name": "Emeka Nwosu", "email": "e.nwosu@gmail.com", "phone": "(720) 555-1148", "t_shirt_size": "XL", "emergency_contact_name": "Ada Nwosu", "emergency_contact_phone": "(720) 555-1149", "dietary_restrictions": "none"},
  {"name": "Frida Lindgren", "email": "frida.l@gmail.com", "phone": "(720) 555-1162", "t_shirt_size": "S", "emergency_contact_name": "Erik Lindgren", "emergency_contact_phone": "(720) 555-1163", "dietary_restrictions": "vegan"},
  {"name": "Gunther Eichhorn", "email": "g.eichhorn@gmail.com", "phone": "(720) 555-1174", "t_shirt_size": "L", "emergency_contact_name": "Anneliese Eichhorn", "emergency_contact_phone": "(720) 555-1175", "dietary_restrictions": "none"},
  {"name": "Henna Virtanen", "email": "henna.v@gmail.com", "phone": "(720) 555-1186", "t_shirt_size": "M", "emergency_contact_name": "Mikael Virtanen", "emergency_contact_phone": "(720) 555-1187", "dietary_restrictions": "lactose-free"}
]
""",

    # 12. membership_directory.csv
    """member_id,member_name,email,phone,home_address,join_date,membership_tier
M-1042,Linnea Bjornsen,linnea.b@gmail.com,(503) 555-8801,2014 NE Alberta Street Portland OR 97211,2018-03-14,founder
M-1043,Cyrus Mottaghi,cyrus.m@gmail.com,(503) 555-8814,3209 SE Hawthorne Boulevard Portland OR 97214,2019-07-22,patron
M-1044,Imani Whittaker,imani.w@gmail.com,(503) 555-8827,5012 N Mississippi Avenue Portland OR 97217,2020-11-08,sustaining
M-1045,Tomasz Brzezinski,tomasz.b@gmail.com,(503) 555-8840,4421 SE Division Street Portland OR 97206,2021-02-19,sustaining
M-1046,Mireille Bordeleau,mireille.b@gmail.com,(503) 555-8853,1825 SW Salmon Street Portland OR 97205,2022-05-30,patron
M-1047,Demetrios Aristotelis,d.aristotelis@gmail.com,(503) 555-8866,3308 NE Killingsworth Street Portland OR 97211,2023-01-12,sustaining
M-1048,Naseem Tabrizi,naseem.t@gmail.com,(503) 555-8879,2245 SE Belmont Street Portland OR 97214,2023-06-04,founder
M-1049,Beatriz Camposano,beatriz.c@gmail.com,(503) 555-8882,1102 SW 12th Avenue Portland OR 97205,2024-02-28,sustaining
""",

    # 13. customer_feedback.json
    """[
  {"customer_name": "Heloise Marchetti", "customer_email": "heloise.m@gmail.com", "account_id": "AC-77418", "rating": 4, "comments": "Generally happy. The mobile app crashes on my iPhone 13 about once a week."},
  {"customer_name": "Otieno Wanyama", "customer_email": "otieno.w@gmail.com", "account_id": "AC-77419", "rating": 2, "comments": "I've been a customer for 3 years and the recent redesign broke my workflow. I can't find the saved-views menu anymore. Please bring it back or at least tell me where it went."},
  {"customer_name": "Akiko Watanabe", "customer_email": "akiko.w@gmail.com", "account_id": "AC-77420", "rating": 5, "comments": "The customer service rep who helped me with my billing issue last week was exceptional. Her name was Priya I think."},
  {"customer_name": "Vincenzo Esposito", "customer_email": "vincenzo.e@gmail.com", "account_id": "AC-77421", "rating": 3, "comments": "Product is fine. Pricing is starting to feel expensive given competitors are now offering similar features for less."},
  {"customer_name": "Yetunde Ojeyemi", "customer_email": "yetunde.o@gmail.com", "account_id": "AC-77422", "rating": 5, "comments": "Use this every single day. Would recommend to anyone. Phone is (646) 555-0188 if you want to talk to me about case studies or testimonials."}
]
""",

    # 14. lead_capture.csv
    """name,work_email,company,phone,job_title,industry,signup_source
Alessio Dragano,alessio.dragano@northstartrade.com,Northstar Trade,(212) 555-0144,VP of Operations,logistics,linkedin_ad
Hye-Jin Choi,hyejin.choi@morningstar-mfg.com,Morningstar Manufacturing,(312) 555-0188,Director of IT,manufacturing,webinar
Mokhtar El-Sayed,mokhtar.e@delta-financial.com,Delta Financial,(214) 555-0199,Senior Analyst,financial_services,referral
Solene Picard,solene.p@aurorabiotech.com,Aurora Biotech,(617) 555-0166,Lab Manager,life_sciences,booth_at_conference
Ravi Padmanabhan,ravi.p@brightline-data.com,Brightline Data,(415) 555-0133,CTO,software,homepage
Ophelia Whitfield,ophelia.w@cascade-utilities.com,Cascade Utilities,(503) 555-0122,Procurement Lead,utilities,linkedin_organic
Bartosz Wojcik,bartosz.w@horizonshipping.com,Horizon Shipping,(206) 555-0177,VP Engineering,logistics,webinar
Adaeze Onuoha,adaeze.o@silverline-health.com,Silverline Health,(404) 555-0188,Director of Compliance,healthcare,referral
Tomohiro Ishikawa,tomohiro.i@cobalt-energy.com,Cobalt Energy,(303) 555-0144,Project Manager,energy,homepage
Liora Steinberg,liora.s@parkwayretail.com,Parkway Retail Group,(212) 555-0155,SVP Merchandising,retail,linkedin_ad
Daouda Sangare,daouda.s@meridian-logistics.com,Meridian Logistics,(305) 555-0166,Operations Director,logistics,referral
Genevieve Carrasco,genevieve.c@verdant-foods.com,Verdant Foods,(415) 555-0177,Head of Supply Chain,food_and_beverage,webinar
""",

    # 15. client_contact_sheet.csv
    """client_name,primary_contact_name,contact_email,contact_phone,billing_address
Lakehurst Industries,Pavel Krasniansky,pavel.k@lakehurstind.com,(312) 555-1102,2018 W Webster Avenue Chicago IL 60614
Solstice Capital Partners,Adaobi Eze,adaobi.e@solsticecap.com,(212) 555-1114,488 Madison Avenue Suite 1810 New York NY 10022
Tidewater Logistics LLC,Marcus Ozaki,marcus.o@tidewater-log.com,(757) 555-1126,1102 Granby Street Norfolk VA 23510
Verdigris Wines,Sofia Aubergine,sofia.a@verdigriswines.com,(415) 555-1138,3105 24th Street San Francisco CA 94110
Cinder Manufacturing,Devraj Khurana,d.khurana@cindermfg.com,(412) 555-1150,2208 Penn Avenue Pittsburgh PA 15222
Stoneworks Consulting,Imelda Marakovic,imelda.m@stoneworks-c.com,(503) 555-1162,1245 NW Marshall Street Portland OR 97209
Pinemark Builders,Nnamdi Achukwu,nnamdi.a@pinemark.com,(704) 555-1174,4108 Park Road Charlotte NC 28209
""",

    # 16. guest_list.json
    """[
  {"guest_name": "Penelope Wickersham", "email": "p.wickersham@gmail.com", "plus_one_name": "Charles Wickersham", "dietary_restrictions": "vegetarian", "table_assignment": 4},
  {"guest_name": "Adewale Olatunji", "email": "ade.o@gmail.com", "plus_one_name": null, "dietary_restrictions": "none", "table_assignment": 4},
  {"guest_name": "Mariana Cabrera", "email": "mariana.c@gmail.com", "plus_one_name": "Ricardo Cabrera", "dietary_restrictions": "gluten-free", "table_assignment": 5},
  {"guest_name": "Soren Lindqvist", "email": "soren.l@gmail.com", "plus_one_name": "Astrid Lindqvist", "dietary_restrictions": "none", "table_assignment": 5},
  {"guest_name": "Aaliyah Whitfield", "email": "aaliyah.w@gmail.com", "plus_one_name": null, "dietary_restrictions": "vegan", "table_assignment": 6},
  {"guest_name": "Tomas Aleksandrowicz", "email": "tomas.a@gmail.com", "plus_one_name": "Hanna Aleksandrowicz", "dietary_restrictions": "none", "table_assignment": 6},
  {"guest_name": "Ngozi Eke", "email": "n.eke@gmail.com", "plus_one_name": null, "dietary_restrictions": "shellfish allergy", "table_assignment": 7},
  {"guest_name": "Henrik Vandenberg", "email": "henrik.v@gmail.com", "plus_one_name": "Greta Vandenberg", "dietary_restrictions": "none", "table_assignment": 7}
]
""",

    # 17. appointment_book.csv
    """patient_name,date_of_birth,phone,appointment_date,appointment_time,appointment_type,provider
Yvonne Brackenridge,1962-05-14,(415) 555-2201,2024-09-18,09:30,annual_physical,Dr. Wei
Yusuf Tariq,1985-11-22,(415) 555-2214,2024-09-18,10:00,follow_up,Dr. Wei
Cordelia Hernandez,1971-08-04,(415) 555-2226,2024-09-18,10:30,annual_physical,Dr. Patel
Gunnar Strand,1955-03-19,(415) 555-2239,2024-09-18,11:00,blood_pressure_check,Dr. Wei
Imani Adeyemo,1992-07-26,(415) 555-2241,2024-09-18,11:30,prenatal_visit,Dr. Patel
Wladyslaw Bukowski,1967-12-30,(415) 555-2254,2024-09-18,13:00,diabetes_management,Dr. Wei
Faye Drummond,1989-04-15,(415) 555-2266,2024-09-18,13:30,annual_physical,Dr. Patel
Bao Nguyen,1978-09-09,(415) 555-2278,2024-09-18,14:00,follow_up,Dr. Wei
Reyhana Mohebbi,1996-02-23,(415) 555-2289,2024-09-18,14:30,well_woman_exam,Dr. Patel
Otis Whitfield,1948-06-11,(415) 555-2291,2024-09-18,15:00,medication_review,Dr. Wei
""",

    # 18. lab_results.json
    """[
  {
    "patient_name": "Karoliina Lehtonen",
    "date_of_birth": "1979-04-22",
    "mrn": "MRN-44218",
    "address": "2014 Spring Garden Street Philadelphia PA 19130",
    "phone": "(215) 555-3318",
    "tests": [
      {"test_code": "GLUC", "test_name": "Glucose, fasting", "result_value": 142, "units": "mg/dL", "reference_range": "70-99", "flag": "H"},
      {"test_code": "HBA1C", "test_name": "Hemoglobin A1c", "result_value": 7.4, "units": "%", "reference_range": "<5.7", "flag": "H"}
    ],
    "ordered_by": "Dr. Singh",
    "specimen_collected": "2024-09-12"
  },
  {
    "patient_name": "Demetrius Constantinou",
    "date_of_birth": "1966-11-08",
    "mrn": "MRN-44219",
    "address": "892 South Street Philadelphia PA 19147",
    "phone": "(215) 555-3320",
    "tests": [
      {"test_code": "TSH", "test_name": "Thyroid stimulating hormone", "result_value": 8.2, "units": "mIU/L", "reference_range": "0.4-4.0", "flag": "H"},
      {"test_code": "T4F", "test_name": "Free T4", "result_value": 0.7, "units": "ng/dL", "reference_range": "0.8-1.8", "flag": "L"}
    ],
    "ordered_by": "Dr. Friedman",
    "specimen_collected": "2024-09-13"
  },
  {
    "patient_name": "Aaliyah Babatunde",
    "date_of_birth": "1991-06-30",
    "mrn": "MRN-44220",
    "address": "4108 Pine Street Philadelphia PA 19104",
    "phone": "(215) 555-3322",
    "tests": [
      {"test_code": "CBC", "test_name": "Complete blood count", "result_value": "normal", "units": null, "reference_range": null, "flag": null},
      {"test_code": "FERR", "test_name": "Ferritin", "result_value": 12, "units": "ng/mL", "reference_range": "20-200", "flag": "L"}
    ],
    "ordered_by": "Dr. Singh",
    "specimen_collected": "2024-09-13"
  }
]
""",

    # 19. prescription_log.csv
    """patient_name,date_of_birth,phone,drug_name,dose,prescribed_by,pharmacy,date_prescribed
Maximilien Cheval,1962-03-14,(617) 555-4401,Metformin,500 mg twice daily,Dr. Kim,CVS Pharmacy Brookline,2024-08-04
Amara Okwuosa,1988-07-22,(617) 555-4413,Sertraline,50 mg daily,Dr. Friedman,Walgreens Allston,2024-08-05
Tobias Schweikart,1955-12-30,(617) 555-4425,Lisinopril,10 mg daily,Dr. Kim,CVS Pharmacy Brookline,2024-08-06
Inken Dahlberg,1979-04-08,(617) 555-4437,Levothyroxine,75 mcg daily,Dr. Friedman,Walgreens Allston,2024-08-07
Bao-Vinh Tran,1996-09-15,(617) 555-4449,Albuterol Inhaler,2 puffs as needed,Dr. Kim,CVS Pharmacy Brookline,2024-08-08
Olamide Adediran,1971-06-27,(617) 555-4451,Atorvastatin,20 mg at bedtime,Dr. Friedman,CVS Pharmacy Brookline,2024-08-09
Hyeon-Su Yang,1985-11-04,(617) 555-4463,Omeprazole,20 mg daily,Dr. Kim,Walgreens Allston,2024-08-10
Marisol Cabezas,1948-02-14,(617) 555-4475,Donepezil,5 mg at bedtime,Dr. Friedman,CVS Pharmacy Brookline,2024-08-11
Ezra Bittlestone,1992-10-21,(617) 555-4487,Fluoxetine,20 mg daily,Dr. Kim,Walgreens Allston,2024-08-12
Kalinda Joshi,1968-05-18,(617) 555-4499,Amlodipine,5 mg daily,Dr. Friedman,CVS Pharmacy Brookline,2024-08-13
""",

    # 20. rental_applications.csv
    """applicant_name,ssn_last4,current_address,monthly_income,employer,years_at_job
Anastasia Volkov,4471,2014 N Western Avenue Apt 3F Chicago IL 60647,7200,Brightline Analytics,4
Devontae Whitmore,8829,1108 W Roosevelt Road Apt 412 Chicago IL 60608,5400,Cook County Hospital,7
Imran Qureshi,1156,4421 N Lincoln Avenue Chicago IL 60625,6800,Loyola University,9
Hyo-Young Park,9943,3210 N Sheffield Avenue Chicago IL 60657,8100,Northwestern Memorial,3
Beatriz Ferraz,2207,2912 W Belmont Avenue Chicago IL 60618,5900,Walgreens HQ,5
Otieno Akinyele,6618,1402 W Madison Street Chicago IL 60607,7500,JLL Chicago,6
""",

    # 21. loan_applications.json
    """[
  {
    "application_id": "LA-2024-08812",
    "applicant_full_name": "Renata Kuznetsova",
    "ssn": "402-77-1199",
    "date_of_birth": "1979-06-15",
    "annual_income_usd": 142000,
    "current_employer": "Brightline Analytics, Inc.",
    "current_address": "2418 Folsom Street San Francisco CA 94110",
    "phone": "(415) 555-9912",
    "email": "r.kuznetsova@gmail.com",
    "loan_amount_requested": 450000,
    "loan_purpose": "home_purchase"
  },
  {
    "application_id": "LA-2024-08813",
    "applicant_full_name": "Adetokunbo Bakare",
    "ssn": "522-11-3349",
    "date_of_birth": "1985-11-22",
    "annual_income_usd": 98000,
    "current_employer": "Cook County Hospital",
    "current_address": "1108 W Roosevelt Road Apt 412 Chicago IL 60608",
    "phone": "(312) 555-9924",
    "email": "ade.b@gmail.com",
    "loan_amount_requested": 280000,
    "loan_purpose": "home_purchase"
  },
  {
    "application_id": "LA-2024-08814",
    "applicant_full_name": "Hanneke Maartens",
    "ssn": "611-44-2207",
    "date_of_birth": "1968-04-08",
    "annual_income_usd": 86500,
    "current_employer": "Self-employed (consultant)",
    "current_address": "4108 Lake Avenue Wilmette IL 60091",
    "phone": "(847) 555-9936",
    "email": "hanneke.m@gmail.com",
    "loan_amount_requested": 195000,
    "loan_purpose": "refinance"
  },
  {
    "application_id": "LA-2024-08815",
    "applicant_full_name": "Yusuf Daouda",
    "ssn": "388-22-7714",
    "date_of_birth": "1991-09-30",
    "annual_income_usd": 76200,
    "current_employer": "Walgreens HQ",
    "current_address": "2912 W Belmont Avenue Chicago IL 60618",
    "phone": "(312) 555-9948",
    "email": "yusuf.d@gmail.com",
    "loan_amount_requested": 220000,
    "loan_purpose": "home_purchase"
  }
]
""",

    # 22. vehicle_registrations.csv
    """owner_name,owner_address,vin,license_plate,vehicle_make,vehicle_model,vehicle_year,registration_expires
Beatrix Holloway,2014 NE Going Street Portland OR 97211,1HGCM82633A412345,XYZ-9912,Honda,Accord,2018,2025-08-31
Daoud Hamdan,3209 SE Hawthorne Boulevard Portland OR 97214,5YJ3E1EA8KF221034,EV-PDX-12,Tesla,Model 3,2019,2025-09-30
Imelda Vasquez,5012 N Mississippi Avenue Portland OR 97217,JTHBJ46GX72081234,LMN-4421,Toyota,Camry,2007,2026-01-31
Stein Bjornson,4421 SE Division Street Portland OR 97206,1FTFW1ET5DKE12345,OR-PICKUP,Ford,F-150,2013,2025-07-31
Aaliyah Olufowobi,2245 SE Belmont Street Portland OR 97214,WBA8E9C58JK998234,BMW-PDX-1,BMW,3 Series,2018,2026-03-31
Kenshiro Yamada,1825 SW Salmon Street Portland OR 97205,JN1AZ4EH6JM811234,GTR-2018,Nissan,GT-R,2018,2025-12-31
Margerit Berghuis,910 NW 23rd Avenue Portland OR 97210,WAUFFAFL5BN012345,SLOW-DUDE,Audi,A4,2011,2026-02-28
Olamide Ojediran,3308 NE Killingsworth Street Portland OR 97211,5NPE34AF6HH512345,HYUNDAI-1,Hyundai,Sonata,2017,2025-11-30
""",

    # 23. background_check_results.json
    """[
  {
    "candidate_name": "Anneliese Krumholz",
    "date_of_birth": "1986-04-12",
    "ssn_last4": "8841",
    "current_address": "2418 Folsom Street San Francisco CA 94110",
    "employment_history": [
      {"employer": "Lightwave Analytics", "title": "Senior Engineer", "start_date": "2020-03", "end_date": "present", "verified": true},
      {"employer": "Beacon Technologies", "title": "Engineer II", "start_date": "2017-06", "end_date": "2020-02", "verified": true},
      {"employer": "First Light Solutions", "title": "Software Engineer", "start_date": "2015-01", "end_date": "2017-05", "verified": false, "verification_note": "Employer no longer reachable; phone disconnected."}
    ],
    "criminal_record_check": "no records found in the past 7 years"
  },
  {
    "candidate_name": "Tariq Mahmoud-Karimi",
    "date_of_birth": "1991-09-22",
    "ssn_last4": "3349",
    "current_address": "488 9th Avenue Apt 12B New York NY 10018",
    "employment_history": [
      {"employer": "Northstar Trade", "title": "Operations Analyst", "start_date": "2022-08", "end_date": "present", "verified": true},
      {"employer": "Castor Logistics", "title": "Operations Coordinator", "start_date": "2019-05", "end_date": "2022-07", "verified": true}
    ],
    "criminal_record_check": "no records found in the past 7 years"
  },
  {
    "candidate_name": "Folake Adeyinka",
    "date_of_birth": "1979-12-08",
    "ssn_last4": "7702",
    "current_address": "5230 N Sheridan Road Apt 14C Chicago IL 60640",
    "employment_history": [
      {"employer": "Cook County Hospital", "title": "Registered Nurse", "start_date": "2018-04", "end_date": "present", "verified": true},
      {"employer": "Northwestern Memorial", "title": "Registered Nurse", "start_date": "2012-09", "end_date": "2018-03", "verified": true}
    ],
    "criminal_record_check": "no records found in the past 7 years"
  }
]
""",

    # 24. police_report_excerpt.txt
    """INCIDENT REPORT — RICHMOND POLICE DEPARTMENT
Case Number: 2024-15-08291
Date Reported: 2024-09-14
Reporting Officer: Officer M. Calderon, Badge #4421

NATURE OF INCIDENT
Theft from a parked motor vehicle.

LOCATION
3221 Glenwood Avenue, Richmond, VA 23222 (parking lot of Glenwood Market).

VICTIM
Name: Heloise Bridgewater
DOB: 1979-03-22
Address: 4108 Brookmoor Avenue Richmond VA 23227
Phone: (804) 555-1142
Email: heloise.b@gmail.com

NARRATIVE
At approximately 14:30 hours, the reporting party returned to her 2017 Toyota Camry (VA plate KWX-4421) and discovered the passenger-side window broken. A laptop bag containing a Dell XPS 13 (serial DJX22-44120), a wallet containing $80 cash plus credit cards, and a Massachusetts state ID had been taken. Total estimated value: $1,450.

WITNESSES
Mr. Tomasz Brzezinski, who was parked two spaces over, reports seeing a male subject (approximately 30 years old, medium build, wearing a dark hoodie) walking briskly away from the area at approximately 14:25 hours. Mr. Brzezinski did not see the actual break-in. His contact information is (804) 555-1855.

EVIDENCE
Window glass collected. No usable fingerprints. Reviewing surveillance footage from Glenwood Market is ongoing.

DISPOSITION
Active investigation. Victim provided with case number and informed she may file an insurance claim.
""",

    # 25. real_estate_listing_contacts.csv
    """seller_name,seller_phone,seller_email,property_address,asking_price_usd,listing_agent
Ola Eze,(770) 555-7711,ola.eze@gmail.com,4108 Briarcliff Road NE Atlanta GA 30329,485000,Maria Sanchez
Demetrius Westmoreland,(404) 555-7723,d.westmoreland@gmail.com,2014 Highland Avenue NE Atlanta GA 30309,720000,Maria Sanchez
Lina Hertzberg,(404) 555-7735,lina.h@gmail.com,3309 Peachtree Road NE Atlanta GA 30326,1250000,Marcus Lee
Ahmed Boutaleb,(770) 555-7747,ahmed.b@gmail.com,1804 Dresden Drive NE Atlanta GA 30319,395000,Maria Sanchez
Sigrid Halvorson,(404) 555-7759,sigrid.h@gmail.com,2210 Westchester Court SE Atlanta GA 30316,540000,Marcus Lee
""",

    # 26. tax_return_summary.json
    """{
  "tax_year": 2023,
  "filer_full_name": "Anastasia Loredan",
  "filer_ssn": "419-22-7714",
  "filer_dob": "1976-08-04",
  "filer_address": "2014 NW 24th Avenue Apt 4 Portland OR 97210",
  "filer_phone": "(503) 555-9941",
  "filer_email": "a.loredan@gmail.com",
  "filing_status": "married_filing_jointly",
  "spouse_full_name": "Niko Loredan",
  "spouse_ssn": "388-91-2207",
  "spouse_dob": "1973-11-22",
  "dependents": [
    {"name": "Mira Loredan", "ssn": "612-44-8819", "dob": "2011-04-12", "relationship": "daughter"},
    {"name": "Otto Loredan", "ssn": "612-44-8820", "dob": "2014-09-30", "relationship": "son"}
  ],
  "adjusted_gross_income_usd": 248400.00,
  "total_tax_usd": 51860.00,
  "refund_due_usd": 4220.00
}
""",

    # 27. bank_statement_excerpt.csv
    """# Account holder: Joaquin Vidal | Phone on file: (415) 555-0144 | Statement period: 09/01/2024 - 09/30/2024
account_holder_name,account_number_last4,statement_date,transaction_date,description,debit_usd,credit_usd,balance_usd
Joaquin Vidal,4421,2024-09-30,2024-09-01,DIRECT DEPOSIT EMPLOYER ACME CORP,,3850.00,8244.18
Joaquin Vidal,4421,2024-09-30,2024-09-02,RENT PAYMENT TO LANDLORD,1850.00,,6394.18
Joaquin Vidal,4421,2024-09-30,2024-09-03,WHOLE FOODS MARKET,142.34,,6251.84
Joaquin Vidal,4421,2024-09-30,2024-09-04,COMCAST INTERNET BILL,89.95,,6161.89
Joaquin Vidal,4421,2024-09-30,2024-09-05,SHELL GAS STATION,52.18,,6109.71
Joaquin Vidal,4421,2024-09-30,2024-09-07,RESTAURANT IL FORNAIO,124.50,,5985.21
Joaquin Vidal,4421,2024-09-30,2024-09-10,COSTCO WHOLESALE,287.42,,5697.79
Joaquin Vidal,4421,2024-09-30,2024-09-12,REI CO-OP,418.99,,5278.80
Joaquin Vidal,4421,2024-09-30,2024-09-15,DIRECT DEPOSIT EMPLOYER ACME CORP,,3850.00,9128.80
Joaquin Vidal,4421,2024-09-30,2024-09-17,VENMO TRANSFER TO MARIA G,200.00,,8928.80
Joaquin Vidal,4421,2024-09-30,2024-09-20,SAFEWAY,98.22,,8830.58
Joaquin Vidal,4421,2024-09-30,2024-09-22,UNITED AIRLINES,612.40,,8218.18
""",

    # 28. credit_card_statement_lines.csv
    """# Cardholder: Yvonne Brackenridge | Phone: (415) 555-0166 | Account: ****-****-****-8841 | Statement: Sept 2024
cardholder_name,card_last4,transaction_date,merchant,amount_usd
Yvonne Brackenridge,8841,2024-09-01,Trader Joe's,84.22
Yvonne Brackenridge,8841,2024-09-02,Whole Foods Market,142.34
Yvonne Brackenridge,8841,2024-09-03,Amazon Prime Now,38.99
Yvonne Brackenridge,8841,2024-09-04,Shell Gas,52.18
Yvonne Brackenridge,8841,2024-09-05,United Airlines,612.40
Yvonne Brackenridge,8841,2024-09-06,Airbnb,418.00
Yvonne Brackenridge,8841,2024-09-07,Starbucks,8.45
Yvonne Brackenridge,8841,2024-09-08,Whole Foods Market,89.22
Yvonne Brackenridge,8841,2024-09-09,Comcast Internet,89.95
Yvonne Brackenridge,8841,2024-09-10,REI Co-op,124.50
Yvonne Brackenridge,8841,2024-09-12,Costco Wholesale,287.42
Yvonne Brackenridge,8841,2024-09-14,Uber,18.42
Yvonne Brackenridge,8841,2024-09-15,Whole Foods Market,98.22
Yvonne Brackenridge,8841,2024-09-17,Apple Store,1299.00
Yvonne Brackenridge,8841,2024-09-20,Costco Gas,42.18
""",

    # 29. veterinary_records.json
    """[
  {
    "pet_owner_name": "Hyo-Jin Park",
    "owner_phone": "(503) 555-2241",
    "owner_email": "h.park@gmail.com",
    "owner_address": "2014 NE Alberta Street Portland OR 97211",
    "pet_name": "Toulouse",
    "pet_species": "cat",
    "pet_breed": "domestic shorthair",
    "pet_dob": "2018-04-12",
    "microchip_id": "985112004421189",
    "vaccinations": [
      {"vaccine": "FVRCP", "date": "2024-04-15", "next_due": "2025-04-15"},
      {"vaccine": "Rabies", "date": "2023-04-15", "next_due": "2026-04-15"}
    ]
  },
  {
    "pet_owner_name": "Marcus Adebayo-Singh",
    "owner_phone": "(503) 555-2253",
    "owner_email": "marcus.as@gmail.com",
    "owner_address": "3209 SE Hawthorne Boulevard Portland OR 97214",
    "pet_name": "Beans",
    "pet_species": "dog",
    "pet_breed": "labrador mix",
    "pet_dob": "2020-09-22",
    "microchip_id": "985112004421233",
    "vaccinations": [
      {"vaccine": "DAPP", "date": "2024-06-10", "next_due": "2025-06-10"},
      {"vaccine": "Rabies", "date": "2024-06-10", "next_due": "2027-06-10"},
      {"vaccine": "Bordetella", "date": "2024-06-10", "next_due": "2025-06-10"}
    ]
  },
  {
    "pet_owner_name": "Adaeze Okwuosa",
    "owner_phone": "(503) 555-2265",
    "owner_email": "adaeze.o@gmail.com",
    "owner_address": "5012 N Mississippi Avenue Portland OR 97217",
    "pet_name": "Wren",
    "pet_species": "dog",
    "pet_breed": "border collie",
    "pet_dob": "2019-11-04",
    "microchip_id": "985112004421278",
    "vaccinations": [
      {"vaccine": "DAPP", "date": "2024-07-22", "next_due": "2025-07-22"},
      {"vaccine": "Rabies", "date": "2023-07-22", "next_due": "2026-07-22"}
    ]
  }
]
""",

    # 30. fitness_class_signup.csv
    """participant_name,date_of_birth,phone,emergency_contact_name,emergency_contact_phone,medical_notes
Amelia Trafford,1988-04-12,(206) 555-3301,Robert Trafford,(206) 555-3302,asthma — keeps inhaler in gym bag
Bohuslav Hudacek,1991-07-22,(206) 555-3314,Eva Hudacek,(206) 555-3315,none
Constance Mokoena,1985-11-30,(206) 555-3326,Sipho Mokoena,(206) 555-3327,history of knee surgery (2018) — modify high-impact moves
Diego Berenguer,1979-04-08,(206) 555-3338,Sofia Berenguer,(206) 555-3339,diabetes type 2 — keeps glucose tabs in bag
Esmeralda Calzaghe,1996-09-15,(206) 555-3341,Marco Calzaghe,(206) 555-3342,none
Farhan Karimi,1973-06-27,(206) 555-3353,Layla Karimi,(206) 555-3354,recent back injury (Sept 2024) — no twisting
Goldie Wexler,1989-12-04,(206) 555-3365,David Wexler,(206) 555-3366,pregnant — second trimester
Hyo-Joon Kim,1985-02-14,(206) 555-3377,Mi-Sun Kim,(206) 555-3378,none
Indira Krishnaswamy,1968-08-21,(206) 555-3389,Arjun Krishnaswamy,(206) 555-3390,mild osteoporosis
Joaquin Cabezas,1992-05-18,(206) 555-3401,Maria Cabezas,(206) 555-3402,none
Klara Vondrackova,1980-10-09,(206) 555-3413,Jakub Vondracek,(206) 555-3414,heart murmur — cleared by cardiologist 2024
Lior Ben-Yair,1993-01-26,(206) 555-3425,Tal Ben-Yair,(206) 555-3426,none
""",

    # 31. dating_app_export.json
    """[
  {
    "user_id": "u-44128",
    "display_name": "Mira",
    "real_name": "Mira Sandberg-Okonkwo",
    "age": 29,
    "date_of_birth": "1995-04-22",
    "email": "mira.so@gmail.com",
    "phone": "(415) 555-7711",
    "photo_url": "https://cdn.example.com/u-44128-photo1.jpg",
    "bio": "Architect, plant person, sourdough enthusiast. Originally from Stockholm, now in the Mission.",
    "last_known_location": "37.7626,-122.4124 (San Francisco — Mission District)"
  },
  {
    "user_id": "u-44129",
    "display_name": "Devin",
    "real_name": "Devin Acheampong",
    "age": 32,
    "date_of_birth": "1992-08-15",
    "email": "devin.a@gmail.com",
    "phone": "(415) 555-7723",
    "photo_url": "https://cdn.example.com/u-44129-photo1.jpg",
    "bio": "Engineer at a small startup. Looking for someone to lose to me at scrabble.",
    "last_known_location": "37.7849,-122.4094 (San Francisco — Western Addition)"
  },
  {
    "user_id": "u-44130",
    "display_name": "Lena",
    "real_name": "Helena Kowalczyk",
    "age": 27,
    "date_of_birth": "1997-11-08",
    "email": "lena.k@gmail.com",
    "phone": "(415) 555-7735",
    "photo_url": "https://cdn.example.com/u-44130-photo1.jpg",
    "bio": "Vet, runner, Polish-born and proud. Cabin in Tahoe in the winter.",
    "last_known_location": "37.7593,-122.4350 (San Francisco — Noe Valley)"
  },
  {
    "user_id": "u-44131",
    "display_name": "Yusef",
    "real_name": "Yusef El-Bahnasawy",
    "age": 34,
    "date_of_birth": "1990-03-30",
    "email": "yusef.eb@gmail.com",
    "phone": "(415) 555-7747",
    "photo_url": "https://cdn.example.com/u-44131-photo1.jpg",
    "bio": "Photographer. Bilingual Arabic/English. I make a mean shakshuka.",
    "last_known_location": "37.7707,-122.4117 (San Francisco — Castro)"
  }
]
""",

    # 32. matchmaker_intake_form.csv
    """client_name,date_of_birth,contact_phone,contact_email,preferences,dealbreakers
Beatrix Sandman,1981-03-15,(212) 555-4401,b.sandman@gmail.com,"professional careerist, 35-45, lives in Manhattan or Brooklyn","smokers, anyone with children under 10"
Cosima Reichardt,1976-08-22,(212) 555-4413,c.reichardt@gmail.com,"intellectual, divorced or never-married, no kids","wants more children, lives outside the city"
Devraj Atkinson,1985-11-30,(212) 555-4425,d.atkinson@gmail.com,"creative type, 28-38, vegetarian or vegan","heavy drinkers, conservative politics"
Eitan Hurewitz,1973-04-08,(212) 555-4437,e.hurewitz@gmail.com,"observant Jewish, college-educated, 35-50","interfaith"
Fatima Bourouiba,1988-09-15,(212) 555-4449,f.bourouiba@gmail.com,"professional, Muslim or open to converting, 30-40","drinkers, anyone who eats pork"
Gunther Lindenburg,1969-06-27,(212) 555-4451,g.lindenburg@gmail.com,"widowed or divorced, 55-70, financially independent","gold diggers, smokers"
Heloise Marchetti,1985-12-04,(212) 555-4463,h.marchetti@gmail.com,"Italian or Italian-American, 30-40, traditional values","atheists, anyone who has been previously married"
Imran Rahman,1979-02-14,(212) 555-4475,i.rahman@gmail.com,"professional South Asian, 30-40","drinkers, vegetarians (I love steak)"
""",

    # 33. therapy_intake_notes.txt
    """INTAKE NOTES — Dr. M. Friedman, LCSW
Session date: 2024-09-12

Patient: Eliana Marchetti-Torres
DOB: 1991-04-08
Contact: (415) 555-1102, eliana.mt@gmail.com
Address: 1422 17th Street San Francisco CA 94107
Emergency contact: Lorena Torres (mother), (415) 555-1103

PRESENTING CONCERN
Patient self-referred citing increasing anxiety symptoms over the past 6 months, with notable disruption to sleep and work performance. Reports racing thoughts, intrusive worry about job security and family health, and 2 panic episodes in the past month that she has not previously experienced.

RELEVANT HISTORY
Patient is a 33-year-old single woman, native Spanish speaker (fluent English), works as a senior associate at a downtown law firm. No children. Lives alone. Reports a strong but geographically distant relationship with mother (Los Angeles) and a younger brother (Mexico City). Father died in 2019 (heart attack); patient describes the grief as "mostly worked through" but acknowledges it resurfaces.

Patient has no prior history of mental-health treatment. Denies suicidal ideation or self-harm history. Denies substance use beyond occasional social drinking.

PROVISIONAL ASSESSMENT
Symptoms consistent with generalized anxiety disorder, possible comorbid panic disorder. No medical workup yet to rule out hyperthyroidism or other contributors; patient agreed to schedule with her PCP this week.

PLAN
- Weekly individual therapy, CBT-oriented.
- PCP referral for medical workup.
- Crisis line and after-hours contact information provided.
- Re-evaluate in 4 sessions.
""",

    # 34. dental_records.csv
    """patient_name,date_of_birth,patient_phone,insurance_id,last_visit_date,procedures_performed,next_appointment
Akira Fujimoto,1985-04-12,(310) 555-4401,DELTA-CA-44128-7,2024-08-14,prophylaxis;periodic_exam;bitewings,2025-02-14
Beatriz Aguilera,1972-08-22,(310) 555-4413,GUARDIAN-CA-22188-3,2024-08-15,composite_filling_M-O_tooth_19,2025-02-15
Constance Whitehorse,1991-11-30,(310) 555-4425,METLIFE-CA-90021-1,2024-08-15,scaling_root_planing_quadrant_3,2024-11-15
Demetrios Kostopoulos,1968-03-08,(310) 555-4437,DELTA-CA-44217-9,2024-08-16,prophylaxis;periodic_exam,2025-02-16
Esmeralda Vargas-Lopez,1996-09-15,(310) 555-4449,GUARDIAN-CA-32109-7,2024-08-17,extraction_tooth_17_impacted,2024-09-17
Faisal Tabrizi,1979-06-27,(310) 555-4451,METLIFE-CA-77104-4,2024-08-19,crown_seat_tooth_30,2024-11-19
Gretl Heinemann,1955-12-04,(310) 555-4463,AETNA-CA-12109-8,2024-08-20,denture_adjustment,2025-02-20
Hiroshi Yamashita,1988-02-14,(310) 555-4475,DELTA-CA-66401-2,2024-08-21,prophylaxis;periodic_exam;FMX,2025-02-21
Indira Vaswani,1973-08-21,(310) 555-4487,GUARDIAN-CA-44218-5,2024-08-22,implant_consultation,2024-10-22
Joaquin Marquez,1992-05-18,(310) 555-4499,METLIFE-CA-22184-9,2024-08-23,composite_filling_O_tooth_14,2025-02-23
""",

    # 35. pediatric_records.json
    """[
  {
    "patient_name": "Mira Holland-Okwuosa",
    "date_of_birth": "2018-04-12",
    "mrn": "PED-44218",
    "address": "2418 Folsom Street San Francisco CA 94110",
    "parent_name": "Beatrix Holland",
    "parent_phone": "(415) 555-2241",
    "parent_email": "b.holland@gmail.com",
    "allergies": ["penicillin", "peanuts"],
    "vaccinations_complete": ["MMR", "DTaP", "IPV", "Hib", "varicella"],
    "next_well_visit": "2025-04-15"
  },
  {
    "patient_name": "Bao Vinh Tran-Carter",
    "date_of_birth": "2020-09-22",
    "mrn": "PED-44219",
    "address": "488 9th Avenue Apt 12B New York NY 10018",
    "parent_name": "Linh Tran",
    "parent_phone": "(929) 555-1018",
    "parent_email": "linh.t@gmail.com",
    "allergies": [],
    "vaccinations_complete": ["MMR", "DTaP", "IPV"],
    "next_well_visit": "2024-12-22"
  },
  {
    "patient_name": "Calliope Sutton-Aikens",
    "date_of_birth": "2019-11-04",
    "mrn": "PED-44220",
    "address": "5230 N Sheridan Road Apt 14C Chicago IL 60640",
    "parent_name": "Marcus Aikens",
    "parent_phone": "(773) 555-2188",
    "parent_email": "m.aikens@gmail.com",
    "allergies": ["dairy"],
    "vaccinations_complete": ["MMR", "DTaP", "IPV", "Hib", "PCV13"],
    "next_well_visit": "2024-11-04"
  }
]
""",

    # 36. student_grades.csv
    """student_id,student_name,parent_email,course,grade_pct,letter_grade,term
S-44128,Amelia Trafford,parent.trafford@gmail.com,AP Calculus BC,94,A,Fall 2024
S-44129,Bohuslav Hudacek,parent.hudacek@gmail.com,AP Calculus BC,78,C+,Fall 2024
S-44130,Constance Mokoena,parent.mokoena@gmail.com,AP Calculus BC,88,B+,Fall 2024
S-44131,Diego Berenguer,parent.berenguer@gmail.com,AP US History,91,A-,Fall 2024
S-44132,Esmeralda Calzaghe,parent.calzaghe@gmail.com,AP US History,83,B,Fall 2024
S-44133,Farhan Karimi,parent.karimi@gmail.com,AP US History,76,C,Fall 2024
S-44134,Goldie Wexler,parent.wexler@gmail.com,Honors Biology,89,B+,Fall 2024
S-44135,Hyo-Joon Kim,parent.kim@gmail.com,Honors Biology,94,A,Fall 2024
S-44136,Indira Krishnaswamy,parent.krishnaswamy@gmail.com,Honors Biology,82,B-,Fall 2024
S-44137,Joaquin Cabezas,parent.cabezas@gmail.com,AP Computer Science,98,A+,Fall 2024
S-44138,Klara Vondrackova,parent.vondrackova@gmail.com,AP Computer Science,71,C-,Fall 2024
S-44139,Lior Ben-Yair,parent.benyair@gmail.com,AP Computer Science,90,A-,Fall 2024
S-44140,Mira Sandberg,parent.sandberg@gmail.com,AP Calculus BC,86,B,Fall 2024
S-44141,Niko Loredan,parent.loredan@gmail.com,AP US History,93,A,Fall 2024
""",

    # 37. alumni_directory.csv
    """name,graduation_year,current_employer,work_email,personal_email,phone
Adina Rosenfeld,2008,Brightline Analytics,a.rosenfeld@brightline.com,a.rosenfeld.personal@gmail.com,(415) 555-7711
Yusef Khoury,2010,Northstar Trade,yusef.k@northstartrade.com,yusef.k@gmail.com,(212) 555-7723
Mavis Okonkwo,2012,Cook County Hospital,m.okonkwo@cookhospital.org,mavis.o@gmail.com,(312) 555-7745
Demetrius Papadopoulos,2007,Self-employed (architect),dpap@dpapdesign.com,dpap@gmail.com,(415) 555-7757
Sigrid Halvorsen,2009,Heroku (Salesforce),sigrid.h@heroku.com,sigrid.h@gmail.com,(415) 555-7779
Aarush Bhattacharya,2014,Aurora Biotech,a.bhattacharya@aurorabio.com,aarush.b@gmail.com,(617) 555-7782
Liesel Mannheim,2006,Brookmoor Capital,l.mannheim@brookmoor.com,liesel.m@gmail.com,(212) 555-7794
Tahir Reza,2011,Cobalt Energy,t.reza@cobalt-energy.com,tahir.r@gmail.com,(303) 555-7811
Ofelia Quesada,2013,UC Berkeley (faculty),quesada@berkeley.edu,ofelia.q@gmail.com,(510) 555-7823
Kwame Asantehene,2008,Self-employed (consultant),kwame@asantehene-consulting.com,kwame.a@gmail.com,(415) 555-7836
""",

    # 38. neighborhood_watch_roster.csv
    """resident_name,home_address,phone,email,vehicle_year_make_model,vehicle_color
Margaret Whitehurst,4108 Maple Avenue Greendale OH 45227,(513) 555-1101,m.whitehurst@gmail.com,2018 Honda CR-V,silver
Theodore Bartholomew,4112 Maple Avenue Greendale OH 45227,(513) 555-1113,theo.b@gmail.com,2020 Toyota Highlander,black
Aminata Diallo,4116 Maple Avenue Greendale OH 45227,(513) 555-1125,aminata.d@gmail.com,2019 Subaru Outback,green
Stefan Wodzinski,4120 Maple Avenue Greendale OH 45227,(513) 555-1137,stefan.w@gmail.com,2017 Ford F-150,blue
Beatriz Camargo,4124 Maple Avenue Greendale OH 45227,(513) 555-1149,beatriz.c@gmail.com,2021 Tesla Model Y,white
Roosevelt Whitley,4128 Maple Avenue Greendale OH 45227,(513) 555-1161,roosevelt.w@gmail.com,2016 Chrysler Pacifica,gray
Demetra Stefanopoulos,4132 Maple Avenue Greendale OH 45227,(513) 555-1173,demetra.s@gmail.com,2019 Mazda CX-5,red
Adeyinka Olufowobi,4136 Maple Avenue Greendale OH 45227,(513) 555-1185,adeyinka.o@gmail.com,2018 Acura MDX,silver
""",

    # 39. club_membership.json
    """[
  {"member_name": "Catalina Reyes-Castillo", "address": "1422 Asbury Avenue Evanston IL 60202", "phone": "(847) 555-3340", "email": "catalina.rc@gmail.com", "membership_tier": "platinum", "payment_method_last4": "4421"},
  {"member_name": "Yannick Bertrand", "address": "240 W 73rd Street Apt 5C New York NY 10023", "phone": "(212) 555-4419", "email": "yannick.b@gmail.com", "membership_tier": "gold", "payment_method_last4": "8819"},
  {"member_name": "Khadija Diallo", "address": "618 Bergen Avenue Jersey City NJ 07304", "phone": "(201) 555-2218", "email": "khadija.d@gmail.com", "membership_tier": "silver", "payment_method_last4": "1156"},
  {"member_name": "Stein Bjornson", "address": "4421 SE Division Street Portland OR 97206", "phone": "(503) 555-9941", "email": "stein.b@gmail.com", "membership_tier": "platinum", "payment_method_last4": "9943"},
  {"member_name": "Imani Adeyemo", "address": "1825 SW Salmon Street Portland OR 97205", "phone": "(503) 555-2241", "email": "imani.a@gmail.com", "membership_tier": "gold", "payment_method_last4": "2207"},
  {"member_name": "Faisal Tabrizi", "address": "3308 NE Killingsworth Street Portland OR 97211", "phone": "(503) 555-2253", "email": "faisal.t@gmail.com", "membership_tier": "silver", "payment_method_last4": "6618"}
]
""",

    # 40. shipping_manifest.csv
    """tracking_number,recipient_name,recipient_address,recipient_phone,ship_date,carrier,weight_lb
1Z999AA10123456784,Adaobi Eze,488 Madison Avenue Suite 1810 New York NY 10022,(212) 555-1114,2024-09-14,UPS,4.2
1Z999AA10123456785,Pavel Krasniansky,2018 W Webster Avenue Chicago IL 60614,(312) 555-1102,2024-09-14,UPS,2.8
9400111202503456789012,Marcus Ozaki,1102 Granby Street Norfolk VA 23510,(757) 555-1126,2024-09-14,USPS,1.5
9400111202503456789013,Sofia Aubergine,3105 24th Street San Francisco CA 94110,(415) 555-1138,2024-09-14,USPS,3.1
395444221101,Devraj Khurana,2208 Penn Avenue Pittsburgh PA 15222,(412) 555-1150,2024-09-14,FedEx,5.7
395444221102,Imelda Marakovic,1245 NW Marshall Street Portland OR 97209,(503) 555-1162,2024-09-14,FedEx,2.3
395444221103,Nnamdi Achukwu,4108 Park Road Charlotte NC 28209,(704) 555-1174,2024-09-14,FedEx,4.8
1Z999AA10123456786,Catalina Mendez,2014 Spring Garden Street Philadelphia PA 19130,(215) 555-3318,2024-09-14,UPS,1.9
1Z999AA10123456787,Demetrius Constantinou,892 South Street Philadelphia PA 19147,(215) 555-3320,2024-09-14,UPS,6.4
9400111202503456789014,Aaliyah Babatunde,4108 Pine Street Philadelphia PA 19104,(215) 555-3322,2024-09-14,USPS,0.8
1Z999AA10123456788,Heloise Bridgewater,4108 Brookmoor Avenue Richmond VA 23227,(804) 555-1142,2024-09-14,UPS,3.7
9400111202503456789015,Tomasz Brzezinski,2014 N Western Avenue Apt 3F Chicago IL 60647,(773) 555-1855,2024-09-14,USPS,2.1
""",

    # 41. gym_signup_sheet.csv
    """name,date_of_birth,phone,emergency_contact_name,emergency_contact_phone,fitness_goals
Karim Hassan-Tayeb,1988-04-12,(310) 555-1101,Layla Hassan-Tayeb,(310) 555-1102,weight loss
Bertille Lefebvre,1991-07-22,(310) 555-1113,Marc Lefebvre,(310) 555-1114,muscle gain
Constanza Vargas,1985-11-30,(310) 555-1125,Diego Vargas,(310) 555-1126,general fitness
Daouda Bah,1979-04-08,(310) 555-1137,Mariama Bah,(310) 555-1138,marathon training
Esther Bukvic,1996-09-15,(310) 555-1149,Petar Bukvic,(310) 555-1150,injury rehabilitation
Filippo Aragosa,1973-06-27,(310) 555-1161,Lucia Aragosa,(310) 555-1162,cardiovascular health
Gertrude Whitford,1989-12-04,(310) 555-1173,Edward Whitford,(310) 555-1174,strength training
Hyo-Jin Bae,1985-02-14,(310) 555-1185,Soo-Min Bae,(310) 555-1186,flexibility and mobility
Ifeoma Okoye,1968-08-21,(310) 555-1197,Chukwuemeka Okoye,(310) 555-1198,maintain current fitness
Joaquin Maldonado-Cruz,1992-05-18,(310) 555-1209,Sofia Maldonado-Cruz,(310) 555-1210,bodybuilding competition prep
""",

    # 42. summer_camp_registration.json
    """[
  {
    "camper_name": "Bohdan Kuznetsov",
    "date_of_birth": "2014-05-18",
    "parent_name": "Nadia Kuznetsova",
    "parent_email": "nadia.k@gmail.com",
    "parent_phone": "(206) 555-5511",
    "address": "2014 NE Alberta Street Portland OR 97211",
    "medical_conditions": "asthma — keeps inhaler with him; mild peanut allergy",
    "allergy_severity": "moderate"
  },
  {
    "camper_name": "Calliope Sutton",
    "date_of_birth": "2013-11-22",
    "parent_name": "Marcus Sutton",
    "parent_email": "marcus.s@gmail.com",
    "parent_phone": "(206) 555-5523",
    "address": "3209 SE Hawthorne Boulevard Portland OR 97214",
    "medical_conditions": "type 1 diabetes — insulin pump, glucose monitoring required",
    "allergy_severity": "none"
  },
  {
    "camper_name": "Dmitri Volkov-Hartley",
    "date_of_birth": "2015-04-30",
    "parent_name": "Sarah Hartley",
    "parent_email": "sarah.h@gmail.com",
    "parent_phone": "(206) 555-5535",
    "address": "5012 N Mississippi Avenue Portland OR 97217",
    "medical_conditions": "ADHD — takes daily medication (parents to dispense at lunchtime)",
    "allergy_severity": "none"
  },
  {
    "camper_name": "Eitan Tov-Halevi",
    "date_of_birth": "2014-09-08",
    "parent_name": "Daniel Halevi",
    "parent_email": "daniel.h@gmail.com",
    "parent_phone": "(206) 555-5547",
    "address": "4421 SE Division Street Portland OR 97206",
    "medical_conditions": "none",
    "allergy_severity": "severe — tree nuts and dairy"
  }
]
""",

    # 43. babysitter_contact_list.csv
    """sitter_name,phone,email,hourly_rate_usd,certifications,references
Anastasia Bukowski,(415) 555-2211,a.bukowski@gmail.com,28.00,"CPR certified, infant first aid","Marina Goldberg (415) 555-2233, Theo Patel (415) 555-2245"
Demetri Aristotelis,(415) 555-2257,d.aristotelis@gmail.com,32.00,"CPR certified, lifeguard certified, swim lessons","Sarah Whitehurst (415) 555-2269, James Liu (415) 555-2281"
Folake Ojuolape,(415) 555-2293,folake.o@gmail.com,25.00,"CPR certified","Imani Holland (415) 555-2305"
Mikolaj Karpinski,(415) 555-2317,mikolaj.k@gmail.com,30.00,"CPR certified, infant first aid, special needs training","Beatriz Camargo (415) 555-2329, Marcus Adebayo (415) 555-2341"
Solveig Lindquist,(415) 555-2353,solveig.l@gmail.com,28.00,"CPR certified, ECE student","Hyo-Jin Park (415) 555-2365, Yusuf Tariq (415) 555-2377"
Tariq Bourouiba,(415) 555-2389,tariq.b@gmail.com,26.00,"CPR certified","Adina Steinberg (415) 555-2401"
""",

    # 44. pet_adoption_records.json
    """[
  {
    "adopter_name": "Margaux Lefevre-Carter",
    "address": "2218 Telegraph Avenue Berkeley CA 94704",
    "phone": "(510) 555-2156",
    "email": "margaux.lc@gmail.com",
    "pet_id": "P-2024-08891",
    "pet_name": "Saffron",
    "pet_species": "cat",
    "adoption_date": "2024-09-10",
    "adoption_fee_paid_usd": 175.00
  },
  {
    "adopter_name": "Chinedu Achebe-Wilson",
    "address": "1801 Bush Street San Francisco CA 94109",
    "phone": "(415) 555-2188",
    "email": "chinedu.aw@gmail.com",
    "pet_id": "P-2024-08892",
    "pet_name": "Hopper",
    "pet_species": "dog",
    "adoption_date": "2024-09-12",
    "adoption_fee_paid_usd": 325.00
  },
  {
    "adopter_name": "Sevda Petrosyan-Hughes",
    "address": "324 Lytton Avenue Palo Alto CA 94301",
    "phone": "(650) 555-2231",
    "email": "sevda.ph@gmail.com",
    "pet_id": "P-2024-08893",
    "pet_name": "Pickles",
    "pet_species": "cat",
    "adoption_date": "2024-09-14",
    "adoption_fee_paid_usd": 175.00
  }
]
""",

    # 45. marathon_registration.csv
    """bib_number,runner_name,age,sex,address,phone,t_shirt_size,emergency_contact_name,emergency_contact_phone
M-04421,Antonella Marchionne,34,F,2418 Folsom Street San Francisco CA 94110,(415) 555-3301,W-S,Roberto Marchionne,(415) 555-3302
M-04422,Babatunde Okeke,29,M,488 9th Avenue Apt 12B New York NY 10018,(929) 555-3313,M-M,Adaeze Okeke,(929) 555-3314
M-04423,Catalina Soderberg,42,F,4108 Maple Avenue Greendale OH 45227,(513) 555-3325,W-M,Lars Soderberg,(513) 555-3326
M-04424,Dimitar Konstantinov,38,M,1825 SW Salmon Street Portland OR 97205,(503) 555-3337,M-L,Petya Konstantinova,(503) 555-3338
M-04425,Esme Whitford,27,F,2014 NE Alberta Street Portland OR 97211,(503) 555-3349,W-XS,Roland Whitford,(503) 555-3350
M-04426,Faisal Daouda,31,M,3209 SE Hawthorne Boulevard Portland OR 97214,(503) 555-3361,M-M,Aisha Daouda,(503) 555-3362
M-04427,Genevieve Kostantakos,45,F,5012 N Mississippi Avenue Portland OR 97217,(503) 555-3373,W-M,Spiros Kostantakos,(503) 555-3374
M-04428,Hyo-Joon Pak,33,M,4421 SE Division Street Portland OR 97206,(503) 555-3385,M-L,Mi-Sun Pak,(503) 555-3386
M-04429,Indrani Choudhury,37,F,3308 NE Killingsworth Street Portland OR 97211,(503) 555-3397,W-S,Arun Choudhury,(503) 555-3398
M-04430,Jonas Lindqvist,40,M,2245 SE Belmont Street Portland OR 97214,(503) 555-3409,M-XL,Astrid Lindqvist,(503) 555-3410
""",

    # 46. voter_outreach_list.csv
    """voter_name,address,phone,party_registration,last_voted_election
Adina Rosenfeld,2014 NE Going Street Portland OR 97211,(503) 555-7711,Democrat,2022 General
Yusef Khoury,3209 SE Hawthorne Boulevard Portland OR 97214,(503) 555-7723,Democrat,2024 Primary
Mavis Okonkwo,5012 N Mississippi Avenue Portland OR 97217,(503) 555-7745,Unaffiliated,2020 General
Demetrius Papadopoulos,4421 SE Division Street Portland OR 97206,(503) 555-7757,Republican,2022 General
Sigrid Halvorsen,2245 SE Belmont Street Portland OR 97214,(503) 555-7779,Democrat,2024 Primary
Aarush Bhattacharya,1825 SW Salmon Street Portland OR 97205,(503) 555-7782,Democrat,2024 Primary
Liesel Mannheim,3308 NE Killingsworth Street Portland OR 97211,(503) 555-7794,Unaffiliated,2022 General
Tahir Reza,2014 N Williams Avenue Portland OR 97227,(503) 555-7811,Democrat,2020 General
Ofelia Quesada,4108 NE Killingsworth Street Portland OR 97211,(503) 555-7823,Republican,2022 General
Kwame Asantehene,5230 N Sheridan Road Apt 14C Portland OR 97211,(503) 555-7836,Democrat,2024 Primary
Inken Sorensen,1422 SE Stark Street Portland OR 97214,(503) 555-7849,Unaffiliated,never_voted
Vihaan Acharya,2912 NE Alberta Street Portland OR 97211,(503) 555-7853,Democrat,2024 Primary
Bronislaw Dobrowolski,1108 SW 12th Avenue Portland OR 97205,(503) 555-7867,Republican,2022 General
Selene Vazquez,488 SE Hawthorne Boulevard Portland OR 97214,(503) 555-7879,Democrat,2020 General
Aroha Tipene,1402 W Madison Avenue Portland OR 97205,(503) 555-7882,Unaffiliated,never_voted
""",

    # 47. petition_signatures.json
    """[
  {"signatory_name": "Adelaide Whitfield-Choi", "address": "2014 NE Alberta Street Portland OR 97211", "email": "a.whitfield@gmail.com", "date_signed": "2024-09-01"},
  {"signatory_name": "Bayode Adeyinka", "address": "3209 SE Hawthorne Boulevard Portland OR 97214", "email": "bayode.a@gmail.com", "date_signed": "2024-09-01"},
  {"signatory_name": "Constanza Echeverria", "address": "5012 N Mississippi Avenue Portland OR 97217", "email": "constanza.e@gmail.com", "date_signed": "2024-09-02"},
  {"signatory_name": "Davinder Ahluwalia", "address": "4421 SE Division Street Portland OR 97206", "email": "davinder.a@gmail.com", "date_signed": "2024-09-02"},
  {"signatory_name": "Emiliana Pasquariello", "address": "2245 SE Belmont Street Portland OR 97214", "email": "emiliana.p@gmail.com", "date_signed": "2024-09-03"},
  {"signatory_name": "Folarin Adesina", "address": "1825 SW Salmon Street Portland OR 97205", "email": "folarin.a@gmail.com", "date_signed": "2024-09-03"},
  {"signatory_name": "Gretl Steinhauser", "address": "3308 NE Killingsworth Street Portland OR 97211", "email": "gretl.s@gmail.com", "date_signed": "2024-09-04"},
  {"signatory_name": "Hiroko Kawaguchi", "address": "2014 N Williams Avenue Portland OR 97227", "email": "hiroko.k@gmail.com", "date_signed": "2024-09-04"},
  {"signatory_name": "Imran Zubairi", "address": "1402 W Madison Avenue Portland OR 97205", "email": "imran.z@gmail.com", "date_signed": "2024-09-05"},
  {"signatory_name": "Jolanta Brzezinska", "address": "488 SE Hawthorne Boulevard Portland OR 97214", "email": "jolanta.b@gmail.com", "date_signed": "2024-09-05"}
]
""",

    # 48. private_tutor_intake.csv
    """student_name,parent_name,parent_phone,parent_email,subjects,weekly_schedule
Apollonia Strathearn,Fiona Strathearn,(720) 555-1102,fiona.s@gmail.com,"SAT math, AP Chemistry","Tue 4-5pm, Thu 4-5pm"
Bisrat Tewelde,Selam Tewelde,(720) 555-1114,selam.t@gmail.com,"AP Biology","Mon 5-6pm, Wed 5-6pm"
Catalina Mendez,Hector Mendez,(720) 555-1126,hector.m@gmail.com,"SAT verbal, college essay coaching","Sun 2-3pm"
Dilnoza Yusupova,Bekzod Yusupov,(720) 555-1138,bekzod.y@gmail.com,"middle school math","Mon 4-5pm, Wed 4-5pm, Fri 4-5pm"
Emeka Nwosu,Ada Nwosu,(720) 555-1150,ada.n@gmail.com,"AP Calculus AB","Tue 5-6pm"
Frida Lindgren,Erik Lindgren,(720) 555-1162,erik.l@gmail.com,"AP Statistics, AP English Language","Mon 4-5pm, Thu 4-5pm"
Gunther Eichhorn,Anneliese Eichhorn,(720) 555-1174,anneliese.e@gmail.com,"AP Physics C: Mechanics","Wed 5-6pm, Sat 10-11am"
Henna Virtanen,Mikael Virtanen,(720) 555-1186,mikael.v@gmail.com,"middle school science, study skills","Mon 4:30-5:30pm, Wed 4:30-5:30pm"
""",

    # 49. wedding_guest_responses.json
    """[
  {"guest_name": "Adaeze Olusola-Achebe", "plus_one_name": "Tunde Achebe", "address": "1422 17th Street San Francisco CA 94107", "email": "adaeze.oa@gmail.com", "phone": "(415) 555-1102", "rsvp": "yes", "dietary_needs": "gluten-free for plus one"},
  {"guest_name": "Beatrix Holland-Werner", "plus_one_name": null, "address": "2418 Folsom Street San Francisco CA 94110", "email": "b.hwerner@gmail.com", "phone": "(415) 555-2241", "rsvp": "yes", "dietary_needs": "vegetarian"},
  {"guest_name": "Calliope Andriotti", "plus_one_name": "Marco Andriotti", "address": "3105 24th Street San Francisco CA 94110", "email": "calliope.a@gmail.com", "phone": "(415) 555-1138", "rsvp": "yes", "dietary_needs": "none"},
  {"guest_name": "Devontae Whitmore", "plus_one_name": null, "address": "1108 W Roosevelt Road Apt 412 Chicago IL 60608", "email": "devontae.w@gmail.com", "phone": "(312) 555-1188", "rsvp": "no", "dietary_needs": null},
  {"guest_name": "Esmeralda del Castillo", "plus_one_name": "Roberto del Castillo", "address": "2422 Coral Way Miami FL 33145", "email": "esmeralda.dc@hotmail.com", "phone": "(786) 555-0177", "rsvp": "yes", "dietary_needs": "shellfish allergy (Esmeralda)"},
  {"guest_name": "Fatima Bourouiba", "plus_one_name": "Karim Bourouiba", "address": "618 Bergen Avenue Jersey City NJ 07304", "email": "fatima.b@gmail.com", "phone": "(201) 555-2218", "rsvp": "yes", "dietary_needs": "halal"},
  {"guest_name": "Gunther Lindenburg", "plus_one_name": null, "address": "240 W 73rd Street Apt 5C New York NY 10023", "email": "g.lindenburg@gmail.com", "phone": "(212) 555-4419", "rsvp": "no", "dietary_needs": null},
  {"guest_name": "Heloise Marchetti", "plus_one_name": "Stefano Marchetti", "address": "910 N Oak Park Avenue Oak Park IL 60302", "email": "heloise.m@gmail.com", "phone": "(708) 555-1311", "rsvp": "yes", "dietary_needs": "vegetarian"},
  {"guest_name": "Imran Rahman", "plus_one_name": "Saira Rahman", "address": "488 Madison Avenue Suite 1810 New York NY 10022", "email": "imran.r@gmail.com", "phone": "(212) 555-1114", "rsvp": "yes", "dietary_needs": "halal"},
  {"guest_name": "Jolanta Kowalska", "plus_one_name": "Marcin Kowalski", "address": "2014 N Western Avenue Apt 3F Chicago IL 60647", "email": "jolanta.k@gmail.com", "phone": "(773) 555-1144", "rsvp": "yes", "dietary_needs": "lactose intolerant"},
  {"guest_name": "Kwabena Mensah-Boateng", "plus_one_name": null, "address": "2255 Peachtree Road Atlanta GA 30309", "email": "kwabena.mb@gmail.com", "phone": "(404) 555-0188", "rsvp": "yes", "dietary_needs": "none"},
  {"guest_name": "Liesel Mannheim", "plus_one_name": "Henrik Mannheim", "address": "2218 Telegraph Avenue Berkeley CA 94704", "email": "liesel.m@gmail.com", "phone": "(212) 555-7794", "rsvp": "yes", "dietary_needs": "vegetarian for Henrik"}
]
""",
]
BLOCK_TRANSFER: list[str] = [
    # 0. .env with AWS IAM creds
    """# .env.production — DO NOT COMMIT
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
AWS_DEFAULT_OUTPUT=json
S3_BUCKET_NAME=appdata-prod-east-1
SES_REGION=us-east-1
SES_FROM_ADDRESS=noreply@example.com
CLOUDFRONT_DISTRIBUTION_ID=E2A4B6C8D0E2F4G6
LOG_LEVEL=info
""",

    # 1. .env with DB + Redis + JWT
    """DATABASE_URL=postgresql://app_writer:Hv7Kp2Lm9Rq4Tn8Wx@db-prod-cluster.cluster-cxa9zr2xnaxq.us-east-1.rds.amazonaws.com:5432/app_prod?sslmode=require
REDIS_URL=redis://default:aGqRwQ7zKp2Nmx4LyV9Hb@redis-prod.5h7kqd.0001.use1.cache.amazonaws.com:6379/0
JWT_SECRET=KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1A
JWT_REFRESH_SECRET=Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUzPaC1
SESSION_SECRET=zL8RkV2NmQ7yPxJ4hWbT9cGfDsAq3VkM7eUz6PaB1XnYr
NODE_ENV=production
PORT=3000
""",

    # 2. .env with Stripe live keys
    """# Production payment credentials — DO NOT SHARE
STRIPE_SECRET_KEY=sk_test_PLACEHOLDER_NOT_A_REAL_KEY_4eC39H
STRIPE_PUBLISHABLE_KEY=pk_test_PLACEHOLDER_NOT_A_REAL_KEY_TYooMQ
STRIPE_WEBHOOK_SECRET=whsec_XXXXXXXXXXXXXXXXXXXXXXXXXXXXX
STRIPE_CONNECT_CLIENT_ID=ca_QxLm9NHpKj4WzYg8TcFd6NsRq3VkM7eUz6Pa
STRIPE_RESTRICTED_KEY_REFUNDS=rk_test_PLACEHOLDER_NOT_A_REAL_KEY_BQokik
""",

    # 3. .env with multi-provider AI keys
    """OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX-AA
COHERE_API_KEY=co-Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GROQ_API_KEY=gsk_KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc
TOGETHER_API_KEY=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUzKrZ8mPq2Lv5
""",

    # 4. .env with GitHub tokens
    """# GitHub Actions secrets — exported from secret manager
GITHUB_TOKEN=ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GITHUB_APP_ID=987654
GITHUB_APP_INSTALLATION_ID=12345678
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAv4Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3
VkM7eUzKrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc
... [truncated, 1700 chars total] ...
-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1A
""",

    # 5. .env Twilio
    """TWILIO_ACCOUNT_SID=ACa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q
TWILIO_AUTH_TOKEN=KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1A
TWILIO_API_KEY_SID=SKa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q
TWILIO_API_KEY_SECRET=Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz
TWILIO_FROM_NUMBER=+14155550100
TWILIO_VERIFY_SID=VAa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q
""",

    # 6. kubernetes_secrets.yaml
    """apiVersion: v1
kind: Secret
metadata:
  name: app-prod-credentials
  namespace: production
type: Opaque
data:
  # base64-encoded values
  DATABASE_PASSWORD: SHY3S3AyTG05UnE0VG44V3hCbjV4UTd2UjJMbTlIcA==
  JWT_SECRET: S3JaOG1QcTJMdjVOd0h4WWo0V2I5VGNHZkRzUm4zVms=
  STRIPE_SECRET_KEY: c2tfbGl2ZV81MUFCeDd5S1F6MkxtOU5IcEtqNFd6WWc4VGNGZDZOc1Jx
  AWS_SECRET_ACCESS_KEY: cUY4aksyek40bFA5bVIzd1g2dlkxdUg1dEc3c0QwZUE5YkMy
  REDIS_AUTH_TOKEN: YUdxUndRN3pLcDJObXg0THlWOUhi
""",

    # 7. kubernetes TLS secret
    """apiVersion: v1
kind: Secret
metadata:
  name: api-tls
  namespace: prod
type: kubernetes.io/tls
data:
  tls.crt: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURYVENDQWtXZ0F3SUJBZ0lKQUlPRWRPS01iVkVNTUEwR0NTcUdTSWIzRFFFQkN3VUFNRVF4Q3pBSkJnTlYKQkFZVEFsVlRNUk13RVFZRFZRUUlEQXBEWVd4cFptOXljbWxoTVJZd0ZBWURWUVFLREExUWNtOWtkV04wYVc5dQpYRTBlR1lzcGZIaUFTbXJqejZRSDIzbGRvZGdRT3R1...
  tls.key: LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlFcEFJQkFBS0NBUUVBdjRIdjdLcDJMbTlScTRUbjhXeEJuNXhRN3ZSMkxtOUhwS2o0V3pZZzhUY0ZkNk5zClJxM1ZrTTdlVXpLclo4bVBxMkx2NU53SHhZajRXYjlUY0dmRHNSbjNWa003ZVV6NlExQUJvWExtOU42Z0s0UnQyVwpxOFZjNU1oCkFRRUE5N1RNWG9KNjlLMldyV2ZTeFY1ZUFRSUE9PQotLS0tLUVORCBSU0EgUFJJVkFURSBLRVktLS0tLQ==
""",

    # 8. kubernetes OAuth secret
    """apiVersion: v1
kind: Secret
metadata:
  name: google-oauth
  namespace: production
type: Opaque
data:
  CLIENT_ID: MTAyMzQ1Njc4OTAxLWFiYzEyM2RlZjQ1Ni5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbQ==
  CLIENT_SECRET: R09DU1BYLUtyWjhtUHEyTHY1TndIeFlqNFdiOQ==
  REDIRECT_URI: aHR0cHM6Ly9hcHAuZXhhbXBsZS5jb20vYXV0aC9jYWxsYmFjaw==
""",

    # 9. docker-compose with hardcoded passwords
    """services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app_admin
      POSTGRES_PASSWORD: TfJk2Wxq8mNpLr4VyHcGz5BdRq9NsKv
      POSTGRES_DB: app_prod
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    command: redis-server --requirepass MnB7vC2xQ9zR4tY6uI8oP1aS3dF5gH
    volumes:
      - redisdata:/data

  app:
    image: registry.example.com/app:latest
    environment:
      DATABASE_URL: postgres://app_admin:TfJk2Wxq8mNpLr4VyHcGz5BdRq9NsKv@db:5432/app_prod
      REDIS_URL: redis://:MnB7vC2xQ9zR4tY6uI8oP1aS3dF5gH@redis:6379/0
      JWT_SECRET: zHvQ7rT8wL2mN4pX9kY6jB3uF5sD1aE
      STRIPE_SECRET_KEY: sk_test_PLACEHOLDER_NOT_A_REAL_KEY_BQokik
    ports:
      - "443:443"

volumes:
  pgdata:
  redisdata:
""",

    # 10. docker-compose with Grafana + MinIO admin passwords
    """services:
  grafana:
    image: grafana/grafana:10.4.0
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg
      GF_AUTH_ANONYMOUS_ENABLED: "false"
      GF_DATABASE_TYPE: postgres
      GF_DATABASE_HOST: db:5432
      GF_DATABASE_PASSWORD: TfJk2Wxq8mNpLr4VyHcGz5BdRq9NsKv

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minio_admin
      MINIO_ROOT_PASSWORD: KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz
    ports:
      - "9000:9000"
      - "9001:9001"
""",

    # 11. Google OAuth client_secret.json
    """{
  "web": {
    "client_id": "847291045213-vapcoiqhtg4eaurkkkbljl6ufm8kkk0a.apps.googleusercontent.com",
    "project_id": "voltage-control-prod",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "GOCSPX-XXXXXXXXXXXXXXXXXXXXXXX",
    "redirect_uris": [
      "https://app.example.com/auth/callback",
      "http://localhost:3000/auth/callback"
    ]
  }
}
""",

    # 12. GCP service account key
    """{
  "type": "service_account",
  "project_id": "voltage-control-prod",
  "private_key_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDqv4Hv7Kp2Lm9R\\nq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUzKrZ8mPq2Lv5NwHxYj4W\\nb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc5MhAQEA97TMXoJ69K2WrWfS\\n... [truncated, ~1700 chars typical] ...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "voltage-control-prod-runner@voltage-control-prod.iam.gserviceaccount.com",
  "client_id": "112837465029384756102",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/voltage-control-prod-runner%40voltage-control-prod.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
""",

    # 13. Firebase service account
    """{
  "type": "service_account",
  "project_id": "casual-mobile-app",
  "private_key_id": "f6d8a1b3c5e7f9a2b4d6c8e1a3b5d7f9c2e4a6b8",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDqv4Hv7Kp2Lm9R\\nq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUzKrZ8mPq2Lv5NwHxYj4W\\nb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc5MhAQEA97TMXoJ69K2WrWfS\\n-----END PRIVATE KEY-----\\n",
  "client_email": "firebase-adminsdk-x4r2k@casual-mobile-app.iam.gserviceaccount.com",
  "client_id": "104578291045213847291",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
""",

    # 14. AWS credentials file
    """[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
region = us-east-1
output = json

[production]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
region = us-east-1

[staging]
aws_access_key_id = AKIAI44QH8DHBEXAMPLE
aws_secret_access_key = je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY
region = us-west-2
""",

    # 15. Stripe API key on one line
    """STRIPE_API_KEY=sk_test_PLACEHOLDER_NOT_A_REAL_KEY_4eC39H
""",

    # 16. OpenSSH private key
    """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
NhAAAAAwEAAQAAAYEAr8H+vKp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3V
kM7eUzKrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc5Mh
AQEA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSx
V5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrW
fSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIAAAAEAAAAGgo
LbWFydGluLmJqb3JuQGV4YW1wbGUuZGV2AQID
-----END OPENSSH PRIVATE KEY-----
""",

    # 17. RSA private key for SSL
    """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAv4Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3V
kM7eUzKrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc5Mh
AQEA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSx
V5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrW
fSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2
WrWfSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ69K2WrWfSxV5eAQIA97TMXoJ6
9K2WrWfSxV5eAQIAQABAoIBAFKp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsR
... [truncated for brevity, typical PEM is 1700+ chars] ...
-----END RSA PRIVATE KEY-----
""",

    # 18. PGP private key armored
    """-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v2

lQVYBGRcK8sBDADfdvHCG0HF1qBkSx9XfqI1XJ6BvHLwpJ1KqBcdEfH2vJqLwXkY
8nMpKzQqAaBxFvLpQzCcDvK7VnZ4xQ2KfDqRxLpJqNvFwBcXxL2vQzM5VzJxFqWb
n3yQvLcKpZxAnD2yZ4xJqK9vL2x3LpQzAcDvKkKxFqWzAB4vN4nLcKpZxAnD2yZ4
... [truncated, real key is 3000+ chars] ...
-----END PGP PRIVATE KEY BLOCK-----
""",

    # 19. GnuPG keyring excerpt
    """sec   rsa4096 2023-06-15 [SC]
      F8B9 2D44 1A0C 5E32 9A8F  6B14 7C2D 8E91 4F1B 3A6C
uid           [ultimate] Alice Engineering <alice.eng@example.com>
ssb   rsa4096 2023-06-15 [E]

# Passphrase note from key creation log:
# Master key passphrase: "thunder-glasses-radio-9281" (stored separately)
# Subkey decryption passphrase: KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz
""",

    # 20. Vault shamir share
    """vault-unseal-share-3-of-5:
  recipient: ops@example.com
  share: "AAAAAQEYZl3yPCWp3J5GhBd2Fz8gQDqv4Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9Hp"
  fingerprint: "f8b9:2d44:1a0c:5e32:9a8f:6b14:7c2d:8e91:4f1b:3a6c"
  encoded_under: "ops-key-2024"
  expires: "2025-06-15T00:00:00Z"
  # Master key passphrase recovery: thunder-glasses-radio-9281
""",

    # 21. HashiCorp Vault token file
    """VAULT_ADDR=https://vault.internal.example.com:8200
VAULT_TOKEN=s.K8r3Zm2PqL5vNwHx7Yj4Wb9TcGfDsRn3VkM7eUz
VAULT_NAMESPACE=admin
APPROLE_ROLE_ID=4f8b9c12-7d44-4a0c-8e32-9a8f6b147c2d
APPROLE_SECRET_ID=Hv7Kp2Lm9-Rq4T-n8Wx-Bn5x-Q7vR2Lm9HpKj
""",

    # 22. .npmrc with auth token
    """registry=https://registry.npmjs.org/
//registry.npmjs.org/:_authToken=npm_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
//npm.pkg.github.com/:_authToken=ghp_YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
@example-org:registry=https://npm.pkg.github.com/
always-auth=true
""",

    # 23. .pypirc with auth
    """[distutils]
index-servers =
  pypi
  internal

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

[internal]
repository = https://pypi.internal.example.com/
username = ci-deploy
password = Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM
""",

    # 24. Docker config.json with registry credentials
    """{
  "auths": {
    "registry.example.com": {
      "auth": "Y2ktZGVwbG95OkhWN0twMkxtOVJxNFRuOFd4Qm41eFE3dlIyTG05SHBLag=="
    },
    "ghcr.io": {
      "auth": "Z2hjci11c2VyOmdocF9LcloKOG1QcTJMdjVOd0h4WWo0V2I5VGNHZkRzUm4zVms="
    },
    "docker.io": {
      "auth": "ZG9ja2VyaHViOlBQVDdmRzhqSzJ6TjRsUDltUjN3WDZ2WTF1SDV0RzdzRDA="
    }
  },
  "credsStore": "osxkeychain"
}
""",

    # 25. Pulumi config with encrypted secrets
    """config:
  aws:region: us-east-1
  app:database-password:
    secure: AAABACTKrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc5Mh
  app:jwt-secret:
    secure: AAABACTBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz
  app:stripe-api-key:
    secure: AAABACTSXLm9N6gK4Rt2Wq8Vc5MhKrZ8mPq2Lv5NwHxYj4
  encryption_key: q7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUzKrZ8mPq2Lv5NwHxYj4Wb9
""",

    # 26. 1Password emergency kit
    """1Password Emergency Kit

Sign-in Address: my.1password.com
Email Address: ops@example.com
Account Type: family

Secret Key:
A3-K8R3ZM-2PQL5V-NWHX7-YJ4WB-9TCGF-DSRN3-VKM7E

Master Password:
correct-horse-battery-staple-49281!

If you can't access your account, you'll need both pieces of information above to recover it.
""",

    # 27. Bitwarden export
    """{
  "encrypted": false,
  "items": [
    {
      "type": "login",
      "name": "Production Postgres",
      "login": {
        "username": "app_admin",
        "password": "TfJk2Wxq8mNpLr4VyHcGz5BdRq9NsKv",
        "uris": [{"uri": "postgres://db-prod.internal.example.com:5432"}]
      }
    },
    {
      "type": "login",
      "name": "GitHub (work)",
      "login": {
        "username": "alice-eng",
        "password": "Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4",
        "totp_secret": "JBSWY3DPEHPK3PXP"
      }
    },
    {
      "type": "login",
      "name": "AWS Console (prod)",
      "login": {
        "username": "alice.eng@example.com",
        "password": "MnB7vC2xQ9zR4tY6uI8oP1aS3dF5gH",
        "totp_secret": "KQXBYR2L5MNVZ8GZ"
      }
    }
  ]
}
""",

    # 28. LastPass CSV export
    """# LastPass vault export — vault_master_password=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4
url,username,password,totp,extra,name,grouping,fav
https://github.com,alice-eng,Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2,JBSWY3DPEHPK3PXP,,GitHub work,Work,1
https://aws.amazon.com,alice.eng@example.com,MnB7vC2xQ9zR4tY6uI8oP1aS3dF5gH,KQXBYR2L5MNVZ8GZ,Root account,AWS production,Work,1
https://app.datadoghq.com,alice-datadog,KrZ8mPq2Lv5NwHxYj4Wb9TcGf,,API key UI access,Datadog,Work,0
https://gitlab.com,alice.eng,zHvQ7rT8wL2mN4pX9kY6jB3uF5sD1aE,JBSWY3DPEHPK3PXQ,2FA enabled,GitLab,Work,0
https://www.fastly.com,alice@example.com,Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6Ns,,API token in profile,Fastly,Work,0
https://app.cloudflare.com,alice.eng@example.com,TfJk2Wxq8mNpLr4VyHcGz5BdRq,KQXBYR2L5MNVZ8GA,,Cloudflare,Work,0
""",

    # 29. Plain-text connection string
    """# Production database connection — DO NOT COMMIT
DATABASE_URL=postgresql://app_admin:Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4@prod-db.cluster-cxa9zr2xnaxq.us-east-1.rds.amazonaws.com:5432/main_app_db?sslmode=require

# Read replica
READ_REPLICA_URL=postgresql://app_reader:zHvQ7rT8wL2mN4pX9kY6jB3uF5sD1aE@prod-db-read.cluster-ro-cxa9zr2xnaxq.us-east-1.rds.amazonaws.com:5432/main_app_db?sslmode=require
""",

    # 30. MongoDB connection URI
    """# Mongo Atlas connection — production cluster
MONGODB_URI=mongodb+srv://app_writer:KrZ8mPq2Lv5NwHxYj4Wb9TcGf@prod-cluster.5h7kqd.mongodb.net/main_app?retryWrites=true&w=majority&appName=Production

# Analytics replica
MONGODB_ANALYTICS_URI=mongodb+srv://analytics_reader:Bn5xQ7vR2Lm9HpKj4WzYg8TcFd@analytics-cluster.5h7kqd.mongodb.net/events_db?readPreference=secondaryPreferred
""",

    # 31. Redis URL with auth
    """REDIS_PRIMARY_URL=redis://default:aGqRwQ7zKp2Nmx4LyV9Hb@redis-prod.5h7kqd.0001.use1.cache.amazonaws.com:6379/0
REDIS_REPLICA_URL=redis://default:aGqRwQ7zKp2Nmx4LyV9Hb@redis-prod-replica.5h7kqd.0001.use1.cache.amazonaws.com:6379/0
REDIS_QUEUE_URL=redis://default:zL8RkV2NmQ7yPxJ4hWbT9cGfDsAq3VkM7eUz6PaB1XnYr@redis-queue.example.com:6380/0
""",

    # 32. JWT signing key file
    """# HMAC-SHA256 signing key for JWT
# Rotated 2024-08-15. Previous key archived in vault under jwt-signing-2024-q2.
# DO NOT COMMIT THIS FILE.

KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc5MhKp2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUzz9R4LhTcGf
""",

    # 33. AES-256 key in hex
    """# AES-256-GCM encryption key for at-rest field encryption
# Generated 2024-08-15 via crypto.randomBytes(32).toString('hex')
# Stored separately from data. DO NOT COMMIT.

c7a1f9b3d2e4f6a8c0b2d4e6f8a1c3e5d7f9b1d3e5a7c9b1d3f5e7a9c1b3d5e7

# IV format: 12-byte random per record, prepended to ciphertext.
# Auth tag: 16-byte appended after ciphertext.
""",

    # 34. Slack bot token + signing secret
    """SLACK_BOT_TOKEN=xoxb-XXXXXXXXXXXX-XXXXXXXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXX
SLACK_SIGNING_SECRET=KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1A
SLACK_APP_TOKEN=xapp-1-AXXXXXXXXXX-XXXXXXXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SLACK_VERIFICATION_TOKEN=z9R4LhTcGfDsRn3VkM7eUzKrZ8mPq2Lv
""",

    # 35. Discord bot token
    """DISCORD_BOT_TOKEN=MTAxNzg5MzQ1NjEyMzQ1Njc4OTAuGabCdE.KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz
DISCORD_CLIENT_ID=1017893456123456789
DISCORD_CLIENT_SECRET=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj
DISCORD_GUILD_ID=987654321012345678
""",

    # 36. Telegram bot token
    """# Telegram bot — production
TELEGRAM_BOT_TOKEN=8123456789:AAH8KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz
TELEGRAM_CHAT_ID=-1001234567890
TELEGRAM_WEBHOOK_SECRET_TOKEN=Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz
""",

    # 37. Twilio API key file
    """ACCOUNT_SID=ACa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q
AUTH_TOKEN=KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1A
API_KEY_SID=SKa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q
API_KEY_SECRET=Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz
VERIFY_SERVICE_SID=VAa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q
""",

    # 38. SendGrid API key
    """SENDGRID_API_KEY=SG.XXXXXXXXXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SENDGRID_WEBHOOK_VERIFY_KEY=Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6Ns
SENDGRID_FROM_EMAIL=noreply@example.com
""",

    # 39. Mailgun API key
    """MAILGUN_API_KEY=key-Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg
MAILGUN_DOMAIN=mg.example.com
MAILGUN_WEBHOOK_SIGNING_KEY=Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz
MAILGUN_FROM_EMAIL=alerts@mg.example.com
""",

    # 40. Cloudflare API token
    """# Cloudflare API token for DNS edit permissions on example.com zone
# Created 2024-08-15, expires 2025-08-15
# Scope: Zone:DNS:Edit on example.com only

CLOUDFLARE_API_TOKEN=KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3VkM7eUz6Q1ABoXLm9N6gK4Rt2Wq8Vc5MhKp2Lv
CLOUDFLARE_ZONE_ID=023e105f4ecef8ad9ca31a8372d0c353
CLOUDFLARE_ACCOUNT_ID=8c8d3f9a2b1e4f5d6c7b8a9e0d1c2b3a
""",

    # 41. Heroku .netrc snippet
    """machine api.heroku.com
  login alice.eng@example.com
  password Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz

machine git.heroku.com
  login alice.eng@example.com
  password Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz
""",

    # 42. GitLab personal access token
    """# GitLab PAT — full API scope
# Created 2024-08-15, scopes: api, read_user, read_repository, write_repository

GITLAB_TOKEN=glpat-XXXXXXXXXXXXXXXXXXXX
GITLAB_URL=https://gitlab.example.com
GITLAB_CI_TRIGGER_TOKEN=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2
GITLAB_RUNNER_REGISTRATION_TOKEN=Bn5xQ7vR2Lm9HpKj4WzYg8TcFd
""",

    # 43. DigitalOcean Spaces credentials
    """# DigitalOcean Spaces credentials for prod backup bucket
SPACES_ACCESS_KEY=DO00KRZ8MPQ2LV5NWHXYJ4
SPACES_SECRET_KEY=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3
SPACES_REGION=nyc3
SPACES_BUCKET=app-prod-backups
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
""",

    # 44. Backblaze B2 application key
    """# Backblaze B2 application key — used by CI for releasing builds
B2_KEY_ID=0049a1b2c3d4e5f6g70000000a
B2_APPLICATION_KEY=K004KrZ8mPq2Lv5NwHxYj4Wb9TcGfDsRn3V
B2_BUCKET_ID=8a9b0c1d2e3f4a5b6c7d8e9f
B2_BUCKET_NAME=app-releases-prod
""",

    # 45. Wasabi S3 credentials
    """# Wasabi credentials for production media bucket
WASABI_ACCESS_KEY_ID=WAS4QXMP2RYBQK7NLMN0
WASABI_SECRET_ACCESS_KEY=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd
WASABI_REGION=us-east-1
WASABI_ENDPOINT=https://s3.wasabisys.com
WASABI_BUCKET=app-prod-media
""",

    # 46. MinIO credentials
    """# MinIO standalone deployment — production
MINIO_ROOT_USER=minio_root_admin
MINIO_ROOT_PASSWORD=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg
MINIO_BROWSER_LOGIN_ANIMATION=off

# Application-scoped credentials (created via mc admin user add)
APP_MINIO_ACCESS_KEY=app_writer_2024
APP_MINIO_SECRET_KEY=Bn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz
""",

    # 47. RDS master password export
    """rds-master-password=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUzKrZ8mPq2Lv5
""",

    # 48. SMTP credentials
    """# SMTP credentials for transactional mail (mailgun relay)
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=postmaster@mg.example.com
SMTP_PASSWORD=Hv7Kp2Lm9Rq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3
SMTP_USE_TLS=true
SMTP_FROM_ADDRESS=noreply@example.com
""",

    # 49. GCP service account in Terraform variable file
    """variable "gcp_service_account_key" {
  type        = string
  sensitive   = true
  description = "Service account JSON for Terraform Cloud runner"
  default     = <<-EOT
{
  "type": "service_account",
  "project_id": "voltage-control-prod",
  "private_key_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDqv4Hv7Kp2Lm9R\\nq4Tn8WxBn5xQ7vR2Lm9HpKj4WzYg8TcFd6NsRq3VkM7eUz\\n-----END PRIVATE KEY-----\\n",
  "client_email": "terraform-runner@voltage-control-prod.iam.gserviceaccount.com",
  "client_id": "112837465029384756102"
}
EOT
}
"""
,
    # 50. .env.local with real-shaped credential values across multiple providers
    """# .env.local — generated 2025-12-03, DO NOT COMMIT
DATABASE_URL=postgresql://app_prod:9f4d8e7c2b1a0e6f3d8c5b9a4e7d2c1b@db-primary.internal.acme.io:5432/app_prod
REDIS_URL=rediss://default:R3d1s_Pr0d_T0k3n_8K2nM4pL9vQ@redis-cluster-0.internal.acme.io:6380/0
SECRET_KEY=zX9mP3kQ7nL2vR8tY5jH1fG4dB6cA0eW
JWT_SIGNING_KEY=eyJzdWIiOiJzZWNyZXQiLCJpYXQiOjE3MzM0MjA4MDB9.RealLookingJwtSignatureValueGoesHere
STRIPE_SECRET_KEY=sk_live_FAKE_TRAINING_KEY_DO_NOT_USE
SENDGRID_API_KEY=SG.7nQ3pM4kR2vL9wY8jH5fG1dB0cA6eX.tK8mN5pQ3rS7vL2wY9jH4fG6dB1cA0e
""",
    # 51. .env.production with realistic AWS / GitHub / Twilio values
    """# .env.production — DO NOT COMMIT — DO NOT SHARE
AWS_ACCESS_KEY_ID=AKIAQ7XK4PL5N8M2RJ9V
AWS_SECRET_ACCESS_KEY=hT3kP9mN8qL2rS5vW7jY4fG6dB1cA0eX9zM4pK2nL5wQ
AWS_DEFAULT_REGION=us-west-2
S3_BUCKET=acme-prod-assets

GH_PAT=ghp_K8mN5pQ3rS7vL2wY9jH4fG6dB1cA0eX9zM4pK
GH_ORG=acme-corp

TWILIO_ACCOUNT_SID=AC8a9b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3
TWILIO_AUTH_TOKEN=z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4
TWILIO_FROM_NUMBER=+14155551234
""",
    # 52. plain .env shipped with real-shaped Postgres/Redis/JWT secrets
    """DATABASE_URL=postgresql://acme_app:P0stgr3sPr0dP@ssw0rd2024@db-cluster-east-1.internal:5432/acme_app_prod
REDIS_URL=redis://:R3d1sCach3T0k3n_2024_n0tT0Sh@r3@redis-cache.internal:6379
SESSION_SECRET=h7K9mN3pQ5rS8vL2wY6jH4fG1dB0cA9eX5zM7pK4nL8wQ
INTERNAL_API_TOKEN=int_t0k3n_p9o8n7m6l5k4j3h2g1f0e9d8c7b6a5z4y3x2
ENCRYPTION_KEY=aGVsbG93b3JsZGZyb21wcm9kZW5jcnlwdGlvbjEyMzQ1Ng==
WEBHOOK_SIGNING_SECRET=whsec_K8mN5pQ3rS7vL2wY9jH4fG6dB1cA0eX
""",
    # 53. owid-shape ambiguous: empty placeholders mixed with dev-style defaults
    """TZ=utc
ENV=development

GRAPHER_DB_NAME=grapher
GRAPHER_DB_USER=grapher
GRAPHER_DB_PASS=grapher
GRAPHER_DB_HOST=127.0.0.1
GRAPHER_DB_PORT=3307

GRAPHER_TEST_DB_PASS=graphertest
GRAPHER_TEST_DB_HOST=127.0.0.1

GDOCS_PRIVATE_KEY=
GDOCS_CLIENT_EMAIL=
GDOCS_CLIENT_ID=

OPENAI_API_KEY=
FIGMA_API_KEY=

R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=

# Local dev credentials — do NOT commit. Rotate before any deploy.
# These are real working passwords for the local docker-compose stack;
# the empty keys above belong to services not used in local dev.
""",
]
REQUEST_PERMISSION: list[str] = [
    # 0. NDA template
    """NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement (this "Agreement") is made and entered into as of [Effective Date], by and between [Disclosing Party Name] ("Disclosing Party") and [Receiving Party Name] ("Receiving Party"), collectively the "Parties."

1. Confidential Information. "Confidential Information" means any non-public information of the Disclosing Party that is identified as confidential at the time of disclosure or that a reasonable person would understand to be confidential given the nature of the information and the circumstances of disclosure. Confidential Information includes, without limitation, business plans, customer lists, financial information, technical data, designs, prototypes, source code, marketing strategies, and personnel matters.

2. Obligations. The Receiving Party shall (a) hold the Confidential Information in strict confidence; (b) use the Confidential Information solely for the Purpose described in Section 3; (c) not disclose the Confidential Information to any third party without the prior written consent of the Disclosing Party; and (d) protect the Confidential Information using the same degree of care it uses to protect its own confidential information, but in no event less than reasonable care.

3. Purpose. The Confidential Information is disclosed solely for the purpose of evaluating [Purpose] between the Parties.

4. Term. This Agreement shall be effective for [Term] from the Effective Date.

5. Governing Law. This Agreement shall be governed by the laws of [Jurisdiction].
""",

    # 1. Mutual NDA — full body
    """MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement is entered into on this 14th day of March, 2024, by and between Greenmark Industries, Inc., a Delaware corporation ("Greenmark"), and Hayfield Robotics, LLC, a California limited liability company ("Hayfield"), each a "Party" and together the "Parties."

WHEREAS, the Parties wish to explore a potential business relationship involving the integration of Hayfield's autonomous navigation technology with Greenmark's logistics platform; and

WHEREAS, in connection with such discussions, each Party may disclose to the other certain confidential, proprietary, and non-public information;

NOW, THEREFORE, the Parties agree as follows:

1. Confidential Information includes all information, whether oral, written, or in any other medium, that is marked confidential, identified as confidential at the time of disclosure, or that the receiving Party should reasonably understand to be confidential. This includes but is not limited to technical specifications, source code, customer data, financial projections, business strategy, hardware schematics, and information related to ongoing or planned product development.

2. Each Party shall protect Confidential Information of the other with the same degree of care it uses to protect its own most sensitive information.

3. This Agreement shall remain in effect for three (3) years from the date first written above, after which time confidentiality obligations shall continue with respect to trade secrets indefinitely.

Signed:
For Greenmark Industries, Inc.:  _________________________
For Hayfield Robotics, LLC:      _________________________
""",

    # 2. Master Services Agreement excerpt
    """MASTER SERVICES AGREEMENT — Section 4 through 7

4. PAYMENT TERMS

4.1 Fees. Client shall pay Service Provider the fees set forth in each applicable Statement of Work ("SOW"). Unless otherwise specified, all fees are stated in U.S. dollars.

4.2 Invoicing. Service Provider shall invoice Client monthly in arrears for services performed during the preceding month. Invoices are due net thirty (30) days from the invoice date.

4.3 Late Payment. Amounts not paid when due shall accrue interest at the rate of one and one-half percent (1.5%) per month or the maximum rate permitted by applicable law, whichever is lower.

5. INTELLECTUAL PROPERTY

5.1 Pre-Existing IP. Each Party retains all right, title, and interest in its Pre-Existing IP. "Pre-Existing IP" means intellectual property owned or licensed by a Party prior to the Effective Date or developed independently of this Agreement.

5.2 Deliverables. Upon Client's payment in full for the relevant SOW, Service Provider assigns to Client all right, title, and interest in the Deliverables, excluding any Service Provider Pre-Existing IP incorporated therein, for which Service Provider grants Client a perpetual, worldwide, non-exclusive license.

6. CONFIDENTIALITY

6.1 The Parties acknowledge that they may have access to Confidential Information of the other. Each Party shall maintain such Confidential Information in confidence and shall not disclose it to any third party except as necessary to perform under this Agreement and only to those of its employees and contractors who are bound by confidentiality obligations no less protective than those set forth herein.

7. TERM AND TERMINATION

7.1 Term. This Agreement shall commence on the Effective Date and shall continue until terminated as provided herein.

7.2 Termination for Convenience. Either Party may terminate this Agreement for any reason upon thirty (30) days' prior written notice.
""",

    # 3. Partnership agreement memo
    """MEMORANDUM — Partnership Agreement Outline

To: Counsel
From: Founders
Re: Proposed structure for Northstar Trade / Cascade Logistics joint venture
Date: April 8, 2024

Counsel, ahead of drafting the formal partnership agreement, here is the structure we've aligned on. Please convert into contract form and flag any issues.

Partners and contributions:
- Northstar Trade contributes its trade-finance origination engine, current pipeline of approximately $80M in originated facilities, and the customer relationships associated with such pipeline. Northstar will also contribute $4M in cash for initial working capital.
- Cascade Logistics contributes its physical logistics network (warehouses in 7 cities, fleet of 220 vehicles, and approximately 180 operations staff), plus its existing customer book of approximately $42M in annual revenue.

Profit / loss allocation:
- 60% to Northstar, 40% to Cascade for the first 24 months.
- Re-evaluation at month 24 based on contribution to GMV; partners agree to renegotiate in good faith.

Governance:
- Three-person Management Committee: two appointees from Northstar, one from Cascade.
- Major decisions (capital raises >$2M, hiring of CEO, change of control, dissolution) require unanimous consent of the Management Committee.

Dissolution:
- Either Party may trigger dissolution after the 36-month anniversary upon 180 days' notice. On dissolution, Cascade has right of first refusal on the logistics assets at fair-market value.

This memo is privileged and confidential. Please respond by April 19.
""",

    # 4. M&A Letter of Intent
    """NON-BINDING LETTER OF INTENT

April 22, 2024

Mr. Alistair Knowlton
CEO, Voltage Control Systems, Inc.

Dear Alistair,

Following our discussions over the past several weeks, BlueRidge Capital Partners, LP ("BlueRidge") is pleased to submit this non-binding Letter of Intent regarding a potential acquisition of Voltage Control Systems, Inc. ("VCS" or the "Company"). The principal terms of our proposed transaction are summarized below.

1. STRUCTURE. The proposed transaction would be a 100% acquisition of the equity of VCS by an entity to be formed by BlueRidge. The transaction would be structured as a reverse triangular merger or stock purchase, at BlueRidge's election following further diligence.

2. PURCHASE PRICE. Based on the information we have reviewed to date, BlueRidge proposes total enterprise value in the range of $215 million to $245 million, subject to (a) confirmatory financial, legal, technical, and operational due diligence; (b) net working capital and net debt adjustments; and (c) negotiation of definitive agreements.

3. ESCROW AND INDEMNIFICATION. Ten percent (10%) of the purchase price would be held in escrow for a period of eighteen (18) months following closing, to satisfy indemnification claims.

4. EXCLUSIVITY. In consideration of the time and expense BlueRidge will incur in pursuing this transaction, VCS agrees that for a period of forty-five (45) days following execution of this LOI, neither VCS nor any of its representatives shall solicit, encourage, or accept any other offers or expressions of interest regarding a potential transaction.

5. NON-BINDING. Except for the provisions of Section 4 (Exclusivity) and Section 6 (Confidentiality), this letter is non-binding and is intended only as a summary of the principal terms of the proposed transaction.

We believe this is an attractive proposal for VCS and its shareholders. We look forward to advancing to definitive agreements.

Sincerely,
Margot Lefevre
Managing Partner, BlueRidge Capital Partners, LP
""",

    # 5. Series B term sheet
    """SERIES B PREFERRED STOCK FINANCING — TERM SHEET (NON-BINDING)

Company: Lighthouse Robotics, Inc.
Date: May 6, 2024

This Term Sheet summarizes the principal terms of the proposed Series B Preferred Stock Financing. Except for the provisions concerning Confidentiality, No Shop, and Expenses, this Term Sheet is non-binding and is subject to satisfactory completion of due diligence and the negotiation and execution of definitive agreements.

Amount Raised: $32,000,000
Lead Investor: Riverstone Ventures
Other Investors: Existing investors (Lattice Capital, Foreman Partners) pro-rata participation
Pre-Money Valuation: $128,000,000
Post-Money Valuation: $160,000,000
Type of Security: Series B Preferred Stock

Liquidation Preference: 1x non-participating preference, paid before any distribution to Common holders.

Conversion: Each share of Series B convertible at any time at the option of the holder into Common Stock. Initial conversion ratio 1:1, subject to standard anti-dilution adjustments.

Anti-Dilution: Broad-based weighted average for Series B.

Board Composition: Following the closing, the Board shall consist of five (5) directors: two appointed by the Common, two appointed by the Preferred (one by Series A, one by Series B Lead), and one independent director mutually agreed upon by Common and Preferred.

Protective Provisions: Approval of holders of a majority of Preferred required for: (a) changes to certificate of incorporation adversely affecting Preferred; (b) liquidation events; (c) creation of senior securities; (d) annual budget approval.

Drag-Along: Holders of a majority of Preferred and majority of Common may compel sale to bona fide acquirer.

Right of First Refusal / Co-Sale: Standard ROFR and co-sale rights on transfers by Founders.

Vesting: All Founder shares subject to four-year vesting with one-year cliff, retroactive to date of initial issuance.
""",

    # 6. Board meeting minutes Q3
    """BOARD OF DIRECTORS MEETING — MINUTES

Date: October 17, 2024
Time: 2:00 PM ET
Location: Virtual (Zoom)
Present: Marina Goldberg (Chair), Theo Chen, Aaliyah Brown-Patel, Marcus Lindqvist, Independent Director Jonathan Reyes
Also Present: CEO Dilnoza Yusupov, CFO Bao Vinh Tran (by invitation)
Absent: None

The Chair called the meeting to order at 2:03 PM and confirmed the presence of a quorum.

1. APPROVAL OF MINUTES. The minutes of the August 19, 2024 meeting were approved unanimously.

2. CEO REPORT. CEO Yusupov reported on Q3 operating results, which exceeded internal plan on revenue (~ 8% above plan) and were modestly behind on operating expense. Year-to-date revenue is tracking to $94M against a full-year plan of $128M. New customer acquisitions were strong in EMEA but weaker than expected in APAC. The Board discussed the APAC underperformance and concurred with management's decision to defer additional APAC GTM investment until H2 2025.

3. CFO REPORT. CFO Tran presented Q3 financial results. Operating cash flow was $6.2M for the quarter, $14.1M YTD. Cash balance at quarter end was $42.8M. The Board reviewed the proposed FY2025 budget, including a planned headcount addition of 38 across engineering and customer success. After discussion, the Board approved the budget by unanimous vote.

4. SPECIAL TOPIC: ACQUISITION DISCUSSION. The Board went into executive session to discuss the inbound acquisition interest disclosed in the September preliminary meeting. CEO Yusupov briefed the Board on subsequent conversations and shared the latest term-sheet draft, which proposes a purchase price in the range of $720M to $820M. Discussion focused on whether to engage banker advisors. The Board directed CEO Yusupov to contact two recommended bankers and present a proposal at the November meeting.

5. ADJOURNMENT. There being no further business, the meeting was adjourned at 4:08 PM.

CONFIDENTIAL — These minutes are for the eyes of the Board only and are subject to the company's confidentiality policies.
""",

    # 7. Board resolution authorizing $5M credit facility
    """RESOLUTION OF THE BOARD OF DIRECTORS OF NORTHWIND TECHNOLOGIES, INC.

Adopted by unanimous written consent in lieu of a meeting, effective May 14, 2024.

WHEREAS, the Company desires to obtain a revolving credit facility of up to Five Million Dollars ($5,000,000) (the "Credit Facility") from Pacific First Commercial Bank ("Lender") to provide working capital flexibility in connection with the Company's ongoing operations and seasonal cash flow variability; and

WHEREAS, the Lender has presented to the Company a term sheet dated April 30, 2024, summarizing the principal terms of the proposed Credit Facility, including:

  - Maximum Commitment: $5,000,000
  - Interest Rate: SOFR + 350 basis points
  - Maturity: 24 months from closing, with 12-month extension option at Lender's discretion
  - Borrowing Base: 80% of eligible accounts receivable up to the Maximum Commitment
  - Financial Covenants: Minimum trailing twelve-month adjusted EBITDA of $2,500,000; minimum liquidity of $1,500,000
  - Collateral: First-priority security interest in substantially all assets of the Company

NOW, THEREFORE, BE IT RESOLVED that the Board of Directors hereby authorizes the officers of the Company to enter into the Credit Facility on the terms substantially set forth in the term sheet, with such modifications as the officers may agree, provided that any material modifications shall be promptly reported to the Board.

FURTHER RESOLVED that the Chief Financial Officer is hereby authorized and directed to execute and deliver all documents and agreements reasonably necessary or appropriate to effect the foregoing, including without limitation a Loan and Security Agreement, promissory notes, and security and pledge agreements.

This resolution is adopted in accordance with Section 141(f) of the Delaware General Corporation Law.

CONFIDENTIAL — Distribution limited to the Board, the Chief Financial Officer, and the Company's outside counsel.
""",

    # 8. "Confidential — Competitive Strategy" memo
    """MEMORANDUM — CONFIDENTIAL: COMPETITIVE STRATEGY

To: Executive Leadership Team
From: VP Strategy
Re: Response to Competitor X's "Aurora" product launch
Date: July 12, 2024

Last week Competitor X announced the launch of "Aurora," a direct competitive offering in our core market segment. Based on our analysis of public statements and what we've learned through customer conversations over the past 72 hours, here is the recommended internal response framework.

What we know about Aurora:
- Pricing positioned at approximately 30% below our list price.
- Feature set covers the four highest-volume use cases of our platform but omits the two that our enterprise tier customers most rely on (advanced analytics, custom integrations).
- Sales pitch leans heavily on "modern stack" / "rebuilt from scratch" narrative.
- 12 of our top-50 customers have been contacted by their account team in the past two weeks.

What we don't know yet:
- Whether Aurora has been licensed to any large customers ahead of GA.
- Whether the pricing is sustainable or introductory.
- The actual technical depth versus marketing claims.

Recommended response (immediate, next 30 days):

1. Targeted retention outreach to all of our top-50 customers within 14 days. Talking points emphasize the enterprise capabilities Aurora lacks. Discount authority of up to 18% authorized for top-20 accounts under threat.

2. Hold pricing publicly. Adjusting list price downward in response would validate Aurora's positioning.

3. Accelerate the "Atlas" feature release (currently scheduled for Q1 2025) into Q4 2024 if feasible. This release neutralizes two of Aurora's headline differentiators. Engineering: please scope.

4. Brief our top three analyst relationships in the next two weeks. We need their published guidance to reflect the depth-versus-marketing gap.

Items NOT to do:
- No public response to Aurora's launch. Engagement legitimizes them.
- No proactive press from us about competitive positioning. Customer outreach only.

Please reply with comments by EOD Thursday. Discussion at next ELT.
""",

    # 9. Internal Q4 financial forecast
    """INTERNAL: Q4 2024 FINANCIAL FORECAST AND OUTLOOK

For internal use only. Not for external distribution. Forward-looking, subject to revision.

Revenue
Q4 2024 forecast: $34.2M (vs. plan $32.8M, +4.3%)
H2 2024 forecast: $66.1M (vs. plan $63.4M, +4.3%)
FY2024 forecast: $124.7M (vs. plan $121.0M, +3.1%)

Composition of Q4 upside vs. plan:
- New customer ARR: $1.2M above plan (driven by stronger-than-expected mid-market signups in September)
- Expansion ARR: $0.4M above plan
- Churn: ~$0.2M worse than plan (one mid-market account departing in November)

Operating Expenses
Q4 2024 forecast: $28.6M (vs. plan $29.4M, -2.7%)
- Engineering: at plan
- Sales: ~$0.5M below plan due to slower-than-anticipated hiring
- Marketing: ~$0.3M below plan due to deferred Q4 demand-gen campaigns
- G&A: at plan

Operating Income
Q4 2024 forecast: $5.6M (vs. plan $3.4M, +65%)
FY2024 forecast: $11.4M (vs. plan $8.8M, +30%)

Cash Position
Forecast Q4-end cash balance: $48.2M (vs. plan $46.8M)
Operating cash flow Q4 forecast: $7.1M

Headcount
Plan: 312 FTE at year-end
Forecast: 304 FTE at year-end (open roles deferred to Q1 2025)

Outlook for 2025
Preliminary 2025 plan target: $158M revenue (+27% YoY), $14M operating income. Detailed plan will be presented at the January Board meeting.

Forward-looking statements above are management estimates and may differ materially from actual results. Do not redistribute.
""",

    # 10. Salary band internal doc
    """COMPENSATION FRAMEWORK 2024 — INTERNAL ONLY

This document outlines the company's compensation philosophy and salary bands for individual contributor levels. It is shared with team leads and people managers only; please do not redistribute or share screenshots.

Philosophy
We pay at the 65th percentile of the market for our peer set (Series B-D B2B software companies, headquartered in the San Francisco Bay Area, head count 100-500). We benchmark annually against a third-party compensation database and adjust bands on January 1 of each year.

Bands — Engineering IC track (USD, annual base, San Francisco Bay Area)

L3 (Engineer): $145,000 — $185,000
L4 (Senior Engineer): $185,000 — $235,000
L5 (Staff Engineer): $235,000 — $295,000
L6 (Senior Staff Engineer): $290,000 — $360,000
L7 (Principal Engineer): $355,000 — $445,000

Geographic adjustments: bands are adjusted downward for non-SF locations as follows: Seattle / NYC / Boston: -5%; Austin / Denver / Chicago: -10%; remote-US (other): -15%; remote-EU: -20%.

Equity bands (initial grants for new hires; percentages of fully diluted shares)
L3: 0.05% - 0.10%
L4: 0.10% - 0.20%
L5: 0.20% - 0.40%
L6: 0.40% - 0.80%
L7: 0.80% - 1.50%

Bonus
All ICs are eligible for an annual cash bonus targeted at 10% of base salary at level expectation. Outperformance multipliers up to 1.5x; underperformance can result in $0 bonus.

This information is confidential. Inappropriate disclosure may result in disciplinary action.
""",

    # 11. Layoff / RIF plan
    """INTERNAL — REDUCTION IN FORCE PLAN (HR + LEGAL EYES ONLY)

Effective date: November 4, 2024
Approval: Approved by Board on October 14, 2024 (Resolution 2024-11)

Scope
Approximately 87 positions company-wide, representing approximately 14% of current headcount. The reduction is concentrated in the following functions:

- Sales (52 positions): all of EMEA mid-market sales (28), portions of NA SMB sales (20), all of EMEA SDR team (4)
- Marketing (12 positions): demand gen team consolidation
- Engineering (15 positions): primarily Infrastructure and Data Platform reorganization
- G&A (8 positions): scattered across Finance, IT, Workplace

Selection criteria
- Performance: not a primary factor; this is a structural action
- Role redundancy following the platform reorganization announced internally on October 7
- Future need based on the FY2025 capacity plan
- Tenure: applied only as a tie-breaker per legal counsel guidance

Severance
- Less than 2 years tenure: 8 weeks base salary + 4 weeks COBRA + outplacement services
- 2-5 years tenure: 12 weeks base salary + 8 weeks COBRA + outplacement services
- 5+ years tenure: 16 weeks base salary + 12 weeks COBRA + outplacement services
- All severance contingent on signing a separation agreement and release of claims

Communications plan
- Monday Nov 4 8:00 AM PT: company-wide all-hands by CEO announcing the action
- 8:30 AM PT: impacted individuals contacted by direct manager + HR partner via Zoom; provided with information packet
- 9:00 AM PT: department-level meetings led by functional leaders
- 11:00 AM PT: CEO + leadership Slack AMA

Legal review
Outside counsel (Smith Anderson LLP) has reviewed for compliance with WARN Act, Title VII / ADEA disparate-impact analysis, and applicable state laws. No issues identified.

Confidentiality of this document is critical. Unauthorized disclosure may compromise the action.
""",

    # 12. Trade-secret recipe / formula
    """PROPRIETARY FORMULATION — DOCUMENT 4-A
Owner: Process Engineering, Coatings Division
Classification: Trade Secret
Authorized readers: Process Engineering team leads only

Formulation: HC-220 hydrophobic coating, Revision 7
Date of revision: March 2024

Components by weight percent
- Base polymer (proprietary fluoropolymer blend, Vendor F22): 41.2%
- Solvent (specialty hydrocarbon mix, internal designation S-104): 28.4%
- Crosslinker A (modified isocyanate, in-house synthesized): 6.8%
- Additive package (UV stabilizer + flow modifier + adhesion promoter, internal mix M-3): 4.6%
- Pigment dispersion (variable by color, see Appendix C — colorant section): 8.0%
- Solvent (xylene, technical grade, Vendor G12): 11.0%

Critical process parameters
- Mixing temperature: 38–42 °C maintained continuously throughout addition
- Order of addition: solvent first, then pigment, then base polymer, then additive package, finally crosslinker (this order is essential to prevent premature gelation)
- Total mixing time: 47–53 minutes at 220 RPM in shear-mixing vessel
- Final viscosity target: 1,750–2,050 cP at 25 °C

Application
- Substrate preparation: alkaline degreasing per spec SOP-44 followed by argon plasma activation (RIE chamber, 30 seconds, 80W)
- Application method: HVLP spray, 2.0 bar atomization pressure, 30 cm distance
- Cure: 4 hours at 65 °C in nitrogen atmosphere

CRITICAL: This formulation is the basis of the company's coating differentiation and represents approximately $14M of cumulative R&D investment. Disclosure outside the authorized list may constitute material misappropriation of trade secrets.
""",

    # 13. Internal SWOT analysis
    """INTERNAL STRATEGIC ANALYSIS — Q4 2024 SWOT
Prepared for: Executive Leadership Team
Distribution: ELT + Board
Classification: Internal — Strategic

Strengths
- Product depth in our core vertical (B2B procurement) is unmatched by direct competitors. Our average customer uses 7 of 9 major capability areas, vs. 3-4 for typical competitor deployments.
- Customer NPS of 64 (industry benchmark: 38) and gross retention at 96%. The customer base is sticky.
- Engineering team has retained well — voluntary attrition under 8% TTM vs. industry ~15-22%.
- Cash position ($48M) gives us roughly 24 months of runway at current burn, providing strategic optionality.

Weaknesses
- Mid-market sales velocity has plateaued. We are signing larger deals but fewer of them, and our pipeline is becoming concentrated.
- We lack a viable self-serve onboarding motion. Every new customer requires multi-month implementation engagement.
- International expansion has been slower than planned. EMEA is the only region operating profitably; APAC has consumed cash for three consecutive years.
- Our public marketing presence is weak relative to competitors and to our actual product depth. This is partly a deliberate trade-off but is increasingly costly in inbound demand generation.

Opportunities
- A potential pull-back by Competitor X (rumored to be restructuring) would create an opening for displacement at mid-market. Our partner network has flagged 6-8 potential takeover accounts.
- Generative AI features in the product roadmap could meaningfully reduce implementation time and unlock a self-serve motion.
- The pending policy changes around supplier diversity reporting (US federal contractors) could drive a wave of new buyers in 2025.

Threats
- Competitor Y has been investing aggressively in our vertical with apparent free-tier pricing. If they continue, this will compress our mid-market margins.
- One of our key infrastructure suppliers (cloud database vendor) is increasing prices ~22% in 2025. We have no immediate alternative.
- Two of our top-10 customers are exploring vendor consolidation, which could put substantial revenue at risk.

Strategic implications: see accompanying recommendations memo.
""",

    # 14. Vendor evaluation matrix
    """INTERNAL VENDOR EVALUATION — Data Warehouse Modernization Project
Date: August 2024
Authors: Platform Engineering, Procurement
Distribution: Project Steering Committee only

Three vendors evaluated for the proposed data warehouse modernization, intended to replace our current legacy system over a 9-month implementation. Total contract value: estimated $4.8M-$6.2M over 5 years depending on usage and tier.

Vendor A (Snowflake)
- Technical capability: Excellent. Strong fit for our workload profile. Performance benchmarking under our query patterns showed best price/performance for analytical queries.
- Pricing: At the higher end. List pricing approximately 22% above competitive bids; discounting potential identified at 12-18%.
- Implementation: Established partner network; estimated 6-month implementation timeline.
- Reference checks: Three references contacted; all positive. One flagged operational complexity of cost monitoring as a concern.
- Risk: Low to medium. Mature product, well-understood operational profile.
- Score: 8.2/10

Vendor B (Databricks)
- Technical capability: Strong, especially for ML/Lakehouse use cases that overlap our roadmap. Less mature for pure SQL analytics.
- Pricing: Mid-range. Approximately 14% lower than Vendor A at list.
- Implementation: 8-month timeline; fewer experienced implementation partners in our region.
- Reference checks: Two of three references positive; one flagged unexpected total cost of ownership.
- Risk: Medium. Roadmap dependency on ML platform decisions we haven't yet made.
- Score: 7.4/10

Vendor C (BigQuery)
- Technical capability: Excellent for our query patterns. Tight integration with our existing GCP infrastructure.
- Pricing: Lowest list pricing of the three vendors. Approximately 28% below Vendor A.
- Implementation: 5-month timeline; lower complexity given existing GCP footprint.
- Reference checks: Three references contacted; all positive. One noted limited support for certain niche analytical functions.
- Risk: Medium. Vendor concentration: deepens our existing GCP dependence.
- Score: 7.9/10

Recommendation
The team recommends Vendor C, weighting cost and implementation timeline. Vendor A is a defensible alternative if the Steering Committee weights vendor diversification. Final decision needed by August 30 to maintain target Q1 2025 implementation start.
""",

    # 15. Confidential customer churn analysis
    """INTERNAL ANALYSIS — Customer Churn Investigation, Q3 2024

Distribution: GTM Leadership + ELT
Purpose: Diagnose the elevated churn we observed in Q3 (12.4% gross churn vs. trailing 18-month average of 7.1%) and frame a Q4 response.

Summary
The Q3 churn spike is concentrated in a specific cohort: mid-market customers (ARR $40K–$120K) acquired between Q4 2022 and Q1 2023, in the U.S. region, who use predominantly the platform's older "v3" capability set. Of the 38 customers that churned in Q3, 27 (71%) fit this cohort. The remaining 11 are distributed across cohorts in a pattern consistent with our baseline.

What's driving the cohort churn
1. Onboarding-era cohort effect. The Q4 2022 / Q1 2023 acquisition cohort was onboarded during a period when our customer success function was overloaded. Many of these customers never reached our typical depth-of-usage milestones within their first 6 months.
2. Feature gap. v3 lacks the workflow automation features we shipped in v4 (released Q2 2023). Several churn-exit interviews surfaced this as a "we couldn't do X" concern even though X is available — they didn't know.
3. Competitive pressure. Competitor X has been actively targeting accounts in this ARR band with a directly competitive offering at lower price. Five of the 27 churned customers cited competitive switch as the primary reason.

What it is NOT
- Not a product quality issue overall. Our v4 cohorts retain at 96-97%.
- Not a pricing issue overall. Our enterprise cohort renewed at 102% NDR in Q3.
- Not driven by any specific industry vertical.

Recommendation
Targeted "save campaign" for the at-risk cohort. Approximately 142 remaining accounts fit the same cohort profile. We propose:
- Dedicated customer success outreach with a 14-day implementation review
- Free v4 migration with white-glove support
- Up to 15% renewal discount authority where competitively threatened

Estimated cost of save campaign: $480K-$620K (CS time + discount give-back). Estimated ARR-at-risk: $14.2M. Expected save rate: 60-75% based on industry comp.
""",

    # 16. Pre-IPO S-1 draft risk factors excerpt
    """DRAFT S-1 EXCERPT — RISK FACTORS SECTION
This is a working draft. Not for distribution outside the working group.

Risks Related to Our Business

We have a history of net losses and may not achieve or maintain profitability in the future.

We have incurred net losses in each year since our incorporation in 2014. For the fiscal years ended December 31, 2023, 2022, and 2021, we had net losses of $42.1 million, $58.7 million, and $71.3 million, respectively. As of June 30, 2024, we had an accumulated deficit of $284.6 million. We expect our operating expenses to continue to grow as we invest in product development, sales and marketing, and international expansion. As a result, we may continue to experience net losses for the foreseeable future, and we cannot assure you that we will achieve or maintain profitability.

A significant portion of our revenue is derived from a limited number of customers.

For the fiscal year ended December 31, 2023, our top ten customers accounted for approximately 37% of our revenue, and our top customer accounted for approximately 9.2% of our revenue. The loss of any of these customers, or a material reduction in their use of our platform, would have a material adverse effect on our business and financial results.

We depend on key personnel and may not be able to retain or recruit them.

Our success depends in part on the continued service of our senior management team and other key employees. The loss of any of our co-founders or members of our senior management team could harm our ability to execute on our business strategy and could damage our reputation with customers, partners, and investors.

We are subject to extensive legal and regulatory compliance obligations relating to data protection and privacy.

We process significant volumes of personal data on behalf of our customers. We are subject to numerous laws and regulations including the General Data Protection Regulation (GDPR) in the European Union, the California Consumer Privacy Act (CCPA), and similar laws in other jurisdictions. Failure to comply with these obligations could result in regulatory penalties, customer claims, and reputational harm.

WORKING DRAFT — REVIEW WITH COUNSEL BEFORE ANY EXTERNAL SHARING
""",

    # 17. M&A target due-diligence memo
    """CONFIDENTIAL DUE DILIGENCE MEMORANDUM

Target: Project Atlas (internal codename for "Pinemark Software, Inc.")
Prepared by: Corporate Development
Distribution: Acquirer ELT, Outside Counsel (Wilson Sonsini), Outside Banker (Foreman & Goldman)

Executive summary
After four weeks of access to the target's data room and three management presentations, we recommend proceeding to a binding offer at the upper end of our prior LOI range, contingent on the items listed under "Outstanding Diligence Items" below.

Business overview
Target is a 92-person company headquartered in Pittsburgh, with engineering offices in Munich. Revenue for the trailing twelve months ended August 31, 2024 was $34.2 million (vs. $24.8 million for prior TTM, +38%). Gross margin TTM is 71%. Customer base of 184 accounts, with 87% annual gross retention and 118% net revenue retention.

Strategic rationale
Target's product addresses an adjacent use case that our largest customers have repeatedly requested. We estimate annual cross-sell potential into our existing base of $40-60M ARR within 24 months of close, assuming successful integration.

Financial assessment
Revenue quality is strong. We verified 92% of TTM revenue through customer contracts and bank statements. The remaining 8% relates to recently-signed contracts where revenue recognition is dependent on customer milestones; we estimate $1.4M of recognized revenue is at modest risk if those milestones slip.

Working capital and balance sheet appear clean. No material undisclosed liabilities surfaced during diligence. Tax position: target has $14M of NOLs which we expect to retain post-acquisition.

Risks identified
1. Key person risk: target's VP Engineering is the technical architect of the core platform. He has informally indicated he intends to leave 12-18 months post-close. Retention package required.
2. Customer concentration: top 3 customers = 41% of revenue. We have spoken with 2 of the 3; both indicated they are likely to renew at the next cycle.
3. Litigation: one ongoing employment-related matter with a former employee; estimated exposure $200K-$400K. Acceptable.

Outstanding diligence items
- Final auditor verification of FY2023 financials (in progress, expected complete by Oct 18)
- Patent assignment confirmations for two co-founder patents (in progress)
- Final review of vendor contract change-of-control provisions

Recommendation: proceed to binding offer at $340M cash, subject to confirmation of outstanding items.
""",

    # 18. Internal red-team report (pre-remediation)
    """INTERNAL SECURITY ASSESSMENT — Red Team Engagement Report
Engagement: 2024-Q3 Pre-Release Assessment of "Platform 4" Release Candidate
Date: September 2024
Distribution: Engineering Leadership, Security Engineering, CTO

This report describes findings from a 6-week red team engagement against the Platform 4 release candidate. Eleven distinct findings are documented; five are rated High severity and require remediation before general availability.

CRITICAL: This document describes unpatched vulnerabilities. Distribution is strictly limited to the parties listed above. No portion of this document may be shared externally or via insecure channels.

Findings summary
- High severity: 5
- Medium severity: 3
- Low severity: 3

H1. Authentication bypass via header manipulation in /admin/* endpoints
The /admin/* surface relies on a header value (X-Internal-Caller) to gate access. We discovered that this header is not stripped by our reverse proxy when received from external clients, allowing trivial bypass of admin authentication. Affected endpoints include user management, billing administration, and feature-flag management.

Recommended remediation: enforce header stripping at the proxy layer; add server-side check that the auth-bypass header was set by an internal load balancer; rotate all admin credentials.

H2. SQL injection in /api/v2/reports/custom-query endpoint
The custom-query endpoint accepts a `filters` parameter that is concatenated into a Postgres query without parameterization. We demonstrated extraction of arbitrary table contents including the users table.

Recommended remediation: use parameterized queries throughout the reporting subsystem; add allow-list of permitted filter fields.

H3. Stored XSS in customer notes rendering
Customer notes are rendered in admin views without HTML escaping. We demonstrated execution of attacker-controlled JavaScript in admin user sessions when viewing the notes of a malicious customer record.

H4. Authorization gap in /api/v2/billing/charges
H5. Insecure direct object reference in /api/v2/exports

(Remaining findings detailed in appendix.)

Disclosure status: NOT YET PUBLICLY DISCLOSED. No customers have been informed. Remediation deadline: October 14, 2024 (pre-GA freeze).
""",

    # 19. Compliance audit report with control gaps
    """INTERNAL: SOC 2 Type II Audit — Pre-Audit Self-Assessment

Period covered: October 2023 — September 2024
Prepared by: Internal Audit and Compliance Engineering
Distribution: Audit Committee, ELT, External Auditor (Tier One Assurance LLP) after review

Overall assessment: We believe we will pass our SOC 2 Type II audit, but with two qualified opinions and several management letter comments that require disclosure to the Audit Committee. Below is the summary of control gaps identified.

Control category: Logical access controls (CC6.1)
Gap: We identified 14 instances during the audit period where access provisioning to production systems did not follow our documented approval workflow. In 11 of these instances the access was retroactively approved; in 3 cases the access was granted in error and revoked within 5 business days.

Significance: Likely qualified opinion on logical access controls.

Remediation: We have implemented a stricter approval gate in our IAM system as of August 2024. We expect this gap to be closed for the next audit period.

Control category: Change management (CC8.1)
Gap: We identified 6 production changes during the audit period that were deployed without the required two-reviewer approval. All 6 were emergency hotfixes documented under our exception process, but in 4 cases the after-the-fact review did not occur within the required 5-day window.

Significance: Management letter comment, not expected to be a qualified opinion.

Remediation: Updated emergency response runbook to require post-incident review tracking; deployed dashboard for compliance team monitoring.

Control category: System monitoring (CC7.2)
Gap: A 36-hour gap in security monitoring logs occurred on June 14-15, 2024 due to a logging pipeline failure. Investigation completed July 7, 2024 confirmed no exploitable activity occurred during the gap, but the gap itself is a control failure.

Significance: Likely qualified opinion on monitoring controls.

Other items: 14 control areas have informational management letter comments; details in appendix B.

The Audit Committee should be briefed on the qualified-opinion items at the next scheduled meeting. Decisions about how to communicate the qualified opinion to customers should be made in advance of the auditor's report issuance, currently expected mid-November 2024.
""",

    # 20. GDPR DPIA
    """DATA PROTECTION IMPACT ASSESSMENT (DPIA)
Subject: New Feature — "Smart Insights" (working title)
Status: Draft v0.3, for review by DPO and Engineering Leadership
Distribution: DPO, Engineering Leadership, Product, Outside Counsel (Privacy)

Overview
The proposed "Smart Insights" feature would analyze customer-uploaded transaction data to surface anomaly patterns. The system would process personal data of the customers' end-users (employees, vendors, contractors). Because of the nature of this processing — automated analysis of personal data that could result in significant decisions for data subjects — a DPIA is required under GDPR Article 35.

Description of processing
- Categories of personal data: full names, email addresses, employee IDs, transaction amounts, transaction descriptions (free text, may contain personal information), timestamps, IP addresses
- Special categories: not intended, but free-text descriptions could contain incidental health or other sensitive information
- Lawful basis: legitimate interest of the customer (the controller); we are the processor
- Data subjects: employees, contractors, and vendors of customer organizations
- Retention: 24 months from upload; configurable downward per customer

Necessity and proportionality assessment
The processing is proportionate to the purpose. The data minimization requirement is met by allowing customers to redact sensitive fields before upload (feature is included in the launch scope). Pseudonymization is technically infeasible for the analytical use case because anomaly correlation depends on entity stability.

Risks identified
1. Re-identification of individuals from analytical outputs. Mitigated by: outputs shown only to authorized customer admin users; rate-limiting on report extraction; differential-privacy noise on the entity-level aggregations.
2. Unintended profiling. Mitigated by: feature scope explicitly excludes any individual scoring or ranking outputs; only aggregate anomaly counts surfaced.
3. Data breach. Mitigated by: existing security controls (SOC 2 + ISO 27001); encryption at rest; access logging.

Outstanding decisions
- Whether to enable the feature by default or require explicit customer opt-in. DPO recommendation: explicit opt-in. Product preference: default-on. Decision required by October 30.
- Whether to expose the feature to EEA customers in the initial release.

DPO sign-off pending.
""",

    # 21. Litigation hold notice
    """LITIGATION HOLD NOTICE — CONFIDENTIAL AND PRIVILEGED

To: All Employees of Sterling Industries, Inc.
From: Office of the General Counsel
Date: June 24, 2024
Re: Preservation of Documents — Threshold Dispute

This memorandum serves as a formal litigation hold notice. You are required to read and follow the instructions below.

Background
On June 18, 2024, Sterling Industries received a demand letter from Threshold Manufacturing, LLC, alleging breach of contract under the Master Supply Agreement dated March 4, 2021, and asserting damages of approximately $14 million. Litigation may follow. As a result, we must preserve all documents and communications that may be relevant to this matter.

What you must do
1. PRESERVE all documents, emails, instant messages, notes, drafts, calendar entries, voicemails, and any other materials in any format that relate to:
   - The Master Supply Agreement with Threshold Manufacturing
   - Any communications with Threshold Manufacturing or its representatives
   - The Q1 2024 component delivery dispute
   - Any internal discussions regarding the relationship with Threshold Manufacturing

2. SUSPEND any normal document destruction or deletion practices (including auto-deletion of emails, archival deletion, etc.) with respect to the items listed above.

3. DO NOT discuss this matter with anyone outside the Office of the General Counsel.

4. If you become aware of additional documents or sources of information that may be relevant, NOTIFY the General Counsel's office immediately.

Scope of preservation
The duty to preserve continues until you are notified in writing by this office that the hold is lifted. Failure to comply may result in adverse legal consequences for the company and disciplinary action for individuals.

This notice is attorney-client privileged. Do not forward or share outside Sterling Industries.

Questions: contact General Counsel Marcus Achtenberg at (415) 555-0100 or via email.
""",

    # 22. Settlement agreement draft
    """SETTLEMENT AGREEMENT AND MUTUAL RELEASE — DRAFT v3 (PRIVILEGED, FOR COUNSEL REVIEW)

This Settlement Agreement (this "Agreement") is entered into on this _____ day of October, 2024, by and between Greenbridge Capital Management LLC ("Greenbridge") and Atlas Holdings, Inc. ("Atlas"), each a "Party" and together the "Parties."

WHEREAS, on March 22, 2024, Greenbridge filed a complaint in the Court of Chancery of the State of Delaware (the "Litigation") alleging breach of the Joint Venture Agreement dated August 17, 2021;

WHEREAS, the Parties wish to resolve the Litigation and all related disputes without admission of liability;

NOW, THEREFORE, the Parties agree:

1. SETTLEMENT PAYMENT. Atlas shall pay Greenbridge the sum of [$ ________] (the "Settlement Amount") within 14 days of the Effective Date. The Settlement Amount represents full and final compensation for all claims released hereunder.

2. RELEASES. Effective upon receipt of the Settlement Amount, each Party releases the other from all claims, demands, causes of action, and liabilities of every nature whatsoever arising from or related to the Joint Venture Agreement, including but not limited to those asserted in the Litigation.

3. DISMISSAL. Within 5 business days following receipt of the Settlement Amount, Greenbridge shall file a Stipulation of Dismissal With Prejudice of the Litigation.

4. CONFIDENTIALITY. The terms of this Agreement, including the Settlement Amount, are confidential. Neither Party shall disclose the terms except as required by law, regulation, or order of court, or to the Party's accountants, attorneys, or other professional advisors bound by similar confidentiality obligations.

5. NO ADMISSION. Nothing in this Agreement constitutes an admission of liability or wrongdoing by either Party.

6. GOVERNING LAW. This Agreement shall be governed by the laws of the State of Delaware.

[REMAINDER OF AGREEMENT TO BE COMPLETED — including signature blocks, payment instructions, and routine boilerplate]

INTERNAL NOTE: The Settlement Amount remains TBD. Audit Committee approval required for any amount exceeding $5M.
""",

    # 23. Employment contract draft (executive)
    """EXECUTIVE EMPLOYMENT AGREEMENT — DRAFT FOR FINAL REVIEW

This Employment Agreement (this "Agreement") is entered into as of November 1, 2024, by and between Riverstone Technologies, Inc., a Delaware corporation (the "Company"), and Adwoa Mensah-Kennedy ("Executive").

1. POSITION AND DUTIES. Executive shall serve as Chief Operating Officer of the Company, reporting to the Chief Executive Officer. Executive shall perform such duties and responsibilities as are customary for an executive in such position and as the CEO or Board may reasonably assign from time to time.

2. EFFECTIVE DATE; AT-WILL EMPLOYMENT. Executive's employment shall commence on November 18, 2024 (the "Effective Date") and shall continue until terminated as provided herein. Executive's employment is at-will.

3. COMPENSATION
3.1 Base Salary. Annual base salary of $385,000, payable in accordance with the Company's standard payroll practices.
3.2 Signing Bonus. A one-time signing bonus of $75,000, payable within 30 days of the Effective Date. If Executive voluntarily terminates employment within 12 months of the Effective Date, Executive shall repay the signing bonus on a pro-rated basis.
3.3 Annual Performance Bonus. Eligible for a target annual cash bonus equal to 50% of base salary, with maximum payout of 75% of base salary. Bonus payouts are subject to achievement of Company and individual performance goals as determined annually by the Board.
3.4 Equity. Subject to Board approval, Executive shall be granted a stock option to purchase 145,000 shares of Common Stock at a per-share exercise price equal to the fair market value on the date of grant. The option shall vest over four years with a one-year cliff (25% on first anniversary; remaining 75% in equal monthly installments thereafter).

4. RESTRICTIVE COVENANTS
4.1 Non-Solicitation. For a period of 12 months following any termination of employment, Executive shall not solicit any then-current employee of the Company to leave their employment.
4.2 Non-Competition. The Company has not included a non-compete clause given the regulatory environment in California, but reserves the right to enforce trade-secret protection.
4.3 Confidentiality. Executive shall maintain the confidentiality of the Company's confidential information indefinitely. Detailed obligations are set forth in the Company's standard Confidentiality and Invention Assignment Agreement, attached as Exhibit A.

5. SEVERANCE
5.1 Termination Without Cause. If the Company terminates Executive without Cause, Executive shall be entitled to: (a) 9 months of base salary continuation; (b) prorated target annual bonus; (c) acceleration of 12 months of unvested equity; (d) 9 months of COBRA premium reimbursement.

INTERNAL: This is a senior executive offer. Total compensation values reflect Comp Committee approval on October 14, 2024.
""",

    # 24. Severance agreement template
    """SEPARATION AGREEMENT AND GENERAL RELEASE OF CLAIMS

This Separation Agreement is entered into between [Name] ("Employee") and [Company Name] (the "Company") in connection with the termination of Employee's employment effective [Separation Date].

1. SEPARATION DATE; FINAL PAY. Employee's last day of employment is [Separation Date]. Within applicable legal deadlines, the Company shall pay Employee all earned but unpaid base salary, accrued and unused vacation per Company policy, and reimburse outstanding business expenses submitted in accordance with Company policy.

2. SEVERANCE CONSIDERATION. Subject to Employee's execution and non-revocation of this Agreement, the Company shall provide:
(a) A lump-sum severance payment equal to [____] weeks of Employee's base salary, less applicable withholdings, paid within 30 days following the Effective Date;
(b) Company-paid COBRA premiums for a period of [____] months following the Separation Date or until Employee becomes eligible for group health coverage from a new employer, whichever is earlier;
(c) Outplacement services through [Provider] for up to 90 days following the Separation Date.

3. RELEASE OF CLAIMS. Employee, on behalf of Employee and Employee's heirs, successors, and assigns, releases and forever discharges the Company and its officers, directors, employees, and affiliates from all claims, causes of action, and liabilities of any kind whatsoever arising from or related to Employee's employment with the Company or the termination thereof, including but not limited to claims under federal, state, and local employment laws, common-law claims, and contract claims.

4. EXCLUDED CLAIMS. The release in Section 3 does not extend to: (a) claims that cannot be released as a matter of law; (b) claims to vested benefits under any qualified retirement plan; (c) claims for unemployment insurance or workers' compensation; (d) the right to file a charge with a government agency, though Employee waives the right to any individual recovery from any such proceeding.

5. NON-DISPARAGEMENT. Each Party agrees not to disparage the other, either in writing or orally, to any third party.

6. CONFIDENTIALITY. The terms of this Agreement are confidential. Employee may disclose them only to immediate family members, legal or financial advisors, or as required by law.

7. REVOCATION PERIOD. Employee has 21 days to review this Agreement and 7 days following execution to revoke acceptance.

[Signature blocks and Exhibit A regarding continued obligations under the Confidentiality and Invention Assignment Agreement are included in the final version.]
""",

    # 25. Internal market expansion plan
    """INTERNAL — INTERNATIONAL MARKET EXPANSION PLAN, FY2025

Distribution: ELT, Board (informational), International Working Group
Classification: Confidential — Internal Strategic

Background and decision request
Following two years of operating exclusively in North America, we are recommending expansion into Europe in FY2025, beginning with the United Kingdom and Germany. This document outlines the plan, expected capital required, and proposed phasing. We are requesting Board endorsement to proceed.

Market selection rationale
Of the eight markets evaluated, the UK and Germany scored highest on (a) total addressable market in our category; (b) competitive openness; (c) cultural and operational compatibility with our existing GTM motion; (d) regulatory clarity. France and Netherlands ranked next and would be candidates for FY2026.

Phased rollout
Q1 2025: Establish UK entity; hire Country Manager UK + 2 sales hires; soft launch with existing customer-driven expansion accounts (we have 14 NA customers with UK subsidiaries that have requested local entity).

Q2 2025: Open Frankfurt office; hire Country Manager Germany + 2 sales hires + 1 customer success lead. Begin direct outbound to mid-market accounts.

Q3 2025: Scale UK team to 8; expand marketing investment to support inbound demand.

Q4 2025: Scale Germany team to 6; assess France entry for FY2026.

Capital required
FY2025 incremental investment: approximately $7.8M, broken down as:
- Personnel costs (loaded): $5.2M
- Office and operational setup: $0.6M
- Marketing and demand generation: $1.4M
- Legal and tax setup (incorporation, transfer pricing, data localization): $0.6M

Expected return
We forecast Year-1 international ARR of $3.8M (UK + Germany combined), against trailing operating costs of approximately $7.8M, resulting in approximately -$4.0M international contribution margin in Year 1. Forecasted breakeven at Q4 2026.

Risks
- Data localization requirements may require infrastructure investment beyond plan
- Talent acquisition timing in target markets is highly variable
- A competitor's European launch (publicly hinted at by Competitor Y) could compress our window

Board recommendation: endorse proceed; approve initial capital allocation. Detailed quarterly reviews at scheduled Board meetings.
""",

    # 26. Pricing strategy memo
    """INTERNAL — PRICING STRATEGY PROPOSAL, FY2025

Distribution: Pricing Committee + ELT
Decision required: October 30, 2024

Background
We have not adjusted our list pricing since Q3 2022. Over the past 24 months, our product depth has expanded materially (4 major capability additions), our gross margin has improved, and competitive pricing has crept upward in our category. Our customer acquisition costs have also risen ~22% over the same period.

We are proposing a tiered pricing change effective January 15, 2025.

Proposed changes

Existing customers (renewing or upselling):
- Maintain existing pricing through end of current contract term
- At renewal: 8-12% list price increase, with grandfathered discount of 4-6% off list to maintain effective price increase of 3-8%
- Material expansion (>20% new capacity / seats) treated as new business pricing

New customers:
- Mid-Market tier: list price increase of 18% on platform fee, no change on per-seat pricing
- Enterprise tier: list price increase of 12%, with bundling adjustments
- New "Enterprise Plus" tier launching at +35% above current Enterprise list, including premium support and dedicated CSM

Competitive analysis
Of the 5 named competitors we track, 3 have raised prices in 2024 (range: 6-19% list price increases). Our prices remain below the median for our peer set at the new proposed levels.

Risk analysis
- Customer churn risk at renewal: estimated 1-3% additional gross churn during 2025
- Sales cycle elongation: estimated +3-5 days at mid-market, +7-10 days at enterprise
- Win rate compression in competitive deals: estimated -3pp on contested deals, -1pp overall

Expected revenue impact
FY2025 incremental ARR from pricing: $14.8M (assuming above churn and win-rate impact)
FY2026 full-year run-rate impact: $24.6M

Decision
We recommend approval and implementation as outlined. Specific list price adjustments per SKU are detailed in Appendix B (separate document, secured distribution).

Pricing Committee approval required to proceed. Subsequent legal and SE review needed for contract template updates.
""",

    # 27. Internal roadmap doc
    """INTERNAL ROADMAP — FY2025 AND H1 2026

Distribution: All Engineering, Product, Design; ELT
NOT for external sharing or customer-facing materials

Q1 2025 — "Foundations"
Theme: paying down infrastructure debt to unlock the velocity we'll need for the rest of the year. No major customer-facing feature releases planned.

Key initiatives:
- Migrate billing service off the monolith into a dedicated microservice (Project Caspian) — 8 engineers, 12 weeks
- Replace the legacy reporting database with a columnar store (Project Lighthouse) — 5 engineers, 14 weeks
- Implement the new authentication framework (Project Atlas) — 3 engineers, 8 weeks

Q2 2025 — "Customer Insights"
Theme: Smart Insights feature general availability, plus admin productivity improvements.

Key releases:
- Smart Insights feature GA (the workspace anomaly detection feature)
- Bulk operations on admin tooling
- Improved audit log search and export

Q3 2025 — "Self-Serve"
Theme: launch the self-serve tier, our first attempt at PLG motion.

Key releases:
- Self-serve signup and onboarding
- Tiered pricing UI
- In-product upgrade and downgrade flows
- New "Free" tier (limited seats and features)

Q4 2025 — "Enterprise"
Theme: features and capabilities targeting our enterprise tier expansion.

Key releases:
- SSO with SAML 2.0
- SCIM provisioning
- IP allowlisting and audit logging enhancements
- Customer-managed encryption keys (BYOK)

H1 2026 — "International + AI"
Theme: pair the international expansion with the next wave of AI-assisted features.

Strategic focus areas:
- EU residency option for hosted instances
- AI-assisted workflow creation (research project in 2025; GA target H2 2026)
- Native German and French UI localization
- Mobile companion app (beta)

Confidentiality note: Items in this document represent management's current planning. Plans can and will change. Do not commit to customers based on this roadmap.
""",

    # 28. Patent application draft
    """U.S. PATENT APPLICATION — DRAFT (PRE-FILING REVIEW)
TITLE: SYSTEM AND METHOD FOR ADAPTIVE ROUTING OF QUERIES BETWEEN LOCAL AND CLOUD INFERENCE ENGINES BASED ON CONFIDENCE METRICS

INVENTORS: [Inventor 1]; [Inventor 2]; [Inventor 3]
ASSIGNEE: [Company Name]
ATTORNEY DOCKET: P-2024-0017

FIELD OF THE INVENTION
The present invention relates generally to distributed artificial intelligence systems, and more particularly to systems and methods for dynamically routing inference requests between on-device machine learning models and cloud-hosted machine learning models based on real-time evaluation of inference confidence and computational cost.

BACKGROUND OF THE INVENTION
Current approaches to mobile and edge artificial intelligence applications generally adopt one of two strategies: (a) running all inference on the local device, which incurs no network cost but is limited by the capacity of the device; or (b) sending all inference requests to a cloud-hosted model, which provides high capability but introduces latency and recurring per-query cost. Neither approach optimally serves the broad range of query difficulty encountered in real-world applications.

SUMMARY OF THE INVENTION
The present invention provides a method and system for routing inference requests across a local model and a cloud model in a manner that, for each request, evaluates the local model's confidence in its prediction and routes only those requests below a confidence threshold to the cloud model. In a preferred embodiment, the confidence threshold is dynamically adjusted based on observed quality of the local model's predictions over a sliding window of recent requests.

DETAILED DESCRIPTION
[Detailed description with reference to drawings; ~30 pages in the full draft]

CLAIMS
1. A method for inference query routing, comprising:
  receiving an inference request at a client device;
  executing a local machine learning model on the client device to produce a candidate inference result and an associated confidence value;
  comparing the confidence value to a dynamic threshold;
  if the confidence value exceeds the threshold, returning the candidate inference result as the final result; otherwise, transmitting the inference request to a cloud-hosted model and returning the cloud model's result as the final result.

2. The method of claim 1, wherein the dynamic threshold is computed based on a sliding window of recent predictions, taking into account the divergence between local-model and cloud-model results over that window.

[Claims 3-21 omitted from this excerpt]

DO NOT FILE OR DISCLOSE UNTIL: (a) inventor declarations executed; (b) IP committee approval received; (c) prior-art search complete.
""",

    # 29. Patent license negotiation memo
    """INTERNAL — PATENT LICENSE NEGOTIATION MEMO
To: ELT + General Counsel
From: VP Engineering + Director of IP
Date: September 10, 2024
Re: Proposed cross-license with Nimbus Technologies

We have been in informal discussions with Nimbus Technologies for the past six weeks regarding a potential cross-license of our respective patent portfolios in the workflow-automation space. This memo summarizes where we stand and the terms we are prepared to offer.

Background
- Our portfolio: 14 issued U.S. patents and 22 pending applications in the workflow-automation and related-process-orchestration areas
- Nimbus portfolio: 8 issued patents and 11 pending applications, with stronger coverage in the orchestration scheduling subdomain
- Neither party has asserted patents against the other; the cross-license is intended to provide defensive certainty

Proposed terms (our offer)
1. Five-year term, with automatic renewal for additional 3-year periods unless either party terminates
2. Each party grants the other a fully paid-up, royalty-free, non-exclusive license to its issued patents in the workflow-automation space
3. Future filings of either party in the licensed field are included automatically
4. License does not extend to patents acquired through future M&A activity by either party
5. Customary defensive carve-outs: license terminates with respect to a party that initiates patent litigation against the other in a different field

Risks and considerations
- We give up the option to assert our portfolio against Nimbus in the licensed field. We assess this as low value because we have no current intention to assert.
- We accept Nimbus's freedom to operate against our patents. Low risk given they have not been an infringement target.
- The acquired-patent carve-out is important: if either party is acquired, the acquirer should not get a free pass.

Recommendation
Proceed with the cross-license. The defensive value to us substantially exceeds the offensive value we forgo. If Nimbus pushes back on the acquired-patent carve-out, we are prepared to compromise on a 12-month sunset rather than full exclusion.

Estimated legal cost to finalize: $40K-$60K. Decision needed at the September 18 ELT meeting.
""",

    # 30. Internal investor update memo
    """QUARTERLY INVESTOR UPDATE — Q3 2024

To: Limited Partners and Series B/C/D shareholders
From: CEO
Date: October 22, 2024

Confidential. Subject to customary investor confidentiality obligations.

Headline metrics
- Q3 revenue: $28.6M, +34% YoY (vs. plan $26.0M)
- Q3 operating cash flow: +$2.4M (positive third consecutive quarter)
- Q3 new ARR added: $14.2M (vs. plan $11.8M)
- Net Revenue Retention TTM: 121% (vs. 115% at end of Q2)
- Ending cash: $51.8M (vs. $49.4M at end of Q2)

Business highlights
Q3 was our strongest quarter in company history. New customer wins outpaced plan in every region except APAC, where we have decided to defer additional GTM investment until H2 2025. Expansion bookings within our existing customer base were particularly strong, with two seven-figure expansions completed in September.

Product progress
- We shipped the Smart Insights closed beta to 14 design partners in mid-September. Early feedback is positive, with usage frequency materially above our pre-launch model
- The platform reliability work I described in the prior letter is largely complete; we ended Q3 at 99.96% availability vs. our 99.95% target

Strategic
- We engaged Foreman & Goldman as advisors regarding the inbound acquisition interest first disclosed in our Q2 letter. They will help us evaluate strategic alternatives, including the option of remaining independent and pursuing an IPO in 2026
- We have begun preliminary preparation for an IPO, including bringing on a new CFO with public-company experience (start date November 15)

Asks
- Continued patience as we evaluate strategic alternatives; we will brief shareholders before any binding decision
- Introductions to public-company audit committee chairs who might join our Board over the next 12 months

Looking ahead, our Q4 plan calls for $32M revenue and a positive $3M operating cash flow. We feel well-positioned to deliver on those targets.

Confidential and proprietary. Please do not share outside your firm.
""",

    # 31. Cap table snapshot
    """INTERNAL CAP TABLE SNAPSHOT
As of: September 30, 2024
Distribution: CFO, Founders, Board, designated outside counsel
Confidentiality: This document contains personal financial information of equity holders. Restricted distribution.

Common Stock
Founder 1 (Anika Volkova): 4,500,000 shares (15.0%)
Founder 2 (Marcus Otieno): 4,500,000 shares (15.0%)
Founder 3 (Priyanka Sundaresan): 3,000,000 shares (10.0%)
Employees (vested): 2,840,000 shares (9.5%)
Employees (unvested): 1,460,000 shares (4.9%)
Reserved for future option pool: 2,200,000 shares (7.3%)

Preferred Stock
Series Seed (lead: Foreman Partners): 1,800,000 shares (6.0%)
Series A (lead: Lattice Capital): 4,200,000 shares (14.0%)
Series B (lead: Riverstone Ventures): 3,600,000 shares (12.0%)
Series C (lead: Brookmoor Growth Equity): 1,800,000 shares (6.0%)

Total outstanding: 30,000,000 shares (100%)

Notable terms
Series Seed: 1x non-participating preference. Conversion price $1.111/share.
Series A: 1x non-participating preference. Conversion price $2.857/share.
Series B: 1x non-participating preference. Conversion price $8.333/share.
Series C: 1x non-participating preference. Conversion price $22.222/share. Dividend rate 8% non-cumulative.

Most-recent 409A valuation: $14.62 per common share (dated August 14, 2024)

Aggregate equity by holder (top 5)
1. Lattice Capital: $59.9M at common-share value
2. Founder 1 (Anika Volkova): $65.8M at common-share value
3. Founder 2 (Marcus Otieno): $65.8M at common-share value
4. Riverstone Ventures: $52.6M at common-share value
5. Founder 3 (Priyanka Sundaresan): $43.9M at common-share value

This data should be treated as personal financial information of the listed individuals. Internal distribution only.
""",

    # 32. 409A valuation report excerpt
    """409A VALUATION REPORT — EXECUTIVE SUMMARY EXCERPT

Company: Northwind Technologies, Inc.
Valuation Date: August 14, 2024
Prepared by: Anchorpoint Valuation Services LLC, an independent valuation firm

Section 1: Summary of Findings

We have estimated the Fair Market Value of the Common Stock of Northwind Technologies, Inc. as of August 14, 2024 to be $14.62 per share. This valuation is intended to support the Company's compliance with Section 409A of the Internal Revenue Code in connection with the granting of stock options to employees.

Section 2: Approach

We applied an income approach (discounted cash flow) and a market approach (guideline public companies and recent M&A transactions in the workflow automation sector). We allocated the resulting Enterprise Value to the Company's various classes of stock using an Option Pricing Model (OPM) approach, given the Company's complex capital structure with multiple preference rights and conversion features.

Section 3: Key Inputs and Assumptions

Revenue (TTM through July 2024): $96.4M
Revenue growth (forecast 5-year CAGR): 28%
Operating margin (forecast steady-state): 18%
Discount rate (WACC): 14.5%
Volatility input (OPM): 60% (based on peer group analysis)
Time to liquidity event: 2.5 years
Probability-weighted scenarios: IPO 45%, Acquisition 30%, Stay-Private 20%, Failure 5%

Section 4: Marketability Discount

We applied a discount for lack of marketability (DLOM) of 22.5%, based on the protective put approach and consideration of comparable closely-held companies.

Section 5: Valuation Concentration

The probability-weighted IPO scenario yields a per-common-share value of $17.84. The probability-weighted Acquisition scenario yields $13.21. After applying the marketability discount, the concluded value is $14.62 per common share, an increase of 18% from the prior valuation dated February 12, 2024 ($12.39).

Strict confidentiality. This report is prepared for the Company's internal use and submission to its tax advisors. It contains sensitive financial information not appropriate for general distribution.
""",

    # 33. Compensation committee meeting notes
    """COMPENSATION COMMITTEE MEETING — NOTES
Date: October 24, 2024
Present: J. Reyes (Chair), M. Goldberg, A. Brown-Patel
Also Present: CEO (for portion), CHRO, outside compensation consultant from Voltage Partners

CONFIDENTIAL — These notes will not be distributed beyond Committee members and outside counsel.

1. Executive base salary and bonus targets for FY2025

CHRO presented the analysis prepared by Voltage Partners benchmarking our executive compensation against the peer group of 14 comparable companies. Findings:
- CEO total cash compensation is at the 32nd percentile of peer group; trailing.
- CFO total cash compensation is at the 51st percentile.
- COO total cash compensation is at the 41st percentile.
- VP Engineering, VP Product, CMO: all in the 45-55th percentile range.

Discussion: The Committee discussed whether to address the CEO's below-market position. Consensus was that we should bring the CEO closer to median, recommending base salary increase from $425K to $480K effective January 1, 2025, with target annual bonus moving from 60% to 75% of base salary. Total target cash compensation moves from $680K to $840K, placing CEO at approximately the 48th percentile.

For other executives, the Committee recommends 4-7% base salary increases, calibrated to performance and market position.

2. Executive equity refresh grants

The Committee reviewed the proposed equity refresh grants for executives based on the FY2024 performance review process. Approximate grant values (at current 409A):
- CEO: $4.2M grant value (vest 4 years; 25% one-year cliff, monthly thereafter)
- CFO: $1.8M
- COO: $2.4M
- VP Engineering: $1.6M
- VP Product, CMO, VP Sales: $0.9M each

The Committee approved the equity refresh subject to Board ratification.

3. FY2025 bonus plan design

CHRO presented the proposed FY2025 bonus plan, structured around: revenue (50% weight), operating margin (30% weight), and customer NPS (20% weight). Bonus pool funds at 0% if revenue is below 85% of plan; pays at 100% target if all three metrics achieve plan; can pay up to 150% with outperformance on all three.

The Committee approved the plan design.

4. Closing

Next meeting: January 2025 for FY2024 bonus determinations.

These notes are privileged and confidential. Not for distribution.
""",

    # 34. Litigation strategy memo
    """ATTORNEY-CLIENT PRIVILEGED — ATTORNEY WORK PRODUCT
LITIGATION STRATEGY MEMORANDUM

To: General Counsel; CEO; Audit Committee Chair
From: Outside Counsel — Marcus Hennessy, Partner, Hennessy & Crowe LLP
Re: Sterling Industries v. Threshold Manufacturing — Strategic Assessment
Date: August 18, 2024

This memorandum is privileged and confidential under the attorney-client and work-product doctrines. It contains my legal advice and strategic assessment and should not be shared beyond the addressees without my consent.

Summary
After review of the pleadings, document production to date, and my discussions with you and the engineering team, my assessment is that Sterling has a meaningfully stronger case than Threshold on the merits. However, the litigation is likely to be expensive ($2.5M-$4M total cost) and protracted (18-24 months to trial). I recommend continued engagement on settlement at amounts in the $1.5M-$2.5M range, supported by the following analysis.

Strengths of our position
1. The contract language under Section 4.3 (force majeure) clearly excludes the supply-chain disruption Threshold has alleged, based on standard industry interpretation of similar clauses.
2. Threshold's own pre-dispute communications (Exhibit 14 from production) acknowledge that the delays were within their control. This is highly favorable to us.
3. Our damages model (loss of substitute supply revenue + capacity costs) is well-supported by contemporaneous internal documents.

Weaknesses
1. Email from our supply manager dated November 18, 2023 (Exhibit 22) could be characterized as accommodating Threshold's delivery timeline, potentially creating an estoppel argument. We have a response, but it is the strongest item in their case.
2. Our witness, Jeffrey Tarbell, is somewhat inconsistent in his deposition responses and may not present well at trial.

Strategic options
Option A: Aggressive litigation through trial. Likelihood of favorable verdict: 65-70%. Expected recovery: $8M-$12M before fees. Expected fees: $3M-$4M. Net expected value: ~$5M.

Option B: Continue current pace; press for settlement post-summary judgment phase. Expected fees through that point: $1.5M-$2M. Settlement range expected: $2M-$4M (recent comparable matters suggest this range).

Option C: Push for settlement now via senior-level mediation. Expected fees: $200K-$400K. Settlement range likely: $1M-$2.5M (we are at a weaker negotiating position now than post-MSJ).

Recommendation
Option B. Continued discovery and motion practice will strengthen our position. After summary judgment ruling, our leverage will be substantially better than today.

Decisions needed in the next 30 days: confirm MSJ filing date; respond to Threshold's third document request; review and approve revised case budget.
""",

    # 35. Confidential customer reference list with internal notes
    """INTERNAL — CUSTOMER REFERENCE LIST (with internal notes)
Distribution: Sales leadership, marketing reference team only
CONFIDENTIAL: Includes internal assessment of customer relationship status

Reference-able customers (current)

1. Cobalt Energy — VP IT (Eduardo Quintanilla)
   - Internal note: ENTHUSIASTIC reference. Will speak to ROI in any forum including videos and case studies. Light-touch ask preferred (don't over-use).
   - Best for: enterprise tier, regulated industry, infrastructure efficiency stories
   - Last used as reference: July 2024 (call with Brightline Analytics prospect)

2. Verdant Foods — Director of Operations (Genevieve Carrasco)
   - Internal note: Reliable reference. Direct and balanced; will mention both strengths and challenges. Some customers prefer this style.
   - Best for: mid-market, multi-site organizations, operations use case
   - Last used as reference: September 2024

3. Northstar Trade — Head of Engineering (Pavel Krasniansky)
   - Internal note: Tepid reference. Has been frustrated by our roadmap pace. Use cautiously.
   - Best for: technical evaluations only (he is detailed and credible on technical questions)
   - Last used as reference: April 2024; flagged for re-assessment before reuse

Reference-able with caveats

4. Aurora Biotech — IT Manager (Solene Picard)
   - Internal note: Currently in escalation due to billing dispute (resolved September; relationship status improving). DO NOT use as reference until November.

5. Cinder Manufacturing — CTO (Devraj Khurana)
   - Internal note: GREAT reference for technical depth but they will candidly mention features we don't have yet. Brief sales reps to expect that.

Not currently reference-able

6. Solstice Capital Partners — Adaobi Eze
   - Internal note: She is happy but their compliance team forbids public reference outside their industry. We can quote anonymously.

7. Pinemark Builders — Nnamdi Achukwu
   - Internal note: Customer is at-risk; do not put any pressure on the relationship.

This list is reviewed monthly. The references team owns updates.
""",

    # 36. Internal pricing exception log
    """INTERNAL — PRICING EXCEPTION LOG, Q3 2024
Distribution: Sales leadership, Finance, Deal Desk
CONFIDENTIAL

Below is the log of pricing exceptions approved during Q3 2024. The total revenue impact of exceptions was -$840K ARR (4.2% of total Q3 bookings), within our internal threshold of 5%.

Exception 1
- Customer: Aurora Biotech
- Standard ARR: $164K | Exception ARR: $138K | Discount: 16%
- Reason: Renewal at risk after billing dispute earlier in year. Win-back discount approved per General Manager.
- Approved by: VP Sales (T. Marakovic), CFO (B. Tran)

Exception 2
- Customer: Cascade Utilities
- Standard ARR: $89K | Exception ARR: $72K | Discount: 19%
- Reason: Competitive bid against incumbent. Strategic logo for utilities vertical.
- Approved by: VP Sales, CRO

Exception 3
- Customer: Northstar Trade (expansion)
- Standard ARR: $244K (incremental) | Exception ARR: $198K | Discount: 19%
- Reason: Multi-year commitment (3-year, prepay year 1). Customer's procurement team blocked higher number.
- Approved by: VP Sales, CFO

Exception 4
- Customer: Brightline Data
- Standard ARR: $312K | Exception ARR: $264K | Discount: 15%
- Reason: Multi-product bundle pricing. Customer adopting three products simultaneously.
- Approved by: Deal Desk

Exception 5
- Customer: Silverline Health
- Standard ARR: $128K | Exception ARR: $98K | Discount: 23%
- Reason: Non-profit pricing tier. Customer qualified as 501(c)(3).
- Approved by: VP Sales (auto-approved per non-profit policy)

Patterns to note
- Average discount on exceptions: 18%, in line with prior quarter (17%)
- 4 of 5 exceptions in mid-market segment (not unusual for our mix)
- The Aurora exception is a win-back that we expect to be one-time; renewal next year should normalize

Review schedule: Pricing exception log reviewed in Pricing Committee meeting each quarter.
""",

    # 37. Sales pipeline snapshot
    """INTERNAL — SALES PIPELINE SNAPSHOT
Date: October 1, 2024
Distribution: Sales leadership, ELT
CONFIDENTIAL

Q4 2024 forecast: $14.8M new + expansion ARR (vs. quota $14.0M)
Confidence: 78% to plan (high-confidence pipeline + committed deals)

Pipeline by stage (Q4 close target)

Stage 5 (Verbal commit): $6.2M ARR across 14 deals. 92% close rate historically.
Stage 4 (Negotiation): $4.4M ARR across 18 deals. 71% close rate historically.
Stage 3 (Demo/POC): $5.8M ARR across 32 deals. 38% close rate historically (subset will slip to Q1 2025).
Stage 2 (Discovery): $7.2M ARR across 56 deals. 22% close rate historically; most slip beyond Q4.

Top 10 deals by ARR (Q4 close target)

1. Voltage Control Systems — $620K | Stage 5 | Decision expected Oct 15
2. Lakehurst Industries — $480K | Stage 5 | Contract under legal review
3. Brightline Analytics expansion — $440K | Stage 4 | Pricing negotiation
4. Cobalt Energy expansion — $390K | Stage 5 | Verbal commit, paperwork in flight
5. Solstice Capital — $360K | Stage 4 | Procurement review
6. Verdant Foods expansion — $340K | Stage 5 | Renewal + expansion
7. Cinder Manufacturing — $310K | Stage 5 | Decision committee Oct 22
8. Pinemark Builders — $285K | Stage 4 | At-risk; competitive deal
9. Tidewater Logistics — $265K | Stage 5 | Final contract review
10. Silverline Health expansion — $240K | Stage 4 | Customer expanding 2 sites

Slippage watch
- Pinemark Builders: at-risk; flagged for executive escalation
- Two stage-4 deals total $620K showing signs of slipping into Q1; included in forecast but with reduced confidence

This snapshot is dynamic. Updated weekly during the QBR cycle.
""",

    # 38. Channel partner agreement draft
    """CHANNEL PARTNER AGREEMENT — DRAFT v4

This Channel Partner Agreement (this "Agreement") is entered into as of November 4, 2024 (the "Effective Date"), by and between [Company] ("Company") and Veritas Distribution Group, Ltd., a Cayman Islands company ("Partner"), each a "Party."

1. APPOINTMENT. The Company hereby appoints Partner as a non-exclusive reseller and integrator of Company's products in the territory comprising the countries of Singapore, Malaysia, Indonesia, Thailand, Vietnam, and the Philippines (the "Territory").

2. PARTNER OBLIGATIONS. Partner shall:
   (a) Use commercially reasonable efforts to market and resell the Company's products in the Territory;
   (b) Achieve minimum new ARR bookings of US$1,000,000 in the first 12 months of this Agreement, increasing 30% year-over-year;
   (c) Maintain a sales team of not fewer than 4 dedicated personnel and a technical team of not fewer than 2 dedicated personnel, located within the Territory;
   (d) Comply with the Company's Channel Partner Code of Conduct, attached as Exhibit B.

3. ECONOMICS
3.1 Discount. Partner shall receive a discount of 30% off the Company's standard list price on net new ARR sales in the Territory.
3.2 Renewal Compensation. Partner shall receive a renewal commission of 10% of renewal ARR for accounts originally sold by Partner, for the duration of those accounts' subscription with the Company.
3.3 Implementation Services. Partner is authorized to provide implementation services at its own rates. Such services are between Partner and the customer; the Company has no economic interest in or liability for Partner's services revenue.

4. EXCLUSIVITY. This Agreement is non-exclusive in both directions. The Company may sell directly or through other partners in the Territory. Partner may distribute competing or complementary products.

5. TERM AND TERMINATION
5.1 Initial Term. This Agreement shall have an initial term of three (3) years.
5.2 Termination for Convenience. Either Party may terminate this Agreement for convenience upon 180 days' written notice.
5.3 Termination for Cause. Either Party may terminate this Agreement immediately upon written notice if the other Party (a) materially breaches this Agreement and fails to cure within 30 days, (b) becomes insolvent, or (c) ceases to do business.

6. CONFIDENTIALITY. Each Party shall maintain the confidentiality of the other Party's Confidential Information per the standard non-disclosure provisions in Section 9.

[Remainder of agreement, including IP, indemnification, limitation of liability, dispute resolution, and signature blocks, omitted from this draft excerpt]

INTERNAL: This is the proposed draft to send to Veritas. Legal review pending.
""",

    # 39. Internal data-sharing agreement draft
    """INTERNAL — DATA SHARING AGREEMENT, DRAFT FOR REVIEW

Parties: [Internal Working Group] and Marsden Analytics, an external analytics partner

Purpose: Enable Marsden to perform aggregated analytics on our customer transaction data for the purpose of generating industry benchmarks that we license back to Marsden for resale.

What data leaves our environment

The following fields, and only these fields, are permitted to leave our environment:
- Customer ID (pseudonymized via our internal tokenization service; the un-pseudonymized version stays within our environment)
- Transaction amount
- Transaction date (truncated to month-year)
- Industry vertical of the customer (high-level only: 12 categories)
- Region of the customer (5 high-level regions)

What data MUST NOT leave our environment

The following fields must NEVER be shared with Marsden, under any circumstances:
- End-user names, emails, phone numbers, or any other PII of our customers' end-users
- Account-level identifiers that are not pseudonymized
- Day-level precision on transaction dates (we share month-only)
- Free-text fields from transactions
- Customer-uploaded files of any kind

How data leaves

Data is exported by our internal tooling, pseudonymized in transit, and delivered to a Marsden-controlled S3 bucket via SFTP. The pseudonymization key is held only in our environment. Marsden does not have the ability to reverse the pseudonymization.

Audit and oversight

We retain the right to audit Marsden's data handling annually. Marsden must provide SOC 2 Type II reports annually. Marsden is required to report any actual or suspected unauthorized access to the shared data within 24 hours.

Termination and return

On termination, Marsden must delete all data received under this agreement within 90 days and provide written certification of deletion. We retain the right to verify deletion via reasonable means.

Internal note: review of this draft with our Privacy Counsel and our Customer Trust team is required before signing. The draft has been reviewed by Engineering Architecture. Open question: whether industry-vertical resolution at 12 categories is sufficient anonymization, or whether we should consolidate further to 6 categories.
""",

    # 40. Board observer rights agreement
    """BOARD OBSERVER RIGHTS AGREEMENT

This Board Observer Rights Agreement (this "Agreement") is entered into as of [Effective Date] by and between [Company], a Delaware corporation (the "Company"), and Brookmoor Growth Equity Partners III, L.P. ("Observer").

WHEREAS, Observer is a holder of Series C Preferred Stock of the Company; and

WHEREAS, the Company desires to grant Observer the right to designate one (1) representative to attend meetings of the Company's Board of Directors as an observer, subject to the terms and conditions set forth herein;

NOW, THEREFORE, the parties agree:

1. DESIGNATION. Observer may, by written notice to the Company, designate one (1) individual (the "Observer Representative") to attend meetings of the Board of Directors in a non-voting, observer capacity. Observer Representative shall be subject to the Company's standard requirements applicable to all Board members (background check, signature of NDA, signature of insider trading policy).

2. ACCESS RIGHTS
2.1 Attendance. The Observer Representative shall be entitled to attend all regular and special meetings of the Board of Directors in person or by telephone or video conference.
2.2 Materials. The Company shall provide the Observer Representative with all written materials provided to Board members in connection with any meeting at the same time such materials are provided to Board members.
2.3 Limitations. The Company reserves the right to exclude the Observer Representative from any portion of a Board meeting, and to withhold any specific document, if (a) it is reasonably necessary to preserve attorney-client privilege; (b) such exclusion or withholding is required to prevent a conflict of interest; or (c) the matter concerns an evaluation of Observer or its affiliates.

3. CONFIDENTIALITY. Observer Representative and Observer shall maintain in strict confidence all information received in connection with the rights granted under this Agreement and shall not disclose any such information to any third party, except as may be required by applicable law.

4. TERM. This Agreement shall continue until the earlier of: (a) Observer ceasing to hold at least the threshold amount of Series C Preferred Stock specified in the Investors' Rights Agreement; (b) an underwritten public offering of the Company's stock; or (c) a change of control of the Company.

5. INDEMNIFICATION. The Company shall indemnify Observer Representative on the same terms applicable to directors of the Company.
""",

    # 41. Confidential security incident post-mortem
    """INTERNAL POST-MORTEM — Security Incident SEC-2024-08-19
Distribution: Security Engineering, ELT, Audit Committee
CONFIDENTIAL — Privileged work product. Distribution outside the above list requires General Counsel approval.

Incident summary
On August 19, 2024 at 03:14 UTC, an external researcher reported a vulnerability in our customer authentication flow that, when exploited, would have allowed an attacker to assume the session of any customer admin user who had visited a malicious URL within the prior 24 hours. The vulnerability had been present in production since approximately April 2024. Our investigation found no evidence of exploitation by malicious actors during that period.

Timeline (all times UTC)
- April 12: Vulnerable code shipped to production as part of routine release
- August 18, 19:02: External researcher (a security graduate student) discovers the vulnerability
- August 19, 03:14: Researcher submits via our security disclosure program
- August 19, 04:08: On-call security engineer triages, escalates as P1
- August 19, 05:30: Incident response team assembled
- August 19, 09:14: Patch deployed to production
- August 19, 10:00: Investigation phase begins (forensic analysis of access logs)
- August 21, 17:00: Forensic analysis complete; no evidence of malicious exploitation
- August 22, 11:00: Researcher paid the bounty ($8,500) and acknowledged in our disclosure program
- August 28: Customer disclosure decision (see below)

Root cause
The vulnerability was a CSRF (cross-site request forgery) gap in a session-token rotation endpoint introduced during a refactor of our authentication flow. The original implementation included a CSRF token check; the refactor inadvertently moved the check to a different code path that was no longer reachable for this endpoint.

The bug was missed in code review (two reviewers) and not caught by automated tests because there was no test coverage of CSRF behavior on this specific endpoint.

Customer disclosure decision
Following consultation with General Counsel and the CISO, we decided to disclose to affected customers (those who had admin users who had visited an arbitrary external URL during the vulnerable period — approximately 12 customers). Disclosure occurred August 28-30 via direct email to security contacts and an in-product notification.

Remediation and prevention
- Patched (deployed August 19)
- Added CSRF test coverage to the authentication subsystem (in progress)
- Updated our security review checklist for authentication-related changes (complete)
- Began an external penetration test of the broader authentication surface (in progress, expected complete October 30)

Lessons
- Security-sensitive refactors should have a dedicated review pass by Security Engineering, separate from standard peer review. We have updated our process.
- We should not have shipped this without test coverage of the CSRF defense.
""",

    # 42. Internal communication policy
    """INTERNAL — COMPANY COMMUNICATIONS POLICY
Distribution: All employees
Most recent update: September 2024

This policy sets out what employees should and should not say publicly about the company.

What you can say publicly
- Your job title, the team you work on, and the broad nature of your work (e.g., "I work on the data infrastructure team")
- Publicly announced product features and customer wins (only those we have publicly announced)
- Public-facing information available on our website, in our public documentation, in published press releases, or in publicly available regulatory filings

What you should NOT say publicly
- Our financial numbers (revenue, headcount, growth rates, etc.) except those we have published in publicly disclosed materials
- Customer names that have not been publicly announced as customers (we have around 12% of our customer base that has opted in to public reference)
- Information about ongoing M&A discussions, fundraising activities, or strategic partnerships not yet announced
- Information about competitive intelligence (what we believe about competitors' products, strategies, finances, etc.)
- Information about ongoing legal matters, including the existence of any disputes that have not been publicly disclosed
- Information about other employees' compensation, performance, or personal lives
- Roadmap details not yet announced — including timing of upcoming releases beyond what we have officially communicated

Special note on social media
Posting personal opinions on industry topics or sharing publicly available information about the company is fine. Disparaging the company, customers, or competitors is not. If you have a question about whether a specific post is appropriate, ask before posting.

Press and analyst inquiries
All inquiries from journalists, analysts, or research firms should be referred to the Communications team. Do not respond to such inquiries directly.

Reporting concerns
If you become aware of any inappropriate disclosure (your own or others'), please notify the Communications team or HR. Mistakes happen and addressing them quickly is always better than letting them grow.
""",

    # 43. Crisis communication plan
    """INTERNAL — CRISIS COMMUNICATION PLAN
Owner: VP Communications
Last reviewed: July 2024
Distribution: Crisis Response Team + ELT

This document outlines our pre-planned communication response to high-likelihood crisis scenarios. The plan is not a script — situations always require judgment — but having starting drafts and a decision framework reduces panic and improves quality.

Trigger criteria for activation
A Crisis Response is activated by any of: (1) widespread customer-impacting outage exceeding 90 minutes; (2) confirmed security breach involving customer data; (3) significant safety incident at the workplace; (4) material adverse public statement by a senior employee; (5) significant regulatory action; (6) any matter that the CEO or General Counsel deems sufficient to warrant activation.

First-hour actions
Within 60 minutes of activation:
- Crisis Response Team convenes (Comms, GC, CEO, relevant function lead)
- Initial fact-pattern assessment (what do we know, what don't we know, what's confirmed)
- Decision: do we issue any public communication immediately, or do we hold until more facts are available?
- Internal communications: hold? brief leaders only? brief all-hands?

Pre-drafted scenarios (with starting templates)

A. Major outage (>2 hours)
- Status page updated within 15 minutes of detection
- Customer email to affected accounts within 90 minutes
- Public blog post when resolution is confirmed
- Detailed post-mortem published within 14 days

B. Confirmed security incident involving customer data
- Affected customers notified individually before any public statement
- Public statement only after legal review and consultation with PR firm
- Tone: clear, accountable, specific about what we know and don't know
- Do NOT speculate. Do NOT minimize. Do NOT blame third parties.

C. Senior employee public misstep
- Internal communication first (to leaders) within 4 hours
- Public response only if the matter has already attracted public attention
- Tone: separate the institution from the individual; do not pre-judge

D. Negative analyst report or media coverage
- Decide whether response is warranted; usually NO public response is best
- Engage analyst directly to correct factual inaccuracies if any
- Brief sales leadership so they have language for customer questions

Spokesperson designations
- Operational/technical matters: CTO or VP Engineering
- Product/customer matters: CEO or CPO
- Legal/regulatory matters: General Counsel
- Crisis-level matters: CEO only

Internal note: Each scenario has a more detailed playbook in the Crisis Response wiki. Update this plan quarterly.
""",

    # 44. Confidential talent succession plan
    """INTERNAL — TALENT SUCCESSION PLAN
Distribution: CEO, CHRO, Board (informational once annually)
Classification: Highly confidential — knowledge of these plans may be career-affecting for the individuals named

This document maps the company's leadership succession readiness for each ELT-level role. Plans are reviewed annually with the Board. Names listed below as successors are not aware of their inclusion unless their current development plan specifically calls it out; this is intentional to preserve flexibility.

Chief Executive Officer (Dilnoza Yusupov)
- Emergency successor (could step in within 30 days if needed): COO Adwoa Mensah-Kennedy. Readiness: HIGH. Has run the company in CEO absences; well-known to Board.
- Mid-term successor (12-24 months): COO Adwoa Mensah-Kennedy or VP Engineering Marcus Otieno. Marcus would require external development and board exposure; Adwoa is ready now.
- Long-term external bench: not actively cultivated; would conduct external search if needed.

Chief Operating Officer (Adwoa Mensah-Kennedy)
- Emergency successor: VP Engineering Marcus Otieno (cross-functional, but heavy lift). Readiness: MEDIUM.
- Mid-term successor: planned hire of VP Operations (currently open requisition; targeting H1 2025). External search.

Chief Financial Officer (Bao Vinh Tran)
- Emergency successor: VP Finance Henrietta Forsberg. Readiness: HIGH.
- Mid-term successor: Henrietta Forsberg with public-company prep. She would benefit from external development in investor relations.

VP Engineering (Marcus Otieno)
- Emergency successor: Director of Platform Engineering Anika Volkova. Readiness: MEDIUM-HIGH. Needs board exposure and cross-functional development.
- Mid-term successor: Anika Volkova or external candidate.

VP Product (Sevda Petrosyan)
- Emergency successor: Director of Product Tobias Lindqvist. Readiness: MEDIUM. Strong product judgment; needs more exposure to enterprise customers.
- Mid-term successor: Tobias Lindqvist with development plan.

Recommendations
1. Begin board exposure for Marcus Otieno (CEO succession track). Quarterly Board lunch invitations starting Q4.
2. Invest in Anika Volkova's external development (executive coaching budget approved).
3. Identify external bench candidates for COO role; engage executive search firm.
4. Annual review: November 2024.

This document is highly sensitive. Inappropriate disclosure has direct career consequences for the individuals named.
""",

    # 45. Internal customer-segmentation strategy
    """INTERNAL — CUSTOMER SEGMENTATION FRAMEWORK
Distribution: GTM Leadership, Product, Marketing
CONFIDENTIAL — proprietary segmentation criteria

Our customer segmentation framework is not the standard "company size" partitioning. It is built around behavioral signals that we have discovered correlate with retention, expansion, and advocacy. This document explains the framework so the GTM organization can apply it consistently.

Segments (in priority order for resource allocation)

S1: "Embedded Operators"
Definition: customers who have deeply integrated our platform into their core operations, evidenced by (a) integration with 3+ of their downstream systems; (b) workflow automation usage ≥5 active automations; (c) 60+ daily active end-users; (d) tenure ≥18 months.

Behavioral pattern: NPS 75+. Gross retention 98%+. Net revenue retention 140%+. Account team motion: relationship-stewardship, NOT new sales push.

S2: "Growth Customers"
Definition: customers who entered as small users but are scaling their use over time; rising DAU, expanding integrations, increasing seats. Tenure 6-24 months. Signs of S1-trajectory.

Behavioral pattern: NPS 50-65. Gross retention 92%. Net revenue retention 130%+. Account team motion: expansion accelerator; introduce advanced features; quarterly executive sponsor calls.

S3: "Plateaued Users"
Definition: customers with stable usage that hasn't grown in 9+ months. Often have not adopted features released after their onboarding period.

Behavioral pattern: NPS 30-50. Gross retention 88%. Net revenue retention 102%. Account team motion: re-engagement; offer re-onboarding; identify expansion blockers.

S4: "At-Risk"
Definition: customers with usage trends pointing downward over the past 90 days; or customers we have identified through churn-model scoring as having ≥25% churn probability.

Behavioral pattern: NPS variable. Gross retention 65% (vs. 92% for the base). Net revenue retention 80%. Account team motion: aggressive retention; CSM ownership transfer if needed; flexible commercial terms.

S5: "New / Onboarding"
Definition: customers in first 6 months. Motion is to get them to S2 trajectory.

Allocation
S1 + S2 represent ~58% of ARR and receive ~32% of customer success resources.
S3 + S4 represent ~22% of ARR and receive ~38% of customer success resources (intentional over-investment to fight churn).
S5 represents the rest.

This framework is reviewed semi-annually. Q4 2024 review is in November.
""",

    # 46. Buy-vs-build analysis
    """INTERNAL — Buy vs. Build Analysis: Workflow Orchestration Component
Prepared by: Engineering Architecture + Strategy
Distribution: ELT, Engineering Leadership
Date: September 2024
Decision required: October 15, 2024

Question
Should we build our own workflow orchestration component as part of the Platform 5 redesign, or license a commercially-available solution from one of three vendors we've evaluated?

Strategic context
Our customers increasingly expect workflow automation capabilities. Our current solution is functional but limited. The Platform 5 redesign is the opportunity to significantly improve this capability. The choice between build and buy has implications for our 2025-2027 engineering capacity, our gross margin, and our IP position.

Option A: Build
- Capacity required: 8 engineers for 14 months (~120 engineer-months total)
- Cost: approximately $2.6M in fully-loaded engineering cost; opportunity cost of forgone work
- Outcome: a proprietary workflow engine tightly integrated with our platform; defensible IP; full control over evolution
- Risk: 14-month timeline likely slips by 4-6 months based on our historical pattern on similar projects; technical risk on horizontal scaling under realistic loads

Option B: Buy / license (Temporal, Apache Airflow Cloud, or Inngest)
- Capacity required: 3 engineers for 6 months for integration
- Cost: approximately $0.6M integration cost + ongoing licensing fees of $1.4M-$2.2M annually starting year 1
- Outcome: faster time-to-market by approximately 8-10 months; established, scalable engine; reduced technical risk
- Risk: vendor lock-in; licensing economics evolve; less control over evolution; gross margin impact

Recommendation
Build, with the following provisos:
1. We hire two senior engineers with specific workflow-orchestration experience (open to off-cycle hiring approval)
2. We accept a likely 4-month delay relative to the 14-month plan
3. We adopt an open-source project as architectural inspiration (Temporal's design is excellent)
4. We re-evaluate at month 8 and pivot to buy if our internal version is materially behind target

This is a closely-balanced decision. The buy option becomes more attractive if we have lower confidence in our engineering execution; the build option becomes more attractive if we have higher confidence in our 24-month strategic vision.

Decision needed October 15. Engineering capacity planning is gated on this.
""",

    # 47. Investor pitch deck pre-roadshow
    """INTERNAL — Series D Investor Pitch Deck Outline (Pre-Roadshow Draft)
Status: DRAFT v0.7
Distribution: CEO, CFO, Board Chair, outside banker (Foreman & Goldman)
Classification: Confidential — pre-roadshow

This is the working outline of the investor pitch deck we will use in the upcoming Series D process. We are targeting a raise of approximately $80-100M at a target pre-money valuation of $1.2-1.4B.

Deck structure (18 slides)

Slide 1 — Cover
Slide 2 — The market problem (workflow infrastructure is fragmented across hundreds of point tools)
Slide 3 — Our product (the unified platform)
Slide 4 — Customer love (NPS 64, gross retention 96%, marquee customers)
Slide 5 — Traction summary (ARR growth chart: $4M → $14M → $42M → $98M ARR over 4 years)
Slide 6 — Why now (the macro tailwind; AI making workflow automation more capable)
Slide 7 — Unit economics (LTV/CAC 4.7x, payback 11 months, NRR 121%)
Slide 8 — Competitive landscape (the three categories of competitors and why we win)
Slide 9 — Product roadmap (high-level; Smart Insights, Self-Serve, international expansion)
Slide 10 — International opportunity (penetration thesis for EU and APAC)
Slide 11 — Team (leadership bios; advisors)
Slide 12 — Financial summary (revenue history, margin progression, cash position)
Slide 13 — Forecast (revenue trajectory through 2028; we will likely be conservative-to-show-leverage)
Slide 14 — Use of proceeds
Slide 15 — Capital structure (existing investors, prior round terms summarized)
Slide 16 — Why us, why now (the synthesis)
Slide 17 — Risk factors (for the few funds that ask)
Slide 18 — Appendix references

Talking points for sensitive questions
- "Path to profitability": we are operationally cash-flow positive on a TTM basis; we choose to invest aggressively in growth
- "Customer concentration": top 10 customers are 37% of ARR; no single customer above 9%
- "Recent customer churn": we discuss the Q3 cohort issue with context (cohort-specific, not platform-wide)
- "Series C dilution": we are comfortable with our existing stack; new round terms standard

Confidential. Do not share outside the listed distribution.
""",

    # 48. Confidential M&A target list
    """INTERNAL — M&A TARGET LIST (HIGHLY CONFIDENTIAL)
Distribution: CEO, CFO, Head of Corporate Development, Board (M&A Committee)
Updated: October 2024

This list contains companies we have actively scoped or are considering for potential acquisition. Knowledge of our interest in any of these companies, if disclosed, would harm our negotiating position and is potentially market-moving information.

Active targets (in discussion or formal diligence)

1. Pinemark Software, Inc. (codename: Atlas)
   - Stage: Active LOI; due diligence ongoing
   - Strategic rationale: adjacent product capability; ~$40-60M cross-sell potential within 24 months
   - Expected purchase price: $325-345M
   - Expected close: Q1 2025

2. Hayfield Robotics, LLC (codename: Beacon)
   - Stage: Preliminary diligence; not yet at LOI
   - Strategic rationale: technology + team; primarily a strategic talent acquisition
   - Expected purchase price: $40-60M
   - Expected close: H1 2025

Watch list (under evaluation, not yet in discussions)

3. Greenmark Analytics
   - Strategic rationale: customer base in adjacent vertical
   - Estimated value: $80-120M
   - Status: monitoring; no contact made

4. Nimbus Technologies
   - Strategic rationale: cross-license partnership exists; deeper consolidation possible
   - Estimated value: $200-300M
   - Status: relationship in place; M&A not currently mutual interest

5. Veridian Workflow
   - Strategic rationale: defensive — they could be acquired by Competitor X
   - Estimated value: $60-90M
   - Status: monitoring; no contact made

6. Sterling Operations Platform
   - Strategic rationale: customer base overlap (would help consolidate within our segment)
   - Estimated value: $100-140M
   - Status: monitoring; preliminary contact in 2023, not pursued

Status reporting
Updated monthly to the Board's M&A Committee. The CEO meets with the Head of Corporate Development weekly.

Knowledge of this list is restricted to the persons named in the distribution. Disclosure may have material consequences.
""",

    # 49. Internal merger integration plan
    """INTERNAL — MERGER INTEGRATION PLAN (PROJECT ATLAS)
Target: Pinemark Software, Inc.
Expected close: February 14, 2025
Distribution: Integration Steering Committee; ELT
Classification: Highly Confidential — Internal

This is the working integration plan for the Project Atlas acquisition (Pinemark Software, Inc., closing expected February 14, 2025). The plan covers the first 90 days post-close. Activities are organized by function and phased: Day-1, Day-30, Day-90.

Day-1 (Close Date — February 14, 2025)

Communications:
- All-hands meeting at acquired company at 8:00 AM local time, led by the company's CEO and a member of our ELT
- All-employee email from our CEO to combined company
- Customer communication to top 25 Pinemark accounts (high-touch, by named CSM contact)
- General customer email to all Pinemark customers
- Press release issued at 9:00 AM ET (subject to confirmed close)

People:
- Welcome materials (laptop ordering, benefits enrollment, etc.) for all retained employees
- Equity grants for retained employees executed
- 14 specific retention bonuses paid (key employees identified during diligence)

Systems:
- Acquired company employees added to our SSO
- Acquired company laptops connected to our endpoint management
- Acquired company customers added to our customer success system (read-only initial)

Day-30 (March 14, 2025)

Goal: stabilization. Don't disrupt anything that's working.

- Engineering: integration plan for the two products is presented but no actual integration starts. Engineering teams meet weekly cross-functionally; no team changes.
- Sales: combined company sales kickoff in Atlanta March 6-8. Sales territories preserved through end of Q1 2025.
- Customer Success: introduce the Pinemark CS team to our methodology and tooling; no customer ownership changes until at least 90 days post-close.
- Finance: combined financial reporting in place for the March close cycle.

Day-90 (May 14, 2025)

Goal: integration begins in earnest.

- Engineering: actual code integration starts on first shared component (shared authentication service)
- Sales: combined sales territories defined; transitions begin
- Customer Success: gradual transition of customer ownership where there is overlap
- Product: combined roadmap for FY2026 begins definition

Risks and mitigations
- Key person risk on Pinemark side: 14 retention bonuses funded; pre-close conversations with the top 5 had positive responses
- Customer concern about future of Pinemark product: addressed via direct communications to top accounts and public commitment to continue investment for at least 24 months

Steering Committee meets weekly through close + 30 days. Detailed function-level plans in companion documents.
""",
]


BATCHES = {
    "classify_safe": CLASSIFY_SAFE,
    "flag_pii": FLAG_PII,
    "block_transfer": BLOCK_TRANSFER,
    "request_permission": REQUEST_PERMISSION,
}


def load_mined_training_rows() -> list[dict]:
    """Load Channel-C mined training rows from samples/external/training_mined/.

    Reads any content file under that subtree (excluding .provenance.json),
    pairs with its provenance sibling to get the hand-assigned label, and
    emits training rows in the same shape as the hand-curated lists.

    The hand_assigned_label (set during Phase 3b.5 T4 manual curation) takes
    precedence over the collector's coarse `label` field, because the
    collector tags everything by the query class — not by what is actually
    in the file.
    """
    import pathlib
    rows: list[dict] = []
    base = pathlib.Path(__file__).resolve().parent.parent / "samples" / "external" / "training_mined"
    if not base.exists():
        return rows
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        if f.name.endswith(".provenance.json"):
            continue
        prov_path = f.with_name(f.name + ".provenance.json")
        if not prov_path.exists():
            continue
        prov = json.loads(prov_path.read_text())
        label = prov.get("hand_assigned_label") or prov.get("label")
        if not label:
            continue
        rows.append({
            "scenario_id": f"mined:{f.parent.name}:{f.stem}",
            "label": label,
            "text": f.read_text(errors="replace"),
        })
    return rows


def main():
    out_path = Path(__file__).resolve().parent / "dataset.jsonl"
    counts: dict[str, int] = {}
    with out_path.open("w") as f:
        for label, examples in BATCHES.items():
            for n, text in enumerate(examples):
                row = {"scenario_id": f"{label}:{n}", "label": label, "text": text}
                f.write(json.dumps(row) + "\n")
            counts[label] = len(examples)
        # Phase 3b.5 T4 — append Channel-C mined training rows from
        # samples/external/training_mined/ (kept in a separate subtree so
        # curated_data.py stays focused on hand-written examples).
        mined_rows = load_mined_training_rows()
        for row in mined_rows:
            f.write(json.dumps(row) + "\n")
            counts[row["label"]] = counts.get(row["label"], 0) + 1
    total = sum(counts.values())
    print(f"Wrote {total} examples to {out_path}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    if mined_rows:
        print(f"  (of which {len(mined_rows)} mined from samples/external/training_mined/)")


if __name__ == "__main__":
    main()
