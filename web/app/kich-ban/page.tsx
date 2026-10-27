"use client";

import Link from "next/link";
import { useState } from "react";

// Kết quả của /api/scenario; mọi số đã được tính và định dạng ở backend (ADR-001).
type Horizon = {
  h: number;
  estimate: number;
  lower: number;
  upper: number;
  n: number;
  includes_zero: boolean;
  text: string;
};

type OutcomeResult = {
  series_id: string;
  name: string;
  unit: string;
  sample_text: string | null;
  insufficient_text: string | null;
  horizons: Horizon[];
};

type ScenarioResult = {
  shock: string;
  shock_name: string;
  size: number;
  unit: string;
  outcomes: OutcomeResult[];
};

const SHOCKS = [
  { id: "global.brent", name: "Giá dầu Brent", unit: "%", size: "20" },
  { id: "us.ust10y", name: "Lợi suất trái phiếu Mỹ 10 năm", unit: "điểm %", size: "0.5" },
  { id: "us.usd_broad", name: "Chỉ số USD rộng (Fed)", unit: "%", size: "5" },
];

export default function ScenarioPage() {
  const [shock, setShock] = useState(SHOCKS[0].id);
  const [size, setSize] = useState(SHOCKS[0].size);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const unit = SHOCKS.find((s) => s.id === shock)?.unit ?? "";

  function run() {
    setLoading(true);
    setError(null);
    const value = size.replace(",", ".");
    fetch(`/api/scenario?shock=${encodeURIComponent(shock)}&size=${encodeURIComponent(value)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`API trả về ${res.status}`);
        return res.json() as Promise<ScenarioResult>;
      })
      .then(setResult)
      .catch((err: unknown) => setError(String(err)))
      .finally(() => setLoading(false));
  }

  return (
    <main>
      <p>
        <Link href="/">← Tổng quan vĩ mô</Link> ·{" "}
        <Link href="/kiem-chung/">Kiểm chứng lịch sử</Link>
      </p>
      <h1>Giả lập kịch bản</h1>
      <p className="disclaimer" data-testid="disclaimer">
        Suy luận theo kịch bản từ quan hệ lịch sử (local projections, khoảng tin cậy 90%),
        không phải dự báo.
      </p>

      <form
        className="scenario-form"
        onSubmit={(event) => {
          event.preventDefault();
          run();
        }}
      >
        <label>
          Cú sốc{" "}
          <select
            data-testid="shock"
            value={shock}
            onChange={(event) => {
              setShock(event.target.value);
              setSize(SHOCKS.find((s) => s.id === event.target.value)?.size ?? "");
            }}
          >
            {SHOCKS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>{" "}
        <label>
          Độ lớn{" "}
          <input
            data-testid="shock-size"
            inputMode="decimal"
            value={size}
            onChange={(event) => setSize(event.target.value)}
            size={6}
          />{" "}
          {unit}
        </label>{" "}
        <button data-testid="run" type="submit" disabled={loading}>
          Giả lập
        </button>
      </form>

      {error && <p role="alert">Không giả lập được: {error}</p>}

      {result &&
        result.outcomes.map((outcome) => (
          <section
            key={outcome.series_id}
            className="outcome"
            data-testid={`response-${outcome.series_id}`}
          >
            <h2>{outcome.name}</h2>
            {outcome.insufficient_text ? (
              <p className="insufficient" data-testid="insufficient">
                {outcome.insufficient_text}
              </p>
            ) : (
              <>
                <p className="sample" data-testid="sample">
                  {outcome.sample_text}
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Tháng</th>
                      <th>Phản ứng [khoảng tin cậy 90%]</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {outcome.horizons.map((row) => (
                      <tr
                        key={row.h}
                        data-testid={`h-${row.h}`}
                        data-estimate={String(row.estimate)}
                        data-lower={String(row.lower)}
                        data-upper={String(row.upper)}
                        data-n={String(row.n)}
                      >
                        <td>{row.h}</td>
                        <td>{row.text}</td>
                        <td>
                          {row.includes_zero && (
                            <span className="zero" data-testid="zero">
                              không phân biệt được với 0
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </section>
        ))}
    </main>
  );
}
