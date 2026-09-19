# Ghana Investment Marketplace — Architecture & Development Methodology

**Version 1.3** — adds §17, the data-acquisition runbook: where every field actually comes from, the SEC register scrape spec, the licence-status display rule, provider outreach, and the week-one sequence. Companion files: `licence-status.ts`, `seed_source_targets.sql`, `provider-price-submission-template.csv`.

*v1.2 changes from 1.1: §16.4 (Serrari and nairaCompare — the proven playbook), deposit products in the universe (§11), net-of-tax real return as headline (§7.1), published market indices (§7.8).*

*v1.1 changes from 1.0: §16 competitive landscape and failure analysis, real returns as headline metric, narrow-and-complete phase ordering, two new CI checks.*

Working name: **CediWise** (placeholder). Separate repo, separate Supabase project, separate Vercel project from finanyst.com. Shared stack, zero shared infrastructure.

---

## 0. The system in one sentence

A verified, provenance-tracked database of Ghanaian investment products, rendered as SEO-indexed comparison pages, with a goal-matching front end and tracked outbound routing to licensed providers.

Everything below follows from three constraints:

1. **No APIs exist.** Ghanaian fund data lives in PDF factsheets, provider HTML pages, and SEC annual-report tables. Ingestion is a human-in-the-loop extraction problem, not an integration problem.
2. **Staleness is the killer.** Prior Ghana trackers died of data-upkeep fatigue, not bad product. Freshness must be a first-class, monitored, publicly-displayed property of every number.
3. **One part-time builder.** A boring monolith with one worker service. No microservices, no queues, no event bus.

---

## 1. Stack

Deliberately mirrors finanyst.com so nothing has to be re-learned.

| Layer | Choice | Notes |
|---|---|---|
| Web app | Next.js (App Router, TypeScript) on Vercel | Public site, admin, API routes |
| UI | Tailwind + shadcn/ui | Same component vocabulary as Finanyst |
| Quiz state | Zustand + localStorage persist | Same pattern as the six-step questionnaire |
| DB / auth / storage | Supabase (Postgres + RLS + Storage) | **New project.** Storage holds immutable source documents |
| Analytics engine | Python FastAPI on Render (Starter tier, no cold-start sleep) | Return + risk metrics and scoring. Pure standard library — no pandas/numpy, so there is nothing to compile and no wheel availability to chase on a new Python |
| Extraction | Claude API, server-side only | PDF factsheets → strict JSON schema, same pattern as the Finanyst statement uploader |
| Scheduled jobs | Vercel Cron → Route Handlers (short) / GitHub Actions (long crawls) | No dedicated queue in v1 |
| Search | Postgres FTS + `pg_trgm` | No Algolia/Meilisearch until >2,000 products |
| Email | Resend, deferred until there's a list | Same reasoning as Finanyst lead capture |
| Analytics | GA4 + first-party event tables in Postgres | Provider reporting needs first-party data |

**Explicit non-goals for v1:** native iOS/Android, microservices, message queues, Kubernetes, GraphQL, realtime subscriptions, portfolio aggregation, any money movement.

### Deliberate divergences from the Finanyst setup

| Finanyst did | Do differently here | Why |
|---|---|---|
| No `supabase/` folder; migrations run in the dashboard, untracked | **Migrations tracked in the repo**, applied via Supabase CLI | The DB *is* the asset. Untracked schema is unrecoverable |
| Floats/plain numerics for money | `bigint` pesewas + `char(3)` currency | GHS/USD mixing plus rounding disputes with providers |
| Mutable rows | Append-only observation tables with correction rows | Published returns must be reproducible on demand |
| RLS policies added as needed | **All four policies written at table creation** | Direct application of the memos-table silent-failure lesson |

---

## 2. What the Python engine is for — and what it is not

The engine earns its place here more than it did on Finanyst, because the maths is real and repeated.

**In scope:** return-series construction from NAV observations, annualisation, volatility, maximum drawdown, downside deviation, rolling-window consistency, excess return over the 91-day T-bill, real (inflation-adjusted) return, peer-group percentile normalisation, winsorisation, and final score computation.

**Out of scope:** CRUD, auth, rendering, anything Next.js can do. Resist the pull.

**Contract — two stateless endpoints:**

```
POST /compute/metrics
  { product_id, currency, observations: [{as_of, nav, basis}],
    benchmarks: {tbill_91: [...], cpi_yoy: [...]}, windows: ["1m","3m","1y","3y","si"] }
  → { engine_version, metrics: [{window_code, total_return, annualised_return,
      volatility, max_drawdown, downside_deviation, excess_over_tbill,
      real_return, observation_count, coverage}] }

POST /compute/scores
  { as_of, methodology_version, config: {...}, peer_groups: {...},
    products: [{product_id, peer_group, factors: {...}}] }
  → { engine_version, scores: [{product_id, profile, total, subscores,
      coverage, rank_in_peer, scored, unscored_reason}] }
```

Two rules, both non-negotiable:

- **Deterministic.** Same input bytes → same output numbers, forever. Golden-file tested against a committed fixture set. If a code change moves a golden number, that is a methodology change and requires a version bump.
- **The engine never reads the database.** All inputs arrive in the payload. This is what makes it testable, replayable, and safe to re-run historically.

Health check at `GET /health` returning `{status, engine_version}`, and **fail-fast env validation on both sides at boot**. The Finanyst `PYTHON_ENGINE_URL=http://localhost:8000` incident cost two days of hunting Vercel and RLS for what was a local env var pointing at nothing — a boot-time assertion would have caught it in one second.

---

## 3. System shape

```
 SOURCES                      INGESTION                   CORE                    SURFACES
 ─────────                    ─────────                   ────                    ────────
 SEC licensee register  ┐
 SEC annual reports     │   ┌──────────┐   ┌────────────┐  ┌──────────┐   ┌─────────────────┐
 Provider factsheets    ├──▶│ fetcher  │──▶│  extractor │─▶│ staging  │   │ public site     │
 Provider websites      │   │ (cron)   │   │  (Claude)  │  │  tables  │   │ product pages   │
 BoG / T-bill results   │   └────┬─────┘   └────────────┘  └────┬─────┘   │ compare pages   │
 GSE reports            ┘        │                              │         │ goal quiz       │
                                 ▼                              ▼         │ articles (SEO)  │
                          ┌─────────────┐                 ┌───────────┐   └────────┬────────┘
                          │  Supabase   │                 │  review   │            │
                          │  Storage    │◀── raw bytes    │  queue    │            │
                          │ (immutable  │    + sha256     │  /admin   │            ▼
                          │  evidence)  │                 └─────┬─────┘   ┌─────────────────┐
                          └─────────────┘                       │         │ outbound router │
                                                    approve ────┘         │ (signed tokens) │
                                                          │               └────────┬────────┘
                                                          ▼                        │
                                              ┌───────────────────────┐            ▼
                                              │  PUBLISHED TABLES     │   ┌─────────────────┐
                                              │  providers, products, │   │ provider portal │
                                              │  fees, nav_obs, ...   │   │ leads + analytics│
                                              └───────────┬───────────┘   └─────────────────┘
                                                          │
                                              ┌───────────▼───────────┐
                                              │  Python engine        │
                                              │  metrics → scores     │
                                              │  (immutable runs)     │
                                              └───────────────────────┘
```

