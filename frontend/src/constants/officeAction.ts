// Local, literal reference detection only. Not a legal classification.
export const MAX_ACTION_TEXT = 60000;
export const MAX_MENTIONS = 80;

export type Statute = '101' | '102' | '103' | '112';
export type MentionKind = 'statute' | 'claims';
export interface ActionMention {
  id: string;
  kind: MentionKind;
  literal: string;
  start: number;
  end: number;
  excerpt: string;
  excerptStart: number;
  excerptEnd: number;
  statute?: Statute;
}

export const GUIDE_SECTIONS: Record<Statute, readonly string[]> = {
  '101': ['2106'],
  '102': ['2131'],
  '103': ['2141'],
  '112': ['2163', '2164'],
};

export const ACTION_CHECKS = [
  'Confirm the complete official action and application record.',
  'Confirm the affected claims, each ground, statutory version and examiner rationale.',
  'Verify cited documents, passages and applicable dates independently.',
  'Review the actual claim language, disclosure support and possible response approaches.',
  'Have a qualified practitioner confirm the response strategy and independently verify every deadline.',
] as const;

export type ReviewStatus = 'unreviewed' | 'needs-source-check' | 'practitioner-review';
export interface ActionIssue {
  status: ReviewStatus;
  examinerRationale: string;
  reference: string;
  responseNotes: string;
}

export const emptyIssue = (): ActionIssue => ({
  status: 'unreviewed', examinerRationale: '', reference: '', responseNotes: '',
});

export function detectActionMentions(text: string): { mentions: ActionMention[]; truncated: boolean } {
  const input = text.slice(0, MAX_ACTION_TEXT);
  // Require an explicit statutory prefix. Do not equate a citation with an
  // actual rejection. Match literal claim numbers/ranges, not inferred claims.
  const rules: { kind: MentionKind; pattern: RegExp }[] = [
    { kind: 'statute', pattern: /\b35[ \t]+U\.?[ \t]*S\.?[ \t]*C\.?[ \t]*(?:§{1,2}[ \t]*|sections?[ \t]+)?(101|102|103|112)(?![\d.])(?:[ \t]*\([a-z0-9]+\))*/gi },
    { kind: 'claims', pattern: /\bclaims?[ \t]+\d+(?:(?:[ \t]*(?:[-–—,]|and|through|to)[ \t]*)\d+)*/gi },
  ];
  const mentions: ActionMention[] = [];
  let limited = text.length > MAX_ACTION_TEXT;
  for (const { kind, pattern } of rules) {
    let count = 0;
    for (const match of input.matchAll(pattern)) {
      // Bound each category independently; sort and cap the combined list.
      if (count++ >= MAX_MENTIONS) { limited = true; break; }
      const start = match.index ?? 0;
      const end = start + match[0].length;
      const excerptStart = Math.max(0, start - 160);
      const excerptEnd = Math.min(input.length, end + 200);
      mentions.push({
        id: kind + ':' + start,
        kind, literal: match[0], start, end,
        excerpt: input.slice(excerptStart, excerptEnd), excerptStart, excerptEnd,
        ...(kind === 'statute' ? { statute: match[1] as Statute } : {}),
      });
    }
  }
  mentions.sort((a, b) => a.start - b.start);
  return { mentions: mentions.slice(0, MAX_MENTIONS), truncated: limited || mentions.length > MAX_MENTIONS };
}

export function makeActionPacket(
  text: string,
  issues: Record<string, ActionIssue>,
  checks: readonly number[],
  notes: string,
): string {
  const detected = detectActionMentions(text);
  return JSON.stringify({
    schemaVersion: 1,
    classification: 'fictional office action issue-spotting draft; unverified',
    notice: 'Literal mentions only; not findings of rejection, claim coverage, legal relevance or deadline. No response is approved or filed. Exact offsets refer to the original pasted text in UTF-16 code units. Full source text is not included.',
    scanTruncated: detected.truncated,
    mentions: detected.mentions.map(mention => ({
      ...mention,
      review: issues[mention.id] ?? emptyIssue(),
      suggestedResearchSections: mention.statute ? GUIDE_SECTIONS[mention.statute] : [],
    })),
    checklist: ACTION_CHECKS.map((item, index) => ({ item, marked: checks.includes(index) })),
    practitionerNotes: notes,
  }, null, 2);
}
