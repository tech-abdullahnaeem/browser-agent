/* ── useTaskApi — React hook wrapping REST API calls ── */

import { useCallback, useState } from "react";
import {
  submitTask,
  getTasks,
  getTask,
  cancelTask,
} from "@/lib/api";
import type { TaskCreateResponse, TaskResult, TaskListResponse } from "@/types/task";

interface UseTaskApiReturn {
  loading: boolean;
  error: string | null;
  submit: (task: string, context?: string) => Promise<TaskCreateResponse>;
  fetchTasks: (limit?: number, offset?: number) => Promise<TaskListResponse>;
  fetchTask: (taskId: string) => Promise<TaskResult>;
  cancel: (taskId: string) => Promise<void>;
}

export function useTaskApi(): UseTaskApiReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wrap = useCallback(
    async <T>(fn: () => Promise<T>): Promise<T> => {
      setLoading(true);
      setError(null);
      try {
        return await fn();
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const submit = useCallback(
    (task: string, context?: string) =>
      wrap(() => submitTask({ task, context })),
    [wrap],
  );

  const fetchTasks = useCallback(
    (limit?: number, offset?: number) =>
      wrap(() => getTasks(limit, offset)),
    [wrap],
  );

  const fetchTask = useCallback(
    (taskId: string) => wrap(() => getTask(taskId)),
    [wrap],
  );

  const cancel = useCallback(
    (taskId: string) => wrap(() => cancelTask(taskId)),
    [wrap],
  );

  return { loading, error, submit, fetchTasks, fetchTask, cancel };
}
