/* ── Task types mirroring backend Pydantic models ── */

export type TaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface TaskRequest {
  task: string;
  context?: string;
}

export interface StepSummary {
  step_number: number;
  action: string;
  element?: string | null;
  reasoning?: string | null;
  thinking?: string | null;
  success?: boolean | null;
  error?: string | null;
  timestamp: string;
}

export interface TaskResult {
  task_id: string;
  task: string;
  status: TaskStatus;
  steps: StepSummary[];
  final_result: string | null;
  error: string | null;
  duration_seconds: number | null;
  total_steps: number;
  model_used: string;
  created_at: string;
}

export interface TaskListResponse {
  tasks: TaskSummary[];
  total: number;
}

export interface TaskSummary {
  task_id: string;
  task: string;
  status: TaskStatus;
  total_steps: number;
  final_result: string | null;
  error: string | null;
  created_at: string;
  duration_seconds: number | null;
}

export interface TaskCreateResponse {
  task_id: string;
  status: TaskStatus;
}
