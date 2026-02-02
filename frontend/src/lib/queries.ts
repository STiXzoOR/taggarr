import {
  useQuery,
  useQueries,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "./api";

export const queryKeys = {
  authStatus: ["auth", "status"] as const,
  stats: ["stats"] as const,
  systemStatus: ["system", "status"] as const,
  instances: ["instances"] as const,
  instance: (id: number) => ["instances", id] as const,
  media: (params?: Parameters<typeof api.getMedia>[0]) =>
    ["media", params] as const,
  tags: ["tags"] as const,
  config: (key: string) => ["config", key] as const,
  uiConfig: ["config", "ui"] as const,
};

export function useAuthStatus() {
  return useQuery({
    queryKey: queryKeys.authStatus,
    queryFn: api.getAuthStatus,
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      username,
      password,
    }: {
      username: string;
      password: string;
    }) => api.login(username, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.authStatus });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.authStatus });
    },
  });
}

export function useInitialize() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      username,
      password,
    }: {
      username: string;
      password: string;
    }) => api.initialize(username, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.authStatus });
    },
  });
}

export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: api.getStats,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: api.getSystemStatus,
  });
}

export function useInstances() {
  return useQuery({
    queryKey: queryKeys.instances,
    queryFn: api.getInstances,
  });
}

export function useInstance(id: number) {
  return useQuery({
    queryKey: queryKeys.instance(id),
    queryFn: () => api.getInstance(id),
    enabled: id > 0,
  });
}

export function useCreateInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createInstance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.instances });
    },
  });
}

export function useUpdateInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: unknown }) =>
      api.updateInstance(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.instances });
      queryClient.invalidateQueries({ queryKey: queryKeys.instance(id) });
    },
  });
}

export function useDeleteInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteInstance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.instances });
    },
  });
}

export function useTags() {
  return useQuery({
    queryKey: queryKeys.tags,
    queryFn: api.getTags,
  });
}

export function useMedia(params?: Parameters<typeof api.getMedia>[0]) {
  return useQuery({
    queryKey: queryKeys.media(params),
    queryFn: () => api.getMedia(params),
  });
}

export function useConfig(key: string) {
  return useQuery({
    queryKey: queryKeys.config(key),
    queryFn: () => api.getConfig(key),
    enabled: !!key,
  });
}

export function useSetConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      api.setConfig(key, value),
    onSuccess: (_, { key }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.config(key) });
      queryClient.invalidateQueries({ queryKey: queryKeys.uiConfig });
    },
  });
}

export function useUIConfig() {
  return useQuery({
    queryKey: queryKeys.uiConfig,
    queryFn: api.getUIConfig,
  });
}

/**
 * Fetch multiple config keys in parallel using useQueries.
 * Returns an object with each key mapped to its query result.
 */
export function useConfigs<T extends string>(keys: T[]) {
  const results = useQueries({
    queries: keys.map((key) => ({
      queryKey: queryKeys.config(key),
      queryFn: () => api.getConfig(key),
      enabled: !!key,
    })),
  });

  // Map results back to their keys for easy access
  const data = keys.reduce(
    (acc, key, index) => {
      acc[key] = results[index]?.data;
      return acc;
    },
    {} as Record<T, unknown>,
  );

  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);

  return { data, results, isLoading, isError };
}

/**
 * Fetch dashboard data (stats, instances, media) in parallel using useQueries.
 * Eliminates waterfall requests by fetching all data simultaneously.
 */
export function useDashboardData(mediaParams?: {
  page: number;
  page_size: number;
}) {
  const results = useQueries({
    queries: [
      {
        queryKey: queryKeys.stats,
        queryFn: api.getStats,
      },
      {
        queryKey: queryKeys.instances,
        queryFn: api.getInstances,
      },
      {
        queryKey: queryKeys.media(mediaParams),
        queryFn: () => api.getMedia(mediaParams),
      },
    ],
  });

  const [statsQuery, instancesQuery, mediaQuery] = results;

  return {
    stats: {
      data: statsQuery.data,
      isLoading: statsQuery.isLoading,
      isError: statsQuery.isError,
    },
    instances: {
      data: instancesQuery.data,
      isLoading: instancesQuery.isLoading,
      isError: instancesQuery.isError,
    },
    media: {
      data: mediaQuery.data,
      isLoading: mediaQuery.isLoading,
      isError: mediaQuery.isError,
    },
    isLoading: results.some((r) => r.isLoading),
    isError: results.some((r) => r.isError),
  };
}
