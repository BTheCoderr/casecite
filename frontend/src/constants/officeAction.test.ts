import { describe, expect, it } from 'vitest';
import { detectActionMentions, emptyIssue, makeActionPacket, MAX_MENTIONS } from './officeAction';

describe('Office Action literal scanner', () => {
  it('preserves exact spans and identifies explicit mentions without classifying rejection', () => {
    const text = 'Synthetic text: Claims 1–3 and 5 are discussed under 35 U.S.C. § 103.\nClaim 7 refers to 35 USC 112(b).';
    const result = detectActionMentions(text);
    expect(result.mentions.map(item => item.literal)).toEqual(['Claims 1–3 and 5', '35 U.S.C. § 103', 'Claim 7', '35 USC 112(b)']);
    expect(result.mentions.filter(item => item.kind === 'statute').map(item => item.statute)).toEqual(['103', '112']);
    for (const mention of result.mentions) {
      expect(text.slice(mention.start, mention.end)).toBe(mention.literal);
      expect(text.slice(mention.excerptStart, mention.excerptEnd)).toBe(mention.excerpt);
    }
  });

  it('does not turn unsupported or bare numbers into statutory findings', () => {
    expect(detectActionMentions('101 pages, 103 examples, 35 U.S.C. § 104.').mentions).toEqual([]);
    expect(detectActionMentions('35 U.S.C. § 1030').mentions).toEqual([]);
  });

  it('reports the scan limit and exports only unverified local review notes', () => {
    expect(detectActionMentions('Claim 1. '.repeat(MAX_MENTIONS + 1)).truncated).toBe(true);
    const text = 'Fictional: 35 U.S.C. § 102.';
    const mention = detectActionMentions(text).mentions[0];
    const packet = JSON.parse(makeActionPacket(text, { [mention.id]: { ...emptyIssue(), responseNotes: 'Verify reference.' } }, [0], 'Synthetic notes'));
    expect(packet.classification).toContain('unverified');
    expect(packet.mentions[0].review.responseNotes).toBe('Verify reference.');
    expect(packet.mentions[0].suggestedResearchSections).toEqual(['2131']);
    expect(packet.checklist[0].marked).toBe(true);
    expect(packet).not.toHaveProperty('sourceText');
  });
});
