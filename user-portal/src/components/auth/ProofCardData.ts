export type ProofCard = {
  id: string;
  quote: string;
  author: string;
  role: string;
  grade?: string;
  score?: number;
};

export const PROOF_CARDS: ProofCard[] = [
  {
    id: 'lena',
    quote:
      "HireLoop told me a role everyone was hyping wasn't a fit. Saved me three weeks of interviews I'd have bombed.",
    author: 'Lena M.',
    role: 'Senior Platform Engineer',
    grade: 'A−',
    score: 87,
  },
  {
    id: 'priya',
    quote:
      'The interview prep reads like a coach who has actually read the JD. I used one of the STAR stories verbatim — offer.',
    author: 'Priya S.',
    role: 'Product Manager, Series-C fintech',
    grade: 'A',
    score: 92,
  },
  {
    id: 'miguel',
    quote:
      "I hate job hunting. This is the only tool that made it feel like I was in charge.",
    author: 'Miguel R.',
    role: 'Staff Backend Engineer',
    grade: 'B+',
    score: 78,
  },
];
