import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "~/lib/toast";
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
import { Badge } from "~/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import {
  Database,
  Download,
  Upload,
  Trash2,
  RefreshCw,
  Save,
  Clock,
} from "lucide-react";
import { SettingsSidebar } from "./general";
import { TableSkeleton } from "~/components/ui/skeleton";

export const Route = createFileRoute("/settings/backup")({
  component: BackupSettingsPage,
});

interface Backup {
  id: number;
  filename: string;
  size: number;
  created_at: string;
  type: "manual" | "scheduled";
}

interface BackupSettings {
  auto_backup_enabled: boolean;
  backup_interval_days: number;
  max_backups: number;
  backup_path: string;
}

function BackupSettingsPage() {
  const queryClient = useQueryClient();

  const { data: backups, isLoading: backupsLoading } = useQuery({
    queryKey: ["backups"],
    queryFn: () =>
      fetch("/api/v1/backup", { credentials: "include" }).then((res) =>
        res.json(),
      ),
  });

  const { data: settings } = useQuery({
    queryKey: ["backup", "settings"],
    queryFn: () =>
      fetch("/api/v1/backup/settings", { credentials: "include" }).then((res) =>
        res.json(),
      ),
  });

  const createBackup = useMutation({
    mutationFn: () =>
      fetch("/api/v1/backup", {
        method: "POST",
        credentials: "include",
      }).then((res) => res.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backups"] });
    },
  });

  const restoreBackup = useMutation({
    mutationFn: (id: number) =>
      fetch(`/api/v1/backup/${id}/restore`, {
        method: "POST",
        credentials: "include",
      }).then((res) => res.json()),
  });

  const deleteBackup = useMutation({
    mutationFn: (id: number) =>
      fetch(`/api/v1/backup/${id}`, {
        method: "DELETE",
        credentials: "include",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backups"] });
    },
  });

  const updateSettings = useMutation({
    mutationFn: (data: Partial<BackupSettings>) =>
      fetch("/api/v1/backup/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        credentials: "include",
      }).then((res) => res.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backup", "settings"] });
    },
  });

  const typedBackups = backups as Backup[] | undefined;
  const typedSettings = settings as BackupSettings | undefined;

  const [formData, setFormData] = useState<Partial<BackupSettings>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<Backup | null>(null);
  const [restoreConfirm, setRestoreConfirm] = useState<Backup | null>(null);

  const currentAutoBackup =
    formData.auto_backup_enabled ?? typedSettings?.auto_backup_enabled ?? false;
  const currentInterval =
    formData.backup_interval_days ?? typedSettings?.backup_interval_days ?? 7;
  const currentMaxBackups =
    formData.max_backups ?? typedSettings?.max_backups ?? 5;

  const handleChange = <K extends keyof BackupSettings>(
    key: K,
    value: BackupSettings[K],
  ) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      await updateSettings.mutateAsync(formData);
      toast.success("Settings saved");
      setHasChanges(false);
      setFormData({});
    } catch {
      toast.error("Failed to save settings");
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteBackup.mutateAsync(deleteConfirm.id);
      toast.success("Backup deleted");
      setDeleteConfirm(null);
    } catch {
      toast.error("Failed to delete backup");
    }
  };

  const handleRestore = async () => {
    if (!restoreConfirm) return;
    try {
      await restoreBackup.mutateAsync(restoreConfirm.id);
      toast.success("Backup restored successfully");
      setRestoreConfirm(null);
    } catch {
      toast.error("Failed to restore backup");
    }
  };

  const handleCreateBackup = async () => {
    try {
      await createBackup.mutateAsync();
      toast.success("Backup created");
    } catch {
      toast.error("Failed to create backup");
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>

      <div className="grid gap-6 md:grid-cols-[200px_1fr]">
        <SettingsSidebar />

        <div className="space-y-6">
          {/* Backup Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Backup Settings</CardTitle>
              <CardDescription>
                Configure automatic backups and retention
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="auto-backup">Automatic Backups</Label>
                <Select
                  value={currentAutoBackup ? "enabled" : "disabled"}
                  onValueChange={(v) =>
                    handleChange("auto_backup_enabled", v === "enabled")
                  }
                >
                  <SelectTrigger id="auto-backup">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="enabled">Enabled</SelectItem>
                    <SelectItem value="disabled">Disabled</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="interval">Backup Interval (days)</Label>
                <Input
                  id="interval"
                  type="number"
                  min="1"
                  max="30"
                  value={currentInterval}
                  onChange={(e) =>
                    handleChange("backup_interval_days", Number(e.target.value))
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="max-backups">Maximum Backups to Keep</Label>
                <Input
                  id="max-backups"
                  type="number"
                  min="1"
                  max="50"
                  value={currentMaxBackups}
                  onChange={(e) =>
                    handleChange("max_backups", Number(e.target.value))
                  }
                />
                <p className="text-sm text-muted-foreground">
                  Older backups will be automatically deleted
                </p>
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={handleSave}
                  disabled={!hasChanges || updateSettings.isPending}
                >
                  <Save className="mr-2 h-4 w-4" />
                  {updateSettings.isPending ? "Saving..." : "Save Settings"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Manual Backup */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Backups</CardTitle>
                <CardDescription>
                  Create and manage database backups
                </CardDescription>
              </div>
              <Button
                onClick={handleCreateBackup}
                disabled={createBackup.isPending}
              >
                <Database className="mr-2 h-4 w-4" />
                {createBackup.isPending ? "Creating..." : "Create Backup"}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {backupsLoading ? (
                <TableSkeleton columns={5} rows={3} />
              ) : !typedBackups || typedBackups.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No backups yet</p>
                  <p className="text-sm mt-1">
                    Create your first backup to protect your data
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Filename</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="w-[120px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {typedBackups.map((backup) => (
                      <TableRow key={backup.id}>
                        <TableCell className="font-medium font-mono text-sm">
                          {backup.filename}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatBytes(backup.size)}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              backup.type === "scheduled"
                                ? "default"
                                : "outline"
                            }
                          >
                            {backup.type === "scheduled" ? (
                              <>
                                <Clock className="mr-1 h-3 w-3" />
                                Scheduled
                              </>
                            ) : (
                              "Manual"
                            )}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(backup.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="icon-sm" asChild>
                              <a
                                href={`/api/v1/backup/${backup.id}/download`}
                                download
                              >
                                <Download className="h-4 w-4" />
                              </a>
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setRestoreConfirm(backup)}
                            >
                              <Upload className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setDeleteConfirm(backup)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Restore Confirmation Dialog */}
      <Dialog
        open={!!restoreConfirm}
        onOpenChange={() => setRestoreConfirm(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Restore Backup</DialogTitle>
            <DialogDescription>
              Are you sure you want to restore from "{restoreConfirm?.filename}
              "? This will replace your current data with the backup data.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreConfirm(null)}>
              Cancel
            </Button>
            <Button onClick={handleRestore} disabled={restoreBackup.isPending}>
              {restoreBackup.isPending ? "Restoring..." : "Restore"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteConfirm}
        onOpenChange={() => setDeleteConfirm(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Backup</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteConfirm?.filename}"? This
              action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteBackup.isPending}
            >
              {deleteBackup.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
