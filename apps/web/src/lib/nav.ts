import {
  BotIcon,
  DatabaseIcon,
  FileTextIcon,
  FlaskConicalIcon,
  GitCompareIcon,
  LayoutDashboardIcon,
  ScrollTextIcon,
  SettingsIcon,
  WaypointsIcon,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV: NavGroup[] = [
  {
    label: "Monitor",
    items: [
      { href: "/", label: "Overview", icon: LayoutDashboardIcon },
      { href: "/agents", label: "Agents", icon: BotIcon },
      { href: "/datasets", label: "Datasets", icon: DatabaseIcon },
      { href: "/evaluations", label: "Evaluations", icon: FlaskConicalIcon },
      { href: "/traces", label: "Execution traces", icon: WaypointsIcon },
      { href: "/benchmarks", label: "Benchmarks", icon: GitCompareIcon },
    ],
  },
  {
    label: "Configure",
    items: [{ href: "/reports", label: "Reports", icon: FileTextIcon }],
  },
  {
    label: "Organization",
    items: [
      { href: "/audit", label: "Audit log", icon: ScrollTextIcon },
      { href: "/settings", label: "Settings", icon: SettingsIcon },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV.flatMap((g) => g.items);

/** The nav item a path belongs to: exact match for "/", prefix match otherwise. */
export function activeNavItem(pathname: string): NavItem | undefined {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/") return NAV_ITEMS.find((i) => i.href === "/");
  return NAV_ITEMS.filter((i) => i.href !== "/" && (path === i.href || path.startsWith(`${i.href}/`))).sort(
    (a, b) => b.href.length - a.href.length,
  )[0];
}

export function isActive(item: NavItem, pathname: string): boolean {
  return activeNavItem(pathname)?.href === item.href;
}
