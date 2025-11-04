import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ArticleSummaryContext } from '@/contexts/ArticleSummary';
import HighlightsTable from '../components/HighlightsTable';
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
        url: 'https://example.com/image1.jpg',
        s3_key: 'image1.jpg',
        title: 'Image 1',
        caption: 'Caption 1'
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

  it('handles generate highlights action', async () => {
    const mockResponse = {
      job_id: '123',
      status: 'completed',
      result: {
        title: 'Generated Title',
        summary: {
          bullets: [
            { text: 'New Highlight 1', image_url: [] },
            { text: 'New Highlight 2', image_url: [] }
          ]
        }
      }
    };

    (global.fetch as jest.Mock)
      .mockImplementationOnce(() => Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ job_id: '123' })
      }))
      .mockImplementationOnce(() => Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      }));

    render(<HighlightsTable />, { wrapper });
    
    const generateButton = screen.getByText('Generate');
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  it('handles form submission', async () => {
    render(<HighlightsTable />, { wrapper });
    
    const continueButton = screen.getByText('Continue');
    fireEvent.click(continueButton);

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('video');
    });
  });

  it('handles model selection change', () => {
    render(<HighlightsTable />, { wrapper });
    
    const modelSelect = screen.getByRole('combobox');
    fireEvent.change(modelSelect, { target: { value: 'anthropic.claude-3-haiku-20240307-v1:0' } });
    
    expect(modelSelect).toHaveValue('anthropic.claude-3-haiku-20240307-v1:0');
  });

  it('handles error during highlights generation', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    const alertSpy = jest.spyOn(window, 'alert').mockImplementation();

    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

    render(<HighlightsTable />, { wrapper });
    
    const generateButton = screen.getByText('Generate');
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith('Error crawling URL: API Error');
    });

    consoleSpy.mockRestore();
    alertSpy.mockRestore();
  });

  it('updates highlight text', () => {
    render(<HighlightsTable />, { wrapper });
    
    const titleInput = screen.getByRole('textbox');
    fireEvent.change(titleInput, { target: { value: 'New Title' } });

    expect(mockSetSummary).toHaveBeenCalled();
  });
});