---

## 4. Subsystem 1 — Evidence and provenance

This is the foundation and it must exist before anything else. Every published number traces to a stored document.

**Rules:**

1. Every fetch writes the **raw bytes** to Supabase Storage, keyed by SHA-256. If the hash is unchanged, no re-extraction — this is the main cost control.
2. Every fact-bearing row carries `source_id` and `verified_on`. No exceptions, including manual entry (which gets a `manual_entry` source row naming who typed it).
3. **Freshness is public.** Every product page shows "NAV as at *date* · verified *date* · source: *document*". This is the differentiator against every existing Ghana tracker and it is also the honest thing to do.
4. **Automatic decay.** A staleness policy per data type; when breached the product flips to `stale` status, the score is suppressed, and the page shows a banner rather than a stale number. Silently serving an 18-month-old return is the failure mode that ends the business.

| Data type | Expected refresh | Flag stale after |
|---|---|---|
| NAV / unit price | Daily–weekly | 14 days |
| Money-market yield | Weekly | 14 days |
| Fees / TER | Annual | 400 days |
| Minimum investment | Ad hoc | 180 days |
| SEC licence status | Quarterly | 120 days |
| Fund size / AUM | Quarterly | 200 days |

---

## 5. Subsystem 2 — Ingestion pipeline

Five stages. Nothing skips a stage; nothing writes straight to published tables.

**1. Fetch.** A `source_targets` table holds, per provider, the URLs and their cadence. A cron route walks due targets, downloads, hashes, stores, and creates a `sources` row. Unchanged hash → stop here.

**2. Extract.** PDFs go to Claude as native base64 documents; XLSX flattened via ExcelJS to TSV first; HTML tables parsed deterministically with cheerio where the structure is stable (deterministic beats LLM whenever the DOM is reliable — it is free and it cannot hallucinate).

The extraction schema carries the **multi-entity lesson from Finanyst directly**: return an `entities` array with an explicit never-combine instruction. A factsheet PDF routinely covers four funds; a schema permitting one fund forces the model to merge them, and it will do so confidently and silently. Set `max_tokens` high (16k) — truncation fails the JSON parse loudly, which is what you want.

**3. Validate.** Deterministic rules, results stored as JSONB alongside the extraction:

- NAV moved more than ±10% since the last observation → flag
- `as_of` in the future, or older than the previous observation → flag
- TER outside 0–8%, management fee outside 0–5% → flag
- currency inconsistent with the product record → flag
- money-market yield more than 15pp from the 91-day T-bill → flag
- any field whose extracted value differs from the stored value by more than a per-field threshold → flag

**4. Review.** `/admin/ingest` shows extracted values next to a rendering of the source page. Approve, correct, or reject. Approvals write to published tables inside a transaction with provenance attached. This is the job that never goes away — budget 2–4 hours a week forever, and design the screen to make one approval take under 20 seconds.

**5. Publish.** Approval enqueues recomputation: metrics → scores → ISR revalidation of affected pages.

**Cost control:** hash-gating skips unchanged documents, deterministic parsing handles stable HTML, and only genuinely new documents reach Claude. At ~30 providers with weekly factsheets that is a small monthly bill, not a large one.

---

## 6. Subsystem 3 — Scoring

The methodology is the intellectual property, so it lives in one file and one file only: `lib/scoring/config.ts` (supplied separately). The public `/methodology` page renders **from that same file**. This is the `ranges.ts` lesson from Finanyst — the moment the published methodology and the executed methodology are two artifacts, they drift, and the drift is invisible until a provider catches it.

Six design decisions worth defending:

**6.1 Rank within peer groups, never across them.** A money-market fund and an equity fund cannot share a leaderboard. Peer group = asset class × currency. There is no site-wide "#1 investment in Ghana", and refusing to publish one is a credibility asset, not a missing feature.

**6.2 Collapse the return factors.** The strategy doc weights "risk-adjusted performance" 20% and "historical performance" 15%. Those are ~90% correlated and the pair silently makes return 35% of the score. Use one return factor, risk-adjusted, at 20%.

**6.3 Coverage gating.** Each factor declares its required inputs. Missing inputs → factor dropped and weights renormalised, but **only while coverage ≥ 70%**. Below that the product is listed as *Not scored — insufficient verified data*, with the reason shown. A nine-factor score computed from four populated factors is false precision, and false precision is exactly what a trust-positioned product cannot afford.

**6.4 Minimum history.** No score below 12 months of observations. Label it *New — insufficient history* and show it in listings anyway, unscored. Suppressing new funds entirely would be its own bias.

**6.5 Immutable score runs.** Every run stores `methodology_version`, the full config JSONB, `as_of`, and `engine_version`. Scores reference the run. Old runs are never deleted. When a provider disputes a rank you reproduce it exactly, from stored inputs, in minutes. Changing any weight = new `methodology_version` + a dated changelog entry on `/methodology`.

**6.6 Build TrustScore only from verifiable facts.** The strategy doc proposes components for customer service (10) and complaint record (10). You have no data for either, and inventing them corrupts the one number whose entire value is that it is not invented. Launch with: SEC licence verified and current (30), custodian/trustee identified (15), audited financials available (15), scheme particulars/prospectus published (15), operating history (10), data freshness (10), disclosure completeness (5). Add service and complaints later, when a survey or a regulator complaints register actually supplies them.

**Benchmarks needed in the DB for any of this to work:** 91-day and 182-day T-bill rates, CPI year-on-year, GSE Composite Index, GHS/USD. Without the T-bill series there is no risk-adjusted anything; without CPI you cannot show real returns, which in a high-inflation market is the single most useful number on the page.

---

## 7. Subsystem 4 — Distribution and attribution

**7.1 Lead with what the investor actually keeps.** The headline number on every product page is the return after fees, after withholding tax, and after inflation — with the nominal figure shown beneath it, greyed. In a market where a fund returning 20% against 23% inflation has lost the investor money, the nominal figure alone is close to misinformation.

