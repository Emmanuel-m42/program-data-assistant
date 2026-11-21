<script lang="ts">
	import type { Source } from '#lib/types.ts';

	let { source, index, highlighted = false }: { source: Source; index: number; highlighted?: boolean } = $props();

	function cell(v: unknown): string {
		if (v === null || v === undefined) return '';
		if (typeof v === 'number') return Number.isInteger(v) ? v.toLocaleString('en-US') : String(v);
		return String(v);
	}
</script>

<article class="card" class:highlighted id={`source-${index}`} tabindex="-1">
	{#if source.type === 'rows'}
		<header>
			<span class="kind">Rows</span>
			<span class="name">{source.table}</span>
			{#if source.row_count !== undefined && source.row_count > source.rows.length}
				<span class="note">first {source.rows.length} of {source.row_count} rows</span>
			{/if}
		</header>
		<div class="scroll">
			<table>
				<thead>
					<tr>{#each source.columns as c (c)}<th scope="col">{c}</th>{/each}</tr>
				</thead>
				<tbody>
					{#each source.rows as row, r (r)}
						<tr>{#each row as v, j (j)}<td class:num={typeof v === 'number'}>{cell(v)}</td>{/each}</tr>
					{/each}
				</tbody>
			</table>
		</div>
		{#if source.sql}
			<details>
				<summary>SQL</summary>
				<div class="scroll"><pre><code>{source.sql}</code></pre></div>
			</details>
		{/if}
	{:else}
		<header>
			<span class="kind">Passage</span>
			<span class="name">{source.doc}</span>
		</header>
		<p class="passage">{source.text}</p>
	{/if}
</article>

<style>
	.card {
		border: 1px solid var(--line);
		border-radius: 8px;
		padding: 0.6rem 0.75rem;
		background: var(--panel);
		scroll-margin-top: 5rem;
		min-width: 0;
		max-width: 100%;
	}
	.card.highlighted {
		border-color: var(--accent);
		box-shadow: 0 0 0 2px var(--accent-soft);
	}
	.card:focus {
		outline: none;
	}
	header {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		align-items: baseline;
		margin-bottom: 0.4rem;
	}
	.kind {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-soft);
	}
	.name {
		font: 0.85rem var(--mono);
		overflow-wrap: anywhere;
	}
	.note {
		font-size: 0.75rem;
		color: var(--ink-soft);
	}
	.scroll {
		overflow-x: auto;
		max-width: 100%;
	}
	table {
		border-collapse: collapse;
		font-size: 0.78rem;
		width: max-content;
		min-width: 100%;
	}
	th,
	td {
		text-align: left;
		padding: 0.2rem 0.5rem;
		border-bottom: 1px solid var(--line);
		white-space: nowrap;
	}
	th {
		font-weight: 600;
		color: var(--ink-soft);
	}
	td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.passage {
		margin: 0;
		font-size: 0.88rem;
		white-space: pre-line;
	}
	details {
		margin-top: 0.4rem;
		font-size: 0.8rem;
	}
	pre {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		background: var(--code);
		padding: 0.5rem;
		border-radius: 6px;
		font: 0.78rem var(--mono);
	}
</style>
