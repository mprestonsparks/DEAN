# DEAN Source Code

This directory contains the core Python implementation of the DEAN orchestration system.

## Directory Structure

- `orchestration/` - Core orchestration logic for coordinating between services
  - `deployment/` - System deployment orchestration
  - `coordination/` - Cross-service task coordination
  - `monitoring/` - System-wide monitoring and alerting

- `interfaces/` - User-facing interfaces
  - `cli/` - Command-line interface implementation
  - `web/` - Web dashboard and API gateway

- `integration/` - External service integration layer
  - Service clients for IndexAgent, Airflow, and infrastructure
  - Adapter patterns for protocol handling

## Purpose

The source code in this directory implements:

1. **Service Orchestration**: Coordinating workflows across IndexAgent, airflow-hub, and infra repositories
2. **User Interfaces**: Providing CLI and web interfaces for system interaction
3. **Integration Abstraction**: Clean interfaces to external services without direct repository dependencies
4. **Monitoring Aggregation**: Collecting and presenting system-wide metrics

## Design Principles

- No direct imports from external repositories
- All external communication through service clients
- Comprehensive error handling and retry logic
- Configuration-driven behavior
- Testable architecture with dependency injection