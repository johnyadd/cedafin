-- Directory entries are draft by design so they can never reach a comparison
-- page and appear to have no charges. But /funds legitimately needs them.
-- RLS policies for the same command are OR'd, so this adds directory access
-- without loosening the published-only rule: a draft that is NOT a cat- entry
-- (a fund mid-review, say) stays hidden.
create policy "public read directory entries" on products
  for select using (status = 'draft' and slug like 'cat-%');