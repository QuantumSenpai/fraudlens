ALTER TABLE public.checks
ADD COLUMN IF NOT EXISTS ml_factors jsonb NOT NULL DEFAULT '[]'::jsonb
CHECK (jsonb_typeof(ml_factors) = 'array');
