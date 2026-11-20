<script lang="ts">
	import { offices } from '#lib/api.ts';
	import type { OfficeSummary, OfficesResponse } from '#lib/types.ts';

	let data = $state<OfficesResponse | null>(null);
	let error = $state('');
	let active = $state('All offices');

	offices()
		.then((d) => (data = d))
		.catch((e) => (error = e instanceof Error ? e.message : String(e)));

	let current: OfficeSummary | undefined = $derived(data?.offices.find((o: OfficeSummary) => o.office === active));

	function num(v: number | null | undefined, digits = 0): string {
		if (v === null || v === undefined) return 'n/a';
		return v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
	}
	function signed(v: number | null | undefined): string {
		if (v === null || v === undefined) return 'n/a';
		return `${v > 0 ? '+' : ''}${num(v)}`;
	}
	function onKey(e: KeyboardEvent, names: string[]) {
		const i = names.indexOf(active);
		const next = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : null;
		if (next === null) return;
		e.preventDefault();
		active = names[(next + names.length) % names.length];
		document.getElementById(`tab-${active}`)?.focus();
	}
</script>

<h1>Offices</h1>
<p class="lede">
	Straight from the program's metric views, no model involved.{#if data}{' '}Data through {data.as_of}.{/if}
</p>

{#if error}
	<p class="panel">Couldn't load the office data: {error}</p>
{:else if data}
	{@const names = data.offices.map((o) => o.office)}
	<div class="tabs" role="tablist" aria-label="Office" tabindex="-1" onkeydown={(e) => onKey(e, names)}>
		{#each names as name (name)}
			<button
				type="button"
				role="tab"
				id={`tab-${name}`}
				aria-selected={active === name}
				aria-controls="office-panel"
				tabindex={active === name ? 0 : -1}
				onclick={() => (active = name)}>{name}</button
			>
		{/each}
	</div>

	{#if current}
		<div class="grid" id="office-panel" role="tabpanel" tabindex="0" aria-labelledby={`tab-${active}`}>
			<div class="panel">
				<h2>Door pace</h2>
				<dl>
					<dt>Goal through Election Day</dt><dd>{num(current.pace.goal_total)}</dd>
					<dt>Doors to date</dt><dd>{num(current.pace.doors_to_date)} of {num(current.pace.goal_to_date)} due by now</dd>
					<dt>Projected by Election Day</dt><dd>{num(current.pace.projected_total)} ({num(current.pace.projected_pct_of_goal, 1)}% of goal)</dd>
					<dt>Projected vs goal</dt>
					<dd class:bad={(current.pace.projected_vs_goal ?? 0) < 0} class:good={(current.pace.projected_vs_goal ?? 0) >= 0}>
						{signed(current.pace.projected_vs_goal)} doors
					</dd>
					<dt>Shifts per day, last 7 days</dt><dd>{num(current.pace.avg_shifts_per_day_last_7d, 1)}</dd>
					<dt>Extra shifts per day needed</dt><dd>{num(current.pace.extra_shifts_per_day_needed, 1)}</dd>
				</dl>
			</div>

			<div class="panel">
				<h2>Contact rate by week</h2>
				<table>
					<thead><tr><th scope="col">Week of</th><th scope="col">Contact rate</th></tr></thead>
					<tbody>
						{#each current.contact_rates as w (w.week_start)}
							<tr><td>{w.week_start}</td><td class="num">{num(w.contact_rate_pct, 1)}%</td></tr>
						{/each}
					</tbody>
				</table>
				<p class="small">Cost per door to date: ${num(current.cost_per_door, 2)}</p>
			</div>

			<div class="panel">
				<h2>Voter registration</h2>
				<dl>
					<dt>Card goal</dt><dd>{num(current.registration.card_goal)}</dd>
					<dt>Valid cards</dt><dd>{num(current.registration.valid_cards)} ({num(current.registration.duplicate_cards)} duplicates removed)</dd>
					<dt>Projected by the deadline</dt><dd>{num(current.registration.projected_valid_cards)}</dd>
					<dt>Cards per hour, last 7 days</dt><dd>{num(current.registration.cards_per_hour_last_7d, 2)}</dd>
					<dt>Cards per hour needed</dt>
					<dd class:bad={(current.registration.cards_per_hour_last_7d ?? 0) < (current.registration.cards_per_hour_needed ?? 0)}>
						{num(current.registration.cards_per_hour_needed, 2)}
					</dd>
				</dl>
			</div>

			<div class="panel">
				<h2>QC this week</h2>
				<dl>
					<dt>Flags</dt><dd>{num(current.qc_this_week.flags)}</dd>
					<dt>Flags per 100 shifts</dt><dd>{num(current.qc_this_week.flags_per_100_shifts, 1)}</dd>
				</dl>
			</div>
		</div>
	{/if}
{:else}
	<p class="lede">Loading.</p>
{/if}

<style>
	.tabs {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
		margin-bottom: 1rem;
	}
	.tabs button {
		border: 1px solid var(--line);
		background: var(--panel);
		border-radius: 999px;
		padding: 0.35rem 0.85rem;
		cursor: pointer;
		color: var(--ink-soft);
		font-size: 0.9rem;
	}
	.tabs button[aria-selected='true'] {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
	}
	.grid {
		display: grid;
		gap: 0.75rem;
		grid-template-columns: repeat(auto-fit, minmax(min(16rem, 100%), 1fr));
	}
	.grid > :global(*) {
		min-width: 0; /* let a card shrink to the screen instead of to its widest content */
	}
	.panel h2 {
		margin-top: 0;
		font-size: 0.95rem;
	}
	dl {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 0.3rem 0.75rem;
		margin: 0;
		font-size: 0.9rem;
	}
	dt {
		color: var(--ink-soft);
	}
	dd {
		margin: 0;
		text-align: right;
		font-variant-numeric: tabular-nums;
		overflow-wrap: anywhere;
	}
	dl {
		grid-template-columns: minmax(0, 1fr) minmax(0, auto);
	}
	.bad {
		color: var(--bad);
	}
	.good {
		color: var(--good);
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.9rem;
	}
	th,
	td {
		text-align: left;
		padding: 0.2rem 0;
		border-bottom: 1px solid var(--line);
	}
	th {
		color: var(--ink-soft);
		font-weight: 600;
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.small {
		font-size: 0.85rem;
		color: var(--ink-soft);
		margin-bottom: 0;
	}
</style>
