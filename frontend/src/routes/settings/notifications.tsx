import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
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
import {
  Plus,
  Pencil,
  Trash2,
  Bell,
  TestTube,
  Mail,
  MessageSquare,
} from "lucide-react";
import { SettingsSidebar } from "./general";
import { TableSkeleton } from "~/components/ui/skeleton";
import { EmptyState } from "~/components/ui/empty-state";

export const Route = createFileRoute("/settings/notifications")({
  component: NotificationsSettingsPage,
});

interface NotificationChannel {
  id: number;
  name: string;
  type: "email" | "webhook" | "discord" | "slack";
  config: Record<string, string>;
  enabled: boolean;
  events: string[];
}

interface ChannelFormData {
  name: string;
  type: "email" | "webhook" | "discord" | "slack";
  enabled: boolean;
  events: string[];
  // Config fields vary by type
  email_to?: string;
  webhook_url?: string;
  discord_webhook?: string;
  slack_webhook?: string;
}

const defaultFormData: ChannelFormData = {
  name: "",
  type: "webhook",
  enabled: true,
  events: ["scan_complete", "tag_changed"],
};

const eventOptions = [
  { value: "scan_complete", label: "Scan Complete" },
  { value: "tag_changed", label: "Tag Changed" },
  { value: "error", label: "Errors" },
  { value: "new_media", label: "New Media Added" },
];

