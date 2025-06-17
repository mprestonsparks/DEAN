-- Create DEAN schema
-- This runs before other initialization scripts

-- Create the dean schema referenced in migrations
CREATE SCHEMA IF NOT EXISTS dean;

-- Grant usage on schema to the database user
GRANT ALL ON SCHEMA dean TO dean_prod;
GRANT ALL ON SCHEMA public TO dean_prod;

-- Set default search path to include both schemas
ALTER DATABASE dean_production SET search_path TO dean, public;