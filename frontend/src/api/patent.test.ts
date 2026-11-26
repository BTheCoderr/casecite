import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./client', () => {
  const api = { request: vi.fn(), authFetch: vi.fn(), getToken: vi.fn().mockReturnValue('test-token') };
  return { api, API_BASE_URL: 'http://localhost:8000/api/v1' };
});

import { api } from './client';
import './patent';

const a = api as any;

describe('api/patent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    a.request.mockResolvedValue({});
  });

  it('lists workspaces for one matter, encoding the id', async () => {
    await a.listPatentWorkspaces('m 1');
    expect(a.request).toHaveBeenCalledWith('/patent-workspaces?matter_id=m%201');
    await a.listPatentWorkspaces();
    expect(a.request).toHaveBeenLastCalledWith('/patent-workspaces');
  });

  it('creates a workspace under a matter', async () => {
    await a.createPatentWorkspace('m1', 'Planter');
    expect(a.request).toHaveBeenCalledWith('/patent-workspaces', {
      method: 'POST',
      body: JSON.stringify({ matter_id: 'm1', title: 'Planter' }),
    });
  });

  it('saves a disclosure version and replaces the claim chart without client-only or verified fields', async () => {
    await a.savePatentDisclosure('pw/1', { title: 'T' });
    expect(a.request).toHaveBeenCalledWith('/patent-workspaces/pw%2F1/disclosures', {
      method: 'POST',
      body: JSON.stringify({ fields: { title: 'T' } }),
    });
    await a.replacePatentClaimElements('pw1', [
      { id: 7, element: 'E', disclosureSupport: 'S', reference: 'R', referencePassage: 'P', status: 'gap', notes: 'N', verified: true },
    ]);
    const [path, options] = a.request.mock.calls[1];
    expect(path).toBe('/patent-workspaces/pw1/claim-elements');
    expect(options.method).toBe('PUT');
    expect(JSON.parse(options.body)).toEqual({
      elements: [{ element: 'E', disclosureSupport: 'S', reference: 'R', referencePassage: 'P', status: 'gap', notes: 'N' }],
    });
  });

  it('updates and deletes by id', async () => {
    await a.updatePatentWorkspace('pw1', { reviewer_notes: 'x' });
    expect(a.request).toHaveBeenCalledWith('/patent-workspaces/pw1', { method: 'PATCH', body: JSON.stringify({ reviewer_notes: 'x' }) });
    await a.deletePatentWorkspace('pw1');
    expect(a.request).toHaveBeenLastCalledWith('/patent-workspaces/pw1', { method: 'DELETE' });
  });
});
