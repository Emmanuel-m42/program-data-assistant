<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { DEMO } from '#lib/api.ts';
	import favicon from '#lib/assets/favicon.svg';
	import type { LayoutProps } from './$types';
	import '../app.css';

	let { children }: LayoutProps = $props();

	const links = [
		{ href: resolve('/'), label: 'Ask' },
		{ href: resolve('/offices'), label: 'Offices' },
		{ href: resolve('/tested'), label: "How it's tested" }
	];
	const here = (href: string) => page.url.pathname.replace(/\/$/, '') === href.replace(/\/$/, '');
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<header class="top">
	<div class="wrap bar">
		<a class="brand" href={resolve('/')}>Program data assistant</a>
		<nav aria-label="Main">
			{#each links as l (l.href)}
				<a href={l.href} aria-current={here(l.href) ? 'page' : undefined}>{l.label}</a>
			{/each}
		</nav>
	</div>
</header>

<main class="wrap">
	{@render children()}
</main>

{#if !DEMO}
	<footer class="wrap foot">
		<p>Live mode.</p>
	</footer>
{/if}
