import { useState } from 'react';
import { api } from '../api/client';
import type { Matter } from '../api/types';
import type { ClaimRow, Disclosure } from '../constants/patentStudio';
import s from './PatentStudioView.module.css';

export interface Worksheet {
  fictional_data_only: true;
  disclosure: Disclosure;
  claim_mappings: Omit<ClaimRow, 'id'>[];
  reviewer_notes: string;
}

interface Snapshot {
  id: string;
  matter_id: string;
  worksheet: Worksheet;
}

interface Props {
  confirmed: boolean;
  worksheet: () => Worksheet;
  onLoad: (worksheet: Worksheet) => void;
}

export default function PatentSnapshotControls({ confirmed, worksheet, onLoad }: Props) {
  const [matters, setMatters] = useState<Matter[]>([]);
  const [selected, setSelected] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const matter = matters.find(item => item.id === selected);
  const canSave = matter?.role === 'owner' && !matter.legal_hold && matter.retention_days == null;

  async function refreshMatters() {
    setBusy(true);
    setMessage('');
    try {
      const result: { matters: Matter[] } = await api.request('/matters');
      setMatters(result.matters);
      setSelected('');
      setMessage(result.matters.length ? 'Choose a matter explicitly.' : 'No accessible matters.');
    } catch {
      setMatters([]);
      setSelected('');
      setMessage('Could not load matters.');
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!selected || !confirmed || !canSave || busy) return;
    setBusy(true);
    setMessage('');
    try {
      const result: Snapshot = await api.request('/matters/' + encodeURIComponent(selected) + '/patent-snapshots', {
        method: 'POST',
        body: JSON.stringify(worksheet()),
      });
      if (result.matter_id !== selected) throw new Error('Unexpected matter');
      setMessage('Fictional snapshot saved. ID: ' + result.id);
    } catch {
      setMessage('Save not confirmed. Check preview settings and matter access before retrying.');
    } finally {
      setBusy(false);
    }
  }

  async function load() {
    if (!selected || !confirmed || busy) return;
    if (!window.confirm('Replace the current worksheet with the latest saved fictional snapshot?')) return;
    setBusy(true);
    setMessage('');
    try {
      const result: Snapshot | null = await api.request('/matters/' + encodeURIComponent(selected) + '/patent-snapshots/latest');
      if (result === null) {
        setMessage('No saved snapshot in this matter.');
      } else {
        if (result.matter_id !== selected || result.worksheet.fictional_data_only !== true) throw new Error('Unexpected snapshot');
        onLoad(result.worksheet);
        setMessage('Loaded snapshot ' + result.id);
      }
    } catch {
      setMessage('Could not load the snapshot. The current worksheet was not replaced.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={s.panel} aria-labelledby="patent-save-heading">
      <h2 id="patent-save-heading">4. Save or reopen a fictional worksheet</h2>
      <p>Development storage preview. Saving sends the worksheet to the selected matter on this server. Choose a fictional test matter only. Each save creates a new snapshot; this panel reopens the latest snapshot.</p>
      <button type="button" className={s.secondary} disabled={busy} onClick={refreshMatters}>Load accessible matters</button>
      <label className={s.field}>Storage matter
        <select value={selected} disabled={busy} onChange={event => { setSelected(event.target.value); setMessage(''); }}>
          <option value="">Choose a matter</option>
          {matters.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </label>
      {matter && !canSave && <p>Saving requires matter ownership and a matter without hold or retention settings.</p>}
      <button type="button" className={s.primary} disabled={busy || !confirmed || !canSave} onClick={save}>Save fictional snapshot</button>{' '}
      <button type="button" className={s.secondary} disabled={busy || !confirmed || !selected} onClick={load}>Reopen latest snapshot</button>
      <p role="status">{busy ? 'Working…' : message}</p>
    </section>
  );
}
