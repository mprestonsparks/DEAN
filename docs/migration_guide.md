# DEAN Architecture Migration Guide

This guide provides step-by-step instructions for migrating existing DEAN deployments to the improved architecture with better service independence and loose coupling.

## Overview

The architectural improvements focus on:
1. **Organized DAG Structure**: DEAN-specific DAGs moved to `dags/dean/` subdirectory
2. **Configurable Dependencies**: No hardcoded service endpoints or paths
3. **Clear Service Boundaries**: Each service can function independently
4. **API-based Economic Governor**: Economic governance now exposed via REST API

## Migration Steps

### Step 1: Update airflow-hub DAG Structure

#### 1.1 Create New Directory Structure
```bash
cd airflow-hub
mkdir -p dags/dean
```

#### 1.2 Move DEAN-specific DAGs
```bash
# Move all DEAN DAGs to subdirectory
mv dags/dean_*.py dags/dean/

# Move DEAN contracts
mv dags/dean_contracts.py dags/dean/
```

#### 1.3 Update Import Statements
If you have custom DAGs that import from `dean_contracts`, update the imports:

```python
# Old import
from dean_contracts import EvolutionInput

# New import
from dean.dean_contracts import EvolutionInput
```

### Step 2: Configure Service Endpoints

#### 2.1 Remove Hardcoded URLs
Replace any hardcoded service URLs with Airflow Connections.

**In Airflow UI:**
1. Navigate to Admin → Connections
2. Add new connection:
   - Connection Id: `dean_api_default`
   - Connection Type: HTTP
   - Host: `dean-agent-evolution` (or your service host)
   - Port: `8000`
   - Schema: `http`

#### 2.2 Configure Path Variables
Add Airflow Variables for configurable paths.

**In Airflow UI:**
1. Navigate to Admin → Variables
2. Add new variable:
   - Key: `DEAN_AGENT_EVOLUTION_PATH`
   - Value: `/opt/agent-evolution` (or your installation path)

### Step 3: Update Service Code

#### 3.1 Update dean_evolution_cycle.py
If you have custom modifications to this file, ensure you're using the Variable:

```python
# Old code
sys.path.append('/opt/agent-evolution')

# New code
agent_evolution_path = Variable.get("DEAN_AGENT_EVOLUTION_PATH", "/opt/agent-evolution")
if agent_evolution_path not in sys.path:
    sys.path.append(agent_evolution_path)
```

#### 3.2 Update Hook Configuration
The `dean_api_hook.py` now requires explicit configuration. Ensure your Connection is configured as described in Step 2.1.

### Step 4: Test the Migration

#### 4.1 Verify DAG Loading
```bash
# Check that Airflow can load the moved DAGs
airflow dags list | grep dean

# Expected output:
# dean.dean_agent_evolution
# dean.dean_evolution_cycle
# ... (other DEAN DAGs)
```

#### 4.2 Test a Simple DAG
```bash
# Test one of the DEAN DAGs
airflow dags test dean.dean_agent_evolution 2024-01-01
```

#### 4.3 Verify Service Connections
```python
# Test script to verify connections
from airflow.hooks.base import BaseHook

# Test DEAN API connection
try:
    conn = BaseHook.get_connection("dean_api_default")
    print(f"✓ DEAN API configured: {conn.host}:{conn.port}")
except:
    print("✗ DEAN API connection not configured")

# Test Variables
from airflow.models import Variable
try:
    path = Variable.get("DEAN_AGENT_EVOLUTION_PATH")
    print(f"✓ Evolution path configured: {path}")
except:
    print("✗ Evolution path variable not set")
```

### Step 5: Migrate Economic Governor Integration

The Economic Governor is now accessed via REST API instead of direct imports.

#### 5.1 Update Imports
Replace direct EconomicGovernor imports with the API client:

```python
# Old import (remove this)
from infra.services.economy.economic_governor import EconomicGovernor

# New import
from dean.utils.economic_client import EconomicGovernorClient
```