Show the whole bridge on the product page, not just the endpoint:

```
Gross yield              18.5%
Less fees                -2.1%
Net of fees              16.4%
Less withholding tax     -1.3%
What you receive         15.1%
Less inflation          -11.8%
What you actually keep    3.3%   ← headline
```

Every line traces to a stored source: fees from `product_fees`, the withholding rate from `products.withholding_rate` (per product, sourced and dated — never hardcoded, since it moves with the Finance Act), inflation from `GH_CPI_YOY`. Confirm the current Ghanaian withholding treatment with an accountant before publishing any of it.

Serrari does the fee-and-tax half of this in Kenya (§16.4) and it is the clearest thing on their site. Adding the inflation step is the part still open, and in Ghana it is the step that matters most.

**7.2 Pages are the product.** Static generation with ISR for every product, provider, peer-group listing, and pairwise comparison. Comparison pages are generated programmatically from the DB within a peer group — that is the SEO surface, and it needs the data model to be renderable, which it is.

**7.3 Performance budget, enforced in CI.** Target audience is on mobile data in Ghana. Under 100KB of JS on comparison and product pages. No client-side charting library on first paint — render sparklines as server-generated SVG. Fail the build if the budget is breached.

**7.4 Outbound routing.** Every "Visit provider" link goes through `/go/[token]` — a server route that records the click, then 302s. The token is signed and single-purpose. This is the billing substrate, so build it before you sell anything.

**7.5 Attribution integrity.** Providers will dispute lead counts; assume it from day one. Immutable `lead_events` ledger, a documented dedupe rule (same session + same product within 24h = one lead), monthly per-provider reconciliation reports generated from the ledger, and a written dispute process in the contract. Reconciliation you can produce on demand is worth more in a commercial negotiation than any dashboard.

**7.6 The quiz session doubles as the compliance audit log.** Each session records the inputs, the `score_run_id` used, and the exact product IDs shown. If the SEC ever asks what a user was shown and why, that record is the answer.

**7.8 Publish an index.** A `GH_MMF_AVG` and a `GH_MMF_LEADERS` index, recomputed on every cycle and stored in `market_indices` with their constituents so any published level is reproducible. It costs almost nothing once the data exists, it gives the monthly change page a headline about *the market* rather than about one fund, and it is the single most quotable artifact you can hand a financial journalist. Serrari runs exactly this in Kenya and cites it throughout their own coverage.

**7.7 Every ingestion cycle must produce a new asset, not just a refresh.** This is the direct counter to the mechanism that killed The Finance Focus (§16.2). A cycle that only overwrites yesterday's numbers has constant cost and zero return — and any pure-cost activity dependent on one person's discipline stops eventually, from arithmetic rather than laziness. So each approved batch writes a row to `content_updates`: what moved, which products, by how much. That table then generates a dated "what changed in Ghanaian funds this month" page (indexed, accumulating), the body of the alert email promised at signup, and the change-log feed on `/methodology`. The maintenance burden becomes the content engine. Build this in Phase 3, not later — retrofitting it means the first six months of changes are lost.

---

## 8. The regulatory boundary, enforced in code

The strategy doc correctly separates information/comparison from advice. A policy document does not enforce that — code does, because in six months you will be shipping fast and the boundary will erode by accident.

`lib/compliance/boundary.ts` owns three things:

**Phase flags.** `COMPLIANCE_PHASE: 1 | 2 | 3`. Phase 1 = factual comparison. Phase 2 = adds outbound routing. Phase 3 = personalised language, and is **gated behind written legal advice**, not a product decision. Every feature that could cross the line reads this flag.

**Permitted output shapes.** Result sets return filtered, sorted lists of products with factual attributes and a factual rationale ("matched because minimum ≤ GH₵500 and dealing is daily"). They never return allocation percentages, never return a suitability assertion, and never use second-person imperatives about what to buy.

**A lint test in CI.** A test that scans rendered result copy and template strings for banned constructions — "you should invest", "we recommend you", "best for you", any `%` adjacent to a product name in an allocation context. It will feel pedantic. It is the cheapest possible insurance against a business-ending mistake, and it runs in 200ms.

Alongside: a single `<Disclaimer />` component (one source of truth, like the benchmark ranges), and every result set written to the audit log per §7.5.

Two compliance items to resolve with Ghanaian counsel **before** Phase 3, not after:

- Where the SEC's Investment Adviser licensing category begins relative to goal-matched product lists under the Securities Industry Act 2016 (Act 929), and what the rules are on publishing performance data for regulated schemes.
- Data protection: registration and controller obligations under Ghana's Data Protection Act, and where the database may be hosted. Decide the Supabase region on the answer, not on latency.

---

## 9. Non-functional requirements

**Security.** RLS on every table with all four policies written at creation. Anonymous role gets SELECT on published rows only. All writes go through the service role in server routes. Admin RBAC on a `profiles.admin_role` column with RLS preventing self-elevation — lift the Finanyst pattern wholesale. Store no PII beyond an email; there is no reason for this product to hold a Ghana Card number, and every reason not to.

**Secrets.** Never `Get-Content .env.local | Select-String` and paste the output — that leaked three Anthropic keys on the Finanyst build. Safe check:

```powershell
(Get-Content ".env.local" -Raw) -match "ANTHROPIC_API_KEY=([\S]+)" | Out-Null; if ($Matches[1]) { "Key present, length: $($Matches[1].Length)" }
```

**Backups.** Supabase PITR, plus a weekly `pg_dump` and a weekly sync of the Storage evidence bucket to independent storage. The database and the evidence locker are the entire company; Vercel and Render are replaceable in an afternoon.

**Observability.** One `/admin/health` page: ingestion success rate by source over 7 days, count of products by staleness band, last successful score run, extraction cost this month, and a diff of the latest score run against the previous one. That last panel is the one that catches a bad ingestion before users do — a rank that moved 14 places overnight is either news or a data error, and you want to know which before Monday.

---

## 10. Repo layout

