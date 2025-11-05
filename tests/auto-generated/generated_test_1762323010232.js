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

  it('renders the highlights table correctly', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('displays all highlights in the table', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    mockHighlights.forEach(highlight => {
      expect(screen.getByText(highlight.text)).toBeInTheDocument();
    });
  });

  it('handles empty highlights array', () => {
    render(<HighlightsTable highlights={[]} />);
    expect(screen.getByText('No highlights available')).toBeInTheDocument();
  });

  it('sorts highlights when clicking column headers', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    const timestampHeader = screen.getByText('Timestamp');
    fireEvent.click(timestampHeader);
    // Add assertions for sorting
  });
});
