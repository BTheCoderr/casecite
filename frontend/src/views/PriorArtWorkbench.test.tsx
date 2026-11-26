import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import PriorArtWorkbench from './PriorArtWorkbench';

describe('PriorArtWorkbench', () => {
  it('plans, records and gates fictional notes without changing external URLs', () => {
    render(<PriorArtWorkbench />);
    const exportButton = screen.getByRole('button', { name: 'Export prior art notes (JSON)' });
    expect(exportButton).toBeDisabled();
    fireEvent.change(screen.getByLabel('Technical feature'), { target: { value: 'fictional valve' } });
    expect(screen.getAllByText('"fictional valve"')).toHaveLength(2);
    expect(screen.getByRole('link', { name: 'USPTO Patent Public Search' })).toHaveAttribute('href', 'https://www.uspto.gov/patents/search/patent-public-search');
    fireEvent.click(screen.getByRole('button', { name: 'Add candidate reference' }));
    fireEvent.change(screen.getByLabel('Reference identifier'), { target: { value: 'Fictional A' } });
    expect(screen.getByText('Candidate 1 (unverified)')).toBeInTheDocument();
    fireEvent.click(screen.getByLabel(/I confirm these prior art notes/));
    expect(exportButton).toBeEnabled();
    fireEvent.change(screen.getByLabel('Reference identifier'), { target: { value: 'Fictional B' } });
    expect(exportButton).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Remove candidate 1' }));
    expect(screen.queryByText('Candidate 1 (unverified)')).toBeNull();
  });
});
