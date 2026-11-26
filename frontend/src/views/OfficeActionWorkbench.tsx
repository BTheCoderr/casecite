import { useState } from 'react';
import { ACTION_CHECKS, detectActionMentions, emptyIssue, GUIDE_SECTIONS, makeActionPacket, MAX_ACTION_TEXT } from '../constants/officeAction';
import type { ActionIssue, ReviewStatus } from '../constants/officeAction';
import { IP_SOURCES } from '../constants/ipSources';
import s from './PriorArtWorkbench.module.css';

export default function OfficeActionWorkbench() {
  const [text, setText] = useState('');
  const [scanned, setScanned] = useState(false);
  const [issues, setIssues] = useState<Record<string, ActionIssue>>({});
  const [checks, setChecks] = useState<number[]>([]);
  const [notes, setNotes] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const detection = scanned ? detectActionMentions(text) : { mentions: [], truncated: false };

  function changeText(value: string) {
    setText(value);
    setScanned(false);
    setIssues({});
    setChecks([]);
    setNotes('');
    setConfirmed(false);
  }

  function updateIssue(id: string, patch: Partial<ActionIssue>) {
    setIssues(previous => ({ ...previous, [id]: { ...(previous[id] ?? emptyIssue()), ...patch } }));
    setConfirmed(false);
  }

  function download() {
    if (!confirmed || !scanned) return;
    const packet = makeActionPacket(text, issues, checks, notes);
    const url = URL.createObjectURL(new Blob([packet], { type: 'application/json' }));
    try {
      const link = document.createElement('a');
      link.href = url;
      link.download = 'counsel-fictional-office-action-review.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
    } finally {
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  }

  return (
    <section className={s.panel} aria-labelledby="office-action-workbench-heading">
      <h2 id="office-action-workbench-heading">Office Action review workbench</h2>
      <p>Fictional-data preview. Paste a synthetic action excerpt to identify explicit statutory and claim references. This is a local text scan, not an AI analysis, rejection classification or legal recommendation. No uploads, persistence, deadline calculation or filing. Editing the source clears all review notes.</p>
      <label>Fictional Office Action text
        <textarea rows={8} maxLength={MAX_ACTION_TEXT} value={text} onChange={event => changeText(event.target.value)} autoComplete="off" />
      </label>
      <button type="button" disabled={!text.trim()} onClick={() => { setScanned(true); setConfirmed(false); }}>Scan explicit references</button>{' '}
      <button type="button" disabled={!text} onClick={() => changeText('')}>Clear Office Action</button>
      {scanned && <>
        <p role="status">{detection.mentions.length} candidate mention{detection.mentions.length === 1 ? '' : 's'} found. These may include background discussion, not actual grounds of rejection.</p>
        {detection.truncated && <p role="alert">Scan limit reached. Review the entire document manually.</p>}
        {detection.mentions.length === 0 && <p>No supported explicit references found. This does not mean the action has no rejections or issues.</p>}
        {detection.mentions.map((mention, index) => {
          const issue = issues[mention.id] ?? emptyIssue();
          const guides = mention.statute ? GUIDE_SECTIONS[mention.statute] : [];
          return <fieldset key={mention.id}>
            <legend>Mention {index + 1} — {mention.literal} (unverified)</legend>
            <p className={s.meta}>Literal {mention.kind === 'statute' ? 'statutory citation' : 'claim reference'} · source offsets {mention.start}–{mention.end}</p>
            <blockquote className={s.excerpt}>{mention.excerpt}</blockquote>
            {guides.length > 0 && <div>
              <p>Starting points for manual research, not a complete or verified legal mapping:</p>
              <ul>{IP_SOURCES.filter(source => guides.includes(source.id)).map(source => <li key={source.id}>
                <a href={source.url} target="_blank" rel="noopener noreferrer">MPEP § {source.id}: {source.title}</a>
              </li>)}</ul>
            </div>}
            <label>Examiner rationale (manual notes)<textarea rows={3} maxLength={3000} value={issue.examinerRationale} onChange={event => updateIssue(mention.id, { examinerRationale: event.target.value })} /></label>
            <label>Cited reference or pinpoint<input maxLength={500} value={issue.reference} onChange={event => updateIssue(mention.id, { reference: event.target.value })} /></label>
            <label>Response questions and evidence gaps<textarea rows={3} maxLength={3000} value={issue.responseNotes} onChange={event => updateIssue(mention.id, { responseNotes: event.target.value })} /></label>
            <label>Review status<select value={issue.status} onChange={event => updateIssue(mention.id, { status: event.target.value as ReviewStatus })}>
              <option value="unreviewed">Unreviewed</option><option value="needs-source-check">Needs source check</option><option value="practitioner-review">Ready for practitioner review (not approved)</option>
            </select></label>
          </fieldset>;
        })}
        <h3>Practitioner review checklist</h3>
        {ACTION_CHECKS.map((item, index) => <label className={s.check} key={item}>
          <input type="checkbox" checked={checks.includes(index)} onChange={event => {
            const checked = event.target.checked;
            setChecks(previous => checked ? [...previous, index] : previous.filter(value => value !== index));
            setConfirmed(false);
          }} /> {item}
        </label>)}
        <label>Office Action practitioner notes<textarea rows={4} maxLength={6000} value={notes} onChange={event => { setNotes(event.target.value); setConfirmed(false); }} /></label>
        <label className={s.check}><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> I confirm this Office Action contains fictional data only and the exported draft is unencrypted and unverified.</label>
        <button type="button" disabled={!confirmed} onClick={download}>Export Office Action review (JSON)</button>
      </>}
    </section>
  );
}
