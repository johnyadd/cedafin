-- First Atlantic Bank - Purple Plus Mortgage, from its tariff guide (24 August 2026, page 2).
-- "Interest rate: GRR plus a minimum of 8% and 12% for USD"; tenor up to 7 years; equity contribution 20%.
--
-- GHS: no single rate is published, so rate_min/rate_max stay empty and rate_basis holds the formula;
--      the card shows it as published. The worked figure in the notes is dated - it goes stale when the
--      Ghana Reference Rate changes, and will be computed from the GRR series once that is loaded.
-- USD: 12% as printed.
--
-- Run in the SQL editor on FinancialAnalysisIntelligence. Safe to re-run: inserts only if the slug is absent.

insert into public.products
  (slug, provider_id, name, asset_class, currency, market_side,
   rate_min, rate_max, rate_basis, lock_in_days, eligibility_notes, status)
select 'first-atlantic-purple-plus-mortgage-ghs', p.id, 'Purple Plus Mortgage (GHS)', 'mortgage', 'GHS', 'borrow',
       null, null, 'Reference Rate + at least 8%', 2555,
       'Published as the Ghana Reference Rate plus a minimum of 8%. At the reference rate of 10.18% effective 2 September 2026, that is at least 18.18% a year. Up to 7 years; 20% equity contribution. First Atlantic tariff guide, 24 August 2026, page 2.',
       'published'
from public.providers p
where p.slug = 'first-atlantic-bank'
  and not exists (select 1 from public.products where slug = 'first-atlantic-purple-plus-mortgage-ghs');

insert into public.products
  (slug, provider_id, name, asset_class, currency, market_side,
   rate_min, rate_max, rate_basis, lock_in_days, eligibility_notes, status)
select 'first-atlantic-purple-plus-mortgage-usd', p.id, 'Purple Plus Mortgage (USD)', 'mortgage', 'USD', 'borrow',
       0.12, 0.12, '12% for USD, as published', 2555,
       'Published as 12% for USD. Up to 7 years; 20% equity contribution. First Atlantic tariff guide, 24 August 2026, page 2.',
       'published'
from public.providers p
where p.slug = 'first-atlantic-bank'
  and not exists (select 1 from public.products where slug = 'first-atlantic-purple-plus-mortgage-usd');

-- Check:
--   select slug, name, currency, rate_min, rate_max, rate_basis, status from public.products
--   where asset_class = 'mortgage' order by slug;
