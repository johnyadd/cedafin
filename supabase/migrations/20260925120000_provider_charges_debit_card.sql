-- 2026-09-25 provider_charges: debit card category
-- Tariff guides price debit cards (issuance, maintenance, ATM and foreign-use charges)
-- separately from credit cards. Run in the SQL editor on FinancialAnalysisIntelligence. Safe to re-run.
begin;
alter table public.provider_charges drop constraint if exists provider_charges_category_check;
alter table public.provider_charges add constraint provider_charges_category_check check (category in (
  'mortgage', 'credit_card', 'personal_loan', 'overdraft', 'investment_management',
  'account', 'other', 'auto_loan', 'business_loan', 'guarantee', 'savings',
  'debit_card'
));
commit;
