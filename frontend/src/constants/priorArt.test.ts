import { describe, expect, it } from 'vitest';
import { buildSearchPlan, emptyCandidate, makePriorArtPacket, PRIOR_ART_SOURCES } from './priorArt';

describe('prior art planning', () => {
  it('creates generic search ideas without sending a query to a provider', () => {
    expect(buildSearchPlan('valve', 'valve, scraper', 'water', 'B01D')).toEqual({
      keywords: '"valve" OR "scraper"',
      combined: '("valve" OR "scraper") AND ("water")',
      classifications: ['B01D'],
    });
    expect(buildSearchPlan('', '', 'water', '').combined).toBe('');
    expect(PRIOR_ART_SOURCES.every(source => source.url.startsWith('https://') && !source.url.includes('?'))).toBe(true);
  });
  it('exports only recorded candidates as unverified', () => {
    const candidate = { ...emptyCandidate(1), identifier: 'Fictional reference', passage: 'Synthetic passage' };
    const packet = JSON.parse(makePriorArtPacket(buildSearchPlan('valve', '', '', ''), [candidate, emptyCandidate(2)], [0]));
    expect(packet.classification).toContain('unverified');
    expect(packet.candidates).toHaveLength(1);
    expect(packet.candidates[0].status).toBe('unverified candidate');
    expect(packet.completedSearchSteps).toHaveLength(1);
  });
});
