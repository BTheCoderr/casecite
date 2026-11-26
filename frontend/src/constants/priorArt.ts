// Manual discovery only: no automatic queries, provider requests or legal conclusions.
export const PRIOR_ART_SOURCES = [
  { id: 'uspto', label: 'USPTO Patent Public Search', url: 'https://www.uspto.gov/patents/search/patent-public-search', scope: 'US published applications and patents' },
  { id: 'epo', label: 'EPO Espacenet', url: 'https://www.epo.org/en/searching-for-patents/technical/espacenet', scope: 'Worldwide patent documents' },
  { id: 'wipo', label: 'WIPO PATENTSCOPE', url: 'https://www.wipo.int/en/web/patentscope/', scope: 'PCT and participating national collections' },
  { id: 'cpc', label: 'USPTO classification search', url: 'https://www.uspto.gov/web/patents/classification/', scope: 'Find relevant CPC classes' },
  { id: 'strategy', label: 'USPTO preliminary search strategy', url: 'https://www.uspto.gov/patents/search/patent-search-strategy', scope: 'Official search methodology' },
] as const;

export const SEARCH_STEPS = [
  'Identify technical features and alternate terminology.',
  'Find and inspect relevant CPC or IPC classifications.',
  'Run keyword and classification searches in more than one collection.',
  'Read claims, descriptions, drawings and cited references; search non-patent literature separately.',
  'Record publication dates, passages and gaps; ask a practitioner to determine applicable dates and legal relevance.',
] as const;

export interface Candidate {
  id: number;
  identifier: string;
  source: 'uspto' | 'epo' | 'wipo' | 'other';
  title: string;
  publicationDate: string;
  passage: string;
  notes: string;
}

export function emptyCandidate(id: number): Candidate {
  return { id, identifier: '', source: 'uspto', title: '', publicationDate: '', passage: '', notes: '' };
}

function terms(value: string): string[] {
  return [...new Set(value.split(/[,\n]/).map(item => item.trim().replace(/["\r\t]/g, ' ').replace(/\s+/g, ' ')).filter(Boolean))].slice(0, 8);
}

export function buildSearchPlan(feature: string, synonyms: string, context: string, classifications: string) {
  const variants = terms([feature, synonyms].join(','));
  const contexts = terms(context);
  const classes = terms(classifications);
  const concept = variants.map(value => '"' + value + '"').join(' OR ');
  const contextGroup = contexts.map(value => '"' + value + '"').join(' OR ');
  return {
    keywords: concept,
    combined: concept && contextGroup ? '(' + concept + ') AND (' + contextGroup + ')' : concept,
    classifications: classes,
  };
}

export function makePriorArtPacket(plan: ReturnType<typeof buildSearchPlan>, candidates: readonly Candidate[], steps: readonly number[]): string {
  return JSON.stringify({
    schemaVersion: 1,
    classification: 'fictional manual prior-art discovery notes; unverified',
    notice: 'No live search performed by Counsel. Search syntax must be adapted to each service. Dates, passages and legal relevance require independent practitioner verification.',
    plan,
    completedSearchSteps: SEARCH_STEPS.filter((_, index) => steps.includes(index)),
    candidates: candidates.filter(item => item.identifier.trim() || item.title.trim()).map(item => ({
      ...item, status: 'unverified candidate',
    })),
  }, null, 2);
}
