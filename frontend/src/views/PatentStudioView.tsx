import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { PatentClaimElement, PatentWorkspaceDetail, PatentWorkspaceSummary } from '../api/types';
import { useMattersStore } from '../stores/mattersStore';
import { DISCLOSURE_FIELDS, STATUS_LABELS, emptyDisclosure, emptyRow, reviewQuestions, makeReviewPacket } from '../constants/patentStudio';
import type { ClaimRow, Disclosure, EvidenceStatus } from '../constants/patentStudio';
import s from './PatentStudioView.module.css';

function rowsFrom(elements: PatentClaimElement[], firstId: number): ClaimRow[] {
  return elements.map((e, index) => ({
    id: firstId + index,
    element: e.element,
    disclosureSupport: e.disclosureSupport,
    reference: e.reference,
    referencePassage: e.referencePassage,
    status: e.status as EvidenceStatus,
    notes: e.notes,
  }));
}

function errorText(error: unknown): string {
  return error instanceof Error && error.message ? error.message : 'unknown error';
}

export default function PatentStudioView() {
  const [disclosure, setDisclosure] = useState<Disclosure>(emptyDisclosure);
  const [rows, setRows] = useState<ClaimRow[]>(() => [emptyRow(1)]);
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const nextId = useRef(2);
  const questions = reviewQuestions(disclosure, rows);

  // Matter persistence. Nothing is sent until "Save to matter" is pressed.
  const matters = useMattersStore((st) => st.matters);
  const activeMatterId = useMattersStore((st) => st.activeMatterId);
  const mattersInit = useMattersStore((st) => st.init);
  const [matterId, setMatterId] = useState('');
  const [workspaces, setWorkspaces] = useState<PatentWorkspaceSummary[]>([]);
  const [workspaceId, setWorkspaceId] = useState('');
  const [role, setRole] = useState<string>('owner');
  const [label, setLabel] = useState('');
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState('');

  useEffect(() => { mattersInit(); }, [mattersInit]);
  useEffect(() => {
    if (matterId || matters.length === 0) return;
    const preferred = matters.find((m) => m.id === activeMatterId) || matters.find((m) => m.is_personal) || matters[0];
    setMatterId(preferred.id);
  }, [matters, activeMatterId, matterId]);

  const loadList = useCallback(async (forMatter: string) => {
    if (!forMatter) { setWorkspaces([]); return; }
    try {
      const { workspaces: list } = await api.listPatentWorkspaces(forMatter);
      setWorkspaces(list);
    } catch (error) {
      setWorkspaces([]);
      setStatus(`Could not load saved workspaces: ${errorText(error)}`);
    }
  }, []);
  useEffect(() => { void loadList(matterId); }, [matterId, loadList]);

  function applyDetail(detail: PatentWorkspaceDetail) {
    setWorkspaceId(detail.id);
    setRole(detail.role);
    setLabel(detail.title);
    setReviewerNotes(detail.reviewer_notes);
    setDisclosure(detail.disclosure ? { ...emptyDisclosure(), ...detail.disclosure.fields } : emptyDisclosure());
    const loaded = rowsFrom(detail.elements, nextId.current);
    nextId.current += Math.max(loaded.length, 1);
    setRows(loaded.length ? loaded : [emptyRow(nextId.current++)]);
  }

  async function openWorkspace(id: string) {
    setStatus('');
    if (!id) {
      setWorkspaceId(''); setRole('owner'); setLabel('');
      return;
    }
    try {
      const detail = await api.getPatentWorkspace(id);
      applyDetail(detail);
      const version = detail.disclosure ? `disclosure version ${detail.disclosure.version}` : 'no saved disclosure';
      setStatus(`Opened "${detail.title}" (${version}, ${detail.elements.length} claim elements).`);
    } catch (error) {
      setStatus(`Could not open the workspace: ${errorText(error)}`);
    }
  }

  const readOnly = Boolean(workspaceId) && role !== 'owner';

  async function saveToMatter() {
    if (!matterId || readOnly) return;
    setSaving(true);
    setStatus('Saving…');
    try {
      const title = (label.trim() || disclosure.title.trim() || 'Untitled workspace').slice(0, 200);
      let id = workspaceId;
      if (!id) {
        const created = await api.createPatentWorkspace(matterId, title);
        id = created.id;
        setWorkspaceId(id);
        setRole(created.role);
      }
      await api.updatePatentWorkspace(id, { title, reviewer_notes: reviewerNotes });
      const saved = await api.savePatentDisclosure(id, disclosure);
      const elements = await api.replacePatentClaimElements(id, rows);
      setLabel(title);
      setStatus(
        `Saved to matter. Disclosure version ${saved.disclosure.version}${saved.created ? '' : ' (unchanged)'}; ${elements.length} claim elements.`,
      );
      await loadList(matterId);
    } catch (error) {
      setStatus(`Could not save: ${errorText(error)}`);
    } finally {
      setSaving(false);
    }
  }

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
      <aside className={s.notice}>Development preview: fictional information only. Entries stay in this page until you press Save to matter; saving stores them on this Counsel server, encrypted at rest and visible to the matter's members. Unsaved changes are lost when you leave or refresh the page. Nothing here is sent to an AI provider. Exports are unencrypted local files. This is not a patentability determination or a deadline calculator.</aside>
      <section className={s.panel} aria-labelledby="matter-heading">
        <h2 id="matter-heading">Matter workspace</h2>
        <div className={s.grid}>
          <label className={s.field}>Matter
            <select value={matterId} onChange={event => { setMatterId(event.target.value); setWorkspaceId(''); setRole('owner'); setLabel(''); setStatus(''); }}>
              {matters.length === 0 && <option value="">No matters available</option>}
              {matters.map(m => <option key={m.id} value={m.id}>{m.is_personal ? `${m.name} (personal)` : m.name}</option>)}
            </select>
          </label>
          <label className={s.field}>Saved workspace (opening one replaces this page's entries)
            <select value={workspaceId} onChange={event => void openWorkspace(event.target.value)}>
              <option value="">New workspace</option>
              {workspaces.map(w => <option key={w.id} value={w.id}>{w.title}{w.role === 'owner' ? '' : ' (shared with you)'}</option>)}
            </select>
          </label>
          <label className={s.field}>Workspace label (a short name, not invention details)
            <input maxLength={200} value={label} disabled={readOnly} onChange={event => setLabel(event.target.value)} />
          </label>
        </div>
        {readOnly && <p>Only the workspace owner can save changes. You can review and export it.</p>}
        <button type="button" className={s.primary} disabled={!matterId || saving || readOnly} onClick={() => void saveToMatter()}>Save to matter</button>
        <p role="status" aria-live="polite">{status}</p>
      </section>
      <div className={s.grid}>
        <section className={s.panel} aria-labelledby="disclosure-heading">
          <h2 id="disclosure-heading">1. Invention disclosure</h2>
          {DISCLOSURE_FIELDS.map(([key, fieldLabel]) => (
            <label key={key} className={s.field}>
              {fieldLabel}
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
              <label className={s.field}>Reviewer mapping status<select value={row.status} onChange={event => updateRow(row.id, { status: event.target.value as EvidenceStatus })}>{Object.entries(STATUS_LABELS).map(([value, statusLabel]) => <option key={value} value={value}>{statusLabel}</option>)}</select></label>
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
        <Link to="/ip-research">Open official IP research directory (unsaved changes are lost)</Link>
        <ul>{questions.map((question, index) => <li key={index}>{question}</li>)}</ul>
        <label className={s.field}>Practitioner notes<textarea rows={4} maxLength={12000} value={reviewerNotes} onChange={event => setReviewerNotes(event.target.value)} /></label>
        <label className={s.confirm}><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> I confirm this contains fictional data only and understand the export is unencrypted and unverified.</label>
        <button type="button" className={s.primary} disabled={!confirmed} onClick={exportPacket}>Export review draft (JSON)</button>
      </section>
    </section>
  );
}
