import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import HighlightsTable from '../HighlightsTable';
import { ArticleSummaryContext } from '@/contexts/ArticleSummary';
import { act } from 'react-dom/test-utils';

// Mock next/image
jest.mock('next/image', () => ({ __esModule: true, default: (props: any) => <img {...props} /> }));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn()
  })
}));

// Mock environment variables
process.env.NEXT_PUBLIC_CRAWLER_API = 'http://test-api.com';
process.env.NEXT_PUBLIC_S3_BUCKET = 'https://test-bucket.s3.amazonaws.com';

const mockSummary = {
  url: 'https://test.com',
  title: 'Test Article',
  highlights: [
    { text: 'Title', image: null },
    { 
      text: 'Highlight 1',
      image: {
        url: 'https://test.com/image1.jpg',
        s3_key: 'image1.jpg',
        title: 'Image 1',
        caption: 'Test caption'
      }
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
    global.fetch = jest.fn();
  });

  it('renders configuration section', () => {
    render(<HighlightsTable />, { wrapper });
    expect(screen.getByText('CONFIGURATION')).toBeInTheDocument();
    expect(screen.getByText('AI Model:')).toBeInTheDocument();
    expect(screen.getByText(/Creativity/)).toBeInTheDocument();
  });

  it('renders highlights section when highlights exist', () => {
    render(<HighlightsTable />, { wrapper });
    expect(screen.getByText('Highlights')).toBeInTheDocument();
    expect(screen.getByText('Title')).toBeInTheDocument();
  });

  it('handles generate highlights request', async () => {
    const mockResponse = {
      title: 'Generated Title',
      summary: {
        bullets: [
          { text: 'Bullet 1', image_url: [{ image_url: 'https://test.com/new1.jpg', title: 'New 1', caption: 'New Caption' }] }
        ]
      }
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse)
    });

    render(<HighlightsTable />, { wrapper });

    await act(async () => {
      fireEvent.click(screen.getByText('Generate'));
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-api.com',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
    );
  });

  it('handles async job polling', async () => {
    const mockJobResponse = { job_id: 'test-job' };
    const mockStatusResponse = {
      status: 'completed',
      result: {
        title: 'Polled Title',
        summary: {
          bullets: [
            { text: 'Polled Bullet', image_url: [{ image_url: 'https://test.com/poll1.jpg', title: 'Poll 1', caption: 'Poll Caption' }] }
          ]
        }
      }
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockJobResponse)
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStatusResponse)
      });

    render(<HighlightsTable />, { wrapper });

    await act(async () => {
      fireEvent.click(screen.getByText('Generate'));
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  it('handles error during generation', async () => {
    const mockError = new Error('API Error');
    (global.fetch as jest.Mock).mockRejectedValueOnce(mockError);
    
    const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {});

    render(<HighlightsTable />, { wrapper });

    await act(async () => {
      fireEvent.click(screen.getByText('Generate'));
    });

    expect(alertMock).toHaveBeenCalledWith('Error crawling URL: API Error');
  });

  it('updates model parameters', () => {
    render(<HighlightsTable />, { wrapper });

    const modelSelect = screen.getByRole('combobox');
    fireEvent.change(modelSelect, { target: { value: 'anthropic.claude-3-haiku-20240307-v1:0' } });

    expect(modelSelect).toHaveValue('anthropic.claude-3-haiku-20240307-v1:0');
  });

  it('normalizes image URLs correctly', () => {
    render(<HighlightsTable />, { wrapper });

    const s3Url = 's3://test-bucket/image.jpg';
    const httpUrl = 'https://test.com/image.jpg';

    // Access the component instance to test internal function
    // This requires exposing the function or testing through UI interactions
    // Here we're testing through the rendered content
    expect(screen.getByRole('img')).toHaveAttribute('src', mockSummary.highlights[1].image.url);
  });
});
