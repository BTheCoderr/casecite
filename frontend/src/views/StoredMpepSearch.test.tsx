import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, it, expect, vi } from 'vitest';

vi.mock('../api', () => ({
  api: { listLegalSources: vi.fn(), searchLegalSourceSections: vi.fn() },
}));

import { api } from '../api';
import StoredMpepSearch from './StoredMpepSearch';

const a = api as unknown as Record<string, ReturnType<typeof vi.fn>>;

// Synthetic fixture values only: section numbers 99xx do not exist in the MPEP.
const SOURCE = {
  id: 'src-1', name: 'MPEP', edition: 'Synthetic Edition', revision: '01.2030', published_on: 'Fixture month',
  source_url: 'https://www.uspto.gov/web/offices/pac/mpep/mpep-9900.html', fetched_at: '2030-01-02T03:04:05', section_count: 3,
};
const HIT = {
  id: 'sec-1', section_id: '9990', title: 'Synthetic Fixture Section', revision_note: 'R-01.2030',
  url: 'https://www.uspto.gov/web/offices/pac/mpep/s9990.html', text_sha256: 'a'.repeat(64),
  fetched_at: '2030-01-02T03:04:05', snippet: 'FIXTURE TEXT ALPHA about a widget…',
};

beforeEach(() => { vi.clearAllMocks(); });

describe('StoredMpepSearch', () => {
  it('explains when nothing has been stored and offers no search', async () => {
    a.listLegalSources.mockResolvedValue({ sources: [] });
    render(<StoredMpepSearch />);
    expect(await screen.findByText(/No MPEP text has been stored on this server yet/)).toBeInTheDocument();
    expect(screen.queryByRole('searchbox', { name: 'Search the stored MPEP copy' })).toBeNull();
  });

  it('says so when the server cannot list sources', async () => {
    a.listLegalSources.mockRejectedValue(new Error('down'));
    render(<StoredMpepSearch />);
    expect(await screen.findByText('Stored MPEP search is unavailable on this server.')).toBeInTheDocument();
  });

  it('searches only on submit and shows provenance with a link to the official page', async () => {
    a.listLegalSources.mockResolvedValue({ sources: [SOURCE] });
    a.searchLegalSourceSections.mockResolvedValue({ source: SOURCE, query: 'widget', results: [HIT] });
    render(<StoredMpepSearch />);
    expect(await screen.findByText(/Synthetic Edition, revision 01.2030 \(Fixture month\), 3 sections, last fetched 2030-01-02/)).toBeInTheDocument();
    const box = screen.getByRole('searchbox', { name: 'Search the stored MPEP copy' });
    const button = screen.getByRole('button', { name: 'Search stored copy' });
    expect(button).toBeDisabled();
    fireEvent.change(box, { target: { value: 'widget' } });
    expect(a.searchLegalSourceSections).not.toHaveBeenCalled();
    await act(async () => { fireEvent.click(button); });
    expect(a.searchLegalSourceSections).toHaveBeenCalledWith('widget');
    expect(screen.getByText('MPEP § 9990 Synthetic Fixture Section')).toBeInTheDocument();
    expect(screen.getByText('Section revision R-01.2030; copied 2030-01-02')).toBeInTheDocument();
    expect(screen.getByText('FIXTURE TEXT ALPHA about a widget…')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Check § 9990 on the official page (USPTO)' })).toHaveAttribute('href', HIT.url);
  });

  it('reports a failed search', async () => {
    a.listLegalSources.mockResolvedValue({ sources: [SOURCE] });
    a.searchLegalSourceSections.mockRejectedValue(new Error('boom'));
    render(<StoredMpepSearch />);
    fireEvent.change(await screen.findByRole('searchbox', { name: 'Search the stored MPEP copy' }), { target: { value: '9990' } });
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Search stored copy' })); });
    expect(screen.getByRole('alert')).toHaveTextContent('could not be searched');
  });
});
