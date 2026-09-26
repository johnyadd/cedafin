-- 2026-09-26 provider_charges: one charge per document, PROVIDER, key and label.
-- The Bank of Ghana's Survey of Bank Charges is one document covering 23 banks, so the
-- same charge key appears once per bank under one source. The old rule (source, key, label)
-- cannot hold that. Existing rows are unaffected: each existing document has one provider.
-- Run in the SQL editor on FinancialAnalysisIntelligence. Safe to re-run.
begin;
alter table public.provider_charges drop constraint if exists provider_charges_one_per_source;
alter table public.provider_charges drop constraint if exists provider_charges_one_per_source_provider;
alter table public.provider_charges add constraint provider_charges_one_per_source_provider
  unique (source_id, provider_id, charge_key, product_label);
commit;
