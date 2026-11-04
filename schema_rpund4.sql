-- Round 4: run after schema_round3.sql
CREATE TABLE IF NOT EXISTS posts (
  id SERIAL PRIMARY KEY,
  kind VARCHAR(12) NOT NULL CHECK (kind IN ('news','notice','schedule','activity','photo','video','service')),
  title_hi VARCHAR(200) NOT NULL DEFAULT '',
  title_en VARCHAR(200) NOT NULL DEFAULT '',
  body_hi TEXT NOT NULL DEFAULT '',
  body_en TEXT NOT NULL DEFAULT '',
  event_date DATE NOT NULL DEFAULT CURRENT_DATE,
  media_url VARCHAR(500),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_posts_kind_date ON posts(kind, event_date DESC);
