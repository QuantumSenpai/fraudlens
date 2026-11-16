CREATE TABLE public.razorpay_webhook_events (
    event_id text PRIMARY KEY CHECK (char_length(event_id) BETWEEN 1 AND 160),
    event_type text NOT NULL CHECK (char_length(event_type) BETWEEN 1 AND 80),
    processed_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.razorpay_webhook_events ENABLE ROW LEVEL SECURITY;
