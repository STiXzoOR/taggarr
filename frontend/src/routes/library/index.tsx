import { createFileRoute, Link, useSearch } from "@tanstack/react-router";
import { useState } from "react";
import { useMedia, useInstances, useTags } from "~/lib/queries";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Button } from "~/components/ui/button";
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
  Search,
  ChevronLeft,
  ChevronRight,
  Film,
  Tv,
  RefreshCw,
} from "lucide-react";
import { TableSkeleton } from "~/components/ui/skeleton";

interface SearchParams {
  page?: number;
  search?: string;
  instance_id?: string;
  tag_id?: string;
}

export const Route = createFileRoute("/library/")({
  component: LibraryPage,
  validateSearch: (search: Record<string, unknown>): SearchParams => {
    return {
      page: Number(search.page) || 1,
      search: search.search as string | undefined,
      instance_id: search.instance_id as string | undefined,
      tag_id: search.tag_id as string | undefined,
    };
  },
});

interface MediaItem {
  id: number;
  title: string;
  type: string;
  instance_id: number;
  instance_name?: string;
  tag_id?: number;
  tag_name?: string;
  last_scanned?: string;
}

interface MediaResponse {
  items: MediaItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface Instance {
  id: number;
  name: string;
  type: string;
}

interface Tag {
  id: number;
  name: string;
}

function LibraryPage() {
  const search = useSearch({ from: "/library/" });
  const [searchInput, setSearchInput] = useState(search.search || "");

  const page = search.page || 1;
  const pageSize = 20;

  const { data: mediaData, isLoading: mediaLoading } = useMedia({
    page,
    page_size: pageSize,
    instance_id: search.instance_id ? Number(search.instance_id) : undefined,
    tag_id: search.tag_id ? Number(search.tag_id) : undefined,
    search: search.search,
  });

  const { data: instances } = useInstances();
  const { data: tags } = useTags();

  const typedMedia = mediaData as MediaResponse | undefined;
  const typedInstances = instances as Instance[] | undefined;
  const typedTags = tags as Tag[] | undefined;

  const navigate = Route.useNavigate();

  const handleSearch = () => {
    navigate({
      search: {
        ...search,
        page: 1,
        search: searchInput || undefined,
      },
    });
  };

  const handleInstanceFilter = (value: string) => {
    navigate({
      search: {
        ...search,
        page: 1,
        instance_id: value === "all" ? undefined : value,
      },
    });
  };

  const handleTagFilter = (value: string) => {
    navigate({
      search: {
        ...search,
        page: 1,
        tag_id: value === "all" ? undefined : value,
      },
    });
  };

  const handlePageChange = (newPage: number) => {
    navigate({
      search: {
        ...search,
        page: newPage,
      },
    });
  };

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Library</h1>
        <Button variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Rescan All
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search media..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="pl-10"
                />
              </div>
            </div>
            <Select
              value={search.instance_id || "all"}
              onValueChange={handleInstanceFilter}
            >
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="All Instances" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Instances</SelectItem>
                {typedInstances?.map((instance) => (
                  <SelectItem key={instance.id} value={String(instance.id)}>
                    {instance.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={search.tag_id || "all"}
              onValueChange={handleTagFilter}
            >
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="All Tags" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tags</SelectItem>
                {typedTags?.map((tag) => (
                  <SelectItem key={tag.id} value={String(tag.id)}>
                    {tag.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={handleSearch}>Search</Button>
          </div>
        </CardContent>
      </Card>

      {/* Media Table */}
      <Card>
        <CardContent className="p-0">
          {mediaLoading ? (
            <TableSkeleton columns={5} rows={10} />
          ) : !typedMedia?.items || typedMedia.items.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No media found
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Type</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Instance</TableHead>
                    <TableHead>Tag</TableHead>
                    <TableHead>Last Scanned</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {typedMedia.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        {item.type === "show" || item.type === "series" ? (
                          <Tv className="h-4 w-4 text-blue-500" />
                        ) : (
                          <Film className="h-4 w-4 text-orange-500" />
                        )}
                      </TableCell>
                      <TableCell>
                        <Link
                          to="/library/$mediaId"
                          params={{ mediaId: String(item.id) }}
                          className="font-medium hover:underline"
                        >
                          {item.title}
                        </Link>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {item.instance_name || `Instance ${item.instance_id}`}
                      </TableCell>
                      <TableCell>
                        {item.tag_name ? (
                          <Badge className={getTagBadgeClass(item.tag_name)}>
                            {item.tag_name}
                          </Badge>
                        ) : (
                          <Badge variant="outline">none</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {item.last_scanned
                          ? new Date(item.last_scanned).toLocaleDateString()
                          : "Never"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {typedMedia.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-4 border-t">
                  <div className="text-sm text-muted-foreground">
                    Showing {(page - 1) * pageSize + 1} to{" "}
                    {Math.min(page * pageSize, typedMedia.total)} of{" "}
                    {typedMedia.total} results
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <span className="text-sm">
                      Page {page} of {typedMedia.pages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page >= typedMedia.pages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
