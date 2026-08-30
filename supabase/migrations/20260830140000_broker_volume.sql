-- Volume share and absolute value, alongside value share.
--
-- WHY VOLUME MATTERS SEPARATELY FROM VALUE
-- IC Securities handled 78.82% of value traded in July 2026 and 62.16% of
-- volume. The gap is the whole point: a broker whose value share exceeds its
-- volume share is handling fewer, larger trades. Institutional block business.
--
-- That is directly useful to a retail saver, and it is the closest this data
-- comes to answering the question they actually have. Nobody publishes whether
-- a Ghanaian broker wants a GH¢5,000 order, but a firm doing GH¢1.08bn across
-- 124,776,830 shares is averaging a trade size no individual is placing.
--
-- WHY THE ABSOLUTE FIGURE MATTERS
-- "52.70% of the market" says nothing without the market. July 2026 turnover
-- was GH¢683.5m — down 60% year on year, on volume down 72%. A share of a
-- shrinking market is a different fact from a share of a growing one, and a
-- percentage alone hides which it is.
--
-- WHAT STILL CANNOT BE SHOWN
-- Which instruments any broker actually traded. The exchange publishes each
-- member's totals, not a breakdown by security, so "IC Securities did 78% of
-- value" cannot be resolved into what they traded it in. That would have to
-- come from the brokers themselves — the same ask as commission rates.

alter table providers
  add column if not exists broker_volume_share_avg_pct numeric(6,2),
  add column if not exists broker_value_traded_ghs numeric(18,2),
  add column if not exists broker_volume_traded bigint,
  add column if not exists broker_latest_month date;

comment on column providers.broker_volume_share_avg_pct is
  'Mean share of GSE VOLUME traded. Read against value share: value above volume means fewer, larger trades.';
comment on column providers.broker_value_traded_ghs is
  'Cedis traded in the most recent month held. A percentage without the absolute hides whether the market is growing or shrinking.';
comment on column providers.broker_volume_traded is
  'Shares traded in the most recent month held.';
comment on column providers.broker_latest_month is
  'Which month the two absolute figures above describe.';
