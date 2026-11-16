ALTER TABLE public.devices
ADD COLUMN screen jsonb CHECK (screen IS NULL OR jsonb_typeof(screen) = 'object'),
ADD COLUMN timezone text CHECK (timezone IS NULL OR char_length(timezone) BETWEEN 1 AND 64),
ADD COLUMN language text CHECK (language IS NULL OR char_length(language) BETWEEN 1 AND 35),
ADD COLUMN last_ip inet,
ADD COLUMN last_lat numeric(9, 6) CHECK (last_lat BETWEEN -90 AND 90),
ADD COLUMN last_lon numeric(9, 6) CHECK (last_lon BETWEEN -180 AND 180);
