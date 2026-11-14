import { getLang, t } from "./i18n";

export class ApiError extends Error {
  status: number;
  code: string;
  data: any;
  constructor(status: number, code: string, message: string, data?: any) {
    super(message);
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

type Opts = { method?: string; body?: any; form?: FormData; signal?: AbortSignal };

export async function api<T = any>(path: string, opts: Opts = {}): Promise<T> {
  const headers: Record<string, string> = { "x-rimetra": "1", "x-rimetra-lang": getLang() };
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["content-type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, {
    method: opts.method ?? (body ? "POST" : "GET"),
    headers,
    body,
    credentials: "same-origin",
    signal: opts.signal,
  });
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) {
    const err = (data && (data as any).error) || {};
    if (res.status === 401 && !path.startsWith("/api/auth/")) {
      window.dispatchEvent(new Event("rimetra:unauthorized"));
    }
    throw new ApiError(res.status, err.code || "HTTP_ERROR", err.message || t("Hata ({status})", { status: res.status }), err);
  }
  return data as T;
}

// ---------------------------------------------------------------- tipler

export type Flag = "normal" | "high" | "low" | "abnormal" | "unknown";

export interface Member {
  id: string;
  display_name: string;
  full_name: string | null;
  sex: "M" | "F" | null;
  birth_year: number | null;
  avatar_color: string | null;
  has_avatar: boolean;
  avatar_version: string | null;
  sort_order: number;
  has_login: boolean;
}

export interface Me {
  id: string;
  username: string;
  role: "master" | "member";
  read_only: boolean;
  theme: string | null;
  lang?: string | null;
  member_id: string | null;
  member: Member | null;
  telegram?: { linked: boolean; username: string | null; linked_at: string | null; notify: boolean };
}

export interface ReportHeader {
  id: string;
  member_id: string;
  report_date: string;
  facility: string | null;
  source: string;
  has_pdf: boolean;
  created_at: string;
  deleted_at: string | null;
  panel_count: number;
  result_count: number;
  out_of_range: number;
  panel_names: string[];
}

export interface ResultRow {
  id: string;
  report_id: string;
  raw_name: string;
  test_key: string | null;
  display_name: string;
  category: string | null;
  specimen: string | null;
  value_numeric: number | null;
  value_text: string | null;
  value_qualifier: string | null;
  positive_degree: number | null;
  raw_value: string | null;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  ref_low_exclusive: boolean;
  ref_high_exclusive: boolean;
  ref_text: string | null;
  ref_note: string | null;
  flag_computed: Flag;
  flag_source: "ok" | "alert" | null;
  flag_mismatch: boolean;
  sample_datetime: string | null;
  report_date?: string;
  facility?: string | null;
  source?: string;
}

export interface SummaryItem {
  test_key: string;
  display_name: string;
  category: string;
  specimen: string;
  value_type: "numeric" | "qualitative" | "text";
  latest: ResultRow;
  previous_value: number | null;
  change_pct: number | null;
  sparkline: { t: string; v: number }[];
  count: number;
  consecutive_out: boolean;
}

export interface Summary {
  member_id: string;
  last_report_date: string | null;
  total_tests: number;
  out_of_range: number;
  report_count: number;
  unmapped_count: number;
  items: SummaryItem[];
}

export interface DashboardMember extends Member {
  last_report_date: string | null;
  last_report_out_of_range: number;
  recent_reports: ReportHeader[];
  reminders_due: number;
}

export interface Note {
  id: string;
  member_id: string;
  date: string;
  text: string;
  test_definition_id: string | null;
  test_key?: string | null;
  test_name?: string | null;
  can_delete?: boolean;
}

export interface TestDef {
  id: string;
  key: string;
  display_name: string;
  specimen: string;
  category: string;
  canonical_unit: string | null;
  value_type: string;
  unit_rules: any;
  is_builtin: boolean;
  aliases?: string[];
  info_what?: string | null;
  info_low?: string | null;
  info_high?: string | null;
  display_name_raw?: string;
  unit_label?: string | null;
  info_what_raw?: string | null;
  info_low_raw?: string | null;
  info_high_raw?: string | null;
}

/** İndirme bağlantıları (CSV/PDF) özel başlık taşıyamadığı için dili adrese ekler. */
export const withLang = (url: string) => `${url}${url.includes("?") ? "&" : "?"}lang=${getLang()}`;

export const avatarUrl = (m: { id: string; avatar_version: string | null }) =>
  `/api/app/members/${m.id}/avatar?v=${m.avatar_version ?? ""}`;
