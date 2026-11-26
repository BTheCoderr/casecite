import { useState } from 'react';
import { searchIpSources } from '../constants/ipSources';
import s from './IpResearchView.module.css';

export default function IpResearchView() {
  const [query, setQuery] = useState('');
  const results = searchIpSources(query);
  return (
    <section className={s.page} aria-labelledby="ip-research-heading">
      <h1 id="ip-research-heading">IP Research</h1>
      <p>Find official USPTO patent examination references by section or topic.</p>
      <aside className={s.notice}>Source directory only. MPEP Ninth Edition, Revision 01.2024 (published November 2024) is the reference baseline verified November 24, 2026. Individual sections have their own revision dates. Check subsequent publications and current law before relying on a source.</aside>
      <label htmlFor="ip-source-search">Search reference directory</label>
      <input id="ip-source-search" className={s.search} type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="e.g. 2106, inventorship, obviousness" autoComplete="off" />
      <p className={s.meta}>Search stays in this browser. Opening a source navigates to the USPTO; never enter confidential invention details in external sites.</p>
      <p aria-live="polite">{results.length} reference{results.length === 1 ? '' : 's'}</p>
      {results.length ? <ul className={s.results}>{results.map(source => (
        <li key={source.id} className={s.item}>
          <span className={s.meta}>{source.kind === 'MPEP' ? 'MPEP § ' + source.id : 'Official updates'}</span>
          <a href={source.url} target="_blank" rel="noopener noreferrer">{source.title} (USPTO)</a>
          <span className={s.meta}>{source.keywords}</span>
        </li>
      ))}</ul> : <p>No matching references. Try a broader topic or use the <a href="https://www.uspto.gov/web/offices/pac/mpep/index.html" target="_blank" rel="noopener noreferrer">official MPEP index</a>.</p>}
      <p className={s.meta}>This directory does not search the full MPEP, generate citations or decide patentability. A qualified practitioner must verify applicable law and facts.</p>
    </section>
  );
}
