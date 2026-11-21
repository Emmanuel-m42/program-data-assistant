<script lang="ts">
	import { tick } from 'svelte';
	import { formatSeconds } from '#lib/api.ts';
	import { parseAnswer } from '#lib/markdown.ts';
	import type { Source, ToolCall } from '#lib/types.ts';
	import Rich from './Rich.svelte';
	import SourceCard from './SourceCard.svelte';

	let {
		answer,
		refused,
		sources,
		toolCalls,
		latencyMs,
		model,
		id
	}: {
		answer: string;
		refused: boolean;
		sources: Source[];
		toolCalls: ToolCall[];
		latencyMs: number;
		model: string;
		id: string;
	} = $props();

	let blocks = $derived(parseAnswer(answer, sources));
	let highlighted: number | null = $state(null);
	let sourcesOpen = $state(false);

	async function showSource(i: number) {
		sourcesOpen = true;
		highlighted = i;
		await tick();
		const el = document.getElementById(`${id}-source-${i}`)?.firstElementChild as HTMLElement | null;
		el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
		el?.focus({ preventScroll: true });
	}

	function argText(c: ToolCall): string {
		const a = c.args as Record<string, unknown>;
		if (typeof a.sql === 'string') return a.sql;
		if (typeof a.query === 'string') return a.query;
		const parts = Object.entries(a)
			.filter(([, v]) => v !== null && v !== undefined && v !== '')
			.map(([k, v]) => `${k}: ${v}`);
		return parts.join(', ');
	}
</script>

<div class="answer" class:refused>
	{#if refused}<p class="refused-label">Declined: the data and documents don't cover this.</p>{/if}
	{#each blocks as b, i (i)}
		{#if b.kind === 'p'}
			<p><Rich tokens={b.inline} onCite={showSource} /></p>
		{:else if b.kind === 'h'}
			<p class="h"><Rich tokens={b.inline} onCite={showSource} /></p>
		{:else}
			<ul>
				{#each b.items as item, j (j)}<li><Rich tokens={item} onCite={showSource} /></li>{/each}
			</ul>
		{/if}
	{/each}

	<p class="meta">{model} &nbsp; {formatSeconds(latencyMs)}</p>

	{#if toolCalls.length}
		<details class="tools">
			<summary>Tools called ({toolCalls.length})</summary>
			<ol>
				{#each toolCalls as c, i (i)}
					<li>
						<span class="tool">{c.name}</span>
						{#if c.ok === false}<span class="fail">failed</span>{/if}
						<div class="code"><pre><code>{argText(c)}</code></pre></div>
						<span class="result">{c.result}</span>
					</li>
				{/each}
			</ol>
		</details>
	{/if}

	{#if sources.length}
		<details class="sources" bind:open={sourcesOpen}>
			<summary>Sources ({sources.length})</summary>
			<div class="cards">
				{#each sources as s, i (i)}
					<div id={`${id}-source-${i}`}>
						<SourceCard source={s} index={i} highlighted={highlighted === i} />
					</div>
				{/each}
			</div>
		</details>
	{/if}
</div>

<style>
	/* Never wider than the card it sits in: wide tables and SQL scroll inside their own boxes. */
	.answer {
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.answer p {
		margin: 0 0 0.6rem;
	}
	.answer ul {
		margin: 0 0 0.6rem;
		padding-left: 1.2rem;
	}
	.answer li {
		margin-bottom: 0.25rem;
	}
	.h {
		font-weight: 600;
	}
	.refused-label {
		font-size: 0.8rem;
		color: var(--warn);
		font-weight: 600;
	}
	.answer.refused {
		border-left: 3px solid var(--warn);
		padding-left: 0.75rem;
	}
	.meta {
		font-size: 0.75rem;
		color: var(--ink-soft);
	}
	details {
		margin-top: 0.5rem;
		min-width: 0;
	}
	.code {
		overflow-x: auto;
		max-width: 100%;
	}
	summary {
		cursor: pointer;
		font-size: 0.85rem;
		color: var(--ink-soft);
		padding: 0.25rem 0;
	}
	summary:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.tools ol {
		padding-left: 1.2rem;
		margin: 0.25rem 0;
		font-size: 0.82rem;
	}
	.tools li {
		margin-bottom: 0.5rem;
	}
	.tool {
		font: 0.8rem var(--mono);
		font-weight: 600;
	}
	.fail {
		color: var(--warn);
		font-size: 0.75rem;
		margin-left: 0.4rem;
	}
	.tools pre {
		margin: 0.25rem 0;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		background: var(--code);
		padding: 0.4rem 0.5rem;
		border-radius: 6px;
		font: 0.76rem var(--mono);
	}
	.result {
		color: var(--ink-soft);
		font-size: 0.78rem;
	}
	.cards {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 0.5rem;
		margin-top: 0.25rem;
	}
	.cards > div {
		min-width: 0;
	}
</style>