```
/app
  /(marketing)          landing, methodology, about, articles
  /invest               goal quiz (Zustand + persist)
  /products/[slug]      product pages (ISR)
  /providers/[slug]     provider pages (ISR)
  /compare/[a]/[b]      programmatic pairwise comparisons
  /go/[token]           outbound router — records click, 302s
  /admin                ingest review, health, score runs, provider accounts
  /api
    /ingest/fetch       cron: walk due source_targets
    /ingest/extract     cron: unextracted sources → Claude → staging
    /ingest/approve     admin action → published tables (transactional)
    /compute/refresh    calls the Python engine, writes metrics + score run
    /providers/report   monthly reconciliation export
/lib
  /scoring/config.ts    METHODOLOGY — single source of truth, renders /methodology
  /scoring/client.ts    typed wrapper over the Python engine
  /ingest/schema.ts     Zod + the Claude extraction JSON schema
  /ingest/validate.ts   deterministic validation rules
  /compliance/boundary.ts
  /money.ts             pesewa helpers — parse, format, never floats
/engine                 Python FastAPI (deployed separately to Render)
  main.py, metrics.py, scoring.py, tests/golden/
/supabase
  /migrations           TRACKED IN GIT. Applied via the Supabase CLI
  seed.sql
```

---

## 11. Delivery methodology

Five phases, each with a hard exit criterion. Do not start a phase until the previous exit criterion is met — especially Phase 0.

### Phase 0 — Manual proof (2–3 weeks, zero code)

A Google Sheet. 60–80 products across money market, fixed income, balanced, equity, plus the T-bill curve. Columns exactly matching §5 of the strategy doc, including **data source URL and date verified on every row**. Then score them by hand with the proposed weights.

Three exit tests:

1. **Can you populate it at all?** If fewer than 60% of products yield a verified TER and a 12-month return series from primary documents, the ranking engine cannot exist as designed and the whole product must be rescoped — likely to money-market funds and T-bills only, where data is best.
2. **Does the ranking survive scrutiny?** Show it to three Ghanaian investors and one fund manager. The fund manager's job is to attack it. If the attacks are unanswerable, fix the methodology now, on a spreadsheet, not in six months on a live site.
3. **Time the refresh.** Update every row a second time and record how long it took. Multiply by 52. If that number is more than about 150 hours a year manually, the ingestion pipeline must reduce it by 5× or the project fails on operations regardless of code quality.

This phase is where the idea gets killed cheaply if it deserves to be. It is the highest-value three weeks in the plan.

### Phase 1 — Data spine (3 weeks)
Supabase project, tracked migrations, all four RLS policies per table, evidence storage, sources and provenance, `/admin` ingest review, manual entry path, SEC licensee ingest.

**Scope discipline — narrow and complete beats wide and empty.** Fifteen products with every field populated and sourced beats eighty that are 40% blank; §16.3 shows what wide-and-empty looks like in production.

But "narrow" means narrow by *depth of metric*, not by the question being answered. Load the full **cash-and-short-term decision set** first — GHS money market funds, fixed deposits, bank savings rates and T-bills — because that is genuinely what a Ghanaian with GH₵1,000 is choosing between, and answering only the mutual-fund third of it makes the product useless for the most common query on the site. The deposit data is also the cheapest in the market: rates sit on bank websites and change slowly.

Deposit products live in their own `deposit:GHS` peer group and are never ranked against funds — a capital-guaranteed deposit and a variable-NAV fund are not comparable on volatility or drawdown. They compare on net-of-tax yield, liquidity, minimum and provider strength, which is exactly the comparison the user wants. Expand to balanced, fixed income and equity funds one peer group at a time, only once the previous is complete.

**Exit:** one peer group fully migrated with provenance on every field, zero placeholder values on any published page, and the admin review screen handling one approval in under 20 seconds.

### Phase 2 — Engine and metrics (2 weeks)
Python service on Render, golden-file fixtures, metrics computation, benchmark series (T-bill, CPI, GSE-CI, FX) loaded. **Exit:** metrics for every product with ≥12 months of history reproduce the spreadsheet's hand calculations exactly.

### Phase 3 — Public surface (3 weeks)
Product, provider, peer-group and comparison pages. Search. **Real return as the headline metric.** Freshness badges everywhere. `content_updates` and the monthly change page (§7.7). Performance budget and the placeholder check in CI. `/methodology` rendering from config. **Exit:** indexed, under the JS budget on 3G, every published number clicks through to its source document, and one full ingestion cycle has produced a dated change page.

### Phase 4 — Scores and quiz (2 weeks)
Score runs, peer-group ranking, coverage gating, the four investor profiles, goal quiz, calculator, compliance boundary and its lint test, audit log. **Exit:** a full score run reproduces from stored inputs, and the boundary test passes on every result template.

### Phase 5 — Attribution and providers (3 weeks)
Signed outbound tokens, lead ledger, dedupe, provider portal with the analytics that make the pitch ("2,340 views, most common goal, compared against 7 competitors"), monthly reconciliation export. **Exit:** a reconciliation report you would be willing to put in front of a fund manager who is trying to pay you less.

Monetisation comes after Phase 5 and after traffic exists — in the order the strategy doc recommends, which is right.

**Sequencing note:** this is roughly 13–16 focused weeks, which at part-time alongside Finanyst is closer to eight or nine months. The plan is correct at that pace; the risk is running two products' worth of promises at once. Phase 0 costs three weeks and answers whether the rest is worth it.

---

## 12. Working practices

- **Trunk-based, small commits.** One branch, deploy often — the Finanyst rhythm works.
- **Migrations in git, always.** Every schema change is a numbered file applied via CLI. This is the single biggest process change from Finanyst.
- **Golden files for anything numeric.** Scoring and metrics get committed fixtures. A changed golden number is a methodology decision requiring a version bump, never a silent fix.
- **Verify the edit, not the commit.** A successful `git push` proves nothing about a file that had no changes to stage. Read the file back.
- **PowerShell file writes:** for anything over ~80 lines use a `List[string]` with `$o.Add()` per line and `WriteAllLines`, split across two blocks. Long heredocs silently produce no file. For edits, single-line `-replace` over a line array from `[System.IO.File]::ReadAllLines()`; multi-line `.Replace()` never matches on CRLF files and fails without an error.
- **Be suspicious of operations that can succeed at zero rows.** Blocked-by-missing-RLS-policy and matched-nothing are indistinguishable. Write all four policies up front.
- **Weekly data QA ritual, 30 minutes, non-negotiable.** Open `/admin/health`, clear the review queue, eyeball the score-run diff. Skipping this for a month is how the product becomes the 2022 tracker.

---

## 13. Risks and kill criteria

