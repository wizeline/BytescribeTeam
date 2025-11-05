import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import HighlightsTable from '../HighlightsTable';

describe('HighlightsTable', () => {
  const mockHighlights = [
    { id: 1, text: 'Test highlight 1', timestamp: '2023-01-01' },
    { id: 2, text: 'Test highlight 2', timestamp: '2023-01-02' }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('displays correct number of highlights', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    const rows = screen.getAllByRole('row');
    expect(rows.length).toBe(mockHighlights.length + 1); // +1 for header row
  });

  it('displays highlight text correctly', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    expect(screen.getByText('Test highlight 1')).toBeInTheDocument();
    expect(screen.getByText('Test highlight 2')).toBeInTheDocument();
  });

  it('handles empty highlights array', () => {
    render(<HighlightsTable highlights={[]} />);
    expect(screen.getByText('No highlights available')).toBeInTheDocument();
  });
});
