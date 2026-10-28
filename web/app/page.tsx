"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { IndicatorCardView } from "./IndicatorCardView";
import type { IndicatorCard } from "./types";

type State =
  | { kind: "loading" }
  | { kind: "ready"; cards: IndicatorCard[] }
  | { kind: "error"; message: string };

export default function OverviewPage() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    fetch("/api/indicators")
      .then((res) => {
        if (!res.ok) throw new Error(`API trả về ${res.status}`);
        return res.json() as Promise<IndicatorCard[]>;
      })
      .then((cards) => setState({ kind: "ready", cards }))
      .catch((err: unknown) => setState({ kind: "error", message: String(err) }));
  }, []);

  return (
    <main>
      <h1>Tổng quan vĩ mô</h1>
      <nav className="nav">
        <Link href="/kich-ban/">Giả lập kịch bản</Link>
        {" · "}
        <Link href="/kiem-chung/">Kiểm chứng lịch sử</Link>
        {" · "}
        <Link href="/anh-huong/">Bản đồ ảnh hưởng</Link>
      </nav>
      {state.kind === "loading" && <p>Đang tải…</p>}
      {state.kind === "error" && <p role="alert">Không tải được dữ liệu: {state.message}</p>}
      {state.kind === "ready" && state.cards.length === 0 && (
        <p>Chưa có chỉ số nào. Chạy `python -m macro.ingest` để lấy dữ liệu.</p>
      )}
      {state.kind === "ready" && state.cards.length > 0 && (
        <section className="cards">
          {state.cards.map((card) => (
            <IndicatorCardView key={card.series_id} card={card} />
          ))}
        </section>
      )}
    </main>
  );
}