| Risk | Mitigation | Kill criterion |
|---|---|---|
| Data unobtainable at quality | Phase 0 proves it before code | <60% of products yield verified TER + 12m series → rescope to MMF/T-bills or stop |
| Upkeep fatigue | Hash-gating, LLM extraction, 20-second reviews | Weekly refresh >4 hours after Phase 1 → automate further or reduce universe |
| A fraudulent provider slips through | Licence status verified against the SEC register quarterly, stored with source, displayed with date | — |
| Regulatory overreach | Phase flags + CI lint + counsel before Phase 3 | Counsel says goal-matching requires an adviser licence → stay at Phase 2 permanently, which is still a business |
| Incumbent tracker improves | Freshness, provenance and goal-matching are the wedge, not the table | — |
| Providers won't pay for leads | Reconciliation-grade attribution built before selling | 12 months post-launch, zero provider revenue → pivot to B2B data licensing |
| Split focus with Finanyst | Phase 0 is cheap and decisive | — |

---

## 14. The one thing to get right

Every number on every page traces to a stored document with a date. That single property is the entire differentiation, the regulatory defence, the provider-dispute defence, and the reason a Ghanaian investor believes the ranking. Build it first, and never ship a number that lacks it.

---

## 15. Engineering process

### 15.1 Environments

Three, no more.

| Environment | Web | DB | Engine | Purpose |
|---|---|---|---|---|
| Local | `next dev` | Supabase local (Docker) or a free cloud dev project | `uvicorn --reload` | Everyday work |
| Preview | Vercel preview per PR | **Staging Supabase project** | Render preview or staging service | Verify migrations and ingestion against real-shaped data |
| Production | Vercel production | Production Supabase | Render Starter | Live |

The staging Supabase project is non-optional here in a way it wasn't for Finanyst. Finanyst's schema changes are small and reversible; here a bad migration against append-only observation tables can destroy history you cannot re-fetch, because provider factsheets get replaced on their websites and the old ones are gone. Staging is the rehearsal, and the Storage evidence bucket is the only reason a bad restore is survivable.

**Promotion path:** branch → PR → preview deploy runs migrations against staging → review → merge to `main` → production deploy → `supabase db push` against production. Never apply a migration to production that hasn't run on staging first.

**Env var discipline.** Values live in exactly three places: `.env.local`, Vercel project settings, and Render service settings. Every one of them is validated at boot by a Zod schema that throws on a missing or malformed value. The Finanyst `PYTHON_ENGINE_URL` incident — two days spent hunting Vercel, middleware, and RLS for what was a local variable pointing at nothing — is prevented by six lines of startup validation.

### 15.2 CI pipeline

Runs on every PR. Ordered so the cheapest checks fail first.

1. `tsc --noEmit` — **against a declared baseline of 0.** Start clean and stay clean. Finanyst carried "23 errors" for weeks, 23 of which turned out to be latent bugs in a single component. A stable error count is not a clean one, so don't allow a count at all. Also note: a fatal parse error makes the count *drop* to 1, not rise — a count of 1 means something is structurally broken.
2. `eslint`
3. `vitest run` — unit tests for scoring wrappers, money helpers, validation rules, compliance boundary
4. `pytest` in `/engine` — including the golden-file suite
5. **Compliance lint** — scans result templates and rendered copy for banned constructions ("you should invest", "we recommend you", allocation percentages adjacent to product names). Fails the build.
6. **Placeholder check (new in 1.1)** — renders every product and provider page and fails the build if any numeric field contains `NaN`, `Infinity`, `undefined`, `null`, `--`, or an empty metric slot. A metric that cannot be populated must be *absent from the DOM*, never rendered as a placeholder. §16.3 is a live production example of why: on a finance site `NaN%` reads as broken software, and broken software destroys the one asset a trust-positioned product has.
7. **Freshness check (new in 1.1)** — fails if any page template can render a figure without an accompanying `verified_on` date. Every number carries its date or it does not ship.
8. **Performance budget** — bundle analysis on `/products/[slug]` and `/compare/[a]/[b]`, fails above 100KB JS
9. **Migration dry-run** against staging
10. Preview deploy

Items 5 through 8 are the ones most people would cut. Don't. They protect the four properties you cannot retrofit — regulatory posture, the appearance of competence, the honesty of every displayed figure, and mobile-data cost to a Ghanaian user.

### 15.3 Testing pyramid

**Golden-file tests (`/engine/tests/golden/`) are the foundation.** A committed fixture set: a synthetic money-market fund, a volatile equity fund, a fund with a gap in its price series, a fund that crosses zero return, a fund with only 11 months of history. Each has an expected output JSON. Any code change that moves a golden number is a methodology change requiring a `METHODOLOGY_VERSION` bump and a `/methodology` changelog entry — never a silent fix.

This is the direct lesson from Finanyst's benchmark ranges: figures the code leaves to discretion get resolved differently each run, and the divergence is invisible until a user compares two outputs. Here the equivalent failure is two providers computing a different rank from the same published methodology.

**Unit tests** for: pesewa arithmetic and rounding, validation rules (each rule gets a passing and a failing fixture), peer-group assignment, coverage gating and weight renormalisation, dedupe key generation, token signing and verification.

**Integration tests** for the ingestion path: a stored fixture PDF → extraction → validation → approval → published row, asserting provenance is attached at every step.

**Deliberately not automated:** end-to-end browser tests. At this scale they cost more to maintain than they catch. The `/admin/health` page plus the weekly QA ritual covers the same ground for a fraction of the effort.

**Data QA is a test, not a chore.** A weekly assertion suite that runs against production and posts results to `/admin/health`: no product published with data older than its staleness threshold, no score published below the coverage floor, no NAV series with a gap longer than 30 days, no product whose fee record has no `source_id`, every published provider has a licence row verified within 120 days.

### 15.4 Cadence and definition of done

Two-week cycles mapped to the phases in §11. One phase may span two or three cycles; never run two phases concurrently.

A change is done when: it's merged, migrations are in the repo and applied to staging then production, tests cover the new logic, any new numeric behaviour has a golden file, any new table has all four RLS policies, any user-facing number shows its source and verified date, and `/admin/health` still passes.

Three habits from the Finanyst build that matter more here, not less:

- **Verify the edit, not the commit.** A successful `git push` proves nothing about a file that had no changes to stage. Read the file back after every scripted edit.
- **Be suspicious of anything that can legitimately succeed at zero rows.** A delete blocked by a missing RLS policy and a delete that matched nothing are indistinguishable. So is a multi-line PowerShell replacement that silently failed to match on a CRLF file. Assert the row count.
- **One command at a time.** Multi-command blocks made diagnosis harder on the Finanyst sessions; against a database holding irreplaceable history, that's a worse trade.

### 15.5 What "complete" means for this app

The app is finished for v1 when a Ghanaian can search a fund, see its cost, real return, worst fall and access terms, click through to the source document behind every one of those numbers, compare it against its true peers, answer four questions and get a factual shortlist, and reach the provider through a link you can bill for and defend in a reconciliation meeting.

