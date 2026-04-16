import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Hero } from '../components/Hero';

describe('Hero', () => {
  it('secondary CTA points to how-it-works anchor', () => {
    render(<Hero />);
    const link = screen.getByRole('link', { name: /How it works/i });
    expect(link).toHaveAttribute('href', '#how-it-works');
  });
});
