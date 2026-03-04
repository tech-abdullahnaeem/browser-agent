/* ── StatusBadge — Task status indicator ── */

import type { TaskStatus } from "@/types/task";

interface StatusBadgeProps {
  status: TaskStatus;
  className?: string;
}

const statusConfig: Record<TaskStatus, { label: string; classes: string }> = {
  pending: {
    label: "Pending",
    classes: "bg-warning/10 text-warning border-warning/30",
  },
  running: {
    label: "Running",
    classes: "bg-brand-500/10 text-brand-400 border-brand-500/30",
  },
  completed: {
    label: "Completed",
    classes: "bg-success/10 text-success border-success/30",
  },
  failed: {
    label: "Failed",
    classes: "bg-error/10 text-error border-error/30",
  },
  cancelled: {
    label: "Cancelled",
    classes: "bg-text-muted/10 text-text-muted border-text-muted/30",
  },
};

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  const config = statusConfig[status];
  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2 py-0.5
        text-xs font-medium rounded-full border
        ${config.classes} ${className}
      `}
    >
      {status === "running" && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500" />
        </span>
      )}
      {config.label}
    </span>
  );
}
