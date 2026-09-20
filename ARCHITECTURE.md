# Cedafin — how the parts fit together

**What this is.** A short description of the system as it exists today: which
components there are, what calls what, and what runs where. Short on purpose —
it is consulted often and must be readable in full.

**What this is not.** The design document. `docs/DESIGN-2026-08.md` holds the
original specification: the constraints, the competitive analysis, the phasing.
Much of its reasoning still holds and it is worth reading once. It describes
what was intended in August 2026, not what was built.

Two files cite this note by section — `lib/data/funds.ts` for the staleness
policy, `engine/metrics.py` for the metrics contract — and until today it did
not exist. Every architectural question was answered by searching the
codebase, which is slow and twice produced a confident wrong answer that took
hours to unpick.

Written 19 September 2026, after a week in which the Treasury bill benchmark
sat three weeks stale, the metrics engine turned out never to have been
deployed, and a load step was found deleting everything a fetcher had just
written.

---

## 1. What talks to what

```
  regulator and provider websites
            │
            ▼
      fetch_*.py ──────────────► data/            (documents, kept)
            │
            ▼
      extract_*.py
            │
            ▼
      load_*.py  ─────────────► Supabase
                                   │
      compute_metrics.py ──────────┤  (imports engine/metrics.py)
                                   │
                                   ▼
                            Next.js on Vercel ───► cedafin.com
```

**The Next.js app talks only to Supabase.** It does not call the metrics
engine, or anything else. Every figure on every page is either a row in the
database or computed in TypeScript from rows in the database.

**The scripts talk to Supabase and to the outside world.** They run on a
laptop or in GitHub Actions; both write to the same database.

**There is no server other than Vercel.** See §4.

---

## 2. The metrics engine

`engine/metrics.py` holds the return calculations — windows, coverage
thresholds, real returns against CPI. `compute_metrics.py` imports it and
calls `compute_metrics(payload: dict) -> dict` directly, in the same process.

`engine/main.py` is a FastAPI wrapper around the same function. **It is not
deployed anywhere and nothing calls it.** It exists for the day a page needs
computation at request time.

That wrapper was, for a while, the only route to the maths:
`compute_metrics.py` POSTed to `localhost:8000`. The service was never
deployed, so every scheduled run failed — and the step was marked
`continue-on-error`, so the job went green. The metrics on the live site were
as old as the last time somebody ran the script by hand.

**If the wrapper is ever deployed**, make `PYTHON_ENGINE_URL` required again in
`lib/env.ts` and decide which of the two paths is authoritative. Two routes to
the same calculation will drift.

---

## 3. What runs where, and when

Scheduled in `.github/workflows/fetch-market-data.yml`:

| Job | When | Does |
|---|---|---|
| `gold` | weekdays 17:30 | Bank of Ghana gold coin circular |
| `tbills` | Fridays 19:00 | Bank of Ghana Treasury bill rates table |
| `gse` | 8th monthly | Ghana Stock Exchange monthly report |
| `apr` | monthly | Bank of Ghana lending rate return |
| `registers` | 1st monthly | SEC and BoG register snapshots |
| `check` | daily 20:00 | `check_consistency.py` |

**Everything else runs by hand.** The `discover_*.py` scanners, every
`load_*.py` for a specific provider, `consolidate_brokers.py`,
`index_archive.py`, `compose_brief.py`.

**Steps that load data must not be `continue-on-error`.** A fetch may fail
because a source is down, which is not a data error. A load failing means data
did not land, and that must turn the job red. The distinction was learned after
three weeks of green jobs writing nothing.

---

## 4. Environment and accounts

| Variable | Where | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel, GitHub secrets, `.env.local` | |
| `SUPABASE_SERVICE_ROLE_KEY` | same three | Full read and write. Never in a browser. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Vercel, `.env.local` | |
| `PYTHON_ENGINE_URL` | optional | Unused. See §2. |

