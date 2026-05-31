import PagePlaceholder from "../../components/PagePlaceholder/PagePlaceholder";

/**
 * The How It Works / educational narrative page. The architecture annotations, tech
 * badges, Educational Mode toggle, and live metrics are built in Epic 17; this scaffold
 * renders the routed placeholder.
 */
export default function HowItWorksPage() {
  return (
    <PagePlaceholder
      pageId="how-it-works-page"
      titleId="how-it-works-page-title"
      bodyId="how-it-works-page-body"
      title="How It Works"
    >
      The architecture walkthrough, tech badges, and live metrics arrive in a later release.
    </PagePlaceholder>
  );
}
