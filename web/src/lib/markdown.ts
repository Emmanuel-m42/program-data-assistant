// A small markdown subset for answers: paragraphs, bullet lists, headings, bold, inline code and
// citations like [table:v_office_pace] or [doc:qc-rules#gaps]. It returns tokens, not HTML, so the
// Svelte components render plain text nodes and nothing in an answer can inject markup.
import type { Citation, Source } from './types';

export type Inline =
	| { kind: 'text'; text: string }
	| { kind: 'bold'; text: string }
	| { kind: 'code'; text: string }
	| { kind: 'cite'; cite: Citation; source: number | null };

export type Block =
	| { kind: 'p'; inline: Inline[] }
	| { kind: 'h'; inline: Inline[] }
	| { kind: 'ul'; items: Inline[][] };

const CITE = /\[\s*((?:table|doc|van)\s*:[^\]]+)\]/g;

/** The source index a citation points to: rows by table name (a source may list several), passages by doc id,
 * VAN tool calls by tool name. */
export function sourceIndex(cite: Citation, sources: Source[]): number | null {
	const i = sources.findIndex((s) =>
		cite.type === 'table'
			? s.type === 'rows' && s.table.split(',').map((t) => t.trim()).includes(cite.id)
			: cite.type === 'van'
				? s.type === 'mcp' && s.tool === cite.id
				: s.type === 'passage' && s.doc === cite.id
	);
	return i === -1 ? null : i;
}

function parseCites(inner: string): Citation[] {
	return [...inner.matchAll(/(table|doc|van)\s*:\s*([A-Za-z0-9_#-]+)/g)].map((m) => ({
		type: m[1] as Citation['type'],
		id: m[2].replace(/[-#]+$/, '')
	}));
}

function styled(text: string, out: Inline[]) {
	// **bold** and `code`; everything else is text.
	const re = /\*\*([^*]+)\*\*|`([^`]+)`/g;
	let last = 0;
	for (const m of text.matchAll(re)) {
		if (m.index! > last) out.push({ kind: 'text', text: text.slice(last, m.index) });
		out.push(m[1] !== undefined ? { kind: 'bold', text: m[1] } : { kind: 'code', text: m[2] });
		last = m.index! + m[0].length;
	}
	if (last < text.length) out.push({ kind: 'text', text: text.slice(last) });
}

export function inline(text: string, sources: Source[]): Inline[] {
	const out: Inline[] = [];
	let last = 0;
	for (const m of text.matchAll(CITE)) {
		styled(text.slice(last, m.index), out);
		for (const cite of parseCites(m[1])) out.push({ kind: 'cite', cite, source: sourceIndex(cite, sources) });
		last = m.index! + m[0].length;
	}
	styled(text.slice(last), out);
	return out.filter((t) => t.kind !== 'text' || t.text.length > 0);
}

export function parseAnswer(answer: string, sources: Source[]): Block[] {
	const blocks: Block[] = [];
	let list: Inline[][] | null = null;
	let para: string[] = [];
	const flushPara = () => {
		if (para.length) blocks.push({ kind: 'p', inline: inline(para.join(' '), sources) });
		para = [];
	};
	const flushList = () => {
		if (list) blocks.push({ kind: 'ul', items: list });
		list = null;
	};
	for (const raw of answer.split('\n')) {
		const line = raw.trim();
		const bullet = /^(?:[-*]|\d+[.)])\s+(.*)$/.exec(line);
		const heading = /^#{1,4}\s+(.*)$/.exec(line);
		if (!line) {
			flushPara();
			flushList();
		} else if (bullet) {
			flushPara();
			(list ??= []).push(inline(bullet[1], sources));
		} else if (heading) {
			flushPara();
			flushList();
			blocks.push({ kind: 'h', inline: inline(heading[1], sources) });
		} else if (list && /^\s{2,}/.test(raw)) {
			// indented continuation of a bullet
			list[list.length - 1].push({ kind: 'text', text: ' ' }, ...inline(line, sources));
		} else {
			flushList();
			para.push(line);
		}
	}
	flushPara();
	flushList();
	return blocks;
}
