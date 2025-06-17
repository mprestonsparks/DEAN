-- Enable useful PostgreSQL extensions for DEAN

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable JSONB additional operators
CREATE EXTENSION IF NOT EXISTS "jsonb_plperl";

-- Enable cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable full text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Add UUID columns to existing tables
ALTER TABLE agents ADD COLUMN IF NOT EXISTS uuid UUID DEFAULT uuid_generate_v4() UNIQUE;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS uuid UUID DEFAULT uuid_generate_v4() UNIQUE;
ALTER TABLE patterns ADD COLUMN IF NOT EXISTS uuid UUID DEFAULT uuid_generate_v4() UNIQUE;

-- Create additional indexes for UUID lookups
CREATE INDEX IF NOT EXISTS idx_agents_uuid ON agents(uuid);
CREATE INDEX IF NOT EXISTS idx_tasks_uuid ON tasks(uuid);
CREATE INDEX IF NOT EXISTS idx_patterns_uuid ON patterns(uuid);