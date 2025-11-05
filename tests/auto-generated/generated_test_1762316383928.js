import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import HighlightsTable from '../HighlightsTable';

const mockHighlights = [
  {
    id: '1',
    text: 'Test highlight',
    timestamp: '2023-01-01T00:00:00Z',
    confidence: 0.95,
    category: 'test'
  }
];

describe('HighlightsTable', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the table with highlights', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    expect(screen.getByText('Test highlight')).toBeInTheDocument();
  });

  it('handles empty highlights array', () => {
    render(<HighlightsTable highlights={[]} />);
    expect(screen.getByText('No highlights found')).toBeInTheDocument();
  });

  it('allows sorting of highlights', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    const sortButton = screen.getByText('Sort by confidence');
    fireEvent.click(sortButton);
    // Add assertions for sorted state
  });

  it('handles highlight deletion', () => {
    const onDelete = jest.fn();
    render(<HighlightsTable highlights={mockHighlights} onDelete={onDelete} />);
    const deleteButton = screen.getByRole('button', { name: 'Delete' });
    fireEvent.click(deleteButton);
    expect(onDelete).toHaveBeenCalledWith('1');
  });
});
