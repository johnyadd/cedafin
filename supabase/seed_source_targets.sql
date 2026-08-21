-- ============================================================================
-- seed_source_targets.sql — the crawl plan
--
-- Run AFTER 0001_core_schema.sql. Provider-specific rows are added by hand as
-- you complete step 3 of the week-one sequence (ARCHITECTURE.md §17.9); these
-- are the sources that exist independently of any provider.
--
-- parser: 'html' = deterministic cheerio parse (free, cannot hallucinate)
--         'llm'  = Claude extraction against a strict schema, then review
--         'csv'  = direct structured download
--         'manual' = keyed by hand into /admin, still needs a source document
-- ============================================================================

-- ---------------------------------------------------------------------------
-- SEC licensee register. No API exists; these are stable server-rendered PHP
-- pages, one per operator type. Weekly fetch, snapshot, cheerio parse, diff
-- against the previous snapshot to produce licence-change events for free.
-- ---------------------------------------------------------------------------

insert into source_targets (provider_id, label, url, kind, parser, cadence_days) values
  (null, 'SEC register — operator type index',
   'https://licensees.sec.gov.gh/', 'sec_register', 'html', 7),
  (null, 'SEC register — fund managers',
   'https://licensees.sec.gov.gh/licensees/FundManager.php', 'sec_register', 'html', 7),
  (null, 'SEC register — mutual funds',
   'https://licensees.sec.gov.gh/licensees/MutualFunds.php', 'sec_register', 'html', 7),
  (null, 'SEC register — exchange traded funds',
   'https://licensees.sec.gov.gh/licensees/ExchangeTradedFunds.php', 'sec_register', 'html', 7),
  (null, 'SEC register — private funds',
   'https://licensees.sec.gov.gh/licensees/PrivateFunds.php', 'sec_register', 'html', 7),
  (null, 'SEC register — registrars',
   'https://licensees.sec.gov.gh/licensees/Registrars.php', 'sec_register', 'html', 7),
  (null, 'SEC register — securities exchanges',
   'https://licensees.sec.gov.gh/licensees/SecuritiesExchanges.php', 'sec_register', 'html', 7);

-- Remaining operator-type pages: enumerate them from the index page on the
-- first crawl and insert the rest here. Do not guess URLs.

-- ---------------------------------------------------------------------------
-- SEC publications. Public notices carry licence revocations (with dates and
-- reasons) — the dead-entity source that prevents survivorship bias.
-- ---------------------------------------------------------------------------

insert into source_targets (provider_id, label, url, kind, parser, cadence_days) values
  (null, 'SEC public notices', 'https://sec.gov.gh/public-notices/', 'sec_notice', 'html', 7),
  (null, 'SEC annual reports — CIS tables', 'https://sec.gov.gh/', 'sec_annual_report', 'llm', 90);

-- ---------------------------------------------------------------------------
-- Benchmarks. Without GH_TBILL_91 there is no risk-adjusted anything; without
-- GH_CPI_YOY there is no real return, which is the headline metric (§7.1).
-- Confirm the exact landing pages on first crawl.
-- ---------------------------------------------------------------------------

insert into source_targets (provider_id, label, url, kind, parser, cadence_days) values
  (null, 'Bank of Ghana — T-bill auction results', 'https://www.bog.gov.gh/', 'bog_release', 'html', 7),
  (null, 'Ghana Statistical Service — CPI', 'https://statsghana.gov.gh/', 'bog_release', 'html', 30),
  (null, 'Bank of Ghana — interbank FX rates', 'https://www.bog.gov.gh/', 'bog_release', 'html', 7),
  (null, 'Ghana Stock Exchange — market report', 'https://gse.com.gh/', 'gse_report', 'html', 7);

-- ---------------------------------------------------------------------------
-- Deposit side (schema v1.2). Cheapest data in the market and the true
-- comparison set for a saver with GH₵1,000. Add one row per bank as you go.
-- ---------------------------------------------------------------------------

-- insert into source_targets (provider_id, label, url, kind, parser, cadence_days)
-- values (<provider>, '<Bank> — fixed deposit rates', '<url>', 'provider_website', 'html', 30);

-- ---------------------------------------------------------------------------
-- Per-provider targets. Three rows per provider, added during §17.9 step 3.
-- ---------------------------------------------------------------------------

-- insert into source_targets (provider_id, label, url, kind, parser, cadence_days) values
--   (<provider>, '<Fund> — unit prices',  '<url>', 'provider_website',   'html', 7),
--   (<provider>, '<Fund> — factsheet',    '<url>', 'provider_factsheet', 'llm',  30),
--   (<provider>, '<Fund> — prospectus',   '<url>', 'prospectus',         'llm',  365);
