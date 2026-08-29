-- Gold, and a flag for products that permit non-interest investors.
--
-- WHY GOLD NEEDS ITS OWN ASSET CLASS
-- Every other product on the invest side is a claim on something that pays:
-- a fund distributes, a bill matures, a deposit earns. Gold pays nothing. Its
-- entire return is the price moving, and for a Ghanaian that means the dollar
-- gold price AND the cedi exchange rate, which have lately pulled in opposite
-- directions. Filing it as fixed_income or balanced would put it in a peer
-- group where the comparison is meaningless.
--
-- THE PREMIUM IS A CHARGE, AND IT IS THE ONLY ONE
-- The Ghana Gold Coin has no management fee, no custody fee, no expense ratio.
-- What it has is a premium over the metal: Bank of Ghana sells an ounce for
-- about 3.5% more than the gold in it is worth at LBMA spot times the day's
-- exchange rate. Across 56 days that ran from 2.15% to 3.73%, so it is
-- managed rather than fixed.
--
-- That premium is the cost of ownership and belongs in product_fees, because a
-- page comparing a 1.75% fund charge against a coin showing "no charges" would
-- be badly misleading. Gold is not free to own; the cost is just charged
-- differently.
--
-- AND SO IS THE SMALL-COIN PENALTY
-- Four quarter-ounce coins cost about 4.4% more than one full ounce — roughly
-- GH¢2,197 at current prices. The saver with the least money pays the most per
-- ounce, which is the same pattern this database already records in fund
-- minimums and SME lending rates. Each denomination is therefore its own
-- product with its own effective cost, not one product in three sizes.
--
-- SHARIA COMPLIANCE
-- A flag rather than a category, because compliant products span asset classes:
-- NewGold ETF is a commodity fund, and any future murabaha or sukuk offering
-- would be fixed income. Ghana has a substantial Muslim population and, as far
-- as this project has established, almost nothing marketed as compliant. A
-- filter that returns one or two results and says so is more honest than
-- omitting the question.
--
-- NULL means we have not established it, which is different from false. Only
-- a product whose own documentation states compliance gets true.

-- 1. Commodity as an asset class ----------------------------------------

alter table products drop constraint if exists products_asset_class_check;
alter table products add constraint products_asset_class_check
  check (asset_class in ('money_market','fixed_income','balanced','equity',
                         'real_estate','deposit','government_security',
                         'commodity',
                         'personal_credit','sme_credit','corporate_credit',
                         'other'));

alter table products drop constraint if exists products_legal_structure_check;
alter table products add constraint products_legal_structure_check
  check (legal_structure in ('unit_trust','mutual_fund','etf','treasury_bill',
                             'government_bond','fixed_deposit','bank_loan',
                             'credit_facility','bullion_coin','other'));

-- 2. Sharia compliance ---------------------------------------------------

alter table products
  add column if not exists sharia_compliant boolean,
  add column if not exists sharia_basis text;

comment on column products.sharia_compliant is
  'NULL = not established, which is not the same as false. TRUE only where the product''s own documentation states compliance.';
comment on column products.sharia_basis is
  'Who certified it and on what basis. A claim without a source is not a claim.';

-- 3. Fee types that describe how gold actually costs money ---------------

alter table product_fees drop constraint if exists product_fees_fee_type_check;
alter table product_fees add constraint product_fees_fee_type_check
  check (fee_type in ('management','custody','performance','entry','exit',
                      'switching','administration','audit','trustee',
                      'stated_charges','total_expense_ratio',
                      'premium_over_spot','denomination_penalty',
                      'other'));

comment on constraint product_fees_fee_type_check on product_fees is
  'premium_over_spot: what a bullion product costs above the metal in it. denomination_penalty: the extra paid per ounce for buying in smaller pieces.';

-- 4. Tax treatment, which differs sharply here ---------------------------
-- T-bill interest carries withholding tax. Ghana Gold Coin is exempt from VAT
-- and its capital gains are untaxed under current law. Two products a saver
-- might weigh against each other, taxed completely differently, and nobody
-- publishes them side by side.

alter table products
  add column if not exists tax_note text;

comment on column products.tax_note is
  'Stated tax treatment, as published. Not advice, and not verified against the Revenue Authority — it records what the issuer says.';