Everything beyond that — portfolio tracking, WhatsApp, the API, mobile apps — is Year 2, and each one is a bigger business than the last. None of them work if the numbers aren't trustworthy, which is why the whole architecture is bent toward that single property.

---

## 16. Competitive landscape and failure analysis

*Added in v1.1. This section corrects an error in v1.0, which grouped three Ghanaian data products together as cautionary failures. Only one of them failed. The other two are instructive for different reasons, and one of them is a serious live incumbent.*

### 16.1 Doobia — a real incumbent, not a cautionary tale

Doobia operates a Ghana mutual fund performance tracker segmented by fund category (money market, fixed income, balanced, equity, ethical, real estate), a "Doobia Jones" ranking across the CIS universe, a members-only screener behind free registration, and a reports archive running from 2014 to 2026. It has extended the same model into Nigeria and Kenya.

That is twelve-plus years of accumulated history across three markets, still publishing. Treat it as the incumbent it is.

**The consequence for strategy.** The "cleanest database of Ghanaian investment products" moat from the strategy document is weaker than it reads — a large part of that catalogue already exists and has a decade of history behind it that cannot be back-filled. Do not compete on catalogue depth.

**What is actually open.** Doobia answers *"how did fund X perform"*. It does not answer *"I have GH₵1,000 for eight months — what are my realistic options, what will they cost me after fees, what will they be worth after inflation, and where do I actually sign up"*. The gap is goal-matching, cost transparency, real returns and provider routing — the decision layer, not the data layer. That is why §7.1, the quiz, and the outbound router matter more than catalogue size, and why Phase 0 tests whether the *ranking* is better than an investor's own research rather than whether the *database* is bigger.

### 16.2 The Finance Focus — the genuine failure, and its exact mechanism

Its tracker still carries a last-updated date of 27 October 2022: a single flat HTML table of annual returns from 2010 to 2022, with no per-fund pages, no fee data, no risk metrics, no source links, and no date attached to any individual figure.

**Why it stopped.** Not fatigue in any vague sense. The structure had a fatal property: **the cost of an update was constant and the return on an update was zero.** Refreshing that table produced no new page, no new search traffic, no email worth sending, no revenue, and no reason for anyone to visit on the day it was refreshed. It was pure cost, borne by one person. Pure-cost activities that depend on individual discipline stop — that is arithmetic, not character.

*Counter:* §7.7 — every cycle writes to `content_updates` and generates a dated, indexed change page. The maintenance burden must produce a compounding asset or it will not survive contact with a busy month.

**The second and worse failure.** The page remains indexed and still presents 2022 figures with no indication that they are four years old. It did not fail safe; it degraded into something actively misleading. This is the strongest argument for automatic staleness decay (§4, rule 4) — that mechanism is not primarily a data-quality feature, it is **insurance against your own future inattention.** Design for the version of yourself that gets pulled into Finanyst for three months. The site should visibly say "prices not published recently enough" rather than quietly lie.

### 16.3 Black Star Group — the empty-metrics failure, live in production

Black Star is not an independent comparator: it is an SEC-licensed advisor and brokerage publishing analytics alongside its own funds. Two lessons, both valuable.

**Lesson one — interface built ahead of data.** Their fund pages carry slots for 3-year Sharpe ratio, annualised return, volatility, beta, Sortino ratio, max drawdown and alpha. Across the funds and indices published, those fields render as `--` and `NaN%`. A three-year Sharpe ratio requires three years of clean NAV observations plus a risk-free series; that substrate is genuinely hard to assemble in Ghana, and without it a sophisticated UI degrades into placeholder text.

The damage is worse than an empty field. On a finance site, `NaN%` reads as broken software — and a product whose entire proposition is *trust the numbers* cannot afford to look broken.

*Counters:* the coverage gate and `MIN_HISTORY_MONTHS` in `scoring-config.ts`, the `DISPLAY_RULES` blocklist in the same file, the new CI placeholder check (§15.2 item 6), and the narrow-and-complete phase ordering (§11, Phase 1). Ship fifteen complete products before eighty incomplete ones.

**Lesson two — the structural conflict.** A licensed fund manager publishing rankings of a universe that includes its own funds is conflicted whatever its intentions. This is the positioning wedge, and it is only credible if the firewall is real: hence the comment on `provider_commercials` that no scoring code path may join that table, and the separation of organic ranking from sponsorship and leads.

### 16.4 The model is already proven in Africa — study it, don't reinvent it

*Added in v1.2, and it corrects a second overstatement. v1.1 claimed goal-matching, cost transparency and provider routing were "open ground". That is true of Ghana as far as can be established, and wrong about the model, which is running in two of Africa's largest markets.*

**Serrari Group (Kenya)** is close to a working implementation of this entire architecture. It compares 163+ investment products side by side — money market funds, fixed deposits, T-Bills, T-Bonds, unit trusts, REITs, SACCOs and savings accounts — with live yields updated daily, free to use. Point for point against the design here:

| Design decision in this document | Serrari's live equivalent |
|---|---|
| Independence, stated plainly | "Serrari tracks and compares funds — we do not manage money or hold deposits. To invest, open an account directly with a licensed fund manager." |
| Tracked provider routing (§7.4) | Marketplace links directly to each fund's onboarding — compare, then click through |
| Goal matching (§7.6) | Rankings framed around emergency fund, short-term savings, MMF vs SACCO vs fixed deposit vs T-bill |
| Published methodology (§6) | "Product scores are algorithmic — not recommendations" |
| Compliance boundary (§8) | "Independent financial data and educational tools… not investment, tax, or legal advice" |
| Published indices (§7.8) | Serrari Average and Leaders indices, recalculated daily |
| Cost transparency (§7.1) | Explicit fee-then-tax walkthrough on every yield |

**nairaCompare (Nigeria)** runs the same play in the larger market, comparing money market rates, performance, fees and features across providers, alongside loans, savings and credit-score products — the NerdWallet model, built and operating.

**In Ghana**, the closest is Achieve by Petra: goal-based savings with automated mutual fund investment, but selling a single provider's own products. Not an independent comparator.

**What this means, honestly.**

*It is validation, and strong validation.* Two teams independently converged on nearly this architecture under comparable conditions — African market, high inflation, mobile-money rails, money-market funds dominating retail. That de-risks the concept far more than any amount of reasoning from first principles.

*It also removes the idea itself as a moat.* Serrari's marginal cost of adding Ghana is far below your cost of building from zero: they already have the ingestion engine, the methodology, the page templates, the index concept and the brand. They publish Ghana macro coverage already, so the market is visibly on their radar even though their comparator tools remain Kenya-only today. **Your defensible position is speed to a complete Ghana dataset and direct relationships with Ghanaian fund managers — nothing else.**

