import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./client', () => {
  const api = { request: vi.fn(), authFetch: vi.fn(), getToken: vi.fn().mockReturnValue('test-token') };
  return { api, API_BASE_URL: 'http://localhost:8000/api/v1' };
});

import { api } from './client';
import './legalSources';

const a = api as any;

describe('api/legalSources', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    a.request.mockResolvedValue({});
  });

  it('lists sources', async () => {
    await a.listLegalSources();
    expect(a.request).toHaveBeenCalledWith('/legal-sources');
  });

  it('searches with an encoded query and optional source', async () => {
    await a.searchLegalSourceSections('§ 2106.04(a) & more');
    expect(a.request).toHaveBeenCalledWith('/legal-sources/sections?q=%C2%A7+2106.04%28a%29+%26+more');
    await a.searchLegalSourceSections('widget', 'src 1');
    expect(a.request).toHaveBeenLastCalledWith('/legal-sources/sections?q=widget&source_id=src+1');
  });

  it('reads one section by id', async () => {
    await a.getLegalSourceSection('a/b');
    expect(a.request).toHaveBeenCalledWith('/legal-sources/sections/a%2Fb');
  });
});
