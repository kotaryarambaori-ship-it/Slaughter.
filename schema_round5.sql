-- Round 5: run after schema_round4.sql
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS before_url VARCHAR(500);
