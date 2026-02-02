import { ErrorBoundary as ReactErrorBoundary } from "react-error-boundary";
import { AlertTriangle, Home, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";

interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md border-destructive/50">
        <CardHeader className="text-center">
          <div className="bg-destructive/10 mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full">
            <AlertTriangle className="text-destructive h-8 w-8" />
          </div>
          <CardTitle className="text-xl">Something went wrong</CardTitle>
          <CardDescription>
            An unexpected error occurred. You can try again or return to the
            home page.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <details className="bg-muted/50 rounded-md border p-3">
            <summary className="text-muted-foreground cursor-pointer text-sm font-medium">
              Error details
            </summary>
            <pre className="text-destructive mt-2 overflow-auto text-xs whitespace-pre-wrap">
              {error.message}
            </pre>
          </details>
        </CardContent>
        <CardFooter className="flex gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => (window.location.href = "/")}
          >
            <Home className="h-4 w-4" />
            Go Home
          </Button>
          <Button className="flex-1" onClick={resetErrorBoundary}>
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

interface ErrorBoundaryProps {
  children: ReactNode;
}

export function ErrorBoundary({ children }: ErrorBoundaryProps) {
  return (
    <ReactErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={() => {
        // Reset any state that might have caused the error
        // The component tree will re-mount when this is called
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
}
