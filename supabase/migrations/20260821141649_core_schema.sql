-- ============================================================================
-- Ghana Investment Marketplace — 0001_core_schema.sql   (schema v1.2)
--
-- v1.1 adds content_updates: every ingestion cycle must produce a compounding
-- asset, not just overwrite yesterday's numbers. See ARCHITECTURE.md §7.7/§16.2.
-- v1.2 widens the universe to deposit products (the real comparison set for a
-- Ghanaian with GH₵1,000), adds tax treatment so yields can be shown net of
-- withholding, and adds market_indices. See ARCHITECTURE.md §16.4.
--
-- CONVENTIONS
--   money        : bigint in MINOR UNITS (pesewas for GHS, cents for USD)
--                  + a char(3) currency column. Never float, never numeric money.
--   percentages  : numeric(12,8) as DECIMALS. 0.02500000 = 2.5%. Never 2.5.
--   observations : APPEND-ONLY. Corrections insert a new row and set
--                  superseded_by on the old one. Published returns must be
--                  reproducible from history.
--   provenance   : every fact-bearing row carries source_id + verified_on.
--   RLS          : all four policies written at creation time. A delete blocked
--                  by a missing policy affects zero rows and returns NO error.
-- ============================================================================

create extension if not exists "pgcrypto";
create extension if not exists "pg_trgm";

-- ============================================================================
-- EVIDENCE
-- ============================================================================

create table sources (
  id              uuid primary key default gen_random_uuid(),
  kind            text not null check (kind in (
                    'sec_register','sec_annual_report','sec_notice',
                    'provider_factsheet','provider_website','prospectus',
                    'scheme_particulars','annual_report','bog_release',
                    'gse_report','provider_submission','manual_entry')),
  publisher       text not null,
  title           text,
  url             text,
  document_date   date,                     -- date ON the document
  retrieved_at    timestamptz not null default now(),
  storage_path    text,                     -- Supabase Storage key, immutable copy
  content_sha256  text,
  entered_by      uuid,                     -- for kind = 'manual_entry'
  created_at      timestamptz not null default now()
);
create unique index sources_sha_idx on sources(content_sha256)
  where content_sha256 is not null;
create index sources_kind_idx on sources(kind, retrieved_at desc);

-- Crawl targets: what to fetch, from whom, how often.
create table source_targets (
  id              uuid primary key default gen_random_uuid(),
  provider_id     uuid,                     -- FK added after providers
  label           text not null,
  url             text not null,
  kind            text not null,
  parser          text not null default 'llm' check (parser in ('llm','html','csv','manual')),
  cadence_days    int  not null default 7,
  last_fetched_at timestamptz,
  last_sha256     text,
  active          boolean not null default true,
  failure_count   int not null default 0,
  created_at      timestamptz not null default now()
);

-- ============================================================================
-- PROVIDERS
-- ============================================================================

