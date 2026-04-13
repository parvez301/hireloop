import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { PipelineFilters } from './PipelineFilters';

describe('PipelineFilters', () => {
  it('calls onMinGradeChange when selection changes', () => {
    const onMinGradeChange = vi.fn();

    render(<PipelineFilters minGrade="" onMinGradeChange={onMinGradeChange} />);

    fireEvent.change(screen.getByLabelText(/Min grade/i), { target: { value: 'B+' } });

    expect(onMinGradeChange).toHaveBeenCalledWith('B+');
  });
});
