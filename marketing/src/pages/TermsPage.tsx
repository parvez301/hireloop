import termsMd from '../content/terms.md?raw';

import { LegalPage } from '../components/LegalPage';
import { metaDescriptions } from '../content/meta';
import { useDocumentTitle } from '../lib/useDocumentTitle';

export function TermsPage() {
  useDocumentTitle('Terms of Service — HireLoop', metaDescriptions.terms);

  return <LegalPage title="Terms of Service" markdown={termsMd} />;
}
