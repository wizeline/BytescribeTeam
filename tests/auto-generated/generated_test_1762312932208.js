import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
        s3_key: 'img1.jpg',
        title: 'Image 1',
        caption: 'Caption 1'
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
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    process.env.NEXT_PUBLIC_CRAWLER_API = 'http://test-api.com';
    process.env.NEXT_PUBLIC_S3_BUCKET = 'https://test-bucket.s3.amazonaws.com';
  });

  it('renders configuration and highlights sections', async () => {
    render(<HighlightsTable />, { wrapper });
    
    await waitFor(() => {
      expect(screen.getByText('CONFIGURATION')).toBeInTheDocument();
      expect(screen.getByText('Highlights')).toBeInTheDocument();
    });
  });

  it('handles generate highlights action', async () => {
    global.fetch = jest.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          job_id: 'test-job',
          status: 'completed',
          result: {
            title: 'Generated Title',
            summary: {
              bullets: [
                { text: 'Generated highlight 1', image_url: [] }
              ]
            }
          }
        })
      })
    );

    render(<HighlightsTable />, { wrapper });
    
    const generateButton = screen.getByText('Generate');
    await userEvent.click(generateButton);

    await waitFor(() => {
      expect(mockSetSummary).toHaveBeenCalled();
    });
  });

  it('handles form submission', async () => {
    render(<HighlightsTable />, { wrapper });
    
    const continueButton = screen.getByText('Continue');
    await userEvent.click(continueButton);

    expect(mockRouter.push).toHaveBeenCalledWith('video');
  });

  it('handles image selection', async () => {
    render(<HighlightsTable />, { wrapper });
    
    const imageCell = screen.getByRole('img');
    await userEvent.click(imageCell);

    await waitFor(() => {
      expect(screen.getByRole('img')).toHaveAttribute('src', 'https://example.com/img1.jpg');
    });
  });

  it('handles error during highlight generation', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    const alertMock = jest.spyOn(window, 'alert').mockImplementation();
    
    global.fetch = jest.fn().mockRejectedValue(new Error('API Error'));

    render(<HighlightsTable />, { wrapper });
    
    const generateButton = screen.getByText('Generate');
    await userEvent.click(generateButton);

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith('Error crawling URL: API Error');
    });

    consoleSpy.mockRestore();
    alertMock.mockRestore();
  });

  it('updates model configuration', async () => {
    render(<HighlightsTable />, { wrapper });
    
    const modelSelect = screen.getByRole('combobox');
    await userEvent.click(modelSelect);
    
    const option = screen.getByText('Anthropic Claude 3 Haiku');
    await userEvent.click(option);

    expect(modelSelect).toHaveValue('anthropic.claude-3-haiku-20240307-v1:0');
  });
});
