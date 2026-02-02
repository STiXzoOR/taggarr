import { createFileRoute, Link } from "@tanstack/react-router";
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

export const Route = createFileRoute("/library/$mediaId")({
  component: MediaDetailPage,
});

interface MediaDetail {
  id: number;
  title: string;
  type: string;
  instance_id: number;
  instance_name?: string;
  tag_id?: number;
  tag_name?: string;
  external_id?: string;
  path?: string;
  last_scanned?: string;
  created_at?: string;
  updated_at?: string;
  seasons?: Season[];
  override_enabled?: boolean;
  override_target_languages?: string[];
}

interface Season {
  season_number: number;
  episode_count: number;
  dubbed_count: number;
  status: string;
}

function MediaDetailPage() {
  const { mediaId } = Route.useParams();
  const [overrideOpen, setOverrideOpen] = useState(false);

  const { data: media, isLoading } = useQuery({
    queryKey: ["media", mediaId],
    queryFn: () =>
      fetch(`/api/v1/media/${mediaId}`, { credentials: "include" }).then(
        (res) => res.json(),
      ),
  });

  const typedMedia = media as MediaDetail | undefined;

  const getTagBadgeClass = (tagName?: string) => {
    switch (tagName) {
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
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/library">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Library
            </Link>
          </Button>
        </div>
        <div className="text-center py-8 text-muted-foreground">
          Loading media details...
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

  const isShow = typedMedia.type === "show" || typedMedia.type === "series";

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
          <Dialog open={overrideOpen} onOpenChange={setOverrideOpen}>
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
                  <Label htmlFor="override-enabled">Enable Override</Label>
                  <Select
                    defaultValue={typedMedia.override_enabled ? "yes" : "no"}
                  >
                    <SelectTrigger id="override-enabled">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="no">
                        No (use instance defaults)
                      </SelectItem>
                      <SelectItem value="yes">Yes (custom settings)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="target-languages">Target Languages</Label>
                  <Input
                    id="target-languages"
                    placeholder="e.g., eng, spa, jpn"
                    defaultValue={
                      typedMedia.override_target_languages?.join(", ") || ""
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Comma-separated ISO 639-2 language codes
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
                <Button onClick={() => setOverrideOpen(false)}>
                  Save Changes
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
              {typedMedia.tag_name ? (
                <Badge className={getTagBadgeClass(typedMedia.tag_name)}>
                  {typedMedia.tag_name}
                </Badge>
              ) : (
                <Badge variant="outline">none</Badge>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">External ID</span>
              <span className="font-mono text-sm">
                {typedMedia.external_id || "N/A"}
              </span>
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
                Created
              </span>
              <span>
                {typedMedia.created_at
                  ? new Date(typedMedia.created_at).toLocaleString()
                  : "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-2">
                <RefreshCw className="h-4 w-4" />
                Updated
              </span>
              <span>
                {typedMedia.updated_at
                  ? new Date(typedMedia.updated_at).toLocaleString()
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
                  <TableHead>Dubbed</TableHead>
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
                      {season.dubbed_count} / {season.episode_count}
                    </TableCell>
                    <TableCell>
                      <Badge
                        className={
                          season.dubbed_count === season.episode_count
                            ? "bg-green-500"
                            : season.dubbed_count > 0
                              ? "bg-yellow-500"
                              : ""
                        }
                        variant={
                          season.dubbed_count === 0 ? "outline" : "default"
                        }
                      >
                        {season.status ||
                          (season.dubbed_count === season.episode_count
                            ? "Complete"
                            : season.dubbed_count > 0
                              ? "Partial"
                              : "None")}
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
      {typedMedia.override_enabled && (
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
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Target Languages</span>
                <span>
                  {typedMedia.override_target_languages?.join(", ") ||
                    "Not configured"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
