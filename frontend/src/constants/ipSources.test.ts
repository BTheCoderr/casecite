import { describe, it, expect } from 'vitest';
import { IP_SOURCES, searchIpSources } from './ipSources';
import { MODE_TO_ROUTE, modeFromPath } from '../routeConfig';

describe('IP research source directory', () => {
  it('returns the full directory for blank queries', () => {
    expect(searchIpSources('  ')).toEqual(IP_SOURCES);
  });
  it('matches sections and topics without fabricating results', () => {
    expect(searchIpSources('§ 2106').map(source => source.id)).toEqual(['2106']);
    expect(searchIpSources('joint inventorship').map(source => source.id)).toEqual(['2109.01']);
    expect(searchIpSources('obviousness')[0].id).toBe('2141');
    expect(searchIpSources('unmatched invented topic')).toEqual([]);
  });
  it('uses only fixed HTTPS USPTO destinations with unique IDs', () => {
    expect(new Set(IP_SOURCES.map(source => source.id)).size).toBe(IP_SOURCES.length);
    for (const source of IP_SOURCES) {
      const url = new URL(source.url);
      expect(url.protocol).toBe('https:');
      expect(url.hostname).toBe('www.uspto.gov');
      expect(url.search).toBe('');
    }
  });
  it('registers the research mode route', () => {
    expect(MODE_TO_ROUTE['ip-research']).toBe('/ip-research');
    expect(modeFromPath('/ip-research')).toBe('ip-research');
  });
});
