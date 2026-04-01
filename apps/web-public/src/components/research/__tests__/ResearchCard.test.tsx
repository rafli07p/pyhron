import { render, screen } from '@testing-library/react';
import { ResearchCard } from '@/components/research/ResearchCard';

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const defaultProps = {
  title: 'Momentum Factor Returns in IDX Small Caps',
  slug: 'momentum-factor-idx-small-caps',
  excerpt: 'An analysis of momentum factor performance across Indonesian small-cap equities over the past decade.',
  category: 'quantitative-research',
  date: '2025-11-15',
  readTime: 12,
  coverImage: '/images/research/momentum.jpg',
};

describe('ResearchCard', () => {
  it('renders title text', () => {
    render(<ResearchCard {...defaultProps} />);
    expect(screen.getByText(defaultProps.title)).toBeInTheDocument();
  });

  it('renders excerpt text', () => {
    render(<ResearchCard {...defaultProps} />);
    expect(screen.getByText(defaultProps.excerpt)).toBeInTheDocument();
  });

  it('renders read time', () => {
    render(<ResearchCard {...defaultProps} />);
    expect(screen.getByText('12 min read')).toBeInTheDocument();
  });

  it('renders formatted date', () => {
    render(<ResearchCard {...defaultProps} />);
    // formatDate('2025-11-15') -> 'Nov 15, 2025'
    expect(screen.getByText('Nov 15, 2025')).toBeInTheDocument();
  });

  it('links to correct research article URL', () => {
    render(<ResearchCard {...defaultProps} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/research/momentum-factor-idx-small-caps');
  });

  it('has hover transform class', () => {
    render(<ResearchCard {...defaultProps} />);
    const link = screen.getByRole('link');
    expect(link.className).toContain('hover:-translate-y-1');
  });
});
