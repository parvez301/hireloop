import { useEffect } from 'react';

const DESCRIPTION_SELECTOR = 'meta[name="description"]';

export function useDocumentTitle(title: string, description: string): void {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = title;

    let el = document.querySelector(DESCRIPTION_SELECTOR);
    if (!el) {
      el = document.createElement('meta');
      el.setAttribute('name', 'description');
      document.head.appendChild(el);
    }
    const previousDescription = el.getAttribute('content') ?? '';
    el.setAttribute('content', description);

    return () => {
      document.title = previousTitle;
      el?.setAttribute('content', previousDescription);
    };
  }, [title, description]);
}
