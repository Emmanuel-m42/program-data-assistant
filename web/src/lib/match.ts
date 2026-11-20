// Demo mode: find the recorded question closest to what someone typed.
import type { RecordedQuestion } from './types';

const STOP = new Set([
	'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'do', 'does', 'for', 'from', 'how', 'if', 'in', 'is', 'it',
	'its', 'many', 'much', 'of', 'on', 'or', 'our', 'should', 'than', 'that', 'the', 'this', 'to', 'up', 'us',
	'was', 'we', 'what', 'whats', 'when', 'where', 'which', 'who', 'whos', 'why', 'will', 'with', 'you'
]);

export function words(text: string): string[] {
	return text
		.toLowerCase()
		.replace(/['’]/g, '')
		.split(/[^a-z0-9]+/)
		.filter((w) => w.length > 1 && !STOP.has(w));
}

function stem(w: string): string {
	return w.replace(/(ing|ed|es|s)$/, '');
}

export interface Match {
	question: RecordedQuestion;
	score: number;
	exact: boolean;
}

/** Exact text first, then overlap with each question's words and keywords. Returns null below the threshold. */
export function matchQuestion(typed: string, questions: RecordedQuestion[], threshold = 0.34): Match | null {
	const norm = (s: string) => words(s).join(' ');
	const t = norm(typed);
	if (!t) return null;
	const exact = questions.find((q) => norm(q.question) === t);
	if (exact) return { question: exact, score: 1, exact: true };

	const typedStems = new Set(words(typed).map(stem));
	let best: Match | null = null;
	for (const q of questions) {
		const vocab = new Set([...words(q.question), ...q.keywords.flatMap(words)].map(stem));
		let hits = 0;
		for (const w of typedStems) if (vocab.has(w)) hits++;
		const score = hits / typedStems.size;
		if (!best || score > best.score) best = { question: q, score, exact: false };
	}
	return best && best.score >= threshold ? best : null;
}
