// Counsel: Patent Studio persistence. Matter-scoped; the server encrypts the text at rest.
import { api, API_BASE_URL } from './client';
import type {
  PatentClaimElement,
  PatentClaimElementInput,
  PatentDisclosure,
  PatentDisclosureFields,
  PatentDisclosureVersion,
  PatentWorkspaceDetail,
  PatentWorkspaceSummary,
} from './types';

const wsPath = (id: string, suffix = '') => `/patent-workspaces/${encodeURIComponent(id)}${suffix}`;

Object.assign(api, {
  async exportPatentReport(workspaceId: string, format: 'pdf' | 'docx'): Promise<Blob> {
    const response = await api.authFetch(API_BASE_URL + wsPath(workspaceId, '/report'), {
      method: 'POST', body: JSON.stringify({ format, fictional_data_only: true }), cache: 'no-store',
    });
    if (!response.ok) throw new Error('Saved report export unavailable. Check preview access and format.');
    const expected = format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    if (!response.headers.get('content-type')?.startsWith(expected)) throw new Error('Unexpected report format');
    return response.blob();
  },
  async listPatentWorkspaces(matterId?: string | null): Promise<{ workspaces: PatentWorkspaceSummary[] }> {
    const q = matterId ? `?matter_id=${encodeURIComponent(matterId)}` : '';
    return api.request(`/patent-workspaces${q}`);
  },

  async createPatentWorkspace(matterId: string, title: string): Promise<PatentWorkspaceDetail> {
    return api.request('/patent-workspaces', {
      method: 'POST',
      body: JSON.stringify({ matter_id: matterId, title }),
    });
  },

  async getPatentWorkspace(workspaceId: string): Promise<PatentWorkspaceDetail> {
    return api.request(wsPath(workspaceId));
  },

  async updatePatentWorkspace(
    workspaceId: string,
    changes: { title?: string; reviewer_notes?: string },
  ): Promise<PatentWorkspaceDetail> {
    return api.request(wsPath(workspaceId), { method: 'PATCH', body: JSON.stringify(changes) });
  },

  async deletePatentWorkspace(workspaceId: string): Promise<{ status: string; id: string }> {
    return api.request(wsPath(workspaceId), { method: 'DELETE' });
  },

  async savePatentDisclosure(
    workspaceId: string,
    fields: PatentDisclosureFields,
  ): Promise<{ created: boolean; disclosure: PatentDisclosure }> {
    return api.request(wsPath(workspaceId, '/disclosures'), { method: 'POST', body: JSON.stringify({ fields }) });
  },

  async listPatentDisclosureVersions(workspaceId: string): Promise<{ versions: PatentDisclosureVersion[] }> {
    return api.request(wsPath(workspaceId, '/disclosures'));
  },

  async replacePatentClaimElements(
    workspaceId: string,
    elements: PatentClaimElementInput[],
  ): Promise<PatentClaimElement[]> {
    // Only the editable fields are sent: `verified` is server-side only.
    const body = elements.map(({ element, disclosureSupport, reference, referencePassage, status, notes }) => ({
      element, disclosureSupport, reference, referencePassage, status, notes,
    }));
    return api.request(wsPath(workspaceId, '/claim-elements'), { method: 'PUT', body: JSON.stringify({ elements: body }) });
  },
});
