/*
 * The site's primary navigation, defined once. Both the desktop/mobile nav and the
 * router map over this list, so adding a page (Epics 15–17) means editing one array.
 * Keep `path` values in sync with the server's RESERVED_WORDS — `dashboard` and
 * `how-it-works` are already reserved so they can never be taken as short codes.
 */

export interface NavigationItem {
  path: string;
  label: string;
  id: string;
}

export const NAVIGATION_ITEMS: NavigationItem[] = [
  { path: "/", label: "Home", id: "nav-item-home" },
  { path: "/dashboard", label: "Dashboard", id: "nav-item-dashboard" },
  { path: "/how-it-works", label: "How It Works", id: "nav-item-how-it-works" },
];
