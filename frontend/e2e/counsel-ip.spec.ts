import { test, expect } from '@playwright/test';
import { fulfillJson, installApiMocks, loginAs } from './helpers/auth';
import type { MockOverride } from './helpers/auth';

// Counsel additions: IP Research directory and Patent Analysis Studio, in a
// real browser against the mocked API. Fictional data only.

test.describe('Counsel IP routes', () => {
  test('both routes require sign-in', async ({ page }) => {
    await installApiMocks(page);
    for (const path of ['/ip-research', '/patent-studio']) {
      await page.goto(path);
      await expect(page.getByRole('heading', { name: 'Welcome to SmartProBono Counsel' })).toBeVisible();
      await expect(page.getByRole('heading', { name: /IP Research|Patent Analysis Studio/ })).toHaveCount(0);
    }
  });

  test('sidebar reaches the new modes and Knowledge Base at the default viewport', async ({ page }) => {
    // Regression: the upload drop zone overlapped the last nav item once the
    // two Counsel modes were added (DocumentPanel safe alignment).
    await loginAs(page, '/research');
    const sidebar = page.locator('aside[data-layout="left-sidebar"]');
    await sidebar.getByRole('button', { name: /IP Research/ }).click();
    await expect(page).toHaveURL(/\/ip-research$/);
    await sidebar.getByRole('button', { name: /Patent Studio/ }).click();
    await expect(page).toHaveURL(/\/patent-studio$/);
    await sidebar.getByRole('button', { name: /Knowledge Base/ }).click();
    await expect(page).toHaveURL(/\/documents$/);
  });

  test('IP Research filters the official USPTO directory locally', async ({ page }) => {
    const state = await loginAs(page, '/ip-research');
    await expect(page.getByRole('heading', { name: 'IP Research' })).toBeVisible();
    const before = state.calls.length;
    const search = page.getByLabel('Search reference directory');
    await search.fill('2106');
    await expect(page.getByText('1 reference', { exact: true })).toBeVisible();
    const link = page.getByRole('link', { name: /Patent subject matter eligibility \(USPTO\)/ });
    await expect(link).toHaveAttribute('href', 'https://www.uspto.gov/web/offices/pac/mpep/s2106.html');
    await expect(link).toHaveAttribute('rel', /noreferrer/);
    await search.fill('unmatched fictional topic');
    await expect(page.getByText('No matching references.')).toBeVisible();
    // Search never reaches the API.
    expect(state.calls.slice(before).filter((c) => !c.startsWith('GET '))).toEqual([]);
  });

  test('Patent Studio export is gated and contains only the entered fictional data', async ({ page }) => {
    const state = await loginAs(page, '/patent-studio');
    await expect(page.getByRole('heading', { name: 'Patent Analysis Studio' })).toBeVisible();
    const before = state.calls.length;

    await page.getByLabel('Working invention title').fill('Fictional self-cleaning valve');
    await page.getByLabel('Technical problem').fill('Fictional: valves clog in muddy water.');
    await page.getByLabel('Claim element').first().fill('A valve body with a rotating scraper');
    await page.getByLabel('Candidate prior art reference').first().fill('Fictional Ref A');
    await page.getByLabel('Pinpoint passage or figure').first().fill('Fig. 2');
    await page.getByLabel('Reviewer mapping status').first().selectOption('candidate');

    const exportButton = page.getByRole('button', { name: 'Export review draft (JSON)' });
    await expect(exportButton).toBeDisabled();
    await page.getByLabel(/I confirm this contains fictional data only/).check();
    await expect(exportButton).toBeEnabled();

    const downloadPromise = page.waitForEvent('download');
    await exportButton.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('counsel-fictional-patent-review.json');
    const path = await download.path();
    const fs = await import('node:fs/promises');
    const packet = JSON.parse(await fs.readFile(path!, 'utf8'));
    expect(packet.disclosure.title).toBe('Fictional self-cleaning valve');
    expect(packet.claimMappings[0]).toMatchObject({ element: 'A valve body with a rotating scraper', reference: 'Fictional Ref A', status: 'candidate' });
    expect(packet.classification).toContain('unverified');
    expect(packet.openQuestions.some((q: string) => q.includes('Practitioner must verify'))).toBe(true);
    // The studio itself sends nothing to the API.
    expect(state.calls.slice(before).filter((c) => !c.startsWith('GET '))).toEqual([]);
  });

  test('Patent Studio saves to the selected matter only when asked, and reopens the saved workspace', async ({ page }) => {
    const matter = { id: 'm-fict', name: 'Fictional Valves Inc.', client_name: null, is_personal: false, owner_id: 'test-user', role: 'owner', member_count: 1 };
    const bodies: Record<string, unknown>[] = [];
    let saved: Record<string, unknown> | null = null;
    const now = new Date().toISOString();
    const summary = { id: 'pw-fict', matter_id: matter.id, title: '', role: 'owner', created_at: now, updated_at: now };
    const reply = async (route: Parameters<MockOverride>[0], status: number, payload: unknown) => {
      await fulfillJson(route, status, payload);
      return true;
    };
    const override: MockOverride = async (route, url, method) => {
      const path = url.pathname.replace(/^.*\/api\/v1/, '');
      if (path === '/matters' && method === 'GET') return reply(route, 200, { matters: [matter] });
      if (!path.startsWith('/patent-workspaces')) return false;
      const body = route.request().postData();
      if (body) bodies.push({ method, path, ...JSON.parse(body) });
      if (path === '/patent-workspaces' && method === 'GET') {
        return reply(route, 200, { workspaces: saved ? [summary] : [] });
      }
      if (path === '/patent-workspaces' && method === 'POST') {
        summary.title = JSON.parse(body!).title;
        return reply(route, 201, { ...summary, reviewer_notes: '', disclosure: null, disclosure_versions: 0, elements: [] });
      }
      if (path === '/patent-workspaces/pw-fict' && method === 'PATCH') return reply(route, 200, { ...summary });
      if (path === '/patent-workspaces/pw-fict/disclosures' && method === 'POST') {
        saved = { ...(saved ?? {}), fields: JSON.parse(body!).fields };
        return reply(route, 200, { created: true, disclosure: { version: 1, content_sha256: 'f'.repeat(64), created_by: 'test-user', created_at: now, fields: saved.fields } });
      }
      if (path === '/patent-workspaces/pw-fict/claim-elements' && method === 'PUT') {
        const elements = (JSON.parse(body!).elements as Record<string, unknown>[]).map((e, i) => ({ ...e, id: `e${i}`, position: i, verified: false }));
        saved = { ...(saved ?? {}), elements };
        return reply(route, 200, elements);
      }
      if (path === '/patent-workspaces/pw-fict' && method === 'GET') {
        return reply(route, 200, {
          ...summary, reviewer_notes: '', disclosure_versions: 1, elements: saved?.elements ?? [],
          disclosure: { version: 1, content_sha256: 'f'.repeat(64), created_by: 'test-user', created_at: now, fields: saved?.fields },
        });
      }
      return false;
    };
    const state = await loginAs(page, '/patent-studio', { overrides: [override] });
    const panel = page.getByRole('region', { name: 'Matter workspace' });
    await expect(panel.getByRole('combobox').first()).toHaveValue(matter.id);
    const before = state.calls.length;
    await page.getByLabel('Working invention title').fill('Fictional self-cleaning valve');
    await page.getByLabel('Claim element').first().fill('A valve body with a rotating scraper');
    await page.getByLabel('Reviewer mapping status').first().selectOption('gap');
    // Typing sends nothing.
    expect(state.calls.slice(before).filter((c) => !c.startsWith('GET ') && !c.startsWith('OPTIONS '))).toEqual([]);

    await page.getByRole('button', { name: 'Save to matter' }).click();
    await expect(page.getByText('Saved to matter. Disclosure version 1; 1 claim elements.')).toBeVisible();
    expect(bodies.map((b) => `${b.method} ${b.path}`)).toEqual([
      'POST /patent-workspaces',
      'PATCH /patent-workspaces/pw-fict',
      'POST /patent-workspaces/pw-fict/disclosures',
      'PUT /patent-workspaces/pw-fict/claim-elements',
    ]);
    expect(bodies[0]).toMatchObject({ matter_id: matter.id, title: 'Fictional self-cleaning valve' });
    const chart = bodies[3] as { elements: Record<string, unknown>[] };
    expect(chart.elements[0]).toMatchObject({ element: 'A valve body with a rotating scraper', status: 'gap' });
    expect(chart.elements[0]).not.toHaveProperty('verified');
    expect(chart.elements[0]).not.toHaveProperty('id');

    // A fresh visit starts empty; opening the saved workspace restores it.
    await page.reload();
    await expect(page.getByLabel('Working invention title')).toHaveValue('');
    await page.getByRole('region', { name: 'Matter workspace' }).getByLabel(/Saved workspace/).selectOption('pw-fict');
    await expect(page.getByLabel('Working invention title')).toHaveValue('Fictional self-cleaning valve');
    await expect(page.getByLabel('Claim element').first()).toHaveValue('A valve body with a rotating scraper');
  });

  test('IP Research searches the stored MPEP copy only on submit and links each excerpt to the official page', async ({ page }) => {
    // Synthetic fixture values: section 9990 does not exist in the MPEP.
    const source = { id: 'src-1', name: 'MPEP', edition: 'Synthetic Edition', revision: '01.2030', published_on: null, source_url: 'https://www.uspto.gov/web/offices/pac/mpep/mpep-9900.html', fetched_at: '2030-01-02T03:04:05', section_count: 1 };
    const hit = { id: 'sec-1', section_id: '9990', title: 'Synthetic Fixture Section', revision_note: 'R-01.2030', url: 'https://www.uspto.gov/web/offices/pac/mpep/s9990.html', text_sha256: 'a'.repeat(64), fetched_at: '2030-01-02T03:04:05', snippet: 'FIXTURE TEXT ALPHA about a widget' };
    const queries: string[] = [];
    const override: MockOverride = async (route, url, method) => {
      const path = url.pathname.replace(/^.*\/api\/v1/, '');
      if (method !== 'GET' || !path.startsWith('/legal-sources')) return false;
      if (path === '/legal-sources') { await fulfillJson(route, 200, { sources: [source] }); return true; }
      if (path === '/legal-sources/sections') {
        queries.push(url.searchParams.get('q') ?? '');
        await fulfillJson(route, 200, { source, query: url.searchParams.get('q'), results: [hit] });
        return true;
      }
      return false;
    };
    const state = await loginAs(page, '/ip-research', { overrides: [override] });
    await expect(page.getByText(/Stored copy: MPEP Synthetic Edition, revision 01\.2030, 1 sections, last fetched 2030-01-02/)).toBeVisible();
    const before = state.calls.length;
    await page.getByRole('searchbox', { name: 'Search the stored MPEP copy' }).fill('widget');
    expect(queries).toEqual([]);
    await page.getByRole('button', { name: 'Search stored copy' }).click();
    await expect(page.getByText('MPEP § 9990 Synthetic Fixture Section')).toBeVisible();
    expect(queries).toEqual(['widget']);
    await expect(page.getByRole('link', { name: 'Check § 9990 on the official page (USPTO)' })).toHaveAttribute('href', hit.url);
    expect(state.calls.slice(before).filter((c) => !c.startsWith('GET ') && !c.startsWith('OPTIONS '))).toEqual([]);
  });
});
