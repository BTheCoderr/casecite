import { describe, it, expect } from 'vitest';
import { emptyDisclosure, emptyRow, makeReviewPacket, reviewQuestions } from './patentStudio';

describe('Patent Studio review packet', () => {
  it('reports missing documentation without declaring patentability', () => {
    const questions = reviewQuestions(emptyDisclosure(), [emptyRow(1)]);
    expect(questions).toContain('Clarify: Technical problem');
    expect(questions).toContain('Row 1: identify the claim element.');
    expect(questions.some(question => question.includes('Practitioner must verify'))).toBe(true);
  });
  it('preserves manual evidence and always includes practitioner verification', () => {
    const disclosure = { ...emptyDisclosure(), title: 'Fictional valve' };
    const row = { ...emptyRow(1), element: 'A valve', reference: 'Fictional reference', referencePassage: 'Figure 2', status: 'candidate' as const };
    const packet = JSON.parse(makeReviewPacket(disclosure, [row], 'Check dates'));
    expect(packet.disclosure.title).toBe('Fictional valve');
    expect(packet.claimMappings[0]).toEqual(row);
    expect(packet.reviewerNotes).toBe('Check dates');
    expect(packet.openQuestions.some((question: string) => question.includes('Practitioner must verify'))).toBe(true);
    expect(packet.classification).toContain('unverified');
  });
  it('requires an element even when all rows were removed', () => {
    expect(reviewQuestions(emptyDisclosure(), [])).toContain('Record at least one claim element for review.');
  });
});
