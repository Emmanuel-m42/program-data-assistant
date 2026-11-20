import { describe, expect, it } from 'vitest';
import recordedJson from '../../../demo/recorded_runs.json';
import { splitChanges } from './changes';

describe('splitChanges', () => {
	it('turns the recorded what_changed text into before, after and a list', () => {
		const c = splitChanges((recordedJson as { scoreboard: { what_changed: string } }).scoreboard.what_changed);
		expect(c.text).toBeNull();
		expect(c.before).toMatch(/^qwen2\.5:7b/);
		expect(c.after).toMatch(/^qwen3\.8:27b/);
		expect(c.items.length).toBeGreaterThan(5);
		expect(c.items.every((i) => /^[A-Z0-9]/.test(i))).toBe(true);
	});

	it('keeps text of another form as one paragraph', () => {
		expect(splitChanges('Just a sentence.')).toEqual({ before: null, after: null, items: [], text: 'Just a sentence.' });
	});
});
