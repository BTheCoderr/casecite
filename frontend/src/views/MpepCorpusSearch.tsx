import { useState } from 'react';
import { api } from '../api/client';
import { IP_SOURCES } from '../constants/ipSources';
import s from './IpResearchView.module.css';

interface Hit {
  section: string;
  heading: string;
  url: string;
  edition_label: string;
  fetched_at: string;
  sha256: string;
  quote: string;
  start: number;
  end: number;
}
interface AnalysisResult {
  notice: string;
  issues: { question: string; citation: Hit }[];
  rejected: number;
  source_count: number;
}

interface SearchResult {
  indexed_pages: number;
  edition_label: string;
  hits: Hit[];
}

export default function MpepCorpusSearch() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<SearchResult | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);

  async function analyze() {
    if (!confirmed || !query.trim() || busy) return;
    setBusy(true);
    setAnalysis(null);
    setMessage('');
    try {
      const data: AnalysisResult = await api.request('/ip-research/analyze', {
        method: 'POST',
        body: JSON.stringify({ query: query.trim(), fictional_data_only: true }),
      });
      setAnalysis(data);
    } catch {
      setMessage('Local model unavailable or analysis failed. No draft accepted.');
    } finally {
      setBusy(false);
    }
  }

  async function search() {
    if (!query.trim() || busy) return;
    setBusy(true);
    setResult(null);
    setMessage('');
    try {
      const data: SearchResult = await api.request('/ip-research/search', {
        method: 'POST',
        body: JSON.stringify({ query: query.trim() }),
      });
      setResult(data);
    } catch {
      setMessage('Corpus unavailable or search not authorized. Use the official directory below.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={s.notice} aria-labelledby="mpep-corpus-heading">
      <h2 id="mpep-corpus-heading">Search imported MPEP text (preview)</h2>
      <p>Search public patent-law terms only. The query stays on this instance; no model or external search request is made.</p>
      <form onSubmit={event => { event.preventDefault(); void search(); }}>
        <label htmlFor="mpep-corpus-query">Search imported pages</label>
        <input id="mpep-corpus-query" className={s.search} type="search" value={query} maxLength={200} onChange={event => { setQuery(event.target.value); setAnalysis(null); setResult(null); setConfirmed(false); }} disabled={busy} autoComplete="off" />
        <button type="submit" disabled={busy || !query.trim()}>Search text</button>
      </form>
      <label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} disabled={busy} /> Fictional public-law topic only; I understand AI questions require practitioner review.</label>
      <button type="button" disabled={busy || !confirmed || !query.trim()} onClick={analyze}>Draft research questions (local model)</button>
      {analysis && <section aria-label="AI research draft">
        <p>{analysis.notice}</p>
        <p>{analysis.issues.length} source-matched questions; {analysis.rejected} rejected; {analysis.source_count} retrieved excerpts.</p>
        <ul className={s.results}>{analysis.issues.map((issue, index) => {
          const citation = issue.citation;
          const official = IP_SOURCES.find(source => source.id === citation.section && source.url === citation.url);
          return <li key={index} className={s.item}>
            <strong>{issue.question}</strong>
            <p>{citation.quote}</p>
            {official && <a href={official.url} target="_blank" rel="noopener noreferrer">MPEP page {citation.section}</a>}
            <span className={s.meta}>Exact text match · {citation.edition_label} · captured {citation.fetched_at}</span>
            <span className={s.meta}>Requires practitioner review · {citation.sha256}</span>
          </li>;
        })}</ul>
      </section>}
      <p role="status">{busy ? 'Searching…' : message}</p>
      {result && <>
        <p>{result.hits.length} matching excerpts across {result.indexed_pages} indexed pages. Edition label: {result.edition_label}. This is not the entire MPEP or a current-law check.</p>
        <ul className={s.results}>{result.hits.map((hit, index) => {
          const official = IP_SOURCES.find(source => source.kind === 'MPEP' && source.id === hit.section && source.url === hit.url);
          return <li key={hit.sha256 + ':' + hit.start + ':' + index} className={s.item}>
            <strong>MPEP page {hit.section} — {hit.heading}</strong>
            <p>{hit.quote}</p>
            {official && <a href={official.url} target="_blank" rel="noopener noreferrer">Open original USPTO page</a>}
            <span className={s.meta}>Exact indexed excerpt · captured {hit.fetched_at} · text offsets {hit.start}–{hit.end}</span>
            <span className={s.meta}>Text SHA-256: {hit.sha256}</span>
          </li>;
        })}</ul>
      </>}
    </section>
  );
}