*It changes which product to study.* Serrari, not Morningstar or NerdWallet, is now the primary reference. Same continent, same inflation problem, same mobile-money rails, same regulatory posture, and a live answer to nearly every design question here. Morningstar remains useful for data architecture at scale; it is the wrong model for a market this size.

**Verify the Ghana gap yourself.** No visible independent multi-provider comparator for Ghana is not the same as none existing — a stealth-stage startup or a bank's internal roadmap would not surface in a search. Ask the fund managers directly during Phase 0 interviews; they will know who has approached them. Treat "nothing visible" as a working assumption with an expiry date, not a finding.

**What was taken from Serrari into this document:** deposit products in the universe (§11), the net-of-tax yield bridge (§7.1), published indices (§7.8), and a diaspora filter as a first-class Phase 3 feature rather than a Year-2 idea — which matters given a UK base and a Ghanaian network.

### 16.5 The competitive position, stated plainly

| | Doobia (GH) | Black Star (GH) | Finance Focus (GH) | Serrari (KE) | This product |
|---|---|---|---|---|---|
| Covers Ghana | Yes | Yes | Frozen | **News only** | Yes |
| Independent of providers | Yes | **No** | Yes | Yes | Yes |
| Catalogue depth | **12+ yrs** | Own funds | Frozen 2022 | **163+ products** | Building |
| Data currency | Current | Current prices | **4 yrs stale** | **Daily** | Enforced by decay |
| Metrics populated | Partial | **`NaN` / `--`** | Annual only | Yes | Coverage-gated |
| Deposit products included | No | No | No | **Yes** | Yes (v1.2) |
| Source shown per figure | Not evident | No | No | Not evident | **Yes, mandatory** |
| Net of tax | No | No | No | **Yes** | Yes (v1.2) |
| Net of inflation | No | No | No | No | **Headline metric** |
| Goal matching | No | No | No | **Yes** | Yes |
| Published methodology | Not evident | No | n/a | Partial | **Yes, from code** |
| Routes to a provider | No | Own products | No | **Yes** | **Yes, tracked** |

Read the Serrari column carefully: on most rows they already do it. **The only column entry that is uniquely yours is Ghana coverage, and the only metric nobody publishes anywhere is the post-inflation return.** Everything else is execution quality, not differentiation — which is a harder position than v1.0 described, and a more accurate one.

The remaining bold entries in the final column are operational disciplines rather than technology advantages, which is precisely why they are enforced by the architecture: discipline erodes when a solo founder gets busy, and code is the only thing that does not get tired.

### 16.6 What would tell you the position is wrong

Watch for these; each would require a rethink rather than a push.

- Doobia adds goal matching, published methodology, or provider routing before you launch.
- Phase 0 shows fewer than 60% of products yield a verified TER and 12-month series — the ranking cannot be built as designed, and the honest response is to narrow to money market funds and T-bills permanently.
- Ghanaian investors shown the Phase 0 ranking say it is roughly as hard as their own research. The whole thesis rests on it being materially easier.
- Weekly refresh still exceeds an hour after the pipeline is built. Automate further or cut the universe; do not absorb it.
- **Serrari or nairaCompare announces Ghana coverage.** This is the highest-probability competitive event in the list, because their marginal cost of entry is low and Ghana is already in their editorial coverage. If it happens before you launch, the honest options are to compete on depth of verification and provider relationships, or to approach them as a Ghana partner rather than a rival. Set a calendar reminder to check both quarterly.

---

## 17. Data acquisition runbook

*Added in v1.3. This is the operational core of the business. Everything in §5 describes the machinery; this describes what actually goes into it and how you get it.*

### 17.1 There is no single source — there are five, with different footings

| Data class | Source | Cadence | Parser | Difficulty |
|---|---|---|---|---|
| Licence status, category, entity list | SEC licensee register | Weekly | `html` | Easy |
| Fees, TER, minimums, dealing terms | Prospectus / scheme particulars | Annual | `llm` | Medium |
| Fund size, holdings, audited performance | Investors' reports (annual + half-yearly) | Half-yearly | `llm` | Medium |
| **Unit price / NAV series** | Provider websites, factsheets | Daily–weekly | `llm` + `html` | **Hard — this is the job** |
| T-bill, CPI, FX, GSE index | Bank of Ghana, Ghana Statistical Service, GSE | Weekly–monthly | `html` / `csv` | Easy |
| Deposit and savings rates | Bank websites | Monthly | `html` | Easy |

Two of these are legally guaranteed to exist, which matters more than it sounds. Every scheme must file a prospectus with the SEC and give a summary disclosure document to each purchaser, and once filed is obliged to provide investors with financial statements and other information on a regular basis. Separately, LI 1695 requires the manager of a unit trust and the board of a mutual fund to prepare an investors' report for **each annual and half-yearly accounting period**, including the manager's performance statement and a statement of assets and liabilities.

So fees, fund size and audited performance are not favours you're asking for. They are documents that must exist and be available to investors. You are one of the investors.

### 17.2 SEC licensee register — scrape spec

**No API.** No developer portal, no JSON endpoints, no `data.sec.gov.gh`. The register is server-rendered PHP, one page per operator type, at stable enumerable URLs:

```
licensees.sec.gov.gh/                              → operator type index
licensees.sec.gov.gh/licensees/FundManager.php
licensees.sec.gov.gh/licensees/MutualFunds.php
licensees.sec.gov.gh/licensees/ExchangeTradedFunds.php
licensees.sec.gov.gh/licensees/PrivateFunds.php
licensees.sec.gov.gh/licensees/Registrars.php
licensees.sec.gov.gh/licensees/SecuritiesExchanges.php
```

This is a better outcome than it looks. Stable HTML tables mean **deterministic parsing with cheerio, not LLM extraction** — free, fast, and structurally incapable of hallucinating. Seeds are in `seed_source_targets.sql`.

**Method:** weekly fetch → snapshot raw HTML to the evidence bucket → parse with cheerio → diff against the previous snapshot. The diff yields licence-status change events at zero marginal cost, which flow into `content_updates` and the monthly change page (§7.7). Respect `robots.txt`, one request per page, identify your user agent honestly.

### 17.3 The licence-status rule — read this before displaying anything

The register carries a regulator-published status classification, surfacing markers such as *"This licensee has regulatory issues that require attention."* That is a supervisory signal from the regulator itself, and nothing you could compute comes close to it.

