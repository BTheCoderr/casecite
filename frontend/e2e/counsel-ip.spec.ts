import { test, expect } from '@playwright/test';
import { installApiMocks, loginAs } from './helpers/auth';

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
});
