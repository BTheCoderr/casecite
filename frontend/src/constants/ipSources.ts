// Counsel additions — official-source discovery, not a legal opinion or AI answer.
export interface IpSource {
  id: string;
  title: string;
  keywords: string;
  url: string;
  kind: 'MPEP' | 'Updates';
}

const base = 'https://www.uspto.gov/web/offices/pac/mpep/';
export const IP_SOURCES: readonly IpSource[] = [
  { id: '2106', title: 'Patent subject matter eligibility', keywords: '101 abstract idea judicial exception practical application', url: base + 's2106.html', kind: 'MPEP' },
  { id: '2131', title: 'Anticipation', keywords: '102 novelty prior art single reference', url: base + 's2131.html', kind: 'MPEP' },
  { id: '2141', title: 'Obviousness examination guidelines', keywords: '103 nonobviousness prior art combination', url: base + 's2141.html', kind: 'MPEP' },
  { id: '2163', title: 'Written description', keywords: '112 disclosure support possession', url: base + 's2163.html', kind: 'MPEP' },
  { id: '2164', title: 'Enablement', keywords: '112 disclosure experimentation', url: base + 's2164.html', kind: 'MPEP' },
  { id: '2109', title: 'Inventorship', keywords: 'inventor conception contribution', url: base + 's2109.html', kind: 'MPEP' },
  { id: '2109.01', title: 'Joint inventorship', keywords: 'inventor co-inventor conception contribution', url: base + 's2109.01.html', kind: 'MPEP' },
  { id: '714', title: 'Amendments', keywords: 'office action prosecution response claim amendment', url: base + 's714.html', kind: 'MPEP' },
  { id: 'index', title: 'Complete MPEP index and subsequent publications', keywords: 'manual revision current rules updates index statutes', url: base + 'index.html', kind: 'Updates' },
  { id: 'eligibility-updates', title: 'USPTO subject matter eligibility guidance', keywords: '101 current guidance updates eligibility', url: 'https://www.uspto.gov/patents/laws/examination-policy/subject-matter-eligibility', kind: 'Updates' },
];

export function searchIpSources(query: string): readonly IpSource[] {
  const terms = query.toLowerCase().replace(/§/g, ' ').trim().split(/\s+/).filter(Boolean);
  if (!terms.length) return IP_SOURCES;
  return IP_SOURCES.filter(source => {
    const text = (source.id + ' ' + source.title + ' ' + source.keywords + ' ' + source.kind).toLowerCase();
    return terms.every(term => text.includes(term));
  });
}
