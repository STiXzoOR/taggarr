/// <reference types="vite/client" />
import {
  Outlet,
  createRootRoute,
  HeadContent,
  Scripts,
  useLocation,
} from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { AuthProvider } from "~/lib/auth";
import { ProtectedRoute } from "~/components/protected-route";
import { MainLayout } from "~/components/layout";
import "~/styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

export const Route = createRootRoute({
  head: () => ({
    meta: [
      {
        charSet: "utf-8",
      },
      {
        name: "viewport",
        content: "width=device-width, initial-scale=1",
      },
      {
        title: "Taggarr",
      },
    ],
  }),
  component: RootComponent,
});

const PUBLIC_ROUTES = ["/login", "/setup"];

function RootComponent() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ProtectedRoute>
          <RootDocument>
            <LayoutWrapper />
          </RootDocument>
        </ProtectedRoute>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function LayoutWrapper() {
  const location = useLocation();
  const isPublicRoute = PUBLIC_ROUTES.includes(location.pathname);

  if (isPublicRoute) {
    return <Outlet />;
  }

  return (
    <MainLayout>
      <Outlet />
    </MainLayout>
  );
}

function RootDocument({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html>
      <head>
        <HeadContent />
      </head>
      <body className="dark">
        {children}
        <Scripts />
      </body>
    </html>
  );
}
