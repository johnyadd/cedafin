-- Broker activity, as figures rather than prose.
--
-- The GSE broker load put market share into providers.notes as a sentence.
-- That was fine for a draft record and useless for a page, which would have to
-- parse English to sort a list. These columns hold the same facts as numbers.
--
-- WHY A RANGE AND NOT A SINGLE FIGURE
-- IC Securities' share of value traded, month by month across fifteen reports:
--
--     68.08  48.98  66.52  42.30  19.97  66.19  44.57  32.65
--     23.40  56.58  76.86  50.28  64.14  51.09  78.82
--
-- Publishing only the latest — 78.82% — would say one firm dominates the Ghana
-- Stock Exchange. Publishing only the average — 52.70% — would say it leads
-- comfortably. Neither is what the data shows. It swings fifty-nine points with
-- no direction, which means a few block trades decide who leads in any month.
-- The market is thin, not captured, and only the range makes that visible.
--
-- So min and max are stored alongside the average, and any page showing one
-- must show all three.
--
-- WHAT THIS IS NOT
-- Not a quality measure, not a cost measure, and explicitly not a ranking a
-- saver should choose on. No Ghanaian licensed dealing member publishes a
-- commission rate — market share is simply the only comparable public fact
-- about them, and a page that used it as a proxy for anything else would be
-- inventing a claim the data cannot carry.

alter table providers
  add column if not exists broker_share_avg_pct numeric(6,2),
  add column if not exists broker_share_min_pct numeric(6,2),
  add column if not exists broker_share_max_pct numeric(6,2),
  add column if not exists broker_months_observed integer,
  add column if not exists broker_first_seen date,
  add column if not exists broker_last_seen date;

comment on column providers.broker_share_avg_pct is
  'Mean share of GSE value traded across observed months. Activity, not quality or cost.';
comment on column providers.broker_share_min_pct is
  'Lowest monthly share observed. Shown WITH the average — one without the other misrepresents a market this thin.';
comment on column providers.broker_share_max_pct is
  'Highest monthly share observed.';
comment on column providers.broker_months_observed is
  'How many monthly reports this broker appeared in. A firm seen in three months is not comparable to one seen in fifteen.';
