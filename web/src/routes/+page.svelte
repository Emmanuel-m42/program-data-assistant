<script lang="ts">
	import { tick } from 'svelte';
	import { ask, CATEGORIES, CATEGORY_LABELS, DEMO, NoRecordedAnswer, recorded, type Answered } from '#lib/api.ts';
	import Answer from '#lib/components/Answer.svelte';

	interface Exchange {
		id: string;
		question: string;
		status: 'loading' | 'done' | 'nomatch' | 'error';
		answered?: Answered;
		error?: string;
		showBefore: boolean;
	}

	let exchanges: Exchange[] = $state([]);
	let draft = $state('');
	let busy = $state(false);
	let n = 0;

	const grouped = CATEGORIES.map((c) => ({
		category: c,
		questions: recorded.questions.filter((q) => q.category === c)
	})).filter((g) => g.questions.length);

	async function submit(question: string) {
		const q = question.trim();
		if (q.length < 3 || busy) return;
		busy = true;
		draft = '';
		const ex: Exchange = { id: `ex${++n}`, question: q, status: 'loading', showBefore: false };
		exchanges.push(ex);
		const i = exchanges.length - 1;
		await tick();
		document.getElementById(ex.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		try {
			exchanges[i].answered = await ask(q);
			exchanges[i].status = 'done';
		} catch (e) {
			if (e instanceof NoRecordedAnswer) {
				exchanges[i].status = 'nomatch';
			} else {
				exchanges[i].status = 'error';
				exchanges[i].error = e instanceof Error ? e.message : String(e);
			}
		} finally {
			busy = false;
		}
	}

	function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		submit(draft);
	}
</script>

<svelte:head><title>Program data assistant</title></svelte:head>

<h1>Ask about the program</h1>
<p class="lede">
	Questions about the fictional Riverbend Votes canvass and Riverbend Registers drive. Every number in an answer links
	to the rows or passage it came from.
</p>

<details class="panel suggestions" open={exchanges.length === 0}>
	<summary>Example questions</summary>
	{#each grouped as g (g.category)}
		<div class="group">
			<h2>{CATEGORY_LABELS[g.category] ?? g.category}</h2>
			<ul>
				{#each g.questions as q (q.id)}
					<li><button type="button" class="suggest" disabled={busy} onclick={() => submit(q.question)}>{q.question}</button></li>
				{/each}
			</ul>
		</div>
	{/each}
</details>

<section class="thread" aria-live="polite">
	{#each exchanges as ex (ex.id)}
		<article class="exchange" id={ex.id}>
			<p class="q">{ex.question}</p>
			{#if ex.status === 'loading'}
				<p class="wait">Working on it{DEMO ? '' : '. The model can take a minute'}.</p>
			{:else if ex.status === 'nomatch'}
				<div class="panel note">
					<p>
						This demo only answers the example questions, and this one doesn't match any of them closely. Pick one
						from the list above.
					</p>
				</div>
			{:else if ex.status === 'error'}
				<div class="panel note"><p>Something went wrong: {ex.error}</p></div>
			{:else if ex.answered}
				{@const a = ex.answered}
				<div class="panel">
					{#if a.recorded && !a.matchedExactly}
						<p class="matched">Closest example question: {a.recorded.question}</p>
					{/if}
					{#if a.recorded?.baseline}
						<div class="toggle" role="group" aria-label="Which run to show">
							<button type="button" aria-pressed={!ex.showBefore} onclick={() => (ex.showBefore = false)}>Current</button>
							<button type="button" aria-pressed={ex.showBefore} onclick={() => (ex.showBefore = true)}>Before (first baseline)</button>
						</div>
					{/if}
					{#if ex.showBefore && a.recorded?.baseline}
						{@const b = a.recorded.baseline}
						<Answer
							id={`${ex.id}-b`}
							answer={b.answer}
							refused={b.refused}
							sources={b.sources}
							toolCalls={b.tool_calls}
							latencyMs={b.latency_ms}
							model="qwen2.5:7b on CPU (baseline)"
						/>
					{:else}
						{#if a.recorded && (a.recorded.eval.after?.pass ?? 1) < 1}
							<p class="missed">
								<span class="badge">Scored a miss</span>
								{a.recorded.eval.note ?? 'This answer failed at least one check in the evals.'}
							</p>
						{/if}
						<Answer
							id={ex.id}
							answer={a.response.answer}
							refused={a.response.refused}
							sources={a.response.sources}
							toolCalls={a.response.tool_calls}
							latencyMs={a.response.latency_ms}
							model={a.response.model.replace(/^ollama\//, '')}
						/>
					{/if}
				</div>
			{/if}
		</article>
	{/each}
</section>

<form class="ask" onsubmit={onSubmit}>
	<label for="question" class="visually-hidden">Question</label>
	<input
		id="question"
		type="text"
		bind:value={draft}
		placeholder="Ask a question about the program"
		autocomplete="off"
		maxlength="500"
	/>
	<button type="submit" disabled={busy || draft.trim().length < 3}>Ask</button>
</form>

<style>
	.suggestions summary {
		cursor: pointer;
		font-weight: 600;
	}
	.group h2 {
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-soft);
		margin: 0.9rem 0 0.3rem;
	}
	.group ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.3rem;
	}
	.suggest {
		text-align: left;
		width: 100%;
		background: none;
		border: 1px solid var(--line);
		border-radius: 8px;
		padding: 0.45rem 0.6rem;
		color: var(--ink);
		cursor: pointer;
		font-size: 0.92rem;
	}
	.suggest:hover:not(:disabled) {
		border-color: var(--accent);
	}
	.thread {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1.25rem;
		margin: 1.25rem 0;
	}
	.exchange {
		scroll-margin-top: 4.5rem;
		min-width: 0;
	}
	.exchange .panel {
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.q {
		font-weight: 600;
		margin: 0 0 0.4rem;
	}
	.wait {
		color: var(--ink-soft);
	}
	.note p {
		margin: 0;
	}
	.matched {
		font-size: 0.8rem;
		color: var(--ink-soft);
		margin: 0 0 0.5rem;
	}
	.missed {
		font-size: 0.82rem;
		color: var(--ink-soft);
		margin: 0 0 0.6rem;
	}
	.badge {
		display: inline-block;
		font-size: 0.72rem;
		font-weight: 600;
		color: var(--bad);
		border: 1px solid var(--bad);
		border-radius: 999px;
		padding: 0 0.45rem;
		margin-right: 0.3rem;
	}
	.toggle {
		display: inline-flex;
		border: 1px solid var(--line);
		border-radius: 8px;
		overflow: hidden;
		margin-bottom: 0.75rem;
	}
	.toggle button {
		border: 0;
		background: var(--panel);
		padding: 0.3rem 0.7rem;
		font-size: 0.82rem;
		cursor: pointer;
		color: var(--ink-soft);
	}
	.toggle button[aria-pressed='true'] {
		background: var(--accent-soft);
		color: var(--accent);
		font-weight: 600;
	}
	.ask {
		position: sticky;
		bottom: 0;
		display: flex;
		gap: 0.5rem;
		padding: 0.75rem 0;
		background: var(--bg);
	}
	.ask input {
		flex: 1;
		min-width: 0;
		font: inherit;
		padding: 0.6rem 0.75rem;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: var(--panel);
	}
	.ask button {
		padding: 0.6rem 1.1rem;
		border: 0;
		border-radius: 8px;
		background: var(--accent);
		color: #fff;
		cursor: pointer;
	}
	.ask button:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.visually-hidden {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
		white-space: nowrap;
	}
</style>
