// Shapes of the API responses (docs/api.md) and of demo/recorded_runs.json.

export interface ToolCall {
	name: string;
	args: Record<string, unknown>;
	result: string;
	ok?: boolean;
}

export interface RowsSource {
	type: 'rows';
	table: string; // comma-separated when one query read several tables
	columns: string[];
	rows: unknown[][];
	row_count?: number;
	sql?: string;
}

export interface PassageSource {
	type: 'passage';
	doc: string;
	text: string;
}

/** One VAN tool call through ngpvan-mcp. `result` is exactly what the model saw, already masked by the server. */
export interface McpSource {
	type: 'mcp';
	server: string;
	tool: string;
	args: Record<string, unknown>;
	result: string;
	audit: {
		ts?: string;
		tool?: string;
		status?: string;
		duration_ms?: number;
		van_requests?: number;
		items?: number;
		truncated?: boolean;
		error_kind?: string;
		[key: string]: unknown;
	} | null;
}

export type Source = RowsSource | PassageSource | McpSource;

export interface Citation {
	type: 'table' | 'doc' | 'van';
	id: string;
}

export interface AskResponse {
	question: string;
	answer: string;
	refused: boolean;
	tool_calls: ToolCall[];
	sources: Source[];
	citations?: Citation[];
	latency_ms: number;
	model: string;
}

export interface Metrics {
	tool_choice: number | null;
	retrieval: number | null;
	facts: number | null;
	citation: number | null;
	refusal: number | null;
	pass?: number | null;
	pass_all?: number | null;
}

export interface SplitBlock {
	cases: number;
	runs_per_case: number;
	pass: number;
	pass_all_runs: number;
	tool_choice: number | null;
	retrieval: number | null;
	facts: number | null;
	citation: number | null;
	refusal: number | null;
	avg_latency_ms: number;
}

export interface Scoreboard {
	before: Metrics & {
		label: string;
		cases: number;
		avg_latency_ms: number;
		heldout?: SplitBlock;
		tuned?: SplitBlock;
		split_note?: string;
	};
	after: { label: string; model: string; commit: string; heldout: SplitBlock; tuned: SplitBlock };
	headline?: string;
	split_note?: string;
	what_changed: string;
	shown_answers_avg_latency_ms?: number;
	latency_note?: string;
}

export interface RecordedRun {
	tool_calls: ToolCall[];
	sources: Source[];
	answer: string;
	refused: boolean;
	latency_ms: number;
}

export interface RecordedQuestion extends RecordedRun {
	id: string;
	question: string;
	category: string;
	keywords: string[];
	model: string;
	baseline?: RecordedRun;
	eval: { before: Metrics | null; after: Metrics | null };
}

export interface RecordedRuns {
	program: string;
	generated_at: string;
	model: string;
	scoreboard: Scoreboard;
	questions: RecordedQuestion[];
}

export interface EvalsResponse {
	model: string;
	scoreboard: Scoreboard;
	questions: Pick<RecordedQuestion, 'id' | 'question' | 'category' | 'eval'>[];
}

export interface OfficeSummary {
	office: string;
	pace: {
		goal_total: number | null;
		goal_to_date: number | null;
		doors_to_date: number | null;
		projected_total: number | null;
		projected_vs_goal: number | null;
		projected_pct_of_goal: number | null;
		avg_shifts_per_day_last_7d: number | null;
		extra_shifts_per_day_needed: number | null;
	};
	contact_rates: { week_start: string; contact_rate_pct: number | null }[];
	cost_per_door: number | null;
	registration: {
		card_goal: number | null;
		valid_cards: number | null;
		duplicate_cards: number | null;
		cards_per_hour_last_7d: number | null;
		cards_per_hour_needed: number | null;
		projected_valid_cards: number | null;
	};
	qc_this_week: { flags: number | null; flags_per_100_shifts: number | null };
}

export interface OfficesResponse {
	as_of: string;
	offices: OfficeSummary[];
}
