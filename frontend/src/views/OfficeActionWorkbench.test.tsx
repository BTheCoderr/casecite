import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import OfficeActionWorkbench from './OfficeActionWorkbench';

describe('OfficeActionWorkbench', () => {
  it('scans only on request, gates export, and clears review on source edit', () => {
    render(<OfficeActionWorkbench />);
    const input = screen.getByLabelText('Fictional Office Action text');
    fireEvent.change(input, { target: { value: 'Fictional: Claim 1, 35 U.S.C. § 103.' } });
    expect(screen.queryByText(/candidate mentions found/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Scan explicit references' }));
    expect(screen.getByText(/2 candidate mentions found/)).toBeInTheDocument();
    const statute = screen.getByRole('group', { name: /Mention 2/ });
    expect(within(statute).getByRole('link', { name: /MPEP § 2141/ })).toHaveAttribute('href', 'https://www.uspto.gov/web/offices/pac/mpep/s2141.html');
    fireEvent.change(within(statute).getByLabelText('Response questions and evidence gaps'), { target: { value: 'Synthetic review note' } });
    const exportButton = screen.getByRole('button', { name: 'Export Office Action review (JSON)' });
    expect(exportButton).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/I confirm this Office Action/));
    expect(exportButton).toBeEnabled();
    fireEvent.change(input, { target: { value: 'Fictional: Claim 2.' } });
    expect(screen.queryByRole('button', { name: 'Export Office Action review (JSON)' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Scan explicit references' }));
    expect(screen.getByLabelText('Response questions and evidence gaps')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Export Office Action review (JSON)' })).toBeDisabled();
  });
});
