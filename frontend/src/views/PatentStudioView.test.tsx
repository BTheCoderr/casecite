import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, it, expect, vi } from 'vitest';

vi.mock('../api', () => ({
  api: {
    listPatentWorkspaces: vi.fn(),
    createPatentWorkspace: vi.fn(),
    getPatentWorkspace: vi.fn(),
    updatePatentWorkspace: vi.fn(),
    savePatentDisclosure: vi.fn(),
    replacePatentClaimElements: vi.fn(),
  },
}));

import { api } from '../api';
import { useMattersStore } from '../stores/mattersStore';
import PatentStudioView from './PatentStudioView';

const a = api as unknown as Record<string, ReturnType<typeof vi.fn>>;

const MATTER = {
  id: 'm-1', name: 'Fictional Widgets LLC', client_name: null, is_personal: false,
  owner_id: 'u-1', role: 'owner', member_count: 2,
};

function detail(overrides: Record<string, unknown> = {}) {
  return {
    id: 'pw-1', matter_id: 'm-1', title: 'Planter', role: 'owner',
    created_at: '2026-11-25T00:00:00', updated_at: null,
    reviewer_notes: '', disclosure: null, disclosure_versions: 0, elements: [],
    ...overrides,
  };
}

function renderView() {
  return render(<MemoryRouter><PatentStudioView /></MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks();
  useMattersStore.setState({ matters: [MATTER] as never, activeMatterId: 'm-1', init: vi.fn() as never });
  a.listPatentWorkspaces.mockResolvedValue({ workspaces: [] });
});

describe('PatentStudioView', () => {
  it('adds/removes elements and requires explicit fictional-data confirmation', async () => {
    renderView();
    await waitFor(() => expect(a.listPatentWorkspaces).toHaveBeenCalledWith('m-1'));
    const exportButton = screen.getByRole('button', { name: 'Export review draft (JSON)' });
    expect(exportButton).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Add claim element' }));
    expect(screen.getByText('Element 2')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Remove element 2' }));
    expect(screen.queryByText('Element 2')).toBeNull();
    fireEvent.click(screen.getByRole('checkbox'));
    expect(exportButton).toBeEnabled();
  });

  it('sends nothing until Save to matter, then creates the workspace and saves both parts', async () => {
    a.createPatentWorkspace.mockResolvedValue(detail());
    a.updatePatentWorkspace.mockResolvedValue(detail());
    a.savePatentDisclosure.mockResolvedValue({ created: true, disclosure: { version: 1 } });
    a.replacePatentClaimElements.mockResolvedValue([{ id: 'e1' }]);
    renderView();
    fireEvent.change(screen.getByLabelText('Working invention title'), { target: { value: 'Fictional planter' } });
    fireEvent.change(screen.getByLabelText('Claim element', { exact: false }), { target: { value: 'A reservoir' } });
    expect(a.createPatentWorkspace).not.toHaveBeenCalled();

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Save to matter' })); });
    expect(a.createPatentWorkspace).toHaveBeenCalledWith('m-1', 'Fictional planter');
    expect(a.savePatentDisclosure.mock.calls[0][0]).toBe('pw-1');
    expect(a.savePatentDisclosure.mock.calls[0][1].title).toBe('Fictional planter');
    const [, sentRows] = a.replacePatentClaimElements.mock.calls[0];
    expect(sentRows[0].element).toBe('A reservoir');
    expect(await screen.findByText(/Saved to matter\. Disclosure version 1; 1 claim elements\./)).toBeInTheDocument();
  });

  it('opens a saved workspace and is read-only for a member', async () => {
    a.listPatentWorkspaces.mockResolvedValue({ workspaces: [{ ...detail(), role: 'member' }] });
    a.getPatentWorkspace.mockResolvedValue(detail({
      role: 'member',
      reviewer_notes: 'Check the seal',
      disclosure: { version: 3, content_sha256: 'x', created_by: 'u-1', created_at: '', fields: { title: 'Fictional planter', problem: 'Dry soil' } },
      elements: [{ id: 'e1', position: 0, element: 'A wick', disclosureSupport: '', reference: '', referencePassage: '', status: 'gap', notes: '', verified: false }],
    }));
    renderView();
    const picker = await screen.findByLabelText(/Saved workspace/);
    await screen.findByRole('option', { name: 'Planter (shared with you)' });
    await act(async () => { fireEvent.change(picker, { target: { value: 'pw-1' } }); });
    expect(screen.getByLabelText('Working invention title')).toHaveValue('Fictional planter');
    expect(screen.getByLabelText('Claim element', { exact: false })).toHaveValue('A wick');
    expect(screen.getByLabelText('Practitioner notes')).toHaveValue('Check the seal');
    expect(screen.getByText(/disclosure version 3, 1 claim elements/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save to matter' })).toBeDisabled();
    expect(screen.getByText(/Only the workspace owner can save changes/)).toBeInTheDocument();
  });

  it('reports a save failure without losing the entries', async () => {
    a.createPatentWorkspace.mockRejectedValue(new Error('Matter not found'));
    renderView();
    fireEvent.change(screen.getByLabelText('Technical problem'), { target: { value: 'Fictional' } });
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Save to matter' })); });
    expect(await screen.findByText('Could not save: Matter not found')).toBeInTheDocument();
    expect(screen.getByLabelText('Technical problem')).toHaveValue('Fictional');
  });
});
