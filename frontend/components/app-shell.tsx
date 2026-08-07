"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { ComponentType, ReactNode } from "react";

import { useAuth } from "@/lib/auth";
import type { CurrentUser } from "@/lib/auth";

import {
  ActivityIcon,
  ApprovalIcon,
  CloseIcon,
  DashboardIcon,
  InventoryIcon,
  MenuIcon,
  OrganisationIcon,
  ReportIcon,
  ReviewIcon,
  UploadIcon
} from "@/components/icons";

interface NavigationItem {
  href: string;
  label: string;
  icon: ComponentType;
  isVisible: (user: CurrentUser) => boolean;
}

const everyUser = () => true;
const tenantAdmin = (user: CurrentUser) =>
  user.is_platform_admin || user.roles.includes("tenant_admin");
const tenantAdminOrAuditor = (user: CurrentUser) =>
  user.is_platform_admin ||
  user.roles.some((role) => ["tenant_admin", "auditor"].includes(role));
const platformAdmin = (user: CurrentUser) => user.is_platform_admin;
const methodologyAdmin = (user: CurrentUser) =>
  user.is_platform_admin || user.roles.includes("methodology_manager");

const navigation: NavigationItem[] = [
  { href: "/", label: "Dashboard", icon: DashboardIcon, isVisible: everyUser },
  { href: "/organisations", label: "Organisations", icon: OrganisationIcon, isVisible: everyUser },
  { href: "/inventories", label: "Inventories", icon: InventoryIcon, isVisible: everyUser },
  { href: "/activities/new", label: "Activity entry", icon: ActivityIcon, isVisible: everyUser },
  { href: "/data-imports", label: "Data imports", icon: UploadIcon, isVisible: everyUser },
  { href: "/scope-3-screening", label: "Scope 3 screening", icon: ReviewIcon, isVisible: everyUser },
  { href: "/data-reviews", label: "DATa review", icon: ReviewIcon, isVisible: everyUser },
  { href: "/approvals", label: "Approvals", icon: ApprovalIcon, isVisible: everyUser },
  { href: "/audit-reports", label: "Audit reports", icon: ReportIcon, isVisible: everyUser },
  { href: "/admin/users", label: "Users and roles", icon: OrganisationIcon, isVisible: tenantAdmin },
  { href: "/admin/tenants", label: "Tenant onboarding", icon: InventoryIcon, isVisible: platformAdmin },
  { href: "/admin/methodologies", label: "Methodologies", icon: ReviewIcon, isVisible: methodologyAdmin },
  { href: "/admin/security-events", label: "Security events", icon: ReviewIcon, isVisible: tenantAdminOrAuditor },
  { href: "/admin/operations", label: "Operations", icon: DashboardIcon, isVisible: tenantAdminOrAuditor },
  { href: "/settings/security", label: "Security settings", icon: ApprovalIcon, isVisible: everyUser }
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { user, loading, logout } = useAuth();
  const environment = process.env.NEXT_PUBLIC_APP_ENV ?? "development";
  const environmentLabel = `${environment.charAt(0).toUpperCase()}${environment.slice(1)} workspace`;
  const isPublic = ['/login', '/accept-invitation', '/forgot-password', '/reset-password'].some((path) => pathname.startsWith(path));
  if (isPublic) return <>{children}</>;
  if (loading || !user) return <div className="api-state"><span className="spinner" /><p>Loading secure workspace…</p></div>;

  return (
    <div className="app-frame">
      <button
        aria-label="Open navigation"
        className="mobile-menu-button"
        onClick={() => setOpen(true)}
        type="button"
      >
        <MenuIcon />
      </button>

      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="brand-row">
          <Link className="brand" href="/" onClick={() => setOpen(false)}>
            <span className="brand-mark" aria-hidden="true">D</span>
            <span>
              <strong>D-carbN</strong>
              <small>Carbon Platform</small>
            </span>
          </Link>
          <button
            aria-label="Close navigation"
            className="sidebar-close"
            onClick={() => setOpen(false)}
            type="button"
          >
            <CloseIcon />
          </button>
        </div>

        <nav aria-label="Primary navigation">
          {navigation.filter((item) => item.isVisible(user)).map(({ href, label, icon: Icon }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);

            return (
              <Link
                className={`nav-link ${active ? "nav-link-active" : ""}`}
                href={href}
                key={href}
                onClick={() => setOpen(false)}
              >
                <Icon />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <p>Workspace</p>
          <strong>{user.tenant_name}</strong>
          <span>{user.tenant_slug}</span>
        </div>
      </aside>

      {open ? (
        <button
          aria-label="Close navigation overlay"
          className="sidebar-backdrop"
          onClick={() => setOpen(false)}
          type="button"
        />
      ) : null}

      <div className="content-frame">
        <header className="topbar">
          <div>
            <span className="environment-dot" />
            {environmentLabel}
          </div>
          <div className="user-menu">
            <span className="avatar">{user.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</span>
            <span>
              <strong>{user.full_name}</strong>
              <small>{user.roles.join(", ")}</small>
            </span>
            <button className="text-button" onClick={() => void logout()} type="button">Sign out</button>
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
