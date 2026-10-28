"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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

// /api/scenario/shocks: các yếu tố dùng được trên dữ liệu đang xem (spec synthetic-data mục 2.2).
type ShockOption = { id: string; name: string; unit: string; default_size: number; scope: string };
type ShockList = { shocks: ShockOption[]; no_real_data: string[] };

const sizeText = (value: number) => String(value);

export default function ScenarioPage() {
  const [shocks, setShocks] = useState<ShockList | null>(null);
  const [shock, setShock] = useState("");
  const [size, setSize] = useState("");
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/scenario/shocks")
      .then((res) => {
        if (!res.ok) throw new Error(`API trả về ${res.status}`);
        return res.json() as Promise<ShockList>;
      })
      .then((list) => {
        setShocks(list);
        if (list.shocks.length > 0) {
          setShock(list.shocks[0].id);
          setSize(sizeText(list.shocks[0].default_size));
        }
      })
      .catch((err: unknown) => setError(String(err)));
  }, []);

  const options = shocks?.shocks ?? [];
  const unit = options.find((s) => s.id === shock)?.unit ?? "";

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
        <Link href="/kiem-chung/">Kiểm chứng lịch sử</Link> ·{" "}
        <Link href="/anh-huong/">Bản đồ ảnh hưởng</Link>
      </p>
      <h1>Giả lập kịch bản</h1>
      <p className="disclaimer" data-testid="disclaimer">
        Suy luận theo kịch bản từ quan hệ lịch sử (local projections, khoảng tin cậy 90%),
        không phải dự báo.
      </p>

      {shocks && shocks.no_real_data.length > 0 && (
        <p className="no-real-data" data-testid="no-real-data">
          Chưa có dữ liệu thật: {shocks.no_real_data.join(", ")}.
        </p>
      )}

      {shocks && (
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
              const picked = options.find((s) => s.id === event.target.value);
              setSize(picked ? sizeText(picked.default_size) : "");
            }}
          >
            {options.map((s) => (
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
      )}

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
