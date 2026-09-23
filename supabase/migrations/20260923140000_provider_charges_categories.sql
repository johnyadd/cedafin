-- 2026-09-23 provider_charges: more categories and a quarterly period
-- First Atlantic's tariff guide prices car loans, business loans, guarantees and
-- savings accounts, and charges guarantee commission per quarter.
-- Savings interest is stored here too, so the table holds a provider's published
-- rates and charges from one document together.
--
-- Run in the SQL editor on FinancialAnalysisIntelligence (ref qhphyavmvawpvbssyutg).
-- Safe to re-run.

begin;

alter table public.provider_charges drop constraint if exists provider_charges_category_check;
alter table public.provider_charges add constraint provider_charges_category_check check (category in (
  'mortgage', 'credit_card', 'personal_loan', 'overdraft', 'investment_management',
  'account', 'other',
  'auto_loan', 'business_loan', 'guarantee', 'savings'
));

alter table public.provider_charges drop constraint if exists provider_charges_rate_period_check;
alter table public.provider_charges add constraint provider_charges_rate_period_check check (rate_period in (
  'one_off', 'year', 'month', 'per_transaction', 'per_occurrence', 'per_billing_cycle', 'not_stated',
  'quarter'
));

commit;

-- Check:
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--   where conrelid = 'public.provider_charges'::regclass and contype = 'c';
