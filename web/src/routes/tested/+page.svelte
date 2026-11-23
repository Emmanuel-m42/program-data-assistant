<script lang="ts">
	import { evals, formatSeconds, pct } from '#lib/api.ts';
	import { splitChanges } from '#lib/changes.ts';
	import type { CompareGroup, EvalsResponse, SplitBlock } from '#lib/types.ts';

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

	const COMPARE_GROUPS: [CompareGroup, string][] = [
		['heldout_v5', 'Fresh held-out (v5, 50)'],
		['heldout_v4', 'Held-out v4 (tuned)'],
		['heldout_v3', 'Held-out v3 (clean)'],
		['dev', 'Tuned'],
		['heldout_v2', 'Held-out v2 (contaminated)'],
		['test', 'Old held-out (contaminated)']
	];

	// The "Passed" row (case counts) followed by the five metrics, for the narrow-screen cards.
	const CARD_ROWS: [keyof SplitBlock | null, string, string][] = [[null, 'Passed', ''], ...METRICS];

	function passed(v: number | null | undefined): string {
		if (v === null || v === undefined) return 'n/a';
		return v >= 1 ? 'pass' : 'miss';
	}
</script>

<svelte:head><title>How it's tested: Program data assistant</title></svelte:head>

<h1>How it's tested</h1>

{#if error}
	<p class="panel">Couldn't load the eval results: {error}</p>
{:else if data}
	{@const sb = data.scoreboard}
	{@const h = sb.after.heldout}
	{@const t = sb.after.tuned}
	{@const changes = splitChanges(sb.what_changed)}
	{#if sb.comparison?.length}
		<p class="lede">
			190 test questions, each with facts checked against SQL on the raw tables, never against the model: 96 tuned
			on (14 from the start, and 82 held out until the latest tuning used them), two held-out sets of 14 and 15
			read while choosing earlier fixes (contaminated), and two clean sets of 15 and 50, each written and committed
			before the fixes it measures. The 50 ran once, after the tuning.
		</p>
	{:else}
		<p class="lede">
			28 test questions, each with facts checked against SQL on the raw tables, never against the model. Half of them
			were set aside and not tuned against.
		</p>
	{/if}

	{#if sb.headline_note && sb.headline}
		<section class="panel headline">
			<p class="big">{sb.headline}</p>
			<p class="small">{sb.headline_note}</p>
		</section>
	{:else}
		<section class="panel headline">
			<p class="big">{h.pass} of {h.cases}</p>
			<p>
				held-out questions passed, the same {h.pass_all_runs} on each of {h.runs_per_case} runs. On the {t.cases} tuned
				questions: {t.pass} of {t.cases}, the same {t.pass_all_runs} on each run.
			</p>
			<p class="small">Model: {sb.after.model.replace(/^ollama\//, '')}.</p>
		</section>
	{/if}

	{#if sb.comparison?.length}
		<h2>Models compared</h2>
		<p class="small">
			Cases passed (the mean over 3 runs), then pass^3: the cases passed on all 3 runs. Code: "latest" is the current
			code, after the tuning on held-out v4; "eval-v3" the code before it, with held-out v4 as first measured; "v2
			before" and "v2 after" an earlier round of fixes, and "first" the first published run, kept for the record.
		</p>
		<div class="scroll">
			<table class="compare">
				<thead>
					<tr>
						<th scope="col">Model</th>
						<th scope="col">Code</th>
						{#each COMPARE_GROUPS as [, label] (label)}<th scope="col">{label}</th>{/each}
					</tr>
				</thead>
				<tbody>
					{#each sb.comparison as row (row.model + row.code)}
						<tr>
							<th scope="row">{row.model}</th>
							<td>{row.code}</td>
							{#each COMPARE_GROUPS as [key] (key)}
								{@const g = row.groups[key]}
								<td>
									{#if row.status === 'running'}running
									{:else if g}{g.pass} of {g.cases}<span class="help">pass^3 {g.pass_all_runs}</span>
									{:else}<span class="muted">not run</span>{/if}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		{#if sb.comparison_note}<p class="note">{sb.comparison_note}</p>{/if}
		{#if sb.shown_run_note}
			<h2>The shown answers</h2>
			<p class="small">{sb.shown_run_note}</p>
		{/if}
	{/if}

	{#if sb.split_note}
		<p class="note">{sb.split_note}</p>
	{/if}

	<h2>Scores by half{#if sb.comparison?.length}, {sb.after.model.replace(/^ollama\//, '')}{/if}</h2>
	<div class="scroll scores-wrap">
		<table class="scores">
			<thead>
				<tr>
					<th scope="col">Metric</th>
					<th scope="col">Old held-out, now</th>
					<th scope="col">Tuned, now</th>
					{#if sb.before.heldout}<th scope="col">Old held-out, baseline</th>{/if}
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
					<dt>Old held-out, now</dt>
					<dd>{key === null ? `${h.pass} of ${h.cases}` : pct(h[key] as number | null)}</dd>
					<dt>Tuned, now</dt>
					<dd>{key === null ? `${t.pass} of ${t.cases}` : pct(t[key] as number | null)}</dd>
					{#if sb.before.heldout}
						<dt>Old held-out, baseline</dt>
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
						<td>
							<span class="id">{q.id}</span>
							{q.question}
							{#if q.eval.note}<span class="qnote">{q.eval.note}</span>{/if}
						</td>
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
		font-size: clamp(1.35rem, 5vw, 2rem);
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
	.compare td,
	.compare th[scope='row'] {
		min-width: 6.5rem;
	}
	.muted {
		color: var(--ink-soft);
	}
	.qnote {
		display: block;
		margin-top: 0.2rem;
		font-size: 0.8rem;
		color: var(--ink-soft);
	}
	td.pass {
		color: var(--good);
	}
	td.miss {
		color: var(--bad);
	}
</style>
