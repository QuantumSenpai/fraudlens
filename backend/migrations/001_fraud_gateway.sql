CREATE TABLE public.merchants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
    api_key_hash text NOT NULL UNIQUE CHECK (api_key_hash ~ '^[a-f0-9]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE public.devices (
    device_id text PRIMARY KEY CHECK (char_length(device_id) BETWEEN 1 AND 160),
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen timestamptz NOT NULL DEFAULT now(),
    user_agent text,
    platform text NOT NULL CHECK (platform IN ('web', 'mobile', 'extension')),
    trust_score integer NOT NULL DEFAULT 0 CHECK (trust_score BETWEEN 0 AND 100)
);

CREATE TABLE public.device_users (
    device_id text NOT NULL REFERENCES public.devices(device_id) ON DELETE CASCADE,
    user_id text NOT NULL CHECK (char_length(user_id) BETWEEN 1 AND 160),
    first_seen timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (device_id, user_id)
);

CREATE TABLE public.checks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id uuid NOT NULL REFERENCES public.merchants(id),
    user_id text NOT NULL CHECK (char_length(user_id) BETWEEN 1 AND 160),
    device_id text NOT NULL REFERENCES public.devices(device_id),
    ip inet,
    amount numeric(12, 2) NOT NULL CHECK (amount > 0 AND amount < 10000000),
    currency text NOT NULL DEFAULT 'INR' CHECK (currency ~ '^[A-Z]{3}$'),
    payment_method text NOT NULL CHECK (payment_method IN ('upi', 'card', 'netbanking', 'wallet')),
    lat numeric(9, 6) CHECK (lat BETWEEN -90 AND 90),
    lon numeric(9, 6) CHECK (lon BETWEEN -180 AND 180),
    ml_score numeric(6, 2) NOT NULL CHECK (ml_score BETWEEN 0 AND 100),
    rule_score numeric(6, 2) NOT NULL CHECK (rule_score BETWEEN 0 AND 100),
    final_score numeric(6, 2) NOT NULL CHECK (final_score BETWEEN 0 AND 100),
    decision text NOT NULL CHECK (decision IN ('ALLOW', 'REVIEW', 'BLOCK')),
    triggered_rules jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(triggered_rules) = 'array'),
    model_version text NOT NULL,
    latency_ms integer NOT NULL DEFAULT 0 CHECK (latency_ms >= 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.payments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    check_id uuid NOT NULL REFERENCES public.checks(id),
    razorpay_order_id text NOT NULL,
    razorpay_payment_id text,
    amount numeric(12, 2) NOT NULL CHECK (amount > 0 AND amount < 10000000),
    status text NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'authorized', 'captured', 'failed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    check_id uuid NOT NULL UNIQUE REFERENCES public.checks(id),
    reviewer text NOT NULL CHECK (char_length(reviewer) BETWEEN 1 AND 160),
    outcome text NOT NULL CHECK (outcome IN ('approve', 'reject')),
    note text CHECK (note IS NULL OR char_length(note) <= 2000),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.feedback_labels (
    check_id uuid PRIMARY KEY REFERENCES public.checks(id) ON DELETE CASCADE,
    label text NOT NULL CHECK (label IN ('fraud', 'legit')),
    source text NOT NULL CHECK (source IN ('reviewer', 'chargeback_sim', 'auto')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX checks_user_id_idx ON public.checks (user_id);
CREATE INDEX checks_device_id_idx ON public.checks (device_id);
CREATE INDEX checks_created_at_idx ON public.checks (created_at DESC);
CREATE INDEX checks_decision_created_at_idx ON public.checks (decision, created_at DESC);
CREATE INDEX device_users_user_id_idx ON public.device_users (user_id);
CREATE INDEX payments_check_id_idx ON public.payments (check_id);
CREATE UNIQUE INDEX payments_razorpay_order_id_idx ON public.payments (razorpay_order_id);
CREATE UNIQUE INDEX payments_razorpay_payment_id_idx ON public.payments (razorpay_payment_id) WHERE razorpay_payment_id IS NOT NULL;

ALTER TABLE public.merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.device_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback_labels ENABLE ROW LEVEL SECURITY;
