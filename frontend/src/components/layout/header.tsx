import { useAuth } from "~/lib/auth";
import { useLogout } from "~/lib/queries";
import { Button } from "~/components/ui/button";
import { useNavigate } from "@tanstack/react-router";
import { LogOut, User, Menu } from "lucide-react";
import { toast } from "~/lib/toast";

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user } = useAuth();
  const logout = useLogout();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout.mutateAsync();
      toast.success("Logged out successfully");
      navigate({ to: "/login" });
    } catch {
      toast.error("Failed to log out");
    }
  };

  return (
    <header className="h-14 border-b border-border bg-card px-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        {/* Hamburger menu button - visible only on mobile */}
        <Button
          variant="ghost"
          size="sm"
          className="md:hidden min-h-[44px] min-w-[44px] p-0"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>
      <div className="flex items-center gap-2 sm:gap-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <User className="h-4 w-4" />
          <span className="hidden sm:inline">{user?.username}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          className="min-h-[44px]"
        >
          <LogOut className="h-4 w-4 sm:mr-2" />
          <span className="hidden sm:inline">Logout</span>
        </Button>
      </div>
    </header>
  );
}
