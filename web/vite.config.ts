import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';

// PUBLIC_API_URL is baked in at build time. Unset or "demo" means demo mode: answers come from the
// recorded runs in ../demo/recorded_runs.json and no API is called.
const apiUrl = process.env.PUBLIC_API_URL ?? 'demo';

export default defineConfig({
	define: {
		__API_URL__: JSON.stringify(apiUrl)
	},
	server: {
		fs: { allow: ['..'] } // the recorded runs live in the repo's demo/ folder
	},
	plugins: [
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			// Static files with an SPA fallback: any host can serve build/, unknown paths get index.html
			// (the build script also copies it to 404.html for GitHub Pages).
			adapter: adapter({ fallback: 'index.html' }),
			// BASE_PATH serves the app under a subpath, e.g. /program-data-assistant on GitHub Pages. Unset locally.
			paths: { base: (process.env.BASE_PATH ?? '') as '' | `/${string}` }
		})
	],
	test: {
		expect: { requireAssertions: true },
		projects: [
			{
				extends: './vite.config.ts',
				test: {
					name: 'unit',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
