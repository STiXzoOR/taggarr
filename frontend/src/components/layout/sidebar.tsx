import { Link, useLocation } from "@tanstack/react-router";
import { cn } from "~/lib/utils";
import {
  LayoutDashboard,
  Library,
  Settings,
  Activity,
  Monitor,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "~/components/ui/sheet";

function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="taggarrGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#06b6d4" />
          <stop offset="50%" stopColor="#0891b2" />
          <stop offset="100%" stopColor="#0e7490" />
        </linearGradient>
      </defs>
      <path
        d="M2 6 L17 6 L28 16 L17 26 L2 26 Q1 26 1 25 L1 7 Q1 6 2 6 Z"
        fill="url(#taggarrGrad)"
      />
      <circle cx="7" cy="16" r="2.5" fill="#0e7490" opacity="0.6" />
      <circle cx="7" cy="16" r="1.5" fill="white" opacity="0.3" />
      <path
        d="M13 10 L24 10 L24 12.5 L20 12.5 L20 22 L17 22 L17 12.5 L13 12.5 Z"
        fill="white"
      />
    </svg>
  );
}

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
      <Link to="/" className="flex items-center gap-2.5">
        <Logo className="h-7 w-7" />
        <span className="text-xl font-bold bg-gradient-to-r from-cyan-500 to-cyan-700 bg-clip-text text-transparent">
          Taggarr
        </span>
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
          <SheetTitle className="flex items-center gap-2.5">
            <Logo className="h-7 w-7" />
            <span className="bg-gradient-to-r from-cyan-500 to-cyan-700 bg-clip-text text-transparent">
              Taggarr
            </span>
          </SheetTitle>
        </SheetHeader>
        <SidebarNav onNavigate={() => onOpenChange(false)} />
      </SheetContent>
    </Sheet>
  );
}
