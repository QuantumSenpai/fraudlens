INSERT INTO public.merchants (name, api_key_hash)
VALUES (
    'FraudLens Demo Merchant',
    'REPLACE_WITH_64_CHARACTER_LOWERCASE_SHA256_HASH'
)
ON CONFLICT (api_key_hash) DO UPDATE
SET name = EXCLUDED.name, is_active = true;