**Supabase holds more than one project and the names are not obvious.**
Cedafin's is **FinancialAnalysisIntelligence**, ref `qhphyavmvawpvbssyutg`.
Finanyst's is a different project with a similar-looking ref.

An afternoon went into "the writes are not landing" when the writes were
landing and the SQL editor was open on the other project. **Check the ref in
the dashboard URL before concluding anything about missing data.**

Render hosts `finmodels-engine`, which belongs to the other project. Cedafin
has nothing deployed there.

---

## 5. Rules learned the hard way

**Read a page's own navigation. Never guess URLs.** Three fetchers were
rewritten for this: the APR notices, the GSE reports, and the Treasury bills.
The last tried eighteen constructed PDF addresses a week, found nothing for
three weeks, and reported success each time. Bank of Ghana publishes a rates
table; reading it takes one request.

**One writer per table.** `load_tbills_as_products.py` began with
`DELETE /nav_observations?product_id=eq.{pid}` and re-inserted from a CSV.
Correct when it was the only writer. Destructive the moment a second appeared:
it deleted every observation the new fetcher wrote, eight seconds after it
wrote them.

**Fail loudly.** A fetcher that cannot reach its source must say so, not report
zero rows as though the week was quiet. A blank figure is honest; a stale one
is confident and wrong.

**Judge freshness by cadence.** A price published every working day is stale at
three weeks. A fund factsheet is not. One threshold for both meant the gold
series read "Prices current" while it sat three weeks behind. See
`stalenessOf` in `lib/data/funds.ts` and `check_freshness` in
`check_consistency.py`.

**Stop after consecutive failures.** The gold fetcher once spent twenty-two
minutes timing out once per missing day. A backlog makes a job slower exactly
when the source is least likely to answer.

**Derive counts; do not type them.** "Six of 97 providers" became eight, then
nine, then eleven within a week, and was wrong on the site in between each
time. `getDisclosureCounts()` exists for this.

**Identify the scanner honestly.** `polite_fetch.py` sends a named user agent
and honours robots.txt. Where a site refuses it, a person reads the page and
the record says it was read by hand.

---

## 6. Known gaps, September 2026

**The Stanbic funds are stuck at March 2026, and it is a format change.**
SIMS factsheets published a monthly RETURN up to March 2026 and a NAV from
April. The extractor builds one series per product and picks whichever kind
has more points — 25 chained against 3 quoted — so the three NAVs are read
and discarded.

They cannot simply be joined. A chained index and a dealing price have no
common scale: the index base is arbitrary, so the ratio between the last
index level and the first NAV means nothing.

Doing it properly means the extractor emitting both series, the unique index
growing to include `series_kind`, and `toFundRow` choosing a series rather
than taking the kind from the last observation — which today would label a
mixed array "quoted" and chart index levels as prices.

Left alone deliberately, September 2026: three data points against a change
that touches the extractor, the schema and every page showing a return, in
the one place a mistake produces a plausible wrong number. Worth revisiting
once SIMS have published a few more months and the NAV format looks settled.

The fee history from those factsheets DID load — 30 new charge rows — so the
collection was not wasted.

**Bank of Ghana stopped publishing gold coin circulars after 2 September.**
Not a fetcher fault. Worth publishing as a finding.

**CPI does not span most observation windows.** 46 products get no real return,
and `compute_metrics.py` says plainly not to display one for them.
`fetch_cpi_index.py` exists; whether it has been run is another question.

**44 published products carry a minimum with no source.** Flagged daily by the
consistency check.

**`/admin/health` does not exist**, though `lib/env.ts` offers `checkEngine()`
for it.

**Homepage and `/funds` count funds differently** — 88 against 144. Both
derived, counting different things, and a reader moving between them sees two
numbers.

---

## 7. When this document is wrong

It will be. Amend it in the same commit as the change that made it wrong — a
note that lags the code is worse than none, because it is believed.
