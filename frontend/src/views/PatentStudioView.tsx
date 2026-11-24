import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { DISCLOSURE_FIELDS, STATUS_LABELS, emptyDisclosure, emptyRow, reviewQuestions, makeReviewPacket } from '../constants/patentStudio';
import type { ClaimRow, EvidenceStatus } from '../constants/patentStudio';
import s from './PatentStudioView.module.css';

export default function PatentStudioView() {
  const [disclosure, setDisclosure] = useState(emptyDisclosure);
  const [rows, setRows] = useState<ClaimRow[]>(() => [emptyRow(1)]);
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const nextId = useRef(2);
  const questions = reviewQuestions(disclosure, rows);

  function updateRow(id: number, patch: Partial<Omit<ClaimRow, 'id'>>) {
    setRows(previous => previous.map(row => row.id === id ? { ...row, ...patch } : row));
  }

  function exportPacket() {
    if (!confirmed) return;
    const blob = new Blob([makeReviewPacket(disclosure, rows, reviewerNotes)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    try {
      const link = document.createElement('a');
      link.href = url;
      link.download = 'counsel-fictional-patent-review.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
    } finally {
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  }

  return (
    <section className={s.page} aria-labelledby="patent-studio-heading">
      <h1 id="patent-studio-heading">Patent Analysis Studio</h1>
      <p>Organize invention disclosures, claim elements and candidate evidence for practitioner review.</p>
      <aside className={s.notice}>Development preview: fictional information only. Entries are kept in this page's memory, not saved to a matter, server, browser storage or AI provider by this module. Leaving or refreshing the page discards entries. Exports are unencrypted local files. This is not a patentability determination or a deadline calculator.</aside>
      <div className={s.grid}>
        <section className={s.panel} aria-labelledby="disclosure-heading">
          <h2 id="disclosure-heading">1. Invention disclosure</h2>
          {DISCLOSURE_FIELDS.map(([key, label]) => (
            <label key={key} className={s.field}>
              {label}
              <textarea rows={key === 'title' ? 1 : 3} maxLength={12000} autoComplete="off" value={disclosure[key]} onChange={event => setDisclosure(previous => ({ ...previous, [key]: event.target.value }))} />
            </label>
          ))}
        </section>
        <section className={s.panel} aria-labelledby="mapping-heading">
          <h2 id="mapping-heading">2. Claim and evidence mapping</h2>
          <p>Enter each claim element separately. Record exact passages and locations; the tool does not verify references.</p>
          {rows.map((row, index) => (
            <fieldset className={s.row} key={row.id}>
              <legend>Element {index + 1}</legend>
              <label className={s.field}>Claim element<textarea rows={2} maxLength={6000} value={row.element} onChange={event => updateRow(row.id, { element: event.target.value })} /></label>
              <label className={s.field}>Disclosure support (page, paragraph or figure)<textarea rows={2} maxLength={6000} value={row.disclosureSupport} onChange={event => updateRow(row.id, { disclosureSupport: event.target.value })} /></label>
              <label className={s.field}>Candidate prior art reference<input maxLength={1000} value={row.reference} onChange={event => updateRow(row.id, { reference: event.target.value })} /></label>
              <label className={s.field}>Pinpoint passage or figure<textarea rows={2} maxLength={6000} value={row.referencePassage} onChange={event => updateRow(row.id, { referencePassage: event.target.value })} /></label>
              <label className={s.field}>Reviewer mapping status<select value={row.status} onChange={event => updateRow(row.id, { status: event.target.value as EvidenceStatus })}>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label className={s.field}>Open issues<textarea rows={2} maxLength={6000} value={row.notes} onChange={event => updateRow(row.id, { notes: event.target.value })} /></label>
              <button type="button" className={s.secondary} onClick={() => setRows(previous => previous.filter(item => item.id !== row.id))}>Remove element {index + 1}</button>
            </fieldset>
          ))}
          <button type="button" className={s.secondary} disabled={rows.length >= 50} onClick={() => { const id = nextId.current++; setRows(previous => [...previous, emptyRow(id)]); }}>Add claim element</button>
        </section>
      </div>
      <section className={s.panel} aria-labelledby="review-heading">
        <h2 id="review-heading">3. Practitioner review</h2>
        <p>Documentation checks only. Resolve eligibility, novelty, obviousness, written description, enablement and inventorship with the applicable authorities and facts.</p>
        <Link to="/ip-research">Open official IP research directory (leaving discards this draft)</Link>
        <ul>{questions.map((question, index) => <li key={index}>{question}</li>)}</ul>
        <label className={s.field}>Practitioner notes<textarea rows={4} maxLength={12000} value={reviewerNotes} onChange={event => setReviewerNotes(event.target.value)} /></label>
        <label className={s.confirm}><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> I confirm this contains fictional data only and understand the export is unencrypted and unverified.</label>
        <button type="button" className={s.primary} disabled={!confirmed} onClick={exportPacket}>Export review draft (JSON)</button>
      </section>
    </section>
  );
}
