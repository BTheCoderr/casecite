import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import IpResearchView from './IpResearchView';

describe('IpResearchView', () => {
  it('filters official sources and handles empty results', () => {
    render(<IpResearchView />);
    const search = screen.getByRole('searchbox', { name: 'Search reference directory' });
    fireEvent.change(search, { target: { value: '2164' } });
    expect(screen.getByRole('link', { name: 'Enablement (USPTO)' })).toHaveAttribute('href', 'https://www.uspto.gov/web/offices/pac/mpep/s2164.html');
    expect(screen.queryByRole('link', { name: 'Anticipation (USPTO)' })).toBeNull();
    fireEvent.change(search, { target: { value: 'unmatched invented topic' } });
    expect(screen.getByText(/No matching references/)).toBeTruthy();
  });
});
