
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import HighlightsTable from '../HighlightsTable';

describe('HighlightsTable', () => {
  const mockHighlights = [
    {
      id: '1',
      text: 'Test highlight',
      timestamp: '2023-01-01',
      confidence: 0.9
    }
  ];

  it('renders without crashing', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('displays highlights data correctly', () => {
    render(<HighlightsTable highlights={mockHighlights} />);
    expect(screen.getByText('Test highlight')).toBeInTheDocument();
    expect(screen.getByText('2023-01-01')).toBeInTheDocument();
  });

  it('handles empty highlights array', () => {
    render(<HighlightsTable highlights={[]} />);
    expect(screen.getByText('No highlights available')).toBeInTheDocument();
  });
});