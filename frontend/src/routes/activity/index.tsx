import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import {
  History,
  ListTodo,
  FileText,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  XCircle,
} from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/activity/")({
  component: ActivityPage,
});

interface HistoryItem {
  id: number;
  media_title: string;
  action: string;
  status: string;
  message?: string;
  created_at: string;
}

interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  page: number;
  pages: number;
}

interface QueueItem {
  id: number;
  media_title: string;
  command: string;
  status: "pending" | "running" | "completed" | "failed";
  priority: number;
  created_at: string;
  started_at?: string;
}

interface LogEntry {
  id: number;
  level: string;
  message: string;
  timestamp: string;
  source?: string;
}

function ActivityPage() {
  const [historyPage, setHistoryPage] = useState(1);
  const pageSize = 20;

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ["activity", "history", historyPage],
    queryFn: () =>
      fetch(
        `/api/v1/activity/history?page=${historyPage}&page_size=${pageSize}`,
        {
          credentials: "include",
        },
      ).then((res) => res.json()),
  });

  const {
    data: queueData,
    isLoading: queueLoading,
    refetch: refetchQueue,
  } = useQuery({
    queryKey: ["activity", "queue"],
    queryFn: () =>
      fetch("/api/v1/activity/queue", { credentials: "include" }).then((res) =>
        res.json(),
      ),
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const {
    data: logsData,
    isLoading: logsLoading,
    refetch: refetchLogs,
  } = useQuery({
    queryKey: ["activity", "logs"],
    queryFn: () =>
      fetch("/api/v1/activity/logs?limit=100", { credentials: "include" }).then(
        (res) => res.json(),
      ),
  });

  const typedHistory = historyData as HistoryResponse | undefined;
  const typedQueue = queueData as QueueItem[] | undefined;
  const typedLogs = logsData as LogEntry[] | undefined;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "running":
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
      case "success":
        return <Badge className="bg-green-500">Completed</Badge>;
      case "failed":
      case "error":
        return <Badge className="bg-red-500">Failed</Badge>;
      case "running":
        return <Badge className="bg-blue-500">Running</Badge>;
      case "pending":
        return <Badge className="bg-yellow-500">Pending</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getLogLevelBadge = (level: string) => {
    switch (level.toLowerCase()) {
      case "error":
        return <Badge className="bg-red-500">{level}</Badge>;
      case "warning":
      case "warn":
        return <Badge className="bg-yellow-500">{level}</Badge>;
      case "info":
        return <Badge className="bg-blue-500">{level}</Badge>;
      case "debug":
        return <Badge variant="outline">{level}</Badge>;
      default:
        return <Badge variant="secondary">{level}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Activity</h1>
      </div>

      <Tabs defaultValue="history" className="space-y-4">
        <TabsList>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            History
          </TabsTrigger>
          <TabsTrigger value="queue" className="flex items-center gap-2">
            <ListTodo className="h-4 w-4" />
            Queue
            {typedQueue && typedQueue.length > 0 && (
              <Badge variant="secondary" className="ml-1">
                {typedQueue.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="logs" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Logs
          </TabsTrigger>
        </TabsList>

        {/* History Tab */}
        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Action History</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {historyLoading ? (
                <div className="p-8 text-center text-muted-foreground">
                  Loading history...
                </div>
              ) : !typedHistory?.items || typedHistory.items.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  No history yet
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-8"></TableHead>
                        <TableHead>Media</TableHead>
                        <TableHead>Action</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Message</TableHead>
                        <TableHead>Time</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {typedHistory.items.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell>{getStatusIcon(item.status)}</TableCell>
                          <TableCell className="font-medium">
                            {item.media_title}
                          </TableCell>
                          <TableCell>{item.action}</TableCell>
                          <TableCell>{getStatusBadge(item.status)}</TableCell>
                          <TableCell className="text-muted-foreground max-w-xs truncate">
                            {item.message || "-"}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {new Date(item.created_at).toLocaleString()}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {typedHistory.pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-4 border-t">
                      <div className="text-sm text-muted-foreground">
                        Page {historyPage} of {typedHistory.pages}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setHistoryPage((p) => p - 1)}
                          disabled={historyPage <= 1}
                        >
                          <ChevronLeft className="h-4 w-4" />
                          Previous
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setHistoryPage((p) => p + 1)}
                          disabled={historyPage >= typedHistory.pages}
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
        </TabsContent>

        {/* Queue Tab */}
        <TabsContent value="queue">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Command Queue</CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchQueue()}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {queueLoading ? (
                <div className="p-8 text-center text-muted-foreground">
                  Loading queue...
                </div>
              ) : !typedQueue || typedQueue.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <ListTodo className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Queue is empty</p>
                  <p className="text-sm mt-1">
                    Commands will appear here when scanning or tagging media
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8"></TableHead>
                      <TableHead>Media</TableHead>
                      <TableHead>Command</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Queued</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {typedQueue.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{getStatusIcon(item.status)}</TableCell>
                        <TableCell className="font-medium">
                          {item.media_title}
                        </TableCell>
                        <TableCell>{item.command}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{item.priority}</Badge>
                        </TableCell>
                        <TableCell>{getStatusBadge(item.status)}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(item.created_at).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Recent Logs</CardTitle>
              <Button variant="outline" size="sm" onClick={() => refetchLogs()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {logsLoading ? (
                <div className="p-8 text-center text-muted-foreground">
                  Loading logs...
                </div>
              ) : !typedLogs || typedLogs.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No logs available</p>
                  <p className="text-sm mt-1">
                    Application logs will appear here
                  </p>
                </div>
              ) : (
                <div className="max-h-[600px] overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[100px]">Level</TableHead>
                        <TableHead className="w-[180px]">Time</TableHead>
                        <TableHead className="w-[120px]">Source</TableHead>
                        <TableHead>Message</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {typedLogs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell>{getLogLevelBadge(log.level)}</TableCell>
                          <TableCell className="text-muted-foreground font-mono text-xs">
                            {new Date(log.timestamp).toLocaleString()}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {log.source || "-"}
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {log.message}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
