"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

// Kết quả của /api/backtest; mọi số đã được tính và định dạng ở backend (ADR-001).
type Episode = {
  cut: string;
  label: string;
  actual: number;
  predicted: number;
  error: number;
  text: string;
};

type OutcomeBacktest = {
  series_id: string;
  name: string;
  unit: string;
  insufficient_text: string | null;
  verdict: string | null;
  mae_model: number | null;
  mae_naive: number | null;
  ratio: number | null;
  hit_rate: number | null;
  summary_text: string | null;
  episodes: Episode[];
};

type BacktestResult = {
  missing_shocks: string[];
  note: string;
  outcomes: OutcomeBacktest[];
};

export default function BacktestPage() {
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/backtest")
      .then((res) => {
        if (!res.ok) throw new Error(`API trả về ${res.status}`);
        return res.json() as Promise<BacktestResult>;
      })
      .then(setResult)
      .catch((err: unknown) => setError(String(err)));
  }, []);

  return (
    <main>
      <p>
        <Link href="/">← Tổng quan vĩ mô</Link> · <Link href="/kich-ban/">Giả lập kịch bản</Link>
      </p>
      <h1>Kiểm chứng lịch sử</h1>
      <p className="disclaimer">
        Mỗi mốc tháng 12: mô hình chỉ học dữ liệu tới mốc đó, nhận các cú sốc thật của 12 tháng
        sau và đoán thay đổi; so với thực tế và với đoán &quot;không đổi&quot;.
      </p>
      {!result && !error && <p>Đang tính…</p>}
      {error && <p role="alert">Không tính được: {error}</p>}
      {result && (
        <>
          <p className="disclaimer">{result.note}</p>
          {result.missing_shocks.length > 0 && (
            <p className="insufficient" data-testid="missing-shocks">
              Cú sốc thiếu dữ liệu: {result.missing_shocks.join(", ")}
            </p>
          )}
          {result.outcomes.map((outcome) => (
            <section
              key={outcome.series_id}
              className="outcome"
              data-testid={`backtest-${outcome.series_id}`}
            >
              <h2>{outcome.name}</h2>
              {outcome.insufficient_text ? (
                <p className="insufficient" data-testid="insufficient">
                  {outcome.insufficient_text}
                </p>
              ) : (
                <>
                  <p data-testid="verdict">
                    <strong>{outcome.verdict}</strong>
                  </p>
                  <p
                    className="sample"
                    data-testid="summary"
                    data-mae-model={String(outcome.mae_model)}
                    data-mae-naive={String(outcome.mae_naive)}
                    data-ratio={String(outcome.ratio)}
                    data-hit-rate={String(outcome.hit_rate)}
                    data-episodes={String(outcome.episodes.length)}
                  >
                    {outcome.summary_text}
                  </p>
                  <table>
                    <tbody>
                      {outcome.episodes.map((episode) => (
                        <tr
                          key={episode.cut}
                          data-testid={`episode-${episode.cut}`}
                          data-actual={String(episode.actual)}
                          data-predicted={String(episode.predicted)}
                        >
                          <td>{episode.label}</td>
                          <td>{episode.text}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </section>
          ))}
        </>
      )}
    </main>
  );
}
