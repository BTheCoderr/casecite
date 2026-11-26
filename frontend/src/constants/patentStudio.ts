// Counsel additions. Manual evidence organization; no patentability inference.
export const DISCLOSURE_FIELDS = [
  ['title', 'Working invention title'],
  ['problem', 'Technical problem'],
  ['solution', 'Technical solution and operation'],
  ['alternatives', 'Alternative embodiments and implementation details'],
  ['disclosures', 'Known public disclosures, dates and supporting records'],
  ['contributions', 'Potential contributors and specific technical contributions'],
  ['officeAction', 'Office action issues, deadlines and references (if applicable)'],
] as const;

export type DisclosureKey = typeof DISCLOSURE_FIELDS[number][0];
export type Disclosure = Record<DisclosureKey, string>;
export type EvidenceStatus = 'unreviewed' | 'candidate' | 'gap' | 'unclear';
export interface ClaimRow {
  id: number;
  element: string;
  disclosureSupport: string;
  reference: string;
  referencePassage: string;
  status: EvidenceStatus;
  notes: string;
}

export const STATUS_LABELS: Record<EvidenceStatus, string> = {
  unreviewed: 'Not reviewed',
  candidate: 'Candidate mapping',
  gap: 'Possible gap',
  unclear: 'Unclear',
};

export function emptyDisclosure(): Disclosure {
  return { title: '', problem: '', solution: '', alternatives: '', disclosures: '', contributions: '', officeAction: '' };
}

export function emptyRow(id: number): ClaimRow {
  return { id, element: '', disclosureSupport: '', reference: '', referencePassage: '', status: 'unreviewed', notes: '' };
}

// This is a documentation checklist, not a quality score or legal conclusion.
export function reviewQuestions(disclosure: Disclosure, rows: readonly ClaimRow[]): string[] {
  const issues: string[] = [];
  for (const [key, label] of DISCLOSURE_FIELDS) {
    if (key !== 'officeAction' && !disclosure[key].trim()) issues.push('Clarify: ' + label);
  }
  if (!rows.some(row => row.element.trim())) issues.push('Record at least one claim element for review.');
  for (const [index, row] of rows.entries()) {
    const prefix = 'Row ' + (index + 1) + ': ';
    if (!row.element.trim()) issues.push(prefix + 'identify the claim element.');
    if (!row.disclosureSupport.trim()) issues.push(prefix + 'locate disclosure support or document a gap.');
    if (!row.reference.trim() || !row.referencePassage.trim()) issues.push(prefix + 'record the reference and pinpoint passage, if available.');
    if (row.status !== 'candidate') issues.push(prefix + 'resolve the evidence mapping with a practitioner.');
  }
  issues.push('Practitioner must verify sources, applicable dates, claim interpretation, inventorship and legal conclusions.');
  return issues;
}

export function makeReviewPacket(disclosure: Disclosure, rows: readonly ClaimRow[], reviewerNotes: string): string {
  return JSON.stringify({
    schemaVersion: 1,
    classification: 'fictional-data prototype; unverified attorney review draft',
    notice: 'Manual entries and candidate evidence mappings only. No legal conclusions, source verification, filing or deadline calculation.',
    disclosure,
    claimMappings: rows.map(({ id, ...row }) => ({ id, ...row })),
    openQuestions: reviewQuestions(disclosure, rows),
    reviewerNotes,
  }, null, 2);
}
