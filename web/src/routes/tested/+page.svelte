<script lang="ts">
	import { evals, formatSeconds, pct } from '#lib/api.ts';
	import { splitChanges } from '#lib/changes.ts';
	import type { EvalsResponse, SplitBlock } from '#lib/types.ts';

	let data = $state<EvalsResponse | null>(null);
	let error = $state('');
	evals()
		.then((d) => (data = d))
		.catch((e) => (error = e instanceof Error ? e.message : String(e)));

	const METRICS: [keyof SplitBlock, string, string][] = [
		['tool_choice', 'Tool choice', 'called the tools the question needs'],
		['retrieval', 'Retrieval', 'the right passages are in the top 4'],
		['facts', 'Facts', 'numbers and names match the database, within tolerance'],
		['citation', 'Citation', 'cites sources, and every cited source was returned'],
		['refusal', 'Refusal', 'declines exactly when the data can’t answer']
	];

	// The "Passed" row (case counts) followed by the five metrics, for the narrow-screen cards.
	const CARD_ROWS: [keyof SplitBlock | null, string, string][] = [[null, 'Passed', ''], ...METRICS];

	function passed(v: number | null | undefined): string {
		if (v === null || v === undefined) return 'n/a';
		return v >= 1 ? 'pass' : 'miss';
	}
</script>

<h1>How it's tested</h1>

