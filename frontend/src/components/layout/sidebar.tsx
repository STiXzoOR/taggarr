import { Link, useLocation } from "@tanstack/react-router";
import { cn } from "~/lib/utils";
import {
  LayoutDashboard,
  Library,
  Settings,
  Activity,
  Server,
  Monitor,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "~/components/ui/sheet";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/library", icon: Library, label: "Library" },
  { to: "/activity", icon: Activity, label: "Activity" },
  { to: "/system", icon: Monitor, label: "System" },
  { to: "/settings", icon: Settings, label: "Settings" },
] as const;

interface SidebarNavProps {
  onNavigate?: () => void;
}

function SidebarNav({ onNavigate }: SidebarNavProps) {
  const location = useLocation();

  return (
    <nav className="flex-1 p-4 space-y-1">
      {navItems.map((item) => {
        const isActive =
          location.pathname === item.to ||
          (item.to !== "/" && location.pathname.startsWith(item.to));
        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-[44px]",
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent",
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarBrand() {
  return (
    <div className="p-4 border-b border-border">
      <Link to="/" className="flex items-center gap-2">
        <Server className="h-6 w-6 text-primary" />
        <span className="text-xl font-bold">Taggarr</span>
      </Link>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden md:flex w-64 border-r border-border bg-card h-screen flex-col">
      <SidebarBrand />
      <SidebarNav />
    </aside>
  );
}

interface MobileSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MobileSidebar({ open, onOpenChange }: MobileSidebarProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-64 p-0">
        <SheetHeader className="p-4 border-b border-border">
          <SheetTitle className="flex items-center gap-2">
            <Server className="h-6 w-6 text-primary" />
            <span>Taggarr</span>
          </SheetTitle>
        </SheetHeader>
        <SidebarNav onNavigate={() => onOpenChange(false)} />
      </SheetContent>
    </Sheet>
  );
}
