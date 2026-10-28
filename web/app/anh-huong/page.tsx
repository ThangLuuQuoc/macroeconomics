"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

// /api/influence: mọi số đã được tính và định dạng ở backend (ADR-001; spec influence-map).
type Effect = "up" | "down" | "uncertain" | "missing";

type Bubble = {
  series_id: string;
  name: string;
  short_name: string;
  unit: string;
  scope: "global" | "domestic";
  default_size: number;
  effect: Effect;
  effect_text: string;
  shock_change: number | null;
  shock_change_text: string;
  contribution: number | null;
  contribution_text: string;
  beta_text: string;
  radius: number;
  link: number;
};

type InfluenceResult = {
  center: string;
  center_name: string;
  unit: string;
  centers: { series_id: string; name: string }[];
  month: string | null;
  months: string[];
  level: number | null;
  level_text: string;
  change: number | null;
  change_text: string;
  insufficient_text: string | null;
  bubbles: Bubble[];
  ranking: string[];
  no_real_data: string[];
  not_additive: string;
  lookback: string;
};

type Horizon = { h: number; estimate: number; lower: number; upper: number; text: string };
type ScenarioResult = {
  size: number;
  outcomes: { series_id: string; insufficient_text: string | null; horizons: Horizon[] }[];
};

// Bố cục hướng tâm cố định: ngoài nước nửa trên, trong nước nửa dưới, theo thứ tự danh mục.
const RING = 190;
const CENTER_R = 62;

function positions(bubbles: Bubble[]): Map<string, { x: number; y: number }> {
  const place = new Map<string, { x: number; y: number }>();
  const arc = (items: Bubble[], from: number, to: number) => {
    items.forEach((b, i) => {
      const t = items.length === 1 ? 0.5 : i / (items.length - 1);
      const angle = ((from + (to - from) * t) * Math.PI) / 180;
      place.set(b.series_id, { x: RING * Math.cos(angle), y: -RING * Math.sin(angle) });
    });
  };
  arc(
    bubbles.filter((b) => b.scope === "global"),
    160,
    20,
  );
  arc(
    bubbles.filter((b) => b.scope === "domestic"),
    -160,
    -20,
  );
  return place;
}

const monthLabel = (key: string) => `${key.slice(5)}/${key.slice(0, 4)}`;

function SimulatePanel({ bubble, result }: { bubble: Bubble; result: InfluenceResult }) {
  const [size, setSize] = useState(String(bubble.default_size));
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const value = Number(size.replace(",", "."));
    if (!Number.isFinite(value)) return;
    const timer = setTimeout(() => {
      fetch(
        `/api/scenario?shock=${encodeURIComponent(bubble.series_id)}&size=${encodeURIComponent(value)}`,
      )
        .then((res) => {
          if (!res.ok) throw new Error(`API trả về ${res.status}`);
          return res.json() as Promise<ScenarioResult>;
        })
        .then((data) => {
          setScenario(data);
          setError(null);
        })
        .catch((err: unknown) => setError(String(err)));
    }, 200);
    return () => clearTimeout(timer);
  }, [bubble.series_id, size]);

  const outcome = scenario?.outcomes.find((o) => o.series_id === result.center);
  const h12 = outcome?.horizons.find((h) => h.h === 12);

  return (
    <section className="simulate" data-testid={`simulate-${bubble.series_id}`}>
      <h2>Giả lập: {bubble.name}</h2>
      <label>
        Độ lớn cú sốc{" "}
        <input
          data-testid="shock-size"
          inputMode="decimal"
          size={6}
          value={size}
          onChange={(event) => setSize(event.target.value)}
        />{" "}
        {bubble.unit}
      </label>
      {error && <p role="alert">Không giả lập được: {error}</p>}
      {scenario && outcome && (
        <p
          data-testid="simulated-response"
          data-size={String(scenario.size)}
          data-estimate={h12 ? String(h12.estimate) : ""}
          data-lower={h12 ? String(h12.lower) : ""}
          data-upper={h12 ? String(h12.upper) : ""}
        >
          {h12
            ? `${result.center_name} sau 12 tháng: ${h12.text}`
            : (outcome.insufficient_text ?? "Chưa đủ dữ liệu ở tầm 12 tháng.")}
        </p>
      )}
    </section>
  );
}

