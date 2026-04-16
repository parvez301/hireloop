import privacyMd from '../content/privacy.md?raw';

import { LegalPage } from '../components/LegalPage';
import { metaDescriptions } from '../content/meta';
import { useDocumentTitle } from '../lib/useDocumentTitle';

export function PrivacyPage() {
  useDocumentTitle('Privacy Policy — HireLoop', metaDescriptions.privacy);

  return <LegalPage title="Privacy Policy" markdown={privacyMd} />;
}
