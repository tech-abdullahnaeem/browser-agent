/* ── TaskList — Task history list in the sidepanel ── */

import { useEffect, useState } from "react";
import { getTasks } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";
import { Spinner } from "@/components/Spinner";
import type { TaskSummary } from "@/types/task";

interface TaskListProps {
  onSelect: (taskId: string) => void;
  refreshTrigger?: number;
}

export function TaskList({ onSelect, refreshTrigger }: TaskListProps) {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getTasks(50, 0)
      .then((data) => {
        if (!cancelled) {
          setTasks(data.tasks);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshTrigger]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-6 text-center">
        <p className="text-error text-sm mb-2">Failed to load tasks</p>
        <p className="text-text-muted text-xs">{error}</p>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-text-muted text-sm">No tasks yet</p>
        <p className="text-text-muted text-xs mt-1">
          Press ⌘K to create your first task
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {tasks.map((task) => (
        <button
          key={task.task_id}
          onClick={() => onSelect(task.task_id)}
          className="
            w-full px-4 py-3 text-left
            hover:bg-surface-lighter transition-colors
          "
        >
          <div className="flex items-start gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-primary truncate">{task.task}</p>
              {task.final_result && (
                <p className="text-xs text-text-secondary mt-1 line-clamp-2">
                  {task.final_result}
                </p>
              )}
              {task.error && (
                <p className="text-xs text-error mt-1 truncate">
                  {task.error}
                </p>
              )}
            </div>
            <StatusBadge status={task.status} />
          </div>
          <div className="flex items-center gap-3 mt-1.5">
            <span className="text-xs text-text-muted">
              {task.total_steps} step{task.total_steps !== 1 ? "s" : ""}
            </span>
            {task.duration_seconds != null && (
              <span className="text-xs text-text-muted">
                {task.duration_seconds.toFixed(1)}s
              </span>
            )}
            <span className="text-xs text-text-muted ml-auto">
              {new Date(task.created_at).toLocaleTimeString()}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
