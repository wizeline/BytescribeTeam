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
        url: 'https://example.com/img1.jpg',
        title: 'Image 1',
        caption: 'Caption 1',
        s3_key: 'img1.jpg'
      }
    }
  ]
};

const mockSetSummary = jest.fn();

const renderComponent = () => {
  return render(
    <ArticleSummaryContext.Provider value={{ summary: mockSummary, setSummary: mockSetSummary }}>
      <HighlightsTable />
    </ArticleSummaryContext.Provider>
  );
};

describe('HighlightsTable', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    global.fetch = jest.fn();
  });

  it('renders configuration and highlights sections', async () => {
    renderComponent();
    
    expect(screen.getByText('CONFIGURATION')).toBeInTheDocument();
    expect(screen.getByText('Highlights')).toBeInTheDocument();
  });

  it('handles model selection change', async () => {
    renderComponent();
    
    const modelSelect = screen.getByLabelText(/AI Model/i);
    fireEvent.change(modelSelect, { target: { value: 'anthropic.claude-3-haiku-20240307-v1:0' } });
    
    expect(modelSelect).toHaveValue('anthropic.claude-3-haiku-20240307-v1:0');
  });

  it('handles temperature slider change', async () => {
    renderComponent();
    
    const slider = screen.getByRole('slider', { name: /Creativity/i });
    fireEvent.change(slider, { target: { value: '0.5' } });
    
    expect(slider).toHaveValue('0.5');
  });

  it('generates highlights successfully', async () => {
    const mockResponse = {
      job_id: '123',
      status: 'completed',
      result: {
        title: 'New Title',
        summary: {
          bullets: [
            { text: 'New highlight 1', image_url: [] }
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

    renderComponent();
    
    const generateButton = screen.getByText('Generate');
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(mockSetSummary).toHaveBeenCalled();
    });
  });

  it('handles generate highlights error', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    const alertSpy = jest.spyOn(window, 'alert').mockImplementation();

    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

    renderComponent();
    
    const generateButton = screen.getByText('Generate');
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith('Error crawling URL: API Error');
    });

    consoleSpy.mockRestore();
    alertSpy.mockRestore();
  });

  it('navigates on form submit', async () => {
    renderComponent();
    
    const continueButton = screen.getByText('Continue');
    fireEvent.click(continueButton);

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('video');
    });
  });

  it('handles image selection in data grid', async () => {
    renderComponent();
    
    const cell = screen.getByRole('cell', { name: /img1.jpg/i });
    fireEvent.doubleClick(cell);

    const newImageUrl = 'https://example.com/img2.jpg';
    fireEvent.change(cell, { target: { value: newImageUrl } });

    expect(mockSetSummary).toHaveBeenCalled();
  });

  it('normalizes image URLs correctly', () => {
    renderComponent();

    // Test s3:// URL normalization
    const s3Url = 's3://my-bucket/image.jpg';
    const cell = screen.getByRole('cell', { name: /img1.jpg/i });
    fireEvent.doubleClick(cell);
    fireEvent.change(cell, { target: { value: s3Url } });

    expect(mockSetSummary).toHaveBeenCalled();
    expect(mockSetSummary.mock.calls[0][0].highlights[1].image.url).toContain('s3.amazonaws.com');
  });
});
