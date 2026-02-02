import { createFileRoute, Link, useLocation } from "@tanstack/react-router";
import { useState } from "react";
import { useConfig, useSetConfig } from "~/lib/queries";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { Settings, Server, Bell, Shield, Database, Save } from "lucide-react";
import { cn } from "~/lib/utils";

export const Route = createFileRoute("/settings/general")({
  component: GeneralSettingsPage,
});

const settingsNav = [
  { to: "/settings/general", icon: Settings, label: "General" },
  { to: "/settings/instances", icon: Server, label: "Instances" },
  { to: "/settings/notifications", icon: Bell, label: "Notifications" },
  { to: "/settings/backup", icon: Database, label: "Backup" },
  { to: "/settings/security", icon: Shield, label: "Security" },
] as const;

function SettingsSidebar() {
  const location = useLocation();

  return (
    <nav className="space-y-1">
      {settingsNav.map((item) => {
        const isActive = location.pathname === item.to;
        return (
          <Link
            key={item.to}
            to={item.to}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
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

function GeneralSettingsPage() {
  const { data: scanInterval } = useConfig("scan_interval");
  const { data: logLevel } = useConfig("log_level");
  const { data: timezone } = useConfig("timezone");
  const setConfig = useSetConfig();

  const [formData, setFormData] = useState({
    scan_interval: "",
    log_level: "",
    timezone: "",
  });
  const [hasChanges, setHasChanges] = useState(false);

  // Update form data when configs load
  const currentScanInterval =
    formData.scan_interval ||
    (scanInterval as { value?: string })?.value ||
    "60";
  const currentLogLevel =
    formData.log_level || (logLevel as { value?: string })?.value || "info";
  const currentTimezone =
    formData.timezone || (timezone as { value?: string })?.value || "UTC";

  const handleChange = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    const updates = [];
    if (formData.scan_interval) {
      updates.push(
        setConfig.mutateAsync({
          key: "scan_interval",
          value: formData.scan_interval,
        }),
      );
    }
    if (formData.log_level) {
      updates.push(
        setConfig.mutateAsync({ key: "log_level", value: formData.log_level }),
      );
    }
    if (formData.timezone) {
      updates.push(
        setConfig.mutateAsync({ key: "timezone", value: formData.timezone }),
      );
    }
    await Promise.all(updates);
    setHasChanges(false);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>

      <div className="grid gap-6 md:grid-cols-[200px_1fr]">
        <SettingsSidebar />

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
              <CardDescription>
                Configure general application behavior
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="scan-interval">Scan Interval (minutes)</Label>
                <Input
                  id="scan-interval"
                  type="number"
                  min="5"
                  max="1440"
                  value={currentScanInterval}
                  onChange={(e) =>
                    handleChange("scan_interval", e.target.value)
                  }
                  placeholder="60"
                />
                <p className="text-sm text-muted-foreground">
                  How often to automatically scan for new media (5-1440 minutes)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="log-level">Log Level</Label>
                <Select
                  value={currentLogLevel}
                  onValueChange={(v) => handleChange("log_level", v)}
                >
                  <SelectTrigger id="log-level">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="debug">Debug</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground">
                  Minimum log level to record
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Select
                  value={currentTimezone}
                  onValueChange={(v) => handleChange("timezone", v)}
                >
                  <SelectTrigger id="timezone">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="UTC">UTC</SelectItem>
                    <SelectItem value="America/New_York">
                      America/New_York
                    </SelectItem>
                    <SelectItem value="America/Los_Angeles">
                      America/Los_Angeles
                    </SelectItem>
                    <SelectItem value="America/Chicago">
                      America/Chicago
                    </SelectItem>
                    <SelectItem value="Europe/London">Europe/London</SelectItem>
                    <SelectItem value="Europe/Paris">Europe/Paris</SelectItem>
                    <SelectItem value="Europe/Berlin">Europe/Berlin</SelectItem>
                    <SelectItem value="Asia/Tokyo">Asia/Tokyo</SelectItem>
                    <SelectItem value="Asia/Shanghai">Asia/Shanghai</SelectItem>
                    <SelectItem value="Australia/Sydney">
                      Australia/Sydney
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground">
                  Timezone for scheduled scans and logs
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button
              onClick={handleSave}
              disabled={!hasChanges || setConfig.isPending}
            >
              <Save className="mr-2 h-4 w-4" />
              {setConfig.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export { SettingsSidebar };
