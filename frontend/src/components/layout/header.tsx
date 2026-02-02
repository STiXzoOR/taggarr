import { useAuth } from "~/lib/auth";
import { useLogout } from "~/lib/queries";
import { Button } from "~/components/ui/button";
import { useNavigate } from "@tanstack/react-router";
import { LogOut, User } from "lucide-react";
import { toast } from "~/lib/toast";

export function Header() {
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
    <header className="h-14 border-b border-border bg-card px-4 flex items-center justify-end gap-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <User className="h-4 w-4" />
        <span>{user?.username}</span>
      </div>
      <Button variant="ghost" size="sm" onClick={handleLogout}>
        <LogOut className="h-4 w-4 mr-2" />
        Logout
      </Button>
    </header>
  );
}
