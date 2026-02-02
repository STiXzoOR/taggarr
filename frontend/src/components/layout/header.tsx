import { useAuth } from "~/lib/auth";
import { useLogout } from "~/lib/queries";
import { Button } from "~/components/ui/button";
import { useNavigate } from "@tanstack/react-router";
import { LogOut, User } from "lucide-react";

export function Header() {
  const { user } = useAuth();
  const logout = useLogout();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout.mutateAsync();
    navigate({ to: "/login" });
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
