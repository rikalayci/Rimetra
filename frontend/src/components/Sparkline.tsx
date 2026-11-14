import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts";
import { t } from "../lib/i18n";
import type { Flag } from "../lib/api";

export function Sparkline({
  points, flag, height = 48,
}: { points: { t: string; v: number }[]; flag: Flag; height?: number }) {
  if (points.length < 2) {
    return <div style={{ height }} className="flex items-center text-xs text-muted">{points.length === 1 ? t("Tek ölçüm") : ""}</div>;
  }
  const color = flag === "low" ? "rgb(var(--warn))" : flag === "high" || flag === "abnormal" ? "rgb(var(--bad))" : "rgb(var(--chart-line))";
  const id = `sp-${Math.random().toString(36).slice(2, 8)}`;
  const data = points.map((p, i) => ({ i, v: p.v, last: i === points.length - 1 }));
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 6, right: 6, bottom: 2, left: 6 }}>
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgb(var(--chart-line))" stopOpacity={0.18} />
              <stop offset="100%" stopColor="rgb(var(--chart-line))" stopOpacity={0} />
            </linearGradient>
          </defs>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Area
            type="linear"
            dataKey="v"
            stroke="rgb(var(--chart-line))"
            strokeWidth={2}
            fill={`url(#${id})`}
            isAnimationActive={false}
            dot={(props: any) => (
              <circle
                key={props.index}
                cx={props.cx}
                cy={props.cy}
                r={props.payload.last ? 4 : 3}
                fill={props.payload.last ? color : "rgb(var(--chart-line))"}
                stroke="rgb(var(--surface))"
                strokeWidth={1.5}
              />
            )}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
