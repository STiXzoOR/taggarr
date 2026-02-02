import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import {
  useInstances,
  useCreateInstance,
  useUpdateInstance,
  useDeleteInstance,
} from "~/lib/queries";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "~/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import { Plus, Pencil, Trash2, Server, Tv, Film, TestTube } from "lucide-react";
import { SettingsSidebar } from "./general";
import { TableSkeleton } from "~/components/ui/skeleton";

export const Route = createFileRoute("/settings/instances")({
  component: InstancesSettingsPage,
});

interface Instance {
  id: number;
  name: string;
  type: "sonarr" | "radarr";
  url: string;
  api_key: string;
  enabled: boolean;
  target_languages?: string[];
}

interface InstanceFormData {
  name: string;
  type: "sonarr" | "radarr";
  url: string;
  api_key: string;
  enabled: boolean;
  target_languages: string;
}

const defaultFormData: InstanceFormData = {
  name: "",
  type: "sonarr",
  url: "",
  api_key: "",
  enabled: true,
  target_languages: "",
};

function InstancesSettingsPage() {
  useEffect(() => {
    document.title = "Instances - Settings - Taggarr";
  }, []);

  const { data: instances, isLoading } = useInstances();
  const createInstance = useCreateInstance();
  const updateInstance = useUpdateInstance();
  const deleteInstance = useDeleteInstance();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingInstance, setEditingInstance] = useState<Instance | null>(null);
  const [formData, setFormData] = useState<InstanceFormData>(defaultFormData);
  const [deleteConfirm, setDeleteConfirm] = useState<Instance | null>(null);

  const typedInstances = instances as Instance[] | undefined;

  const handleCreate = async () => {
    try {
      await createInstance.mutateAsync({
        ...formData,
        target_languages: formData.target_languages
          ? formData.target_languages.split(",").map((l) => l.trim())
          : [],
      });
      toast.success("Instance created");
      setIsCreateOpen(false);
      setFormData(defaultFormData);
    } catch {
      toast.error("Failed to create instance");
    }
  };

  const handleUpdate = async () => {
    if (!editingInstance) return;
    try {
      await updateInstance.mutateAsync({
        id: editingInstance.id,
        data: {
          ...formData,
          target_languages: formData.target_languages
            ? formData.target_languages.split(",").map((l) => l.trim())
            : [],
        },
      });
      toast.success("Instance updated");
      setEditingInstance(null);
      setFormData(defaultFormData);
    } catch {
      toast.error("Failed to update instance");
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteInstance.mutateAsync(deleteConfirm.id);
      toast.success("Instance deleted");
      setDeleteConfirm(null);
    } catch {
      toast.error("Failed to delete instance");
    }
  };

  const openEdit = (instance: Instance) => {
    setEditingInstance(instance);
    setFormData({
      name: instance.name,
      type: instance.type,
      url: instance.url,
      api_key: instance.api_key,
      enabled: instance.enabled,
      target_languages: instance.target_languages?.join(", ") || "",
    });
  };

  const InstanceForm = ({
    onSubmit,
    isEdit,
  }: {
    onSubmit: () => void;
    isEdit: boolean;
  }) => (
    <div className="space-y-4 py-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
          placeholder="My Sonarr"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="type">Type</Label>
        <Select
          value={formData.type}
          onValueChange={(v: "sonarr" | "radarr") =>
            setFormData((f) => ({ ...f, type: v }))
          }
        >
          <SelectTrigger id="type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="sonarr">Sonarr (TV Shows)</SelectItem>
            <SelectItem value="radarr">Radarr (Movies)</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="url">URL</Label>
        <Input
          id="url"
          value={formData.url}
          onChange={(e) => setFormData((f) => ({ ...f, url: e.target.value }))}
          placeholder="http://localhost:8989"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="api_key">API Key</Label>
        <Input
          id="api_key"
          type="password"
          value={formData.api_key}
          onChange={(e) =>
            setFormData((f) => ({ ...f, api_key: e.target.value }))
          }
          placeholder="Enter API key"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="target_languages">Target Languages</Label>
        <Input
          id="target_languages"
          value={formData.target_languages}
          onChange={(e) =>
            setFormData((f) => ({ ...f, target_languages: e.target.value }))
          }
          placeholder="eng, spa, jpn"
        />
        <p className="text-xs text-muted-foreground">
          Comma-separated ISO 639-2 language codes for dub detection
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="enabled">Status</Label>
        <Select
          value={formData.enabled ? "enabled" : "disabled"}
          onValueChange={(v) =>
            setFormData((f) => ({ ...f, enabled: v === "enabled" }))
          }
        >
          <SelectTrigger id="enabled">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="enabled">Enabled</SelectItem>
            <SelectItem value="disabled">Disabled</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-muted-foreground">Settings</p>
        <h1 className="text-3xl font-bold">Instances</h1>
      </div>

      <div className="grid gap-6 md:grid-cols-[200px_1fr]">
        <SettingsSidebar />

        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Instances</CardTitle>
                <CardDescription>
                  Manage your Sonarr and Radarr connections
                </CardDescription>
              </div>
              <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Instance
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Instance</DialogTitle>
                    <DialogDescription>
                      Connect a new Sonarr or Radarr instance
                    </DialogDescription>
                  </DialogHeader>
                  <InstanceForm onSubmit={handleCreate} isEdit={false} />
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setIsCreateOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleCreate}
                      disabled={createInstance.isPending}
                    >
                      {createInstance.isPending ? "Creating..." : "Create"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="p-0">
              {isLoading ? (
                <TableSkeleton columns={6} rows={3} />
              ) : !typedInstances || typedInstances.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Server className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No instances configured</p>
                  <p className="text-sm mt-1">
                    Add a Sonarr or Radarr instance to get started
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">Type</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>URL</TableHead>
                      <TableHead>Languages</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-[120px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {typedInstances.map((instance) => (
                      <TableRow key={instance.id}>
                        <TableCell>
                          {instance.type === "sonarr" ? (
                            <Tv className="h-4 w-4 text-blue-500" />
                          ) : (
                            <Film className="h-4 w-4 text-orange-500" />
                          )}
                        </TableCell>
                        <TableCell className="font-medium">
                          {instance.name}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {instance.url}
                        </TableCell>
                        <TableCell>
                          {instance.target_languages?.length ? (
                            <span className="text-sm">
                              {instance.target_languages.join(", ")}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">
                              Default
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={instance.enabled ? "default" : "secondary"}
                          >
                            {instance.enabled ? "Active" : "Disabled"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => openEdit(instance)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setDeleteConfirm(instance)}
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

      {/* Edit Dialog */}
      <Dialog
        open={!!editingInstance}
        onOpenChange={() => setEditingInstance(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Instance</DialogTitle>
            <DialogDescription>Update instance configuration</DialogDescription>
          </DialogHeader>
          <InstanceForm onSubmit={handleUpdate} isEdit={true} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingInstance(null)}>
              Cancel
            </Button>
            <Button onClick={handleUpdate} disabled={updateInstance.isPending}>
              {updateInstance.isPending ? "Saving..." : "Save Changes"}
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
            <DialogTitle>Delete Instance</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteConfirm?.name}"? This
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
              disabled={deleteInstance.isPending}
            >
              {deleteInstance.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
