import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { Label } from "~/components/ui/label";
import { Input } from "~/components/ui/input";
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
  DialogTrigger,
} from "~/components/ui/dialog";
import {
  ArrowLeft,
  Film,
  Tv,
  RefreshCw,
  Settings,
  Clock,
  Calendar,
} from "lucide-react";
import { useState } from "react";
import { toast } from "~/lib/toast";
import { Skeleton } from "~/components/ui/skeleton";

export const Route = createFileRoute("/library/$mediaId")({
  component: MediaDetailPage,
});

interface MediaDetail {
  id: number;
  title: string;
  media_type: string;
  instance_id: number;
  instance_name?: string;
  tag_id?: number;
  tag_label?: string;
  path?: string;
  last_scanned?: string;
  added?: string;
  seasons?: Season[];
  override_require_original?: boolean | null;
  override_notify?: boolean | null;
}

interface Season {
  season_number: number;
  episode_count: number;
  status?: string;
}

function MediaDetailPage() {
  const { mediaId } = Route.useParams();
  const [overrideOpen, setOverrideOpen] = useState(false);
  const queryClient = useQueryClient();

  // Form state for override settings
  const [overrideRequireOriginal, setOverrideRequireOriginal] = useState<
    boolean | null
  >(null);
  const [overrideNotify, setOverrideNotify] = useState<boolean | null>(null);

  const { data: media, isLoading } = useQuery({
    queryKey: ["media", mediaId],
    queryFn: () =>
      fetch(`/api/v1/media/${mediaId}`, { credentials: "include" }).then(
        (res) => res.json(),
      ),
  });

  const typedMedia = media as MediaDetail | undefined;

  // Mutation for updating media overrides
  const updateMediaMutation = useMutation({
    mutationFn: (data: {
      override_require_original?: boolean | null;
      override_notify?: boolean | null;
    }) => api.updateMedia(Number(mediaId), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["media", mediaId] });
      setOverrideOpen(false);
    },
  });

  // Sync form state when media loads or dialog opens
  const handleOpenChange = (open: boolean) => {
    if (open && typedMedia) {
      setOverrideRequireOriginal(typedMedia.override_require_original ?? null);
      setOverrideNotify(typedMedia.override_notify ?? null);
    }
    setOverrideOpen(open);
  };

  const handleSaveOverrides = async () => {
    try {
      await updateMediaMutation.mutateAsync({
        override_require_original: overrideRequireOriginal,
        override_notify: overrideNotify,
      });
      toast.success("Override settings saved");
    } catch {
      toast.error("Failed to save settings");
    }
  };

  const getTagBadgeClass = (tagLabel?: string) => {
    switch (tagLabel) {
      case "dub":
        return "bg-green-500 hover:bg-green-600";
      case "semi-dub":
        return "bg-yellow-500 hover:bg-yellow-600";
      case "wrong-dub":
        return "bg-red-500 hover:bg-red-600";
      default:
        return "";
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header Skeleton */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/library">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Link>
            </Button>
            <div className="flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded" />
              <div>
                <Skeleton className="h-7 w-64 mb-2" />
                <Skeleton className="h-4 w-32" />
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-9 w-24" />
            <Skeleton className="h-9 w-36" />
          </div>
        </div>

        {/* Details Cards Skeleton */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-20" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-12" />
                <Skeleton className="h-5 w-20 rounded-full" />
              </div>
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-8" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
              <div className="space-y-1">
                <Skeleton className="h-4 w-10" />
                <Skeleton className="h-10 w-full" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-28" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-4 w-36" />
              </div>
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-36" />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!typedMedia) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/library">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Library
            </Link>
          </Button>
        </div>
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            Media not found
          </CardContent>
        </Card>
      </div>
    );
  }

  const isShow =
    typedMedia.media_type === "show" || typedMedia.media_type === "series";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/library">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>
          <div className="flex items-center gap-3">
            {isShow ? (
              <Tv className="h-8 w-8 text-blue-500" />
            ) : (
              <Film className="h-8 w-8 text-orange-500" />
            )}
            <div>
              <h1 className="text-2xl font-bold">{typedMedia.title}</h1>
              <p className="text-muted-foreground">
                {typedMedia.instance_name ||
                  `Instance ${typedMedia.instance_id}`}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <RefreshCw className="mr-2 h-4 w-4" />
            Rescan
          </Button>
          <Dialog open={overrideOpen} onOpenChange={handleOpenChange}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="mr-2 h-4 w-4" />
                Override Settings
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Override Settings</DialogTitle>
                <DialogDescription>
                  Configure custom settings for this media item
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="override-require-original">
                    Require Original Language
                  </Label>
                  <Select
                    value={
                      overrideRequireOriginal === null
                        ? "default"
                        : overrideRequireOriginal
                          ? "yes"
                          : "no"
                    }
                    onValueChange={(value) =>
                      setOverrideRequireOriginal(
                        value === "default" ? null : value === "yes",
                      )
                    }
                  >
                    <SelectTrigger id="override-require-original">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">
                        Use instance default
                      </SelectItem>
                      <SelectItem value="yes">
                        Yes (require original)
                      </SelectItem>
                      <SelectItem value="no">
                        No (skip original check)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Whether to require original language audio
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="override-notify">Notifications</Label>
                  <Select
                    value={
                      overrideNotify === null
                        ? "default"
                        : overrideNotify
                          ? "yes"
                          : "no"
                    }
                    onValueChange={(value) =>
                      setOverrideNotify(
                        value === "default" ? null : value === "yes",
                      )
                    }
                  >
                    <SelectTrigger id="override-notify">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">
                        Use instance default
                      </SelectItem>
                      <SelectItem value="yes">
                        Yes (send notifications)
                      </SelectItem>
                      <SelectItem value="no">
                        No (skip notifications)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Whether to send notifications for this media
                  </p>
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setOverrideOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveOverrides}
                  disabled={updateMediaMutation.isPending}
                >
                  {updateMediaMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Details Card */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Type</span>
              <Badge variant="outline">{isShow ? "TV Show" : "Movie"}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Tag</span>
              {typedMedia.tag_label ? (
                <Badge className={getTagBadgeClass(typedMedia.tag_label)}>
                  {typedMedia.tag_label}
                </Badge>
              ) : (
                <Badge variant="outline">none</Badge>
              )}
            </div>
            {typedMedia.path && (
              <div className="space-y-1">
                <span className="text-muted-foreground">Path</span>
                <p className="text-sm font-mono bg-muted p-2 rounded break-all">
                  {typedMedia.path}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Timestamps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Last Scanned
              </span>
              <span>
                {typedMedia.last_scanned
                  ? new Date(typedMedia.last_scanned).toLocaleString()
                  : "Never"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Added
              </span>
              <span>
                {typedMedia.added
                  ? new Date(typedMedia.added).toLocaleString()
                  : "N/A"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Seasons (for TV shows) */}
      {isShow && typedMedia.seasons && typedMedia.seasons.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Seasons</CardTitle>
            <CardDescription>Episode dub status by season</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Season</TableHead>
                  <TableHead>Episodes</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {typedMedia.seasons.map((season) => (
                  <TableRow key={season.season_number}>
                    <TableCell className="font-medium">
                      Season {season.season_number}
                    </TableCell>
                    <TableCell>{season.episode_count}</TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {season.status || "Unknown"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Override indicator */}
      {(typedMedia.override_require_original !== null ||
        typedMedia.override_notify !== null) && (
        <Card className="border-yellow-500/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="h-5 w-5 text-yellow-500" />
              Custom Override Active
            </CardTitle>
            <CardDescription>
              This media has custom settings that override the instance defaults
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {typedMedia.override_require_original !== null && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">
                    Require Original Language
                  </span>
                  <Badge variant="outline">
                    {typedMedia.override_require_original ? "Yes" : "No"}
                  </Badge>
                </div>
              )}
              {typedMedia.override_notify !== null && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Notifications</span>
                  <Badge variant="outline">
                    {typedMedia.override_notify ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