#### 5.2 Update Function Calls
Replace direct EconomicGovernor usage:

```python
# Old code
governor = EconomicGovernor(db_url, total_budget)
metrics = governor.get_system_metrics()
governor.use_tokens(agent_id, tokens, action_type, success, quality)

# New code
client = EconomicGovernorClient()
metrics = client.get_system_metrics()
client.use_tokens(agent_id, tokens, action_type, success, quality)
```

#### 5.3 Configure API Endpoint
Set the DEAN API URL in Airflow Variables:
- Variable Name: `dean_api_url`
- Variable Value: `http://infra-api:8091` (or your deployment URL)

Or set via environment variable:
```bash
export DEAN_API_URL=http://infra-api:8091
```

#### 5.4 Verify Economic API
Test the Economic Governor API:
```bash
# Check metrics endpoint
curl http://localhost:8091/api/v1/economy/metrics

# Test token usage (will fail with test agent, but confirms API works)
curl -X POST http://localhost:8091/api/v1/economy/use-tokens \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "test", "tokens": 10, "action_type": "test", "task_success": 1.0, "quality_score": 1.0}'
```

### Step 6: Update Documentation

Update any internal documentation that references:
- Old DAG paths (now in `dags/dean/`)
- Hardcoded service endpoints (now in Connections)
- Hardcoded paths (now in Variables)
- Direct EconomicGovernor usage (now via API)

## Backward Compatibility

### Maintaining Compatibility During Migration

If you need to maintain backward compatibility during migration:

1. **Create Symlinks** (temporary):
```bash
cd dags
for dag in dean/*.py; do
    ln -s "$dag" "$(basename $dag)"
done
```

2. **Dual Configuration** (temporary):
```python
# Support both old and new configuration
try:
    # Try new configuration first
    conn = BaseHook.get_connection("dean_api_default")
    base_url = f"{conn.schema}://{conn.host}:{conn.port}"
except:
    # Fall back to old hardcoded value
    import warnings
    warnings.warn("Using deprecated hardcoded URL. Please configure dean_api_default connection.", DeprecationWarning)
    base_url = "http://dean-agent-evolution:8000"
```

3. **Gradual Migration**:
   - Week 1: Deploy new structure, maintain symlinks
   - Week 2: Update all references to use new paths
   - Week 3: Remove symlinks and deprecated code

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Symptom: `ModuleNotFoundError: No module named 'dean_contracts'`
   - Solution: Update imports to use `from dean.dean_contracts import ...`

2. **Connection Not Found**
   - Symptom: `AirflowException: No host configured for connection 'dean_api_default'`
   - Solution: Configure the connection in Airflow UI as described in Step 2.1

3. **Variable Not Found**
   - Symptom: `KeyError: 'Variable DEAN_AGENT_EVOLUTION_PATH does not exist'`
   - Solution: Add the variable in Airflow UI as described in Step 2.2

### Rollback Plan

If issues arise, you can quickly rollback:

1. Move DAGs back to root:
```bash
mv dags/dean/dean_*.py dags/
```

2. Revert code changes:
```bash
git checkout -- dags/dean_evolution_cycle.py
git checkout -- plugins/agent_evolution/hooks/dean_api_hook.py
```

## Benefits After Migration

1. **Cleaner Organization**: DEAN DAGs isolated in their own directory
2. **Environment Flexibility**: Different configurations per environment
3. **Service Independence**: airflow-hub can be used without DEAN
4. **Explicit Dependencies**: All configuration requirements are visible
5. **Easier Maintenance**: Clear separation of concerns

## Next Steps

After completing this migration:

1. Consider packaging DEAN contracts as a separate Python package
2. Implement service health checks in your DAGs
3. Add monitoring for the new configuration variables
4. Document your specific DEAN deployment configuration

For questions or issues, please refer to the DEAN documentation or create an issue in the repository.