import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ScanResultsCard } from './ScanResultsCard';

describe('ScanResultsCard', () => {
  it('lists top jobs and scan summary', () => {
    render(
      <ScanResultsCard
        data={{
          scan_run_id: 'sr-1',
          scan_name: 'Weekly',
          scanned_count: 10,
          new_count: 4,
          top_jobs: [
            {
              job_id: 'j1',
              title: 'Engineer',
              company: 'Acme',
              location: 'Remote',
              salary_range: null,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText(/Scan results — Weekly/)).toBeInTheDocument();
    expect(screen.getByText('10 jobs scanned · 4 new')).toBeInTheDocument();
    expect(screen.getByText('Engineer')).toBeInTheDocument();
    expect(screen.getByText(/@ Acme/)).toBeInTheDocument();
  });
});