export default function InfluencePage() {
  const [center, setCenter] = useState<string | null>(null);
  const [month, setMonth] = useState<string | null>(null);
  const [result, setResult] = useState<InfluenceResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (center) params.set("center", center);
    if (month) params.set("month", month);
    fetch(`/api/influence?${params.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error(`API trả về ${res.status}`);
        return res.json() as Promise<InfluenceResult>;
      })
      .then((data) => {
        setResult(data);
        setError(null);
      })
      .catch((err: unknown) => setError(String(err)));
  }, [center, month]);

  const place = result ? positions(result.bubbles) : new Map();
  const picked = result?.bubbles.find((b) => b.series_id === selected && b.effect !== "missing");
  const byId = new Map(result?.bubbles.map((b) => [b.series_id, b]) ?? []);
  const largest = Math.max(1e-9, ...(result?.bubbles.map((b) => Math.abs(b.contribution ?? 0)) ?? []));

  return (
    <main>
      <p>
        <Link href="/">← Tổng quan vĩ mô</Link> · <Link href="/kich-ban/">Giả lập kịch bản</Link>{" "}
        · <Link href="/kiem-chung/">Kiểm chứng lịch sử</Link>
      </p>
      <h1>Bản đồ ảnh hưởng</h1>
      {error && <p role="alert">Không tải được: {error}</p>}
      {!result && !error && <p>Đang tính…</p>}
      {result && (
        <>
          <div className="influence-controls">
            <label>
              Trung tâm{" "}
              <select
                data-testid="center-select"
                value={result.center}
                onChange={(event) => {
                  setSelected(null);
                  setCenter(event.target.value);
                }}
              >
                {result.centers.map((c) => (
                  <option key={c.series_id} value={c.series_id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>{" "}
            {result.months.length > 0 && (
              <label>
                Tháng{" "}
                <select
                  data-testid="month-select"
                  value={result.month ?? ""}
                  onChange={(event) => setMonth(event.target.value)}
                >
                  {result.months
                    .slice()
                    .reverse()
                    .map((m) => (
                      <option key={m} value={m}>
                        {monthLabel(m)}
                      </option>
                    ))}
                </select>
              </label>
            )}
          </div>
          <p className="disclaimer">{result.lookback}</p>
          {result.no_real_data.length > 0 && (
            <p className="no-real-data" data-testid="no-real-data">
              Chưa có dữ liệu thật: {result.no_real_data.join(", ")}.
            </p>
          )}

          <div
            data-testid="center"
            data-series={result.center}
            data-change={result.change === null ? "" : String(result.change)}
            data-level={result.level === null ? "" : String(result.level)}
            className="center-summary"
          >
            <strong>{result.center_name}</strong>
            {result.month && ` · ${monthLabel(result.month)}: ${result.level_text}`}
            {result.change_text && ` · ${result.change_text}`}
          </div>

          {result.insufficient_text ? (
            <p className="insufficient" data-testid="insufficient">
              {result.insufficient_text}
            </p>
          ) : (
            <div className="influence-layout">
              <svg
                className="influence-map"
                viewBox="-300 -265 600 530"
                role="img"
                aria-label={`Bản đồ ảnh hưởng lên ${result.center_name}`}
              >
                <text className="group-label" x={-292} y={-246}>
                  Ngoài nước
                </text>
                <text className="group-label" x={-292} y={256}>
                  Trong nước
                </text>
                {result.bubbles.map((b) => {
                  const p = place.get(b.series_id);
                  if (!p || b.effect === "missing") return null;
                  return (
                    <line
                      key={`link-${b.series_id}`}
                      className={`link effect-${b.effect}`}
                      x1={0}
                      y1={0}
                      x2={p.x}
                      y2={p.y}
                      strokeWidth={1 + 5 * b.link}
                      opacity={0.25 + 0.6 * b.link}
                    />
                  );
                })}
                <circle className="center-bubble" r={CENTER_R} />
                <text className="center-name" y={-6} textAnchor="middle">
                  {result.center_name.split(" (")[0]}
                </text>
                <text className="center-change" y={14} textAnchor="middle">
                  {result.change === null ? "" : result.change_text.split(" trong")[0]}
                </text>
                {result.bubbles.map((b) => {
                  const p = place.get(b.series_id);
                  if (!p) return null;
                  // Nửa trên: nhãn đặt phía trên bong bóng để đường nối không cắt qua chữ.
                  const labelAbove = p.y < 0;
                  return (
                    <g
                      key={b.series_id}
                      data-testid={`bubble-${b.series_id}`}
                      data-scope={b.scope}
                      data-effect={b.effect}
                      data-contribution={b.contribution === null ? "" : String(b.contribution)}
                      data-shock-change={b.shock_change === null ? "" : String(b.shock_change)}
                      data-radius={String(b.radius)}
                      className={`bubble effect-${b.effect}${selected === b.series_id ? " selected" : ""}`}
                      transform={`translate(${p.x} ${p.y})`}
                      onClick={() => setSelected(b.series_id)}
                      role="button"
                      aria-label={`${b.name}: ${b.effect_text}`}
                    >
                      <title>
                        {[b.name, b.shock_change_text, b.beta_text].filter(Boolean).join("\n")}
                      </title>
                      <circle r={b.radius} />
                      <text className="bubble-value" y={4} textAnchor="middle">
                        {b.contribution_text}
                      </text>
                      <text
                        className="bubble-name"
                        y={labelAbove ? -b.radius - 22 : b.radius + 14}
                        textAnchor="middle"
                      >
                        {b.short_name}
                      </text>
                      <text
                        className="bubble-detail"
                        y={labelAbove ? -b.radius - 8 : b.radius + 28}
                        textAnchor="middle"
                      >
                        {b.effect === "missing"
                          ? b.effect_text
                          : `${b.shock_change_text.split(" trong")[0]} · ${b.effect_text}`}
                      </text>
                    </g>
                  );
                })}
              </svg>

              <div className="influence-side">
                <p className="disclaimer" data-testid="not-additive">
                  {result.not_additive}
                </p>
                <p className="legend">
                  <span className="swatch effect-up" /> đẩy lên · <span className="swatch effect-down" />{" "}
                  kéo xuống · <span className="swatch effect-uncertain" /> chưa chắc
                </p>
                <ol className="ranking" data-testid="ranking">
                  {result.ranking.map((id) => {
                    const b = byId.get(id);
                    if (!b) return null;
                    const width = (50 * Math.abs(b.contribution ?? 0)) / largest;
                    const positive = (b.contribution ?? 0) > 0;
                    return (
                      <li key={id} data-testid={`rank-${id}`} className={`effect-${b.effect}`}>
                        <span className="rank-name">{b.short_name}</span>
                        <span className="rank-bar">
                          <span
                            className="rank-fill"
                            style={{
                              left: positive ? "50%" : `${50 - width}%`,
                              width: `${width}%`,
                            }}
                          />
                        </span>
                        <span className="rank-value">{b.contribution_text}</span>
                      </li>
                    );
                  })}
                </ol>
                {picked && <SimulatePanel key={picked.series_id} bubble={picked} result={result} />}
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}
