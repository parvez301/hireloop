import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FaqItem } from '../components/FaqItem';

describe('FAQ accordion', () => {
  it('toggles details open when summary is clicked', () => {
    render(<FaqItem question="Test question?" answer="Test answer." />);
    const details = screen.getByText('Test question?').closest('details');
    expect(details).not.toBeNull();
    expect(details).toHaveProperty('open', false);
    fireEvent.click(screen.getByText('Test question?'));
    expect(details).toHaveProperty('open', true);
  });
});
