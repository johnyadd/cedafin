import { getPublishedFunds, getPeerGroups } from "@/lib/data/funds";
const funds = await getPublishedFunds();
console.log(`${funds.length} published funds\n`);
for (const f of funds) {
  const nav = f.latestNav ? f.latestNav.value.toFixed(4) : `— (${f.seriesKind})`;
  console.log(`${f.name} [${f.shareClass}]`);
  console.log(`   nav ${nav}  obs ${f.observationCount}  ${f.staleness} (${f.daysSinceLastObservation}d)`);
  console.log(`   mgmt ${f.currentManagementFeePct?.value ?? "—"}%  TER ${f.lastFullYearTerPct?.value ?? "—"}% (${f.lastFullYearTerYear ?? "n/a"})  changed: ${f.feeChanged}`);
  console.log(`   source: ${f.latestNav?.source ?? f.currentManagementFeePct?.source ?? "—"}`);
}
console.log("\npeer groups");
for (const g of await getPeerGroups()) console.log(`   ${g.label}: ${g.fundCount} ${g.rankable ? "(rankable)" : "(too few to rank)"}`);
