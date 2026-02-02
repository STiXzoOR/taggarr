import * as React from "react";
import { cn } from "~/lib/utils";
import { LucideIcon } from "lucide-react";
import { Button } from "./button";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick?: () => void;
    href?: string;
  };
  className?: string;
  variant?: "default" | "compact";
}

/**
 * A visually engaging empty state component with gradient background,
 * subtle pattern, and clear call to action.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  variant = "default",
}: EmptyStateProps) {
  const isCompact = variant === "compact";

  return (
    <div
      className={cn(
        "relative overflow-hidden",
        isCompact ? "py-8 px-4" : "py-12 px-6",
        className,
      )}
    >
      {/* Background pattern - subtle dots */}
      <div
        className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, currentColor 1px, transparent 1px)`,
          backgroundSize: "24px 24px",
        }}
      />

      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-muted/50 via-transparent to-muted/30" />

      {/* Content */}
      <div className="relative flex flex-col items-center text-center">
        {/* Icon with decorative ring */}
        <div className="relative mb-4">
          <div className="absolute inset-0 -m-2 rounded-full bg-gradient-to-br from-primary/10 to-primary/5 blur-sm" />
          <div
            className={cn(
              "relative flex items-center justify-center rounded-full bg-muted/80 border border-border/50",
              isCompact ? "h-14 w-14" : "h-16 w-16",
            )}
          >
            <Icon
              className={cn(
                "text-muted-foreground/70",
                isCompact ? "h-7 w-7" : "h-8 w-8",
              )}
            />
          </div>
        </div>

        {/* Title */}
        <h3
          className={cn(
            "font-semibold text-foreground",
            isCompact ? "text-base mb-1" : "text-lg mb-2",
          )}
        >
          {title}
        </h3>

        {/* Description */}
        <p
          className={cn(
            "text-muted-foreground max-w-sm",
            isCompact ? "text-sm" : "text-sm",
          )}
        >
          {description}
        </p>

        {/* Action button */}
        {action && (
          <div className={cn(isCompact ? "mt-4" : "mt-6")}>
            {action.href ? (
              <Button
                variant="outline"
                size={isCompact ? "sm" : "default"}
                asChild
              >
                <a href={action.href}>{action.label}</a>
              </Button>
            ) : action.onClick ? (
              <Button
                variant="outline"
                size={isCompact ? "sm" : "default"}
                onClick={action.onClick}
              >
                {action.label}
              </Button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
