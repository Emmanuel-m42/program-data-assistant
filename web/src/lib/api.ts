// Talks to the FastAPI backend, or in demo mode answers from the recorded runs bundled at build time.
import recordedJson from '../../../demo/recorded_runs.json';
import officesJson from './demo/offices.json';
import { matchQuestion } from './match';
import type { AskResponse, EvalsResponse, OfficesResponse, RecordedQuestion, RecordedRuns } from './types';

export const API_URL: string = typeof __API_URL__ === 'string' ? __API_URL__ : 'demo';
export const DEMO = !API_URL || API_URL === 'demo';

export const recorded = recordedJson as unknown as RecordedRuns;

export interface Answered {
	response: AskResponse;
	recorded?: RecordedQuestion; // demo mode: the recorded question this answer came from
	matchedExactly?: boolean;
}

export class NoRecordedAnswer extends Error {}

function fromRecorded(q: RecordedQuestion, typed: string): AskResponse {
	return {
		question: typed,
		answer: q.answer,
		refused: q.refused,
		tool_calls: q.tool_calls,
		sources: q.sources,
		latency_ms: q.latency_ms,
		model: q.model
	};
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
	const r = await fetch(`${API_URL.replace(/\/$/, '')}${path}`, init);
	if (!r.ok) throw new Error(`${path} returned ${r.status}`);
	return (await r.json()) as T;
}

export async function ask(question: string): Promise<Answered> {
	if (DEMO) {
		const m = matchQuestion(question, recorded.questions);
		if (!m) throw new NoRecordedAnswer(question);
		return { response: fromRecorded(m.question, question), recorded: m.question, matchedExactly: m.exact };
	}
	const response = await getJson<AskResponse>('/ask', {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify({ question })
	});
	return { response };
}

export async function offices(): Promise<OfficesResponse> {
	return DEMO ? (officesJson as OfficesResponse) : getJson<OfficesResponse>('/offices');
}

export async function evals(): Promise<EvalsResponse> {
	if (DEMO) {
		return {
			model: recorded.model,
			scoreboard: recorded.scoreboard,
			questions: recorded.questions.map(({ id, question, category, eval: e }) => ({ id, question, category, eval: e }))
		};
	}
	return getJson<EvalsResponse>('/evals');
}

export const CATEGORIES = [
	'pace',
	'staffing',
	'office siting',
	'door gaps',
	'QC',
	'VR rate',
	'payroll',
	'client report'
] as const;

export const CATEGORY_LABELS: Record<string, string> = {
	pace: 'Pace',
	staffing: 'Staffing',
	'office siting': 'Office siting',
	'door gaps': 'Door gaps',
	QC: 'QC',
	'VR rate': 'Registration rate',
	payroll: 'Payroll',
	'client report': 'Client report'
};

export function formatSeconds(ms: number): string {
	return `${Math.round(ms / 1000)} s`;
}

export function pct(v: number | null | undefined): string {
	return v === null || v === undefined ? 'n/a' : `${Math.round(v * 100)}%`;
}
