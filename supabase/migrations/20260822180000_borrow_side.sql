-- The borrowing side of the market.
--
-- THE CENTRAL IDEA: a loan and a fund are the same object with different
-- fields populated. Both have a provider, a term, charges, a rate and a
-- source document. So this adds columns and two tables rather than a parallel
-- schema — the comparison pages, provider pages, fee history and provenance
-- all reuse. A bank appears once in `providers` and sells fixed deposits on
-- one side and SME loans on the other, which is a view no competitor offers.
--
-- WHAT IS DIFFERENT, and why each needs its own column:
--
--   A RANGE, NOT A RATE. A fund charges 2.25% to everyone. A loan is priced
--   per applicant — 22% to 30% depending on collateral, history and security.
--   rate_min / rate_max hold the advertised range; a single figure would be a
--   fiction.
--
--   ELIGIBILITY IS THE REAL COMPARISON. For a Ghanaian SME the binding
--   question is not price, it is whether they qualify at all. Bank of Ghana's
--   capital rules make small loans uneconomic, so most SMEs are refused
--   regardless of fundamentals. eligibility_notes holds it as text for now;
--   a structured score comes later, from research rather than guesswork.
--
--   LEAD ROUTING IS LICENSED. Publishing a comparison is not credit broking.
--   Being PAID to introduce a borrower to a lender is, and it is licensed —
--   the payer being the lender rather than the borrower does not change that.
--   So the tables exist and routing is gated behind
--   platform_settings.lead_routing_enabled, which stays false until a licence
--   is held. Structure now, switch later.

-- 1. Which side of the market a product sits on -------------------------

alter table products
  add column if not exists market_side text not null default 'invest',
  add column if not exists rate_min numeric(12,8),
  add column if not exists rate_max numeric(12,8),
  add column if not exists rate_basis text,
  add column if not exists max_advance_minor bigint,
  add column if not exists eligibility_notes text,
  add column if not exists security_required text,
  add column if not exists decision_days_min integer,
  add column if not exists decision_days_max integer;

alter table products drop constraint if exists products_market_side_check;
alter table products add constraint products_market_side_check
  check (market_side in ('invest','borrow'));

-- A borrow product must carry a rate range or say it does not publish one.
-- Half a range is worse than none: it reads as precision that is not there.
alter table products drop constraint if exists products_rate_range_check;
alter table products add constraint products_rate_range_check
  check (
    (rate_min is null and rate_max is null)
    or (rate_min is not null and rate_max is not null and rate_min <= rate_max)
  );

comment on column products.market_side is
  'invest = the user puts money in. borrow = the user takes money out.';
comment on column products.rate_basis is
  'How the rate is quoted: flat, reducing_balance, apr. NOT comparable across bases — a 2% flat monthly rate is far more than 2% reducing.';

-- 2. Lender-facing commercial terms -------------------------------------
-- Mirrors provider_commercials on the invest side, and inherits its rule:
-- NO SCORING OR ORDERING CODE PATH MAY JOIN THIS TABLE. Sponsored placement
-- must be visibly marked and must never move a product up a comparison.

create table if not exists lender_commercials (
  id                 uuid primary key default gen_random_uuid(),
  provider_id        uuid not null references providers(id) on delete cascade,
  arrangement        text not null,
  sponsored_placement boolean not null default false,
  cost_per_click_minor bigint,
  cost_per_lead_minor  bigint,
  agreement_ref      text,
  starts_on          date not null,
  ends_on            date,
  created_at         timestamptz not null default now()
);

alter table lender_commercials drop constraint if exists lender_commercials_arrangement_check;
alter table lender_commercials add constraint lender_commercials_arrangement_check
  check (arrangement in ('none','display_ad','sponsored_listing','cost_per_click','cost_per_lead'));

comment on table lender_commercials is
  'Commercial terms with lenders. Never joined by ranking or scoring code. display_ad and sponsored_listing are advertising; cost_per_lead is credit broking and requires a licence.';

alter table lender_commercials enable row level security;
-- No public read policy: commercial terms are not public.

-- 3. Enquiries ----------------------------------------------------------
-- Deliberately NOT called leads. A record here is a business that asked to be
-- contacted — it is their data, held on their instruction, and the naming
-- should keep that in view.

create table if not exists funding_enquiries (
  id                 uuid primary key default gen_random_uuid(),
  product_id         uuid references products(id) on delete set null,
  provider_id        uuid references providers(id) on delete set null,
  business_name      text,
  contact_name       text,
  contact_email      text,
  contact_phone      text,
  amount_sought_minor bigint,
  purpose            text,
  years_trading      numeric(4,1),
  monthly_revenue_minor bigint,
  -- Consent is recorded, not assumed. Ghana's Data Protection Act 2012
  -- applies and this is personal data about a named contact.
  consent_to_share   boolean not null default false,
  consent_given_at   timestamptz,
  routed_at          timestamptz,
  routing_status     text not null default 'held',
  created_at         timestamptz not null default now()
);

alter table funding_enquiries drop constraint if exists funding_enquiries_routing_status_check;
alter table funding_enquiries add constraint funding_enquiries_routing_status_check
  check (routing_status in ('held','routed','declined','withdrawn'));

comment on column funding_enquiries.routing_status is
  'held = captured but NOT sent anywhere. Default, and the only legal state until a broking licence is held.';

create index if not exists funding_enquiries_status_idx
  on funding_enquiries(routing_status, created_at desc);

alter table funding_enquiries enable row level security;
-- Insert-only for the public: a business may submit an enquiry and may not
-- read anyone else's.
drop policy if exists "public insert enquiries" on funding_enquiries;
create policy "public insert enquiries" on funding_enquiries
  for insert with check (true);

-- 4. The switch ---------------------------------------------------------
-- One row, one flag. Routing is off until a licence exists. The tables above
-- fill up regardless, so nothing is lost by waiting — enquiries sit in 'held'
-- and can be routed retrospectively once the flag flips.

create table if not exists platform_settings (
  id                    boolean primary key default true,
  lead_routing_enabled  boolean not null default false,
  lead_routing_note     text,
  updated_at            timestamptz not null default now(),
  constraint platform_settings_single_row check (id)
);

insert into platform_settings (id, lead_routing_enabled, lead_routing_note)
values (
  true, false,
  'Routing disabled: no credit broking licence held. Publishing comparisons is not broking; being paid to introduce a borrower to a lender is, regardless of which party pays. Enquiries are captured and held. Flip this only when a licence is in hand.'
)
on conflict (id) do nothing;

alter table platform_settings enable row level security;
drop policy if exists "public read settings" on platform_settings;
create policy "public read settings" on platform_settings
  for select using (true);
