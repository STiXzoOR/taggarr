import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "~/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import {
  Server,
  Database,
  Clock,
  Archive,
  RefreshCw,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { SystemCardsSkeleton, Skeleton } from "~/components/ui/skeleton";

export const Route = createFileRoute("/system")({
  component: SystemPage,
});

interface SystemStatus {
  version: string;
  uptime_seconds: number;
  database_size_bytes: number;
  last_backup: string | null;
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  const parts: string[] = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (parts.length === 0) parts.push(`${seconds}s`);

  return parts.join(" ");
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function SystemPage() {
  const {
    data: status,
    isLoading,
    error,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["system", "status"],
    queryFn: () => api.getSystemStatus() as Promise<SystemStatus>,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">System</h1>
          <Skeleton className="h-9 w-24" />
        </div>

        {/* Health Status Skeleton */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-5" />
              <Skeleton className="h-5 w-32" />
            </div>
            <Skeleton className="h-4 w-48 mt-2" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-4 w-36" />
            </div>
          </CardContent>
        </Card>

        {/* Status Cards Skeleton */}
        <SystemCardsSkeleton />

        {/* Detailed Info Skeleton */}
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-56 mt-2" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between border-b pb-2 last:border-0"
                >
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="h-4 w-32" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">System</h1>
        <Card>
          <CardContent className="py-8 text-center">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
            <p className="text-red-500">Failed to load system status</p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => refetch()}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">System</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isRefetching}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${isRefetching ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {/* Health Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            System Health
          </CardTitle>
          <CardDescription>Overall system status and health</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Badge className="bg-green-500">Healthy</Badge>
            <span className="text-sm text-muted-foreground">
              All systems operational
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Status Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Version */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Server className="h-4 w-4" />
              Version
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.version || "N/A"}</div>
          </CardContent>
        </Card>

        {/* Uptime */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Uptime
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {status ? formatUptime(status.uptime_seconds) : "N/A"}
            </div>
          </CardContent>
        </Card>

        {/* Database Size */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Database className="h-4 w-4" />
              Database Size
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {status ? formatBytes(status.database_size_bytes) : "N/A"}
            </div>
          </CardContent>
        </Card>

        {/* Last Backup */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Archive className="h-4 w-4" />
              Last Backup
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {status?.last_backup
                ? new Date(status.last_backup).toLocaleDateString()
                : "Never"}
            </div>
            {status?.last_backup && (
              <p className="text-xs text-muted-foreground mt-1">
                {new Date(status.last_backup).toLocaleTimeString()}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Detailed Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">System Information</CardTitle>
          <CardDescription>Detailed system configuration</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-muted-foreground">Application</span>
              <span className="font-medium">Taggarr</span>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-muted-foreground">Version</span>
              <span className="font-mono">{status?.version || "N/A"}</span>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-muted-foreground">Uptime</span>
              <span className="font-mono">
                {status
                  ? `${status.uptime_seconds.toLocaleString()} seconds`
                  : "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-muted-foreground">Database Size</span>
              <span className="font-mono">
                {status
                  ? `${status.database_size_bytes.toLocaleString()} bytes`
                  : "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Last Backup</span>
              <span className="font-mono">
                {status?.last_backup
                  ? new Date(status.last_backup).toISOString()
                  : "Never"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
