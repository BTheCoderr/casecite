import { useRef, useState } from 'react';
import { buildSearchPlan, emptyCandidate, makePriorArtPacket, PRIOR_ART_SOURCES, SEARCH_STEPS } from '../constants/priorArt';
import type { Candidate } from '../constants/priorArt';
import s from './PriorArtWorkbench.module.css';

export default function PriorArtWorkbench() {
  const [feature, setFeature] = useState('');
  const [synonyms, setSynonyms] = useState('');
  const [context, setContext] = useState('');
  const [classifications, setClassifications] = useState('');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [steps, setSteps] = useState<number[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const nextId = useRef(1);
  const plan = buildSearchPlan(feature, synonyms, context, classifications);

  function update(id: number, patch: Partial<Omit<Candidate, 'id'>>) {
    setCandidates(items => items.map(item => item.id === id ? { ...item, ...patch } : item));
    setConfirmed(false);
  }

  function exportNotes() {
    if (!confirmed || !plan.keywords) return;
    const url = URL.createObjectURL(new Blob([makePriorArtPacket(plan, candidates, steps)], { type: 'application/json' }));
    try {
      const link = document.createElement('a');
      link.href = url;
      link.download = 'counsel-fictional-prior-art-notes.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
    } finally {
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  }

  return (
    <section className={s.panel} aria-labelledby="prior-art-heading">
      <h2 id="prior-art-heading">Prior art discovery workbench</h2>
      <p>Manual research preview. Use fictional information only. No automatic patent database search, AI, network submission or server storage. Entries disappear when you leave this page. The export is an unencrypted local file.</p>
      <h3>1. Prepare search concepts</h3>
      <label>Technical feature<input value={feature} maxLength={300} onChange={event => { setFeature(event.target.value); setConfirmed(false); }} /></label>
      <label>Alternate terms (comma or newline separated)<textarea value={synonyms} maxLength={600} onChange={event => { setSynonyms(event.target.value); setConfirmed(false); }} /></label>
      <label>Application or context terms<textarea value={context} maxLength={600} onChange={event => { setContext(event.target.value); setConfirmed(false); }} /></label>
      <label>Candidate CPC or IPC classes<input value={classifications} maxLength={300} onChange={event => { setClassifications(event.target.value); setConfirmed(false); }} /></label>
      <p className={s.meta}>Generic Boolean search ideas only. Each database has its own field syntax and operators. Confirm classification codes before using them.</p>
      {plan.keywords && <div className={s.output}>
        <strong>Broad concept query</strong><code>{plan.keywords}</code>
        <strong>Concept plus context query</strong><code>{plan.combined}</code>
        {plan.classifications.length > 0 && <><strong>Classification terms to check</strong><code>{plan.classifications.join(', ')}</code></>}
      </div>}
      <h3>2. Open official search collections</h3>
      <p>Links are fixed and never include your worksheet or search terms. Search manually in the external service; do not enter confidential invention details. USPTO account requirements may apply.</p>
      <ul className={s.sources}>{PRIOR_ART_SOURCES.map(source => <li key={source.id}>
        <a href={source.url} target="_blank" rel="noopener noreferrer">{source.label}</a><span className={s.meta}>{source.scope}</span>
      </li>)}</ul>
      <h3>3. Research checklist</h3>
      {SEARCH_STEPS.map((step, index) => <label key={step} className={s.check}>
        <input type="checkbox" checked={steps.includes(index)} onChange={event => {
          setSteps(previous => event.target.checked ? [...previous, index] : previous.filter(item => item !== index));
          setConfirmed(false);
        }} /> {step}
      </label>)}
      <h3>4. Record candidate references</h3>
      <p>All entries are unverified candidates, not a finding of prior art or invalidity. No dates are calculated or interpreted.</p>
      {candidates.map((item, index) => <fieldset key={item.id}>
        <legend>Candidate {index + 1} (unverified)</legend>
        <label>Reference identifier<input maxLength={120} value={item.identifier} onChange={event => update(item.id, { identifier: event.target.value })} /></label>
        <label>Collection<select value={item.source} onChange={event => update(item.id, { source: event.target.value as Candidate['source'] })}>
          <option value="uspto">USPTO</option><option value="epo">Espacenet</option><option value="wipo">PATENTSCOPE</option><option value="other">Other / non-patent literature</option>
        </select></label>
        <label>Reference title<input maxLength={500} value={item.title} onChange={event => update(item.id, { title: event.target.value })} /></label>
        <label>Reported publication date<input type="date" value={item.publicationDate} onChange={event => update(item.id, { publicationDate: event.target.value })} /></label>
        <label>Candidate passage or figure<textarea maxLength={6000} value={item.passage} onChange={event => update(item.id, { passage: event.target.value })} /></label>
        <label>Review notes<textarea maxLength={4000} value={item.notes} onChange={event => update(item.id, { notes: event.target.value })} /></label>
        <button type="button" onClick={() => { setCandidates(items => items.filter(row => row.id !== item.id)); setConfirmed(false); }}>Remove candidate {index + 1}</button>
      </fieldset>)}
      <button type="button" disabled={candidates.length >= 30} onClick={() => { const id = nextId.current++; setCandidates(items => [...items, emptyCandidate(id)]); setConfirmed(false); }}>Add candidate reference</button>
      <label className={s.check}><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> I confirm these prior art notes contain fictional data only and are unverified.</label>
      <button type="button" disabled={!confirmed || !plan.keywords} onClick={exportNotes}>Export prior art notes (JSON)</button>
    </section>
  );
}
