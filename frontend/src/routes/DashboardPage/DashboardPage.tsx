import PagePlaceholder from "../../components/PagePlaceholder/PagePlaceholder";

/**
 * The public dashboard. The paginated link list and per-link analytics views are built
 * in Epic 16; this scaffold renders the routed placeholder so the shell is navigable.
 */
export default function DashboardPage() {
  return (
    <PagePlaceholder
      pageId="dashboard-page"
      titleId="dashboard-page-title"
      bodyId="dashboard-page-body"
      title="Dashboard"
    >
      The link list and per-link analytics arrive in a later release.
    </PagePlaceholder>
  );
}
