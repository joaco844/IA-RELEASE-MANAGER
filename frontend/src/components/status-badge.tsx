import { Badge } from "@/components/ui/badge";
import type { ReleaseStatus, RiskLevel } from "@/types";
import { cn } from "@/lib/utils";

const statusConfig: Record<
  ReleaseStatus,
  { label: string; variant: "gray" | "blue" | "green" | "red" | "violet"; pulse?: boolean }
> = {
  pending: { label: "Pending", variant: "gray" },
  running: { label: "Running", variant: "blue", pulse: true },
  completed: { label: "Completed", variant: "green" },
  failed: { label: "Failed", variant: "red" },
  published: { label: "Published", variant: "violet" },
};

const dotColor: Record<ReleaseStatus, string> = {
  pending: "bg-zinc-400",
  running: "bg-blue-400",
  completed: "bg-emerald-400",
  failed: "bg-red-400",
  published: "bg-violet-400",
};

export function StatusBadge({ status }: { status: ReleaseStatus }) {
  const config = statusConfig[status];
  return (
    <Badge variant={config.variant}>
      <span
        className={cn("h-1.5 w-1.5 rounded-full", dotColor[status], config.pulse && "animate-pulse")}
      />
      {config.label}
    </Badge>
  );
}

const riskConfig: Record<RiskLevel, { label: string; variant: "green" | "amber" | "red" }> = {
  low: { label: "Low risk", variant: "green" },
  medium: { label: "Medium risk", variant: "amber" },
  high: { label: "High risk", variant: "red" },
};

export function RiskBadge({ risk }: { risk: RiskLevel | null }) {
  if (!risk) return null;
  const config = riskConfig[risk];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
