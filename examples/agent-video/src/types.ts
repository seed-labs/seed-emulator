export interface TimelineSegment {
  id: string;
  duration_sec: number;
  start_sec: number;
  end_sec: number;
  zh: string;
  en: string;
}

export interface RuntimeSnapshot {
  generated_at_utc?: string;
  source?: string;
  task_id?: string;
  objective?: string;
  session_id?: string;
  begin_status?: string | null;
  execute_status?: string;
  task_status?: string | null;
  job_id?: string;
  job_status?: string;
  planner_mode?: string;
  risk_gate_status?: string;
  notes?: string[];
}

export interface ArchRef {
  layer: string;
  owner: string;
  key_points: string[];
  refs: string[];
}
