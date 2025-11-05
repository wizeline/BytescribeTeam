import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import HighlightsTable from '../HighlightsTable';
import { ArticleSummaryContext } from '@/contexts/ArticleSummary';
import { useRouter } from 'next/navigation';

jest.mock('next/navigation', () => ({
  useRouter: jest.fn()
}));

jest.mock('next/image', () => ({
  __esModule: true,
  default: (props: any) => {
    return <img {...props} />
  },
}));

const mockRouter = {
  push: jest.fn()
};

const mockSummary = {
  url: 'https://example.com',
  title: 'Test Article',
  highlights: [
    { text: 'Title', image: null },
    { 
      text: 'Highlight 1',
      image: {
        url: 'https://example.com/img1.jpg',
        title: 'Image 1',
        caption: 'Caption 1',
        s3_key: 'img1.jpg'
      }
    },
    {
      text: 'Highlight 2',
      image: null
    }
  ]
};

const mockSetSummary = jest.fn();

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <ArticleSummaryContext.Provider value={{ summary: mockSummary, setSummary: mockSetSummary }}>
    {children}
  </ArticleSummaryContext.Provider>
);

describe('HighlightsTable', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    global.fetch = jest.fn();
  });

  it('renders configuration section', async () => {
    render(<HighlightsTable />, { wrapper });
    
    await waitFor(() => {
      expect(screen.getByText('CONFIGURATION')).toBeInTheDocument();
      expect(screen.getByText('AI Model:')).toBeInTheDocument();
      expect(screen.getByText(/Creativity/)).toBeInTheDocument();
    });
  });

  it('renders highlights table when highlights exist', async () => {
    render(<HighlightsTable />, { wrapper });
    
    await waitFor(() => {
      expect(screen.getByText('Highlights')).toBeInTheDocument();
      expect(screen.getByText('Highlight 1')).toBeInTheDocument();
      expect(screen.getByText('Highlight 2')).toBeInTheDocument();
    });
  });

  it('handles generate highlights request', async () => {
    const mockResponse = {
      ok: true,
      json: () => Promise.resolve({
        job_id: '123',
        status: 'completed',
        result: {
          title: 'New Title',
          summary: {
            bullets: [
              { text: 'New Highlight 1', image_url: [] },
              { text: 'New Highlight 2', image_url: [] }
            ]
          }
        }
      })
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);
    (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);

    process.env.NEXT_PUBLIC_CRAWLER_API = 'http://api.test';

    render(<HighlightsTable />, { wrapper });

    const generateButton = screen.getByText('Generate');
    await act(async () => {
      fireEvent.click(generateButton);
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://api.test',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      );
    });
  });

  it('handles form submission', async () => {
    render(<HighlightsTable />, { wrapper });

    const continueButton = screen.getByText('Continue');
    await act(async () => {
      fireEvent.click(continueButton);
    });

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('video');
    });
  });

  it('handles error during highlights generation', async () => {
    const mockError = new Error('API Error');
    (global.fetch as jest.Mock).mockRejectedValueOnce(mockError);
    
    const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {});
    process.env.NEXT_PUBLIC_CRAWLER_API = 'http://api.test';

    render(<HighlightsTable />, { wrapper });

    const generateButton = screen.getByText('Generate');
    await act(async () => {
      fireEvent.click(generateButton);
    });

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith('Error crawling URL: API Error');
    });

    alertMock.mockRestore();
  });

  it('updates row data when editing highlights', async () => {
    render(<HighlightsTable />, { wrapper });

    await waitFor(() => {
      const cells = screen.getAllByRole('cell');
      expect(cells.length).toBeGreaterThan(0);
    });

    // Note: Full cell editing test would require more complex DataGrid interaction simulation
  });
});
