-- Cross-provider cost comparison needs a fee type that both providers publish.
-- FAAM discloses no expense ratio at all — only management and custody — so
-- comparing Stanbic's TER against FAAM's stated charges would compare two
-- different things. 'stated_charges' is management + custody, which both give.
alter table product_fees drop constraint if exists product_fees_fee_type_check;
alter table product_fees add constraint product_fees_fee_type_check
  check (fee_type in ('management','ter','performance','entry','exit',
                      'early_exit','custody','stated_charges','other'));