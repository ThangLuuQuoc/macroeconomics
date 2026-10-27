-- Schema của macroeconomics (ADR-001, .proofline/data-sources.md).
-- Mọi câu lệnh idempotent: chạy lại khi khởi động không đổi dữ liệu.

-- Registry: mỗi chuỗi số liệu và trạng thái của nó. "Đã chọn nguồn" không có nghĩa là "đã có dữ liệu".
CREATE TABLE IF NOT EXISTS series (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    measures            TEXT NOT NULL,
    connector           TEXT NOT NULL,
    upstream_provider   TEXT NOT NULL,
    source_series_id    TEXT,
    frequency           TEXT NOT NULL CHECK (frequency IN ('D', 'W', 'M', 'Q', 'A')),
    unit                TEXT NOT NULL,
    transform           TEXT NOT NULL CHECK (transform IN ('level', 'yoy', 'mom', 'index')),
    seasonal_adjustment BOOLEAN NOT NULL DEFAULT FALSE,
    status              TEXT NOT NULL
                        CHECK (status IN ('verified', 'partial', 'needs_mapping', 'blocked')),
    is_proxy            BOOLEAN NOT NULL DEFAULT FALSE,
    definition          TEXT NOT NULL DEFAULT '',
    source_url          TEXT NOT NULL DEFAULT '',
    terms_note          TEXT NOT NULL DEFAULT '',
    display_order       INTEGER NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Mỗi lần một connector lấy dữ liệu: thành công hay lỗi, lúc nào, lỗi gì.
CREATE TABLE IF NOT EXISTS fetch_runs (
    id          BIGSERIAL PRIMARY KEY,
    connector   TEXT NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status      TEXT NOT NULL CHECK (status IN ('running', 'ok', 'error')),
    error       TEXT,
    raw_path    TEXT
);

-- Giá trị theo kỳ. Mỗi lần lấy ghi một bản, để giữ phiên bản số liệu (số có thể bị sửa lại).
CREATE TABLE IF NOT EXISTS observations (
    series_id    TEXT NOT NULL REFERENCES series (id),
    period       DATE NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    fetch_run_id BIGINT NOT NULL REFERENCES fetch_runs (id),
    PRIMARY KEY (series_id, period, fetch_run_id)
);

-- Giá trị hiện hành của mỗi kỳ: bản của lần lấy gần nhất.
CREATE OR REPLACE VIEW latest_observations AS
SELECT DISTINCT ON (series_id, period) series_id, period, value, fetch_run_id
FROM observations
ORDER BY series_id, period, fetch_run_id DESC;
