import type { IndicatorCard } from "./types";

// Hợp đồng giao diện (spec overview-dashboard mục 6): data-testid của thẻ và các phần bên trong.
export function IndicatorCardView({ card }: { card: IndicatorCard }) {
  return (
    <article className="card" data-testid={`indicator-${card.series_id}`}>
      <h2 className="card-name">{card.name}</h2>
      <p className="card-value" data-testid="value">
        {card.value_text}
      </p>
      <p className="card-period" data-testid="period">
        {card.period_text}
      </p>
      {card.change_prev_text && (
        <p className="card-change" data-testid="change-prev">
          {card.change_prev_text}
        </p>
      )}
      {card.change_yoy_text && (
        <p className="card-change" data-testid="change-yoy">
          {card.change_yoy_text}
        </p>
      )}
      <p className="card-source" data-testid="source">
        {card.source_text}
      </p>
      <p className="card-status" data-testid="status">
        {card.status_text ?? ""}
      </p>
    </article>
  );
}