function NotificationsSettingsPage() {
  useEffect(() => {
    document.title = "Notifications - Settings - Taggarr";
  }, []);

  const queryClient = useQueryClient();

  const { data: channels, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () =>
      fetch("/api/v1/notifications", { credentials: "include" }).then((res) =>
        res.json(),
      ),
  });

  const createChannel = useMutation({
    mutationFn: (data: ChannelFormData) =>
      fetch("/api/v1/notifications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        credentials: "include",
      }).then((res) => res.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const updateChannel = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ChannelFormData }) =>
      fetch(`/api/v1/notifications/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        credentials: "include",
      }).then((res) => res.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const deleteChannel = useMutation({
    mutationFn: (id: number) =>
      fetch(`/api/v1/notifications/${id}`, {
        method: "DELETE",
        credentials: "include",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const testChannel = useMutation({
    mutationFn: (id: number) =>
      fetch(`/api/v1/notifications/${id}/test`, {
        method: "POST",
        credentials: "include",
      }).then((res) => res.json()),
  });

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingChannel, setEditingChannel] =
    useState<NotificationChannel | null>(null);
  const [formData, setFormData] = useState<ChannelFormData>(defaultFormData);
  const [deleteConfirm, setDeleteConfirm] =
    useState<NotificationChannel | null>(null);

  const typedChannels = channels as NotificationChannel[] | undefined;

  const handleCreate = async () => {
    try {
      await createChannel.mutateAsync(formData);
      toast.success("Channel created");
      setIsCreateOpen(false);
      setFormData(defaultFormData);
    } catch {
      toast.error("Failed to create channel");
    }
  };

  const handleUpdate = async () => {
    if (!editingChannel) return;
    try {
      await updateChannel.mutateAsync({
        id: editingChannel.id,
        data: formData,
      });
      toast.success("Channel updated");
      setEditingChannel(null);
      setFormData(defaultFormData);
    } catch {
      toast.error("Failed to update channel");
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteChannel.mutateAsync(deleteConfirm.id);
      toast.success("Channel deleted");
      setDeleteConfirm(null);
    } catch {
      toast.error("Failed to delete channel");
    }
  };

  const handleTest = async (channel: NotificationChannel) => {
    try {
      await testChannel.mutateAsync(channel.id);
      toast.success("Test notification sent");
    } catch {
      toast.error("Failed to send test notification");
    }
  };

  const openEdit = (channel: NotificationChannel) => {
    setEditingChannel(channel);
    setFormData({
      name: channel.name,
      type: channel.type,
      enabled: channel.enabled,
      events: channel.events,
      webhook_url: channel.config.webhook_url,
      discord_webhook: channel.config.discord_webhook,
      slack_webhook: channel.config.slack_webhook,
      email_to: channel.config.email_to,
    });
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "email":
        return <Mail className="h-4 w-4 text-blue-500" />;
      case "discord":
        return <MessageSquare className="h-4 w-4 text-indigo-500" />;
      case "slack":
        return <MessageSquare className="h-4 w-4 text-green-500" />;
      default:
        return <Bell className="h-4 w-4 text-orange-500" />;
    }
  };

  const ChannelForm = () => (
    <div className="space-y-4 py-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
          placeholder="My Webhook"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="type">Type</Label>
        <Select
          value={formData.type}
          onValueChange={(v: ChannelFormData["type"]) =>
            setFormData((f) => ({ ...f, type: v }))
          }
        >
          <SelectTrigger id="type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="webhook">Webhook</SelectItem>
            <SelectItem value="discord">Discord</SelectItem>
            <SelectItem value="slack">Slack</SelectItem>
            <SelectItem value="email">Email</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Type-specific config */}
      {formData.type === "webhook" && (
        <div className="space-y-2">
          <Label htmlFor="webhook_url">Webhook URL</Label>
          <Input
            id="webhook_url"
            value={formData.webhook_url || ""}
            onChange={(e) =>
              setFormData((f) => ({ ...f, webhook_url: e.target.value }))
            }
            placeholder="https://..."
          />
        </div>
      )}

      {formData.type === "discord" && (
        <div className="space-y-2">
          <Label htmlFor="discord_webhook">Discord Webhook URL</Label>
          <Input
            id="discord_webhook"
            value={formData.discord_webhook || ""}
            onChange={(e) =>
              setFormData((f) => ({ ...f, discord_webhook: e.target.value }))
            }
            placeholder="https://discord.com/api/webhooks/..."
          />
        </div>
      )}

      {formData.type === "slack" && (
        <div className="space-y-2">
          <Label htmlFor="slack_webhook">Slack Webhook URL</Label>
          <Input
            id="slack_webhook"
            value={formData.slack_webhook || ""}
            onChange={(e) =>
              setFormData((f) => ({ ...f, slack_webhook: e.target.value }))
            }
            placeholder="https://hooks.slack.com/services/..."
          />
        </div>
      )}

      {formData.type === "email" && (
        <div className="space-y-2">
          <Label htmlFor="email_to">Email Address</Label>
          <Input
            id="email_to"
            type="email"
            value={formData.email_to || ""}
            onChange={(e) =>
              setFormData((f) => ({ ...f, email_to: e.target.value }))
            }
            placeholder="user@example.com"
          />
        </div>
      )}

      <div className="space-y-2">
        <Label>Events</Label>
        <div className="space-y-2">
          {eventOptions.map((event) => (
            <label key={event.value} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.events.includes(event.value)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setFormData((f) => ({
                      ...f,
                      events: [...f.events, event.value],
                    }));
                  } else {
                    setFormData((f) => ({
                      ...f,
                      events: f.events.filter((ev) => ev !== event.value),
                    }));
                  }
                }}
                className="rounded border-input"
              />
              <span className="text-sm">{event.label}</span>
            </label>
          ))}
        </div>
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
        <h1 className="text-3xl font-bold">Notifications</h1>
      </div>

      <div className="grid gap-6 md:grid-cols-[200px_1fr]">
        <SettingsSidebar />

        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Notification Channels</CardTitle>
                <CardDescription>
                  Configure where to send notifications
                </CardDescription>
              </div>
              <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Channel
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Notification Channel</DialogTitle>
                    <DialogDescription>
                      Configure a new notification destination
                    </DialogDescription>
                  </DialogHeader>
                  <ChannelForm />
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setIsCreateOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleCreate}
                      disabled={createChannel.isPending}
                    >
                      {createChannel.isPending ? "Creating..." : "Create"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="p-0">
              {isLoading ? (
                <TableSkeleton columns={5} rows={3} />
              ) : !typedChannels || typedChannels.length === 0 ? (
                <EmptyState
                  icon={Bell}
                  title="No notification channels"
                  description="Set up webhooks, Discord, Slack, or email notifications to stay informed about tag changes and scan results."
                  action={{
                    label: "Add Channel",
                    onClick: () => setIsCreateOpen(true),
                  }}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">Type</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Events</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-[150px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {typedChannels.map((channel) => (
                      <TableRow key={channel.id}>
                        <TableCell>{getTypeIcon(channel.type)}</TableCell>
                        <TableCell className="font-medium">
                          {channel.name}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {channel.events.map((event) => (
                              <Badge
                                key={event}
                                variant="outline"
                                className="text-xs"
                              >
                                {event}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={channel.enabled ? "default" : "secondary"}
                          >
                            {channel.enabled ? "Active" : "Disabled"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => handleTest(channel)}
                              disabled={testChannel.isPending}
                            >
                              <TestTube className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => openEdit(channel)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setDeleteConfirm(channel)}
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
        open={!!editingChannel}
        onOpenChange={() => setEditingChannel(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Channel</DialogTitle>
            <DialogDescription>
              Update notification channel settings
            </DialogDescription>
          </DialogHeader>
          <ChannelForm />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingChannel(null)}>
              Cancel
            </Button>
            <Button onClick={handleUpdate} disabled={updateChannel.isPending}>
              {updateChannel.isPending ? "Saving..." : "Save Changes"}
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
            <DialogTitle>Delete Channel</DialogTitle>
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
              disabled={deleteChannel.isPending}
            >
              {deleteChannel.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
