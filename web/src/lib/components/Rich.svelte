<script lang="ts">
	import type { Inline } from '#lib/markdown.ts';

	let { tokens, onCite }: { tokens: Inline[]; onCite: (source: number) => void } = $props();
</script>

{#each tokens as t, i (i)}
	{#if t.kind === 'text'}{t.text}{:else if t.kind === 'bold'}<strong>{t.text}</strong>{:else if t.kind === 'code'}<code
			>{t.text}</code
		>{:else if t.source !== null}<button
			type="button"
			class="chip"
			title="Show the source"
			onclick={() => onCite(t.source as number)}>{t.cite.id}</button
		>{:else}<span class="chip missing" title="No matching source in this answer">{t.cite.id}</span>{/if}
{/each}

<style>
	.chip {
		display: inline-block;
		font: 0.72rem/1.4 var(--mono);
		padding: 0 0.4rem;
		margin: 0 0.15rem;
		border: 1px solid var(--line);
		border-radius: 999px;
		background: var(--chip);
		color: var(--ink-soft);
		cursor: pointer;
		vertical-align: 0.1em;
		max-width: 100%;
		overflow-wrap: anywhere;
	}
	button.chip:hover,
	button.chip:focus-visible {
		border-color: var(--accent);
		color: var(--accent);
	}
	.chip.missing {
		cursor: default;
		opacity: 0.7;
	}
</style>
