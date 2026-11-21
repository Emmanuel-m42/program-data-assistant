import { describe, expect, it } from 'vitest';
import { inline, parseAnswer, sourceIndex } from './markdown';
import type { Source } from './types';

const sources: Source[] = [
	{ type: 'rows', table: 'v_office_pace', columns: ['office'], rows: [['Eastgate']] },
	{ type: 'rows', table: 'client_daily_report, v_daily_doors', columns: ['office'], rows: [] },
	{ type: 'passage', doc: 'qc-rules#flash-knocking', text: '...' }
];

describe('citations', () => {
	it('map to sources by table, including multi-table sources, and by doc id', () => {
		expect(sourceIndex({ type: 'table', id: 'v_office_pace' }, sources)).toBe(0);
		expect(sourceIndex({ type: 'table', id: 'v_daily_doors' }, sources)).toBe(1);
		expect(sourceIndex({ type: 'doc', id: 'qc-rules#flash-knocking' }, sources)).toBe(2);
		expect(sourceIndex({ type: 'doc', id: 'qc-rules#gaps' }, sources)).toBeNull();
	});

	it('map VAN citations to the matching tool call', () => {
		const withVan: Source[] = [
			...sources,
			{ type: 'mcp', server: 'ngpvan-mcp', tool: 'turf_door_counts', args: {}, result: '{"doors": 437}', audit: { status: 'ok' } }
		];
		expect(sourceIndex({ type: 'van', id: 'turf_door_counts' }, withVan)).toBe(3);
		expect(sourceIndex({ type: 'van', id: 'list_events' }, withVan)).toBeNull();
		const t = inline('437 doors on VAN saved lists [van:turf_door_counts].', withVan);
		expect(t.find((x) => x.kind === 'cite')).toEqual({ kind: 'cite', cite: { type: 'van', id: 'turf_door_counts' }, source: 3 });
	});

	it('become chip tokens, including several inside one bracket', () => {
		const t = inline('Short by 3,204 [table:v_office_pace] and [table: v_daily_doors, doc:qc-rules#flash-knocking].', sources);
		expect(t.filter((x) => x.kind === 'cite').map((x) => (x.kind === 'cite' ? [x.cite.id, x.source] : null))).toEqual([
			['v_office_pace', 0],
			['v_daily_doors', 1],
			['qc-rules#flash-knocking', 2]
		]);
		expect(t[0]).toEqual({ kind: 'text', text: 'Short by 3,204 ' });
	});
});

describe('markdown subset', () => {
	it('keeps markup as plain text, so nothing can be injected', () => {
		const blocks = parseAnswer('<script>alert(1)</script> **bold** <img src=x onerror=alert(1)>', sources);
		expect(blocks).toHaveLength(1);
		const b = blocks[0];
		expect(b.kind).toBe('p');
		if (b.kind !== 'p') return;
		// tokens are text/bold only; the Svelte components render them as text nodes, never as HTML
		expect(b.inline.map((x) => x.kind)).toEqual(['text', 'bold', 'text']);
		expect(b.inline[0]).toEqual({ kind: 'text', text: '<script>alert(1)</script> ' });
	});

	it('parses paragraphs, bullets, headings, bold and code', () => {
		const blocks = parseAnswer('Answer first.\n\n### Detail\n- **Eastgate**: `v_office_pace` misses\n- Harbor', sources);
		expect(blocks.map((b) => b.kind)).toEqual(['p', 'h', 'ul']);
		const ul = blocks[2];
		expect(ul.kind === 'ul' && ul.items.length).toBe(2);
		expect(ul.kind === 'ul' && ul.items[0].map((x) => x.kind)).toEqual(['bold', 'text', 'code', 'text']);
	});
});
