alter table products
  add column if not exists share_class text not null default 'main',
  add column if not exists share_class_label text,
  add column if not exists distributes boolean not null default false,
  add column if not exists distribution_note text;

alter table products drop constraint if exists products_slug_key;
create unique index if not exists products_class_unique
  on products(provider_id, name, share_class);

alter table nav_observations
  add column if not exists series_kind text not null default 'quoted',
  add column if not exists period_return numeric(12,8);

alter table nav_observations
  drop constraint if exists nav_observations_series_kind_check;
alter table nav_observations
  add constraint nav_observations_series_kind_check
  check (series_kind in ('quoted','chained','adjusted'));

create table if not exists distributions (
  id              uuid primary key default gen_random_uuid(),
  product_id      uuid not null references products(id) on delete cascade,
  ex_date         date not null,
  amount_per_unit numeric(20,8) not null,
  currency        char(3) not null default 'GHS',
  source_id       uuid not null references sources(id),
  verified_on     date not null,
  created_at      timestamptz not null default now()
);
create unique index if not exists distributions_unique
  on distributions(product_id, ex_date);

alter table distributions enable row level security;
drop policy if exists "public read distributions" on distributions;
create policy "public read distributions" on distributions
  for select using (true);