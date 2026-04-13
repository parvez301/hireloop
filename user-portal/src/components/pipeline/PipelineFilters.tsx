interface Props {
  minGrade: string;
  onMinGradeChange: (grade: string) => void;
}

const GRADES = ['', 'B-', 'B', 'B+', 'A-', 'A'];

export function PipelineFilters({ minGrade, onMinGradeChange }: Props) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <label htmlFor="pipeline-min-grade">
        Min grade:{' '}
        <select
          id="pipeline-min-grade"
          value={minGrade}
          onChange={(e) => onMinGradeChange(e.target.value)}
          className="rounded border border-[#e3e2e0] px-2 py-1"
        >
          {GRADES.map((g) => (
            <option key={g} value={g}>
              {g || 'any'}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
