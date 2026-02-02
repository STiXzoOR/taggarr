import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { useDashboardData } from "~/lib/queries";
import { Badge } from "~/components/ui/badge";
import { getTagBadgeClass } from "~/lib/tag-utils";
import {
  Skeleton,
  StatsGridSkeleton,
  InstanceListSkeleton,
  MediaListSkeleton,
  CardContentSkeleton,
} from "~/components/ui/skeleton";
import {
  Film,
  Tv,
  Server,
  CheckCircle,
  AlertCircle,
  Clock,
  ArrowRight,
} from "lucide-react";
import { Button } from "~/components/ui/button";

export const Route = createFileRoute("/")({
  component: Dashboard,
});

interface StatsData {
  total_media: number;
  total_instances: number;
  media_by_tag: Record<string, number>;
  media_by_type?: Record<string, number>;
}

interface MediaItem {
  id: number;
  title: string;
  instance_name?: string;
  tag_name?: string;
  last_scanned?: string;
}

interface MediaResponse {
  items: MediaItem[];
  total: number;
}

interface Instance {
  id: number;
  name: string;
  type: string;
  url: string;
  enabled: boolean;
}

function Dashboard() {
  // Fetch all dashboard data in parallel to avoid request waterfalls
  const {
    stats: { data: stats, isLoading: statsLoading },
    instances: { data: instances, isLoading: instancesLoading },
    media: { data: recentMedia, isLoading: mediaLoading },
  } = useDashboardData({ page: 1, page_size: 5 });

  const typedStats = stats as StatsData | undefined;
  const typedInstances = instances as Instance[] | undefined;
  const typedMedia = recentMedia as MediaResponse | undefined;

  const totalMedia = typedStats?.total_media ?? 0;
  const totalInstances = typedStats?.total_instances ?? 0;
  const mediaByTag = typedStats?.media_by_tag ?? {};

  const dubbedCount = mediaByTag["dub"] ?? 0;
  const semiDubbedCount = mediaByTag["semi-dub"] ?? 0;
  const wrongDubCount = mediaByTag["wrong-dub"] ?? 0;
  const issuesCount = semiDubbedCount + wrongDubCount;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Button asChild>
          <Link to="/library">
            View Library
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>

      {/* Stats Cards */}
      {statsLoading ? (
        <StatsGridSkeleton />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Film className="h-4 w-4" />
                Total Media
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalMedia}</div>
              <p className="text-xs text-muted-foreground">
                Movies and TV shows tracked
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Server className="h-4 w-4" />
                Instances
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalInstances}</div>
              <p className="text-xs text-muted-foreground">
                Sonarr/Radarr connected
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Dubbed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-500">
                {dubbedCount}
              </div>
              <p className="text-xs text-muted-foreground">
                Fully dubbed media
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                Issues
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-destructive">
                {issuesCount}
              </div>
              <p className="text-xs text-muted-foreground">
                Semi-dub or wrong-dub
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tag Breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Tag Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge className="bg-green-500 hover:bg-green-600">dub</Badge>
                  <span className="text-sm text-muted-foreground">
                    Full dubs available
                  </span>
                </div>
                <span className="font-medium">{dubbedCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge className="bg-yellow-500 hover:bg-yellow-600">
                    semi-dub
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    Partial dubs
                  </span>
                </div>
                <span className="font-medium">{semiDubbedCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge className="bg-red-500 hover:bg-red-600">
                    wrong-dub
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    Unexpected languages
                  </span>
                </div>
                <span className="font-medium">{wrongDubCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">none</Badge>
                  <span className="text-sm text-muted-foreground">
                    No tag assigned
                  </span>
                </div>
                <span className="font-medium">
                  {totalMedia - dubbedCount - semiDubbedCount - wrongDubCount}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Connected Instances</CardTitle>
          </CardHeader>
          <CardContent>
            {instancesLoading ? (
              <InstanceListSkeleton count={3} />
            ) : !typedInstances || typedInstances.length === 0 ? (
              <div className="text-center py-4">
                <p className="text-muted-foreground mb-4">
                  No instances configured
                </p>
                <Button asChild variant="outline" size="sm">
                  <Link to="/settings/instances">Add Instance</Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {typedInstances.slice(0, 5).map((instance: Instance) => (
                  <div
                    key={instance.id}
                    className="flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      {instance.type === "sonarr" ? (
                        <Tv className="h-4 w-4 text-blue-500" />
                      ) : (
                        <Film className="h-4 w-4 text-orange-500" />
                      )}
                      <span className="font-medium">{instance.name}</span>
                    </div>
                    <Badge variant={instance.enabled ? "default" : "secondary"}>
                      {instance.enabled ? "Active" : "Disabled"}
                    </Badge>
                  </div>
                ))}
                {typedInstances.length > 5 && (
                  <p className="text-sm text-muted-foreground text-center">
                    +{typedInstances.length - 5} more
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Media */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Recently Scanned</CardTitle>
          <Button asChild variant="ghost" size="sm">
            <Link to="/library">
              View all
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {mediaLoading ? (
            <MediaListSkeleton count={5} />
          ) : !typedMedia?.items || typedMedia.items.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-muted-foreground">No media scanned yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {typedMedia.items.map((item: MediaItem) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div>
                    <Link
                      to="/library/$mediaId"
                      params={{ mediaId: String(item.id) }}
                      className="font-medium hover:underline"
                    >
                      {item.title}
                    </Link>
                    <p className="text-sm text-muted-foreground">
                      {item.instance_name}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {item.tag_name && (
                      <Badge className={getTagBadgeClass(item.tag_name)}>
                        {item.tag_name}
                      </Badge>
                    )}
                    {item.last_scanned && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(item.last_scanned).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