create table providers (
  id                uuid primary key default gen_random_uuid(),
  slug              text not null unique,
  legal_name        text not null,
  trading_name      text,
  website           text,
  incorporated_year int,
  custodian         text,
  trustee           text,
  contact_email     text,
  contact_phone     text,
  aum_minor         bigint,
  aum_currency      char(3),
  aum_as_of         date,
  aum_source_id     uuid references sources(id),
  audited_accounts_url  text,
  status            text not null default 'draft'
                      check (status in ('draft','published','suspended','delisted')),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

alter table source_targets
  add constraint source_targets_provider_fk
  foreign key (provider_id) references providers(id) on delete cascade;

-- Licence history. Never updated in place — a status change inserts a new row.
create table provider_licences (
  id             uuid primary key default gen_random_uuid(),
  provider_id    uuid not null references providers(id) on delete cascade,
  regulator      text not null default 'SEC_GH' check (regulator in ('SEC_GH','NPRA','BOG')),
  category       text not null,             -- Fund Manager / Broker-Dealer / Investment Adviser / ...
  licence_number text,
  status         text not null check (status in
                   ('active','suspended','revoked','expired','unverified')),
  first_seen_on  date,
  verified_on    date not null,
  source_id      uuid not null references sources(id),
  created_at     timestamptz not null default now()
);
create index provider_licences_current_idx
  on provider_licences(provider_id, verified_on desc);

-- ============================================================================
-- PRODUCTS
-- ============================================================================

create table products (
  id                  uuid primary key default gen_random_uuid(),
  slug                text not null unique,
  provider_id         uuid not null references providers(id),
  name                text not null,
  -- v1.2: deposit products included deliberately. For a Ghanaian with GH₵1,000
  -- the real question is "money market fund vs fixed deposit vs T-bill vs
  -- savings account" — excluding banks answers a narrower question than the
  -- one people actually ask, and the data is cheap to collect.
  legal_structure     text check (legal_structure in (
                        'mutual_fund','unit_trust','etf','treasury_bill',
                        'treasury_bond','corporate_bond','equity','reit',
                        'pension_tier3','fixed_deposit','savings_account',
                        'other')),
  asset_class         text check (asset_class in (
                        'money_market','fixed_income','balanced','equity',
                        'real_estate','multi_asset','government_security',
                        'deposit')),
  currency            char(3) not null default 'GHS',
  -- peer_group is the ONLY ranking universe. Never rank across peer groups.
  peer_group          text generated always as (asset_class || ':' || currency) stored,
  min_initial_minor   bigint,
  min_subsequent_minor bigint,
  min_source_id       uuid references sources(id),
  min_verified_on     date,
  -- Tax treatment (v1.2). Yields are displayed net of fees AND withholding, so
  -- the headline answers "what would I actually keep". Rates differ by product
  -- type and change with the Finance Act — never hardcode them in the app.
  withholding_rate    numeric(12,8),        -- decimal, e.g. 0.08 = 8%
  tax_exempt          boolean not null default false,
  tax_note            text,
  tax_source_id       uuid references sources(id),
  tax_verified_on     date,
  dealing_frequency   text check (dealing_frequency in
                        ('daily','weekly','monthly','at_maturity','exchange_traded')),
  redemption_days     int,                  -- business days to cash
  lock_in_days        int,
  inception_date      date,
  objective           text,
  channels            text[],               -- {momo,bank_transfer,card,branch,app}
  status              text not null default 'draft' check (status in
                        ('draft','published','stale','suspended','closed')),
  stale_reason        text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index products_peer_idx on products(peer_group, status);
create index products_name_trgm on products using gin (name gin_trgm_ops);

create table product_fees (
  id            uuid primary key default gen_random_uuid(),
  product_id    uuid not null references products(id) on delete cascade,
  fee_type      text not null check (fee_type in
                  ('management','ter','performance','entry','exit',
                   'early_exit','custody','other')),
  rate          numeric(12,8),              -- decimal: 0.025 = 2.5%
  flat_minor    bigint,
  basis         text check (basis in ('annual_nav','transaction','flat')),
  conditions    text,                       -- e.g. 'redemption within 90 days'
  effective_from date not null,
  effective_to   date,
  source_id     uuid not null references sources(id),
  verified_on   date not null
);
create index product_fees_current_idx on product_fees(product_id, fee_type, effective_from desc);

-- ============================================================================
-- OBSERVATIONS (append-only)
-- ============================================================================

create table nav_observations (
  id                bigserial primary key,
  product_id        uuid not null references products(id),
  as_of             date not null,
  nav               numeric(20,8),          -- price per unit
  yield_annualised  numeric(12,8),          -- for MMF / T-bill style quotes
  fund_size_minor   bigint,
  basis             text not null default 'single'
                      check (basis in ('bid','offer','mid','single')),
  source_id         uuid not null references sources(id),
  ingested_at       timestamptz not null default now(),
  is_correction     boolean not null default false,
  superseded_by     bigint references nav_observations(id)
);
create unique index nav_live_unique
  on nav_observations(product_id, as_of, basis) where superseded_by is null;
create index nav_series_idx on nav_observations(product_id, as_of desc)
  where superseded_by is null;

-- Benchmarks. Without GH_TBILL_91 there is no risk-adjusted anything;
-- without GH_CPI_YOY you cannot show real returns.
create table macro_series (
  series_code  text not null,               -- GH_TBILL_91 | GH_TBILL_182 |
                                            -- GH_CPI_YOY | GSE_CI | GHS_USD
  as_of        date not null,
  value        numeric(20,8) not null,
  source_id    uuid not null references sources(id),
  primary key (series_code, as_of)
);

-- ============================================================================
-- DERIVED METRICS (recomputable, never hand-edited)
-- ============================================================================

create table product_metrics (
  product_id          uuid not null references products(id) on delete cascade,
  as_of               date not null,
  window_code         text not null,        -- 1m|3m|6m|1y|3y|5y|si
  total_return        numeric(12,8),
  annualised_return   numeric(12,8),
  volatility          numeric(12,8),
  max_drawdown        numeric(12,8),
  downside_deviation  numeric(12,8),
  excess_over_tbill   numeric(12,8),
  real_return         numeric(12,8),
  positive_period_pct numeric(12,8),        -- consistency
  observation_count   int not null,
  coverage            numeric(5,4) not null,-- observed / expected points
  engine_version      text not null,
  computed_at         timestamptz not null default now(),
  primary key (product_id, as_of, window_code)
);

-- ============================================================================
-- INGESTION STAGING  (nothing writes straight to published tables)
-- ============================================================================

create table extractions (
  id             uuid primary key default gen_random_uuid(),
  source_id      uuid not null references sources(id),
  provider_id    uuid references providers(id),
  product_id     uuid references products(id),
  model          text,
  prompt_version text,
  payload        jsonb not null,            -- the entities array, never merged
  validation     jsonb,                     -- deterministic rule results
  state          text not null default 'extracted' check (state in
                   ('extracted','flagged','approved','rejected','superseded')),
  reviewed_by    uuid,
  reviewed_at    timestamptz,
  review_note    text,
  created_at     timestamptz not null default now()
);
create index extractions_queue_idx on extractions(state, created_at);

-- ============================================================================
-- SCORING (immutable runs — a rank must be reproducible on demand)
-- ============================================================================

create table score_runs (
  id                   uuid primary key default gen_random_uuid(),
  methodology_version  text not null,
  config               jsonb not null,      -- the FULL config at run time
  engine_version       text not null,
  as_of                date not null,
  started_at           timestamptz not null default now(),
  finished_at          timestamptz,
  product_count        int,
  scored_count         int,
  notes                text
);

create table scores (
  score_run_id    uuid not null references score_runs(id) on delete cascade,
  product_id      uuid not null references products(id) on delete cascade,
  profile         text not null check (profile in
                    ('conservative','balanced','growth','beginner')),
  scored          boolean not null,
  unscored_reason text,                     -- 'insufficient_coverage' | 'insufficient_history'
  total           numeric(6,3),
  subscores       jsonb,
  coverage        numeric(5,4),
  peer_group      text not null,
  rank_in_peer    int,
  primary key (score_run_id, product_id, profile)
);
create index scores_lookup_idx on scores(score_run_id, profile, peer_group, rank_in_peer);

create table trust_scores (
  score_run_id  uuid not null references score_runs(id) on delete cascade,
  provider_id   uuid not null references providers(id) on delete cascade,
  total         numeric(6,3),
  components    jsonb,
  coverage      numeric(5,4),
  primary key (score_run_id, provider_id)
);

-- ============================================================================
-- PUBLISHED INDICES  (v1.2)
--
-- A "Ghana MMF Average" and a "Leaders" index, recomputed on every cycle.
-- Cheap once the data exists, quotable by journalists, and it gives the
-- monthly change page (§7.7) a headline that is about the market rather than
-- about one fund. Constituents are stored so any published figure is
-- reproducible — same discipline as score_runs.
-- ============================================================================

create table market_indices (
  code           text not null,             -- GH_MMF_AVG | GH_MMF_LEADERS | GH_FD_AVG
  as_of          date not null,
  value          numeric(20,8) not null,    -- the index level or average yield
  constituents   uuid[] not null,           -- product ids included
  method         text not null,             -- 'equal_weighted_net_yield' etc.
  engine_version text not null,
  computed_at    timestamptz not null default now(),
  primary key (code, as_of)
);
comment on table market_indices is
  'Constituents stored so any published index level can be reproduced years later.';

-- ============================================================================
-- CONTENT ENGINE  (v1.1)
--
-- Counter to the mechanism that killed a prior Ghanaian tracker: a refresh
-- cycle whose cost is constant and whose return is zero eventually stops.
-- Each approved ingestion batch writes a row here; these rows generate the
-- dated "what changed this month" page, the alert email body, and the feed.
-- ============================================================================

create table content_updates (
  id             uuid primary key default gen_random_uuid(),
  period         date not null,             -- month the change belongs to
  change_type    text not null check (change_type in
                   ('nav_moved','fee_changed','minimum_changed','new_product',
                    'product_closed','licence_changed','rank_moved',
                    'methodology_changed','went_stale')),
  product_id     uuid references products(id) on delete set null,
  provider_id    uuid references providers(id) on delete set null,
  old_value      text,
  new_value      text,
  delta          numeric(20,8),
  headline       text not null,             -- one human-readable line
  source_id      uuid references sources(id),
  score_run_id   uuid references score_runs(id),
  published      boolean not null default false,
  created_at     timestamptz not null default now()
);
create index content_updates_period_idx on content_updates(period desc, change_type);
create index content_updates_product_idx on content_updates(product_id, created_at desc);

comment on table content_updates is
  'Every ingestion cycle writes here. If a cycle produces no rows, the cycle produced no asset.';

-- ============================================================================
-- DISTRIBUTION, ATTRIBUTION, COMPLIANCE AUDIT
-- ============================================================================

-- Doubles as the compliance audit log: what was shown, to whom, under which
-- methodology version.
create table quiz_sessions (
  id               uuid primary key default gen_random_uuid(),
  session_id       uuid not null,
  goal             text,
  amount_min_minor bigint,
  amount_max_minor bigint,
  currency         char(3) default 'GHS',
  horizon_months   int,
  risk_tolerance   text check (risk_tolerance in ('low','medium','high')),
  liquidity_need   text check (liquidity_need in ('immediate','moderate','none')),
  score_run_id     uuid references score_runs(id),
  profile_used     text,
  shown_product_ids uuid[],
  compliance_phase int not null,
  created_at       timestamptz not null default now()
);

create table outbound_clicks (
  id               uuid primary key default gen_random_uuid(),
  token            text not null unique,
  product_id       uuid references products(id),
  provider_id      uuid not null references providers(id),
  session_id       uuid,
  quiz_session_id  uuid references quiz_sessions(id),
  context          text,                    -- results|compare|product|provider|article
  ip_hash          text,
  ua_hash          text,
  referrer         text,
  created_at       timestamptz not null default now()
);
create index outbound_billing_idx on outbound_clicks(provider_id, created_at);

-- Immutable ledger. Providers will dispute counts; this is the answer.
create table lead_events (
  id                 uuid primary key default gen_random_uuid(),
  outbound_click_id  uuid references outbound_clicks(id),
  provider_id        uuid not null references providers(id),
  product_id         uuid references products(id),
  stage              text not null check (stage in
                       ('click','qualified','account_opened','funded','rejected')),
  reported_by        text not null check (reported_by in ('platform','provider')),
  amount_minor       bigint,
  currency           char(3),
  occurred_at        timestamptz not null,
  billing_period     date,
  dedupe_key         text,                  -- session+product+day for stage='click'
  note               text,
  created_at         timestamptz not null default now()
);
create unique index lead_events_dedupe_idx on lead_events(dedupe_key)
  where dedupe_key is not null;

-- Commercial relationships. MUST NOT be readable by the scoring pipeline.
create table provider_commercials (
  provider_id     uuid primary key references providers(id) on delete cascade,
  tier            text not null default 'free'
                    check (tier in ('free','professional','enterprise')),
  lead_rate_minor bigint,
  sponsored_until date,
  contract_url    text,
  created_at      timestamptz not null default now()
);
comment on table provider_commercials is
  'Payment must never influence organic ranking. No scoring code path may join this table.';

-- ============================================================================
-- RLS — all four policies per public-readable table
-- ============================================================================

alter table providers            enable row level security;
alter table products             enable row level security;
alter table product_fees         enable row level security;
alter table nav_observations     enable row level security;
alter table product_metrics      enable row level security;
alter table scores               enable row level security;
alter table trust_scores         enable row level security;
alter table provider_licences    enable row level security;
alter table macro_series         enable row level security;
alter table sources              enable row level security;
alter table extractions          enable row level security;
alter table lead_events          enable row level security;
alter table outbound_clicks      enable row level security;
alter table provider_commercials enable row level security;
alter table content_updates      enable row level security;
alter table market_indices       enable row level security;

-- Public read of published entities only.
create policy "public read published providers" on providers
  for select using (status = 'published');
create policy "public read published products" on products
  for select using (status in ('published','stale'));
create policy "public read fees" on product_fees for select using (true);
create policy "public read navs" on nav_observations
  for select using (superseded_by is null);
create policy "public read metrics" on product_metrics for select using (true);
create policy "public read scores" on scores for select using (true);
create policy "public read trust" on trust_scores for select using (true);
create policy "public read licences" on provider_licences for select using (true);
create policy "public read macro" on macro_series for select using (true);
create policy "public read sources" on sources for select using (true);
create policy "public read published updates" on content_updates
  for select using (published = true);
create policy "public read indices" on market_indices for select using (true);

-- Everything else: no anon policy at all. Writes go through the service role
-- in server routes only. extractions, lead_events, outbound_clicks and
-- provider_commercials are deliberately unreadable by the anon key.

-- Insert-only for click recording via a server route using the service role.
-- (No anon insert policy: tokens are minted and consumed server-side.)
