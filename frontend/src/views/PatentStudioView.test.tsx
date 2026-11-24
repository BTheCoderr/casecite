import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import PatentStudioView from './PatentStudioView';

describe('PatentStudioView', () => {
  it('adds/removes elements and requires explicit fictional-data confirmation', () => {
    render(<MemoryRouter><PatentStudioView /></MemoryRouter>);
    const exportButton = screen.getByRole('button', { name: 'Export review draft (JSON)' });
    expect(exportButton).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Add claim element' }));
    expect(screen.getByText('Element 2')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Remove element 2' }));
    expect(screen.queryByText('Element 2')).toBeNull();
    fireEvent.click(screen.getByRole('checkbox'));
    expect(exportButton).toBeEnabled();
  });
});
