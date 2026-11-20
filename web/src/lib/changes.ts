// Splits the scoreboard's what_changed text into a short list for display.
// Expected form: "Before: ... After: ... Changes in between: a; b; c." Anything else stays one paragraph.

export interface Changes {
	before: string | null;
	after: string | null;
	items: string[];
	text: string | null; // fallback when the text doesn't have that form
}

export function splitChanges(text: string): Changes {
	const m = /^\s*Before:\s*(.+?)\s*After:\s*(.+?)\s*Changes in between:\s*(.+?)\s*$/s.exec(text);
	if (!m) return { before: null, after: null, items: [], text };
	const items = m[3]
		.replace(/\.\s*$/, '')
		.split(/;\s*/)
		.map((s) => s.trim())
		.filter(Boolean)
		.map((s) => s[0].toUpperCase() + s.slice(1));
	return { before: m[1].replace(/\.$/, ''), after: m[2].replace(/\.$/, ''), items, text: null };
}
