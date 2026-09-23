export type TimelineEventType =
  | 'SPILL_EVENT'
  | 'SAR_OBSERVATION'
  | 'SOURCE_WINDOW_START'
  | 'SOURCE_WINDOW_END'
  | 'VESSEL_INTERCEPT'
  | 'CURRENT_SECTOR';

export interface TimelineMarker {
  id: string;
  type: TimelineEventType;
  timestamp_utc: string;
  label: string;
  description?: string;
  color?: string;
}

export interface TimelineSpan {
  start_utc: string;
  end_utc: string;
  current_time_utc: string;
  markers: TimelineMarker[];
}
