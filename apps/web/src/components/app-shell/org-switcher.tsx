"use client";

import { Building2Icon, CheckIcon, ChevronsUpDownIcon } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useActiveOrg, useOrgs } from "@/features/orgs/api";
import { cn } from "@/lib/cn";
import { useUiPrefs } from "@/lib/store";

/** Switch between the organizations the signed-in user belongs to. Hidden entirely for
 * a user in exactly one organization, the common case, so it never adds noise. */
export function OrgSwitcher({ collapsed = false }: { collapsed?: boolean }) {
  const orgs = useOrgs();
  const { org } = useActiveOrg();
  const setActiveOrgId = useUiPrefs((s) => s.setActiveOrgId);

  if (!orgs.data || orgs.data.length <= 1) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "flex h-8 items-center gap-2 rounded-lg px-2 text-[12.5px] font-medium text-muted-foreground outline-none transition-colors hover:bg-accent/70 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
          collapsed ? "w-full justify-center" : "w-full justify-between",
        )}
        aria-label="Switch organization"
      >
        <span className="flex min-w-0 items-center gap-2">
          <Building2Icon className="size-3.5 shrink-0" />
          {!collapsed && <span className="truncate">{org?.name ?? "Select organization"}</span>}
        </span>
        {!collapsed && <ChevronsUpDownIcon className="size-3.5 shrink-0" />}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel>Organizations</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {orgs.data.map((o) => (
          <DropdownMenuItem key={o.id} onClick={() => setActiveOrgId(o.id)}>
            <span className="flex-1 truncate">{o.name}</span>
            {o.id === org?.id && <CheckIcon className="size-3.5 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
