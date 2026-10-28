"use client";

import { useEffect, useState } from "react";

// Công tắc Thật/Giả lập và dải cảnh báo trên mọi trang (spec synthetic-data mục 2.3–2.4, 4).
type ScenarioPreset = { name: string; title: string; seed: number };

type DataMode = {
  mode: "real" | "synthetic";
  scenario: string | null;
  seed: number | null;
  scenarios: ScenarioPreset[];
};

const COOKIE = "macro_data";

export function DataModeBar() {
  const [mode, setMode] = useState<DataMode | null>(null);
  const [open, setOpen] = useState(false);
  const [scenario, setScenario] = useState("");
  const [seed, setSeed] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/data-mode")
      .then((res) => res.json() as Promise<DataMode>)
      .then((data) => {
        setMode(data);
        const current =
          data.scenarios.find((s) => s.name === data.scenario) ??
          data.scenarios.find((s) => s.name === "baseline") ??
          data.scenarios[0];
        if (current) {
          setScenario(current.name);
          setSeed(String(data.seed ?? current.seed));
        }
      })
      .catch((err: unknown) => setError(String(err)));
  }, []);

  function chooseReal() {
    setOpen(false);
    // Theo cookie chứ không theo trạng thái đã tải: bấm sớm vẫn về đúng số thật.
    if (synthetic || document.cookie.includes(`${COOKIE}=synthetic`)) {
      document.cookie = `${COOKIE}=real; path=/; samesite=lax`;
      window.location.reload();
    }
  }

  function load() {
    setLoading(true);
    setError(null);
    const body: { scenario: string; seed?: number } = { scenario };
    if (seed.trim() !== "") body.seed = Number(seed);
    fetch("/api/synthetic/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        if (!res.ok) {
          const detail = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(detail?.detail ?? `API trả về ${res.status}`);
        }
        window.location.reload();
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      });
  }

  const synthetic = mode?.mode === "synthetic";

  return (
    <>
      {synthetic && (
        <div
          className="synthetic-banner"
          data-testid="synthetic-banner"
          data-scenario={mode.scenario ?? ""}
          data-seed={String(mode.seed ?? "")}
          role="status"
        >
          DỮ LIỆU GIẢ LẬP — kịch bản {mode.scenario}, seed {mode.seed}. Không phải số liệu thật.
        </div>
      )}
      <div className="data-mode" data-testid="data-mode-switch">
        <span>Dữ liệu:</span>{" "}
        <button
          type="button"
          data-testid="mode-real"
          aria-pressed={!synthetic}
          disabled={mode === null}
          onClick={chooseReal}
        >
          Thật
        </button>
        <button
          type="button"
          data-testid="mode-synthetic"
          aria-pressed={synthetic}
          disabled={mode === null}
          onClick={() => setOpen(true)}
        >
          Giả lập
        </button>
        {open && mode && (
          <span className="data-mode-form">
            <label>
              Kịch bản{" "}
              <select
                data-testid="scenario-select"
                value={scenario}
                onChange={(event) => {
                  setScenario(event.target.value);
                  const preset = mode.scenarios.find((s) => s.name === event.target.value);
                  if (preset) setSeed(String(preset.seed));
                }}
              >
                {mode.scenarios.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.title}
                  </option>
                ))}
              </select>
            </label>{" "}
            <label>
              Seed{" "}
              <input
                data-testid="seed-input"
                inputMode="numeric"
                size={5}
                value={seed}
                onChange={(event) => setSeed(event.target.value)}
              />
            </label>{" "}
            <button type="button" data-testid="load-synthetic" disabled={loading} onClick={load}>
              Nạp
            </button>
            {loading && (
              <span className="muted" data-testid="synthetic-loading">
                {" "}
                Đang nạp dữ liệu giả lập…
              </span>
            )}
          </span>
        )}
        {error && (
          <span role="alert" className="data-mode-error">
            {" "}
            {error}
          </span>
        )}
      </div>
    </>
  );
}
