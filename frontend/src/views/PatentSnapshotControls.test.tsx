import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import PatentSnapshotControls from './PatentSnapshotControls';
import { emptyDisclosure } from '../constants/patentStudio';
import { api } from '../api/client';

vi.mock('../api/client', () => ({ api: { request: vi.fn() } }));

describe('PatentSnapshotControls', () => {
  it('requires explicit matter selection and sends only after an explicit confirmed save', async () => {
    const request = vi.mocked(api.request);
    request.mockReset();
    request.mockResolvedValueOnce({ matters: [{ id: 'm1', name: 'Fictional matter', role: 'owner' }] });
    request.mockResolvedValueOnce({ id: 's1', matter_id: 'm1' });
    const worksheet = { fictional_data_only: true as const, disclosure: emptyDisclosure(), claim_mappings: [], reviewer_notes: '' };
    render(<PatentSnapshotControls confirmed worksheet={() => worksheet} onLoad={vi.fn()} />);
    const save = screen.getByRole('button', { name: 'Save fictional snapshot' });
    expect(save).toBeDisabled();
    expect(request).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Load accessible matters' }));
    await screen.findByRole('option', { name: 'Fictional matter' });
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByRole('combobox', { name: 'Storage matter' }), { target: { value: 'm1' } });
    fireEvent.click(save);
    await waitFor(() => expect(request).toHaveBeenCalledWith('/matters/m1/patent-snapshots', { method: 'POST', body: JSON.stringify(worksheet) }));
    await screen.findByText('Fictional snapshot saved. ID: s1');
  });
});
