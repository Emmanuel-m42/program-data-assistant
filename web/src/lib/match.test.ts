import { describe, expect, it } from 'vitest';
import recordedJson from '../../../demo/recorded_runs.json';
import { matchQuestion } from './match';
import type { RecordedRuns } from './types';

const questions = (recordedJson as unknown as RecordedRuns).questions;

describe('matchQuestion', () => {
	it('matches every recorded question to itself exactly', () => {
		for (const q of questions) {
			const m = matchQuestion(q.question, questions);
			expect(m?.question.id).toBe(q.id);
			expect(m?.exact).toBe(true);
		}
	});

	it('ignores case and punctuation for an exact match', () => {
		const m = matchQuestion('WHICH offices will miss their goal and by how much', questions);
		expect(m?.question.id).toBe('q02');
		expect(m?.exact).toBe(true);
	});

	it('finds a close paraphrase by keywords', () => {
		expect(matchQuestion("who's over 40 hours for overtime this week?", questions)?.question.id).toBe('q18');
		expect(matchQuestion('duplicate registrations by canvasser', questions)?.question.id).toBe('q16');
		expect(matchQuestion('where should a fourth office go', questions)?.question.id).toBe('q06');
	});

	it('returns nothing for an unrelated question', () => {
		expect(matchQuestion('what is the weather in Paris tomorrow', questions)).toBeNull();
		expect(matchQuestion('?!', questions)).toBeNull();
	});
});
