<script lang="ts">
	import { page } from '$app/state';
	import { DEMO, recorded } from '#lib/api.ts';
	import favicon from '#lib/assets/favicon.svg';
	import type { LayoutProps } from './$types';
	import '../app.css';

	let { children }: LayoutProps = $props();

	const links = [
		{ href: '/', label: 'Ask' },
		{ href: '/offices', label: 'Offices' },
		{ href: '/tested', label: "How it's tested" }
	];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Program data assistant</title>
</svelte:head>

<header class="top">
	<div class="wrap bar">
		<a class="brand" href="/">Program data assistant</a>
		<nav aria-label="Main">
			{#each links as l (l.href)}
				<a href={l.href} aria-current={page.url.pathname === l.href ? 'page' : undefined}>{l.label}</a>
			{/each}
		</nav>
	</div>
</header>

<main class="wrap">
	{@render children()}
</main>

<footer class="wrap foot">
	<p>
		Fictional demo data: Riverbend Votes (GOTV) and Riverbend Registers (voter registration).
		{#if DEMO}
			Demo mode: answers are recorded runs of {recorded.model.replace('ollama/', '')}.
		{:else}
			Live mode.
		{/if}
	</p>
</footer>
