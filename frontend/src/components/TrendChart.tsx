import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Note, ResultRow } from "../lib/api";
import { locale, t } from "../lib/i18n";
import { FLAG_LABEL, fmtDate, fmtNum, isOut, refText, valueText } from "../lib/format";

const tickFmt = (tx: number) => {
  const d = new Date(tx);
  return `${d.toLocaleDateString(locale(), { month: "short" }).replace(".", "")} ${d.getFullYear()}`;
};

export function TrendChart({
  measurements, notes = [], height = 300, compact,
}: { measurements: ResultRow[]; notes?: Note[]; height?: number; compact?: boolean }) {
  const pts = measurements.filter((m) => m.value_numeric !== null && m.sample_datetime);
  if (!pts.length) return null;
  const vals = pts.map((p) => p.value_numeric as number);
  const bounds = pts.flatMap((p) => [p.ref_low, p.ref_high]).filter((x): x is number => x !== null);
  let yMin = Math.min(...vals, ...bounds);
  let yMax = Math.max(...vals, ...bounds);
  const pad = (yMax - yMin) * 0.18 || Math.abs(yMax) * 0.2 || 1;
  yMin = yMin >= 0 ? Math.max(0, yMin - pad) : yMin - pad;
  yMax = yMax + pad;
  // yuvarlak eksen değerleri
  const rawStep = (yMax - yMin) / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((x) => x >= rawStep) ?? rawStep;
  yMin = Math.floor(yMin / step) * step;
  yMax = Math.ceil(yMax / step) * step;
  const ticks: number[] = [];
  for (let v = yMin; v <= yMax + step / 2; v += step) ticks.push(+v.toFixed(10));

  const data = pts.map((p, i) => {
    const tx = new Date(p.sample_datetime!).getTime();
    const hasBand = p.ref_low !== null || p.ref_high !== null;
    return {
      t: tx,
      v: p.value_numeric,
      band: hasBand ? [p.ref_low ?? yMin, p.ref_high ?? yMax] : null,
      r: p,
      last: i === pts.length - 1,
    };
  });
  let tMin = data[0].t;
  let tMax = data[data.length - 1].t;
  if (tMin === tMax) {
    tMin -= 86400000 * 45;
    tMax += 86400000 * 45;
  }
  const span = tMax - tMin;
  const xDomain = [tMin - span * 0.04, tMax + span * 0.06];
  const noteMarks = notes
    .map((n) => ({ ...n, t: new Date(n.date + "T12:00:00").getTime() }))
    .filter((n) => n.t >= xDomain[0] && n.t <= xDomain[1]);
  // bant noktaları: değişen aralıkları basamak olarak göster; uçlara uzat
  const bandData = data.filter((d) => d.band);
  const series = [
    ...(bandData.length ? [{ t: xDomain[0], band: bandData[0].band, v: null as number | null, edge: true }] : []),
    ...data,
    ...(bandData.length ? [{ t: xDomain[1], band: bandData[bandData.length - 1].band, v: null as number | null, edge: true }] : []),
  ];

  const Dot = (props: any) => {
    const { cx, cy, payload } = props;
    if (payload.v === null || payload.v === undefined || cx === undefined) return <g key={props.index} />;
    const out = isOut(payload.r.flag_computed);
    const color = payload.r.flag_computed === "low" ? "rgb(var(--warn))" : out ? "rgb(var(--bad))" : "rgb(var(--chart-line))";
    return (
      <g key={props.index}>
        {payload.last && !compact && (
          <g>
            <rect x={cx - 20} y={cy - 36} width={40} height={22} rx={6} fill={out ? "rgb(var(--bad))" : "rgb(var(--chart-line))"} />
            <text x={cx} y={cy - 21} textAnchor="middle" fontSize={12} fontWeight={700} fill="white">{fmtNum(payload.v)}</text>
          </g>
        )}
        <circle cx={cx} cy={cy} r={payload.last ? 6 : 5} fill={out ? color : "rgb(var(--chart-line))"} stroke="rgb(var(--surface))" strokeWidth={2} />
        {payload.last && <circle cx={cx} cy={cy} r={9} fill="none" stroke={color} strokeOpacity={0.35} strokeWidth={2} />}
      </g>
    );
  };

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={series} margin={{ top: compact ? 24 : 40, right: 18, bottom: 4, left: -8 }}>
          <CartesianGrid vertical horizontal strokeDasharray="4 4" />
          <XAxis dataKey="t" type="number" scale="time" domain={xDomain} tickFormatter={tickFmt} tickLine={false}
            axisLine={{ stroke: "rgb(var(--line))" }} minTickGap={36} />
          <YAxis domain={[yMin, yMax]} ticks={ticks} tickFormatter={(v) => fmtNum(v, 2)} tickLine={false} axisLine={false} width={48} />
          <Area dataKey="band" type="stepAfter" stroke="none" fill="rgb(var(--chart-band))" fillOpacity={0.75}
            isAnimationActive={false} connectNulls activeDot={false} />
          {noteMarks.map((n) => (
            <ReferenceLine key={n.id} x={n.t} stroke="rgb(var(--ink))" strokeOpacity={0.55} strokeDasharray="5 4"
              label={(props: any) => {
                const { viewBox } = props;
                const text = n.text.length > 22 ? n.text.slice(0, 21) + "…" : n.text;
                const w = text.length * 6.6 + 18;
                return (
                  <g>
                    <rect x={viewBox.x - w / 2} y={viewBox.y - (compact ? 22 : 36)} width={w} height={22} rx={6} fill="rgb(var(--surface2))" stroke="rgb(var(--line))" />
                    <text x={viewBox.x} y={viewBox.y - (compact ? 7 : 21)} textAnchor="middle" fontSize={11.5} fill="rgb(var(--ink))">{text}</text>
                  </g>
                );
              }} />
          ))}
          <Line dataKey="v" type="monotone" stroke="rgb(var(--chart-line))" strokeWidth={2.5} dot={<Dot />}
            activeDot={false} connectNulls isAnimationActive={false} />
          <Tooltip
            cursor={{ stroke: "rgb(var(--line))" }}
            content={({ active, payload }: any) => {
              const p = payload?.find((x: any) => x.payload?.r)?.payload;
              if (!active || !p?.r) return null;
              const r: ResultRow = p.r;
              return (
                <div className="card px-3 py-2 text-xs">
                  <div className="font-bold">{fmtDate(r.sample_datetime)}</div>
                  <div>{valueText(r)} {r.unit ?? ""} · <span className={isOut(r.flag_computed) ? "text-bad" : "text-ok"}>{FLAG_LABEL[r.flag_computed]}</span></div>
                  <div className="text-muted">{t("Referans:")}{" "}{refText(r)}</div>
                  {r.facility && <div className="max-w-[240px] truncate text-muted">{r.facility}</div>}
                </div>
              );
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Nitel testler için renkli zaman şeridi. */
export function QualStrip({ measurements, compact }: { measurements: ResultRow[]; compact?: boolean }) {
  const items = compact ? measurements.slice(-6) : measurements;
  return (
    <div className={`flex ${compact ? "gap-1" : "gap-2"} overflow-x-auto pb-1`}>
      {items.map((m) => {
        const out = isOut(m.flag_computed);
        const cls = out ? "bg-badbg text-bad border-bad/30" : m.flag_computed === "normal" ? "bg-okbg text-ok border-ok/20" : "bg-surface2 text-muted border-line";
        const deg = m.positive_degree ?? 0;
        return (
          <div key={m.id} className={`flex shrink-0 flex-col rounded-xl border ${cls} ${compact ? "min-w-[44px] px-1.5 py-1" : "min-w-[112px] px-3 py-2"}`}
            title={`${fmtDate(m.sample_datetime)} · ${valueText(m)}`}>
            {!compact && <span className="text-[11px] font-semibold opacity-80">{fmtDate(m.sample_datetime)}</span>}
            <span className={`font-bold ${compact ? "text-[10px] leading-tight" : "text-sm"}`}>
              {compact ? (deg ? "+".repeat(Math.min(deg, 4)) : out ? "!" : "✓") : valueText(m)}
            </span>
            {!compact && deg > 0 && (
              <span className="mt-1 flex gap-0.5">{Array.from({ length: 4 }).map((_, i) => (
                <span key={i} className={`h-1.5 w-4 rounded-full ${i < deg ? "bg-bad" : "bg-bad/15"}`} />
              ))}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
