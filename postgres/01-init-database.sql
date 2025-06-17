-- DEAN Database Initialization Script
-- This script creates the dean_production database and initial schema

-- Note: The database creation is handled by POSTGRES_DB environment variable
-- This script runs inside the dean_production database context

-- Create initial schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial version
INSERT INTO schema_version (version, description) 
VALUES ('1.0.0', 'Initial DEAN database schema');

-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    configuration JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create evolution history table
CREATE TABLE IF NOT EXISTS evolution_history (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    generation INTEGER NOT NULL,
    fitness_score DECIMAL(10, 6),
    mutation_details JSONB,
    parent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create patterns table
CREATE TABLE IF NOT EXISTS patterns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    pattern_data JSONB NOT NULL,
    frequency INTEGER DEFAULT 1,
    effectiveness DECIMAL(5, 2),
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);

-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    configuration JSONB DEFAULT '{}',
    result JSONB,
    agent_id INTEGER REFERENCES agents(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create service registry table
CREATE TABLE IF NOT EXISTS service_registry (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(255) NOT NULL UNIQUE,
    service_type VARCHAR(100) NOT NULL,
    endpoint VARCHAR(500) NOT NULL,
    health_check_url VARCHAR(500),
    status VARCHAR(50) DEFAULT 'unknown',
    last_health_check TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(type);
CREATE INDEX idx_evolution_agent_id ON evolution_history(agent_id);
CREATE INDEX idx_evolution_generation ON evolution_history(generation);
CREATE INDEX idx_patterns_type ON patterns(type);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX idx_service_registry_status ON service_registry(status);

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to relevant tables
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_service_registry_updated_at BEFORE UPDATE ON service_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (using the dean_prod user from environment)
-- Note: These grants will be applied to the user specified in POSTGRES_USER
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dean_prod;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dean_prod;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO dean_prod;