{#if error}
	<p class="panel">Couldn't load the eval results: {error}</p>
{:else if data}
	{@const sb = data.scoreboard}
	{@const h = sb.after.heldout}
	{@const t = sb.after.tuned}
	{@const changes = splitChanges(sb.what_changed)}
	<p class="lede">
		28 test questions, each with facts checked against SQL on the raw tables, never against the model. Half of them
		were set aside and not tuned against.
	</p>

	<section class="panel headline">
		<p class="big">{h.pass} of {h.cases}</p>
		<p>
			held-out questions passed, the same {h.pass_all_runs} on each of {h.runs_per_case} runs. On the {t.cases} tuned
			questions: {t.pass} of {t.cases}, the same {t.pass_all_runs} on each run.
		</p>
		<p class="small">Model: {sb.after.model.replace(/^ollama\//, '')}.</p>
	</section>

	{#if sb.split_note}
		<p class="note">{sb.split_note}</p>
	{/if}

	<h2>Scores by half</h2>
	<div class="scroll scores-wrap">
		<table class="scores">
			<thead>
				<tr>
					<th scope="col">Metric</th>
					<th scope="col">Held out, now</th>
					<th scope="col">Tuned, now</th>
					{#if sb.before.heldout}<th scope="col">Held out, baseline</th>{/if}
					{#if sb.before.tuned}<th scope="col">Tuned, baseline</th>{/if}
				</tr>
			</thead>
			<tbody>
				<tr>
					<th scope="row">Passed</th>
					<td>{h.pass} of {h.cases}</td>
					<td>{t.pass} of {t.cases}</td>
					{#if sb.before.heldout}<td>{sb.before.heldout.pass} of {sb.before.heldout.cases}</td>{/if}
					{#if sb.before.tuned}<td>{sb.before.tuned.pass} of {sb.before.tuned.cases}</td>{/if}
				</tr>
				{#each METRICS as [key, label, help] (key)}
					<tr>
						<th scope="row">{label}<span class="help">{help}</span></th>
						<td>{pct(h[key] as number | null)}</td>
						<td>{pct(t[key] as number | null)}</td>
						{#if sb.before.heldout}<td>{pct(sb.before.heldout[key] as number | null)}</td>{/if}
						{#if sb.before.tuned}<td>{pct(sb.before.tuned[key] as number | null)}</td>{/if}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	<div class="cards">
		{#each CARD_ROWS as [key, label, help] (label)}
			<div class="metric panel">
				<p class="mlabel">{label}{#if help}<span class="help">{help}</span>{/if}</p>
				<dl>
					<dt>Held out, now</dt>
					<dd>{key === null ? `${h.pass} of ${h.cases}` : pct(h[key] as number | null)}</dd>
					<dt>Tuned, now</dt>
					<dd>{key === null ? `${t.pass} of ${t.cases}` : pct(t[key] as number | null)}</dd>
					{#if sb.before.heldout}
						<dt>Held out, baseline</dt>
						<dd>{key === null ? `${sb.before.heldout.pass} of ${sb.before.heldout.cases}` : pct(sb.before.heldout[key] as number | null)}</dd>
					{/if}
					{#if sb.before.tuned}
						<dt>Tuned, baseline</dt>
						<dd>{key === null ? `${sb.before.tuned.pass} of ${sb.before.tuned.cases}` : pct(sb.before.tuned[key] as number | null)}</dd>
					{/if}
				</dl>
			</div>
		{/each}
	</div>
	{#if sb.before.split_note}
		<p class="small">Baseline: {sb.before.cases} questions, one run. {sb.before.split_note}</p>
	{/if}

	<h2>Speed</h2>
	<ul class="plain">
		{#if sb.shown_answers_avg_latency_ms}
			<li>
				The answers shown in this demo took {formatSeconds(sb.shown_answers_avg_latency_ms)} each on average (one run per
				question).
			</li>
		{/if}
		<li>
			Averaged over every eval answer in all {h.runs_per_case} runs, including the quick document and refusal questions:
			{formatSeconds(h.avg_latency_ms)} on the held-out half and {formatSeconds(t.avg_latency_ms)} on the tuned half.
		</li>
		<li>The first baseline took {formatSeconds(sb.before.avg_latency_ms)} per answer.</li>
	</ul>

	<h2>What changed from the baseline</h2>
	{#if changes.text}
		<p class="changed">{changes.text}</p>
	{:else}
		<dl class="beforeafter">
			<dt>Before</dt><dd>{changes.before}</dd>
			<dt>Now</dt><dd>{changes.after}</dd>
		</dl>
		<ul class="changes">
			{#each changes.items as item, i (i)}<li>{item}</li>{/each}
		</ul>
	{/if}

	<h2>Demo questions</h2>
	<div class="scroll">
		<table class="questions">
			<thead>
				<tr><th scope="col">Question</th><th scope="col">Before</th><th scope="col">Now</th></tr>
			</thead>
			<tbody>
				{#each data.questions as q (q.id)}
					<tr>
						<td><span class="id">{q.id}</span> {q.question}</td>
						<td class={passed(q.eval.before?.pass)}>{passed(q.eval.before?.pass)}</td>
						<td class={passed(q.eval.after?.pass)}>{passed(q.eval.after?.pass)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{:else}
	<p class="lede">Loading.</p>
{/if}

<style>
	.headline .big {
		font-size: 2rem;
		font-weight: 700;
		margin: 0;
		line-height: 1.1;
	}
	.headline p {
		margin: 0.2rem 0;
	}
	.note {
		border-left: 3px solid var(--line);
		padding-left: 0.75rem;
		color: var(--ink-soft);
		font-size: 0.9rem;
	}
	.small {
		font-size: 0.82rem;
		color: var(--ink-soft);
	}
	.scroll {
		overflow-x: auto;
	}
	table {
		border-collapse: collapse;
		width: 100%;
		font-size: 0.88rem;
		background: var(--panel);
	}
	th,
	td {
		text-align: left;
		padding: 0.35rem 0.5rem;
		border-bottom: 1px solid var(--line);
		vertical-align: top;
	}
	thead th {
		color: var(--ink-soft);
		font-weight: 600;
		white-space: nowrap;
	}
	.scores td {
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.help {
		display: block;
		font-weight: 400;
		font-size: 0.75rem;
		color: var(--ink-soft);
	}
	.changed {
		font-size: 0.9rem;
	}
	/* Scores: a table on wide screens, one card per metric on narrow ones. */
	.cards {
		display: none;
		gap: 0.5rem;
	}
	@media (max-width: 40rem) {
		.scores-wrap {
			display: none;
		}
		.cards {
			display: grid;
		}
	}
	.metric {
		padding: 0.6rem 0.75rem;
	}
	.mlabel {
		margin: 0 0 0.35rem;
		font-weight: 600;
	}
	.metric dl {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 0.15rem 0.75rem;
		margin: 0;
		font-size: 0.88rem;
	}
	.metric dt {
		color: var(--ink-soft);
	}
	.metric dd {
		margin: 0;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.plain {
		padding-left: 1.1rem;
	}
	.plain li,
	.changes li {
		margin-bottom: 0.3rem;
	}
	.changes {
		padding-left: 1.1rem;
		font-size: 0.92rem;
	}
	.beforeafter {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.3rem 0.75rem;
		margin: 0 0 0.6rem;
		font-size: 0.92rem;
	}
	.beforeafter dt {
		font-weight: 600;
	}
	.beforeafter dd {
		margin: 0;
	}
	.id {
		font: 0.75rem var(--mono);
		color: var(--ink-soft);
	}
	td.pass {
		color: var(--good);
	}
	td.miss {
		color: var(--bad);
	}
</style>
