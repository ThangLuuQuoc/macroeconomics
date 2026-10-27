// Một thẻ trên bảng tổng quan, đúng như /api/indicators trả về.
// Mọi con số đã được tính và định dạng sẵn ở backend; web chỉ hiển thị (ADR-001).
export type IndicatorCard = {
  series_id: string;
  name: string;
  value_text: string;
  period_text: string;
  change_prev_text: string | null;
  change_yoy_text: string | null;
  source_text: string;
  status_text: string | null;
};
