ALTER TABLE public.checks
ADD COLUMN idempotency_key text CHECK (
    idempotency_key IS NULL OR char_length(idempotency_key) BETWEEN 1 AND 128
);

ALTER TABLE public.payments
ADD COLUMN idempotency_key text CHECK (
    idempotency_key IS NULL OR char_length(idempotency_key) BETWEEN 1 AND 128
);

CREATE UNIQUE INDEX checks_merchant_id_idempotency_key_idx
ON public.checks (merchant_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX payments_check_id_idempotency_key_idx
ON public.payments (check_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;