**It is also the single most likely way this product gets you sued.** The SEC has stated publicly that it has not issued any list of fund management firms that are unsafe to invest with; that the classification on its website only indicates the status of licensees with regulatory issues or unresolved complaints — some suspended, some having voluntarily surrendered licences, others at various stages of resolving complaints; and that it is inaccurate and wrong to universally categorise all those flagged as companies that are not safe to invest in.

**Therefore, absolutely:**

- Render the status from a fixed verbatim map (`licence-status.ts`), never paraphrased, never generated.
- Never translate a flag into "unsafe", "avoid", "warning", "risky", or a red visual treatment implying danger.
- Always link to the SEC register beside the status, with the date checked.
- Never apply a TrustScore penalty that reads as a safety judgement. A flagged licensee scores lower on *licence verified and current* — that is a factual component, not a verdict.
- Enforce it: a CI check that the licence-status string in any rendered output matches an entry in the map exactly.

This belongs in `lib/compliance/boundary.ts` alongside the investment-advice rules, and for the same reason — it is a rule that will erode by accident once you are shipping fast.

### 17.4 Solving the history problem

You need 12 months minimum before anything can be scored, and you cannot scrape the past. Run all three routes in parallel.

**SEC annual reports.** Year-by-year CIS tables — returns of unit trusts, asset allocation with NAV and expense ratio, AUM by fund manager. Three reports give you an annual backbone immediately.

**annualreportsghana.com and Databank research.** This assembly has been done before: an academic study built a survivorship-bias-free dataset of yearly after-fee returns for all Ghanaian mutual funds and unit trusts from January 2011 to December 2019, drawn from the Ghana SEC, individual asset management companies, the GSE, Databank research and annualreportsghana.com. That is a tested source list, and the authors are contactable — academics generally share methodology and sometimes data.

**Ask the providers.** A fund's price history is marketing material, not a secret. This is the substance of the Founding Partner ask (§17.6).

**Record dead funds.** The study above minimised survivorship bias by including funds alive *and* dead across the period. If you track only survivors, every historical average you publish flatters the industry, and a fund manager will eventually catch it. The SEC's public revocation notices give you incorporation dates, licence dates and specific reasons per firm — that is your dead-entity source.

### 17.5 Three acquisition modes, in the order you will use them

**Mode 1 — Fetch (months 0–6).** Cron walks `source_targets`, downloads, hashes, stores, extracts. Fragile: a site redesign breaks a parser. Fine for the first 20 providers.

**Mode 2 — Structured submission (months 3–12).** The one that makes this survivable. Providers email back a one-tab template (`provider-price-submission-template.csv`) weekly or monthly. **You still require the supporting factsheet as the source document** — a submitted number without a document has no provenance and no defence in a dispute.

**Mode 3 — Provider portal (Phase 5).** They enter prices, you verify against the attached document, approve, publish. **This is the strategic endgame: it flips ingestion from pull to push and turns your largest recurring cost into the provider's marketing task.** It is also the point at which the operational risk in §16.2 stops being existential.

### 17.6 Provider outreach — the data ask

Send this after you have a working catalogue page for their fund, not before. Showing a provider their own product already displayed, accurately, changes the conversation entirely.

> **Subject:** Your fund on [Platform] — checking our figures are right
>
> Dear [Name],
>
> I'm building [Platform], an independent comparison site for Ghanaian investment products. We list regulated funds with their fees, minimums, liquidity terms and performance, and link investors directly to the provider to open an account. We don't manage money, hold deposits, or take payment for rankings.
>
> [Fund name] is already listed: [link]. Every figure there cites the document we took it from and the date we checked it.
>
> Two requests:
>
> 1. Could you confirm the fees, minimum investment and redemption terms we've shown are current?
> 2. Could you send the fund's unit price history since inception, in any format you have? We use it to calculate return, volatility and drawdown on a published methodology: [link].
>
> As a founding partner there's no charge to be listed, and I'll send you monthly figures on how many investors viewed and compared your fund.
>
> Happy to come in and walk through the methodology.
>
> [Name] · [Phone] · [Email]

Three things that make this work: the fund is already listed so the ask is *correction*, not *permission*; the methodology is public so you look like an analyst rather than a lead broker; and the analytics offer gives them something they cannot currently get.

### 17.7 Approaching the SEC

Ask the **Funds Management Department** — it owns fund management companies, custodians and trustees. Contact points are public: `info@sec.gov.gh`, toll-free 0800 100 065, main line +233-302-768970-2.

Two asks, in order:

1. **A structured export of the licensee register.** Low sensitivity — it's already public, you're asking for CSV instead of HTML. Good chance of a yes, and it removes your only scraping dependency.
2. **CIS returns data.** Fund managers already file periodic returns to the Commission under the Investment Guidelines for Fund Managers, in the forms specified in Schedules 1 and 2. Bigger prize, harder ask.

Frame it as investor protection: a product whose purpose is *verify the licence before you invest* sits alongside the SEC's own public warnings about unlicensed schemes, not against them. Offer to display licence status prominently and link back to the register.

**Build the scraper before you ask.** "I've built this, here's what it does, a feed would make it more accurate for your licensees" is a far better meeting than a concept.

### 17.8 Rules that do not bend

1. **Never take numbers from Doobia, Black Star, or any aggregator.** Their terms likely prohibit it, one explicitly blocks automated access, you would inherit errors you cannot detect, and "we copied a competitor" is not a defence in a dispute. Primary sources only.
2. **Provider-submitted numbers still need a document.** No document, no publication.
3. **Licence status renders verbatim** (§17.3).
4. **Record dead funds and revoked licences.**
5. **Every fetch snapshots raw bytes before parsing.** The parse can be redone; a page that has since changed cannot be re-fetched.

### 17.9 Week one — the actual sequence

1. Scrape the full licensee register across all operator-type pages into a spreadsheet. That single artifact is your provider universe *and* your sales prospect list.
2. Pick the ten largest fund managers by AUM from the most recent SEC annual report.
3. For each, spend 30 minutes recording: unit price page URL, factsheet URL, prospectus URL, publication cadence, format. That is `source_targets`, hand-built.
4. Download the last three SEC annual reports; extract the CIS tables as your history backbone.
5. Add the five deposit-side sources: three or four bank fixed-deposit rate pages plus the BoG T-bill auction results.
6. **Time yourself doing one full manual refresh of those ten.** Multiply by 52.

Step 6 is the Phase 0 exit test and the honest annual cost of the business. Step 3 is the one people skip, and it is where you discover which providers publish prices at all — expect the distribution to be uneven, with some publishing daily, some quarterly, and some only on request. That distribution determines your launch universe more than any strategic preference, which is exactly why Phase 0 comes before code.
