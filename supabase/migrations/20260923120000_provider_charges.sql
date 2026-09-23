-- 2026-09-23 provider_charges
-- Charges as printed in a provider's tariff guide, pricing guide or account agreement.
-- Kept separate from product_fees, which holds fund charges on an annual_nav basis and
-- feeds fund cost comparisons; lending fees there would be read as yearly fund charges.
--
-- Run in the SQL editor on FinancialAnalysisIntelligence (ref qhphyavmvawpvbssyutg).
-- Safe to re-run: every statement checks before creating.

begin;

-- 1. New source kinds for the documents this table cites -----------------------
alter table public.sources drop constraint if exists sources_kind_check;
alter table public.sources add constraint sources_kind_check check (kind = any (array[
  'provider_factsheet', 'prospectus', 'scheme_particulars', 'annual_report',
  'sec_register', 'sec_notice', 'manual_entry', 'regulator_publication',
  'provider_submission', 'other',
  'tariff_guide',     -- a bank's published tariff or pricing guide
  'account_form'      -- an account-opening form or agreement stating terms
]));

-- 2. The charges table ----------------------------------------------------------
create table if not exists public.provider_charges (
  id              uuid primary key default gen_random_uuid(),
  provider_id     uuid not null references public.providers(id) on delete cascade,
  product_id      uuid references public.products(id) on delete set null,  -- only when the charge clearly belongs to one product
  category        text not null check (category in (
                    'mortgage', 'credit_card', 'personal_loan', 'overdraft',
                    'investment_management', 'account', 'other')),
  product_label   text not null default '',   -- variant as printed: 'Visa Credit Classic', 'RB', 'FCL' ...; '' = whole category
  charge_key      text not null,              -- stable machine key, e.g. 'processing_resident'
  charge_name     text not null,              -- the document's own label
  applies_when    text,                       -- condition as printed
  rate            numeric,                    -- 0.015 = 1.5%
  rate_period     text check (rate_period in (
                    'one_off', 'year', 'month', 'per_transaction',
                    'per_occurrence', 'per_billing_cycle', 'not_stated')),
  rate_basis      text,                       -- 'loan_amount', 'property_value', 'not_stated' ...
  flat_minor      bigint,                     -- fixed amount in minor units (pesewas / cents / pence)
  flat_currency   char(3),                    -- required whenever flat_minor is set
  limit_note      text,                       -- minimum / maximum / 'whichever is higher', as printed
  collected_for   text not null default 'not_stated' check (collected_for in (
                    'bank', 'manager', 'government_stamp_duty',
                    'deposit_towards_registration', 'not_stated')),
  wording         text not null,              -- the document's exact wording for this charge
  page            integer,
  source_id       uuid not null references public.sources(id),
  effective_from  date,                       -- null when the document states no date
  effective_note  text,                       -- how effective_from was derived, or why it is empty
  verified_on     date not null,              -- when we read it
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint provider_charges_currency_check check (flat_minor is null or flat_currency is not null),
  constraint provider_charges_one_per_source unique (source_id, charge_key, product_label)
);

create index if not exists provider_charges_provider_category_idx
  on public.provider_charges (provider_id, category);

-- 3. Public read, like the rest of the published data ---------------------------
-- Tariffs are published documents. The service role (loaders) bypasses RLS.
alter table public.provider_charges enable row level security;
drop policy if exists provider_charges_public_read on public.provider_charges;
create policy provider_charges_public_read on public.provider_charges
  for select using (true);

commit;

-- Check after running:
--   select count(*) from public.provider_charges;          -- expect 0 before loading
--   select pg_get_constraintdef(oid) from pg_constraint where conname = 'sources_kind_check';
