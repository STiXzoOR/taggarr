import { createFileRoute, Navigate } from "@tanstack/react-router";

export const Route = createFileRoute("/settings/")({
  component: SettingsIndex,
});

function SettingsIndex() {
  // Redirect to general settings by default
  return <Navigate to="/settings/general" />;
}
