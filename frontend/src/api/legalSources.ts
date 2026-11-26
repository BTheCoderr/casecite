// Counsel: read the operator-ingested copy of public legal sources (MPEP). Read-only.
import { api } from './client';
import type { LegalSource, LegalSourceSearchResult, LegalSourceSectionDetail } from './types';

Object.assign(api, {
  async listLegalSources(): Promise<{ sources: LegalSource[] }> {
    return api.request('/legal-sources');
  },

  async searchLegalSourceSections(q: string, sourceId?: string | null): Promise<LegalSourceSearchResult> {
    const params = new URLSearchParams({ q });
    if (sourceId) params.set('source_id', sourceId);
    return api.request(`/legal-sources/sections?${params.toString()}`);
  },

  async getLegalSourceSection(sectionId: string): Promise<LegalSourceSectionDetail> {
    return api.request(`/legal-sources/sections/${encodeURIComponent(sectionId)}`);
  },
});
