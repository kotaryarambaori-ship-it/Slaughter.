-- Round 3a: run after schema_round2.sql
CREATE TABLE IF NOT EXISTS activity_logs (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  action VARCHAR(40) NOT NULL,
  detail TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_logs_date ON activity_logs(created_at DESC);

CREATE TABLE IF NOT EXISTS settings (
  key VARCHAR(50) PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);

-- Admin banane ke liye (pehle Register karo, phir apna mobile likhkar chalao):
-- UPDATE users SET role='admin' WHERE mobile='9XXXXXXXXX';
