// Counsel: search the MPEP text an operator stored on this server (scripts/ingest_mpep.py).
// Read-only; every excerpt shows where and when it was copied from.
import { useEffect, useState } from 'react';
import { api } from '../api';
import type { LegalSource, LegalSourceSearchResult } from '../api/types';
import s from './IpResearchView.module.css';

const day = (iso: string) => iso.slice(0, 10);

export default function StoredMpepSearch() {
  const [sources, setSources] = useState<LegalSource[] | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<LegalSourceSearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    api.listLegalSources()
      .then(({ sources: list }) => { if (live) setSources(list); })
      .catch(() => { if (live) { setSources([]); setUnavailable(true); } });
    return () => { live = false; };
  }, []);

  async function search(event: React.FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (q.length < 2) return;
    setSearching(true);
    setError('');
    try {
      setResult(await api.searchLegalSourceSections(q));
    } catch {
      setResult(null);
      setError('The stored MPEP copy could not be searched. Try again, or use the official MPEP index.');
    } finally {
      setSearching(false);
    }
  }

  const latest = sources && sources.length ? sources[0] : null;

  return (
    <section aria-labelledby="stored-mpep-heading">
      <h2 id="stored-mpep-heading">Stored MPEP text</h2>
      {sources === null && <p className={s.meta}>Checking for stored MPEP text…</p>}
      {sources !== null && unavailable && <p>Stored MPEP search is unavailable on this server.</p>}
      {sources !== null && !unavailable && !latest && (
        <p>No MPEP text has been stored on this server yet. An operator can load official USPTO pages with <code>scripts/ingest_mpep.py</code>.</p>
      )}
      {latest && (
        <>
          <p className={s.meta}>
            Stored copy: {latest.name} {latest.edition}, revision {latest.revision}
            {latest.published_on ? ` (${latest.published_on})` : ''}, {latest.section_count} sections, last fetched {day(latest.fetched_at)}.
            Excerpts may be out of date. Confirm each one on the official USPTO page before relying on it.
          </p>
          <form onSubmit={event => void search(event)}>
            <label htmlFor="stored-mpep-search">Search the stored MPEP copy</label>
            <input id="stored-mpep-search" className={s.search} type="search" value={query} maxLength={200} onChange={event => setQuery(event.target.value)} placeholder="e.g. 2106.04, judicial exception" autoComplete="off" />
            <p className={s.meta}>This search goes to this Counsel server only. Search for legal concepts, not confidential invention details.</p>
            <button type="submit" disabled={searching || query.trim().length < 2}>Search stored copy</button>
          </form>
        </>
      )}
      {error && <p role="alert">{error}</p>}
      {result && (
        <>
          <p aria-live="polite">{result.results.length} stored section{result.results.length === 1 ? '' : 's'}</p>
          <ul className={s.results}>
            {result.results.map(hit => (
              <li key={hit.id} className={s.item}>
                <strong>MPEP § {hit.section_id} {hit.title}</strong>
                <span className={s.meta}>Section revision {hit.revision_note}; copied {day(hit.fetched_at)}</span>
                <blockquote>{hit.snippet}</blockquote>
                <a href={hit.url} target="_blank" rel="noopener noreferrer">Check § {hit.section_id} on the official page (USPTO)</a>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
