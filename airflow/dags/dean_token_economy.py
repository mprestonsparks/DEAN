"""DEAN Token Economy DAG - Economic governance and budget management."""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.utils.dates import days_ago
import json
import logging

logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'dean-system',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email': ['dean-alerts@example.com'],
}

# Create DAG
dag = DAG(
    'dean_token_economy',
    default_args=default_args,
    description='DEAN token economy management and budget enforcement',
    schedule_interval='0 * * * *',  # Every hour
    catchup=False,
    tags=['dean', 'economy', 'governance'],
)

def calculate_token_allocation(**context):
    """Calculate token allocation based on agent performance."""
    import httpx
    import numpy as np
    
    # Get agent performance data
    indexagent_url = "http://indexagent:8081"
    
    try:
        response = httpx.get(f"{indexagent_url}/api/v1/agents")
        response.raise_for_status()
        agents = response.json()
        
        # Calculate efficiency scores
        allocations = {}
        total_budget = context['params'].get('total_budget', 100000)
        
        for agent in agents:
            efficiency = agent.get('fitness_score', 0) / max(agent.get('tokens_consumed', 1), 1)
            base_allocation = total_budget / len(agents)
            
            # Apply performance multiplier
            performance_multiplier = min(2.0, max(0.5, efficiency * 10))
            allocations[agent['id']] = int(base_allocation * performance_multiplier)
        
        # Ensure we don't exceed total budget
        total_allocated = sum(allocations.values())
        if total_allocated > total_budget:
            scale_factor = total_budget / total_allocated
            allocations = {k: int(v * scale_factor) for k, v in allocations.items()}
        
        logger.info(f"Calculated allocations for {len(allocations)} agents")
        return allocations
        
    except Exception as e:
        logger.error(f"Failed to calculate allocations: {e}")
        raise

def enforce_budget_limits(**context):
    """Enforce token budget limits across all agents."""
    ti = context['ti']
    allocations = ti.xcom_pull(task_ids='calculate_token_allocation')
    
    enforced_count = 0
    exceeded_agents = []
    
    for agent_id, budget in allocations.items():
        # In production, this would update the database and enforce limits
        # For now, simulate enforcement
        current_usage = context['params'].get('mock_usage', {}).get(agent_id, 0)
        
        if current_usage > budget:
            exceeded_agents.append({
                'agent_id': agent_id,
                'budget': budget,
                'usage': current_usage,
                'overage': current_usage - budget
            })
            enforced_count += 1
    
    logger.info(f"Enforced budget limits on {enforced_count} agents")
    
    if exceeded_agents:
        logger.warning(f"Agents exceeding budget: {json.dumps(exceeded_agents, indent=2)}")
    
    return {
        'enforced_count': enforced_count,
        'exceeded_agents': exceeded_agents,
        'timestamp': datetime.utcnow().isoformat()
    }

def apply_budget_decay(**context):
    """Apply budget decay to long-running agents."""
    decay_rate = context['params'].get('decay_rate', 0.9)
    generation_threshold = context['params'].get('generation_threshold', 5)
    
    # In production, query database for agent generations
    # For now, simulate decay application
    decayed_agents = []
    
    # Mock data for demonstration
    long_running_agents = [
        {'id': 'agent-1', 'generations': 8, 'current_budget': 4096},
        {'id': 'agent-2', 'generations': 12, 'current_budget': 4096},
    ]
    
    for agent in long_running_agents:
        if agent['generations'] > generation_threshold:
            generations_over = agent['generations'] - generation_threshold
            decay_factor = decay_rate ** generations_over
            new_budget = int(agent['current_budget'] * decay_factor)
            
            decayed_agents.append({
                'agent_id': agent['id'],
                'generations': agent['generations'],
                'old_budget': agent['current_budget'],
                'new_budget': new_budget,
                'decay_factor': decay_factor
            })
    
    logger.info(f"Applied budget decay to {len(decayed_agents)} agents")
    return decayed_agents

def calculate_roi_metrics(**context):
    """Calculate return on investment metrics."""
    ti = context['ti']
    
    # In production, aggregate from database
    # For now, calculate mock ROI
    metrics = {
        'total_tokens_consumed': 75000,
        'total_value_generated': 850,
        'overall_efficiency': 850 / 75000,
        'roi_percentage': ((850 - 75) / 75) * 100,
        'top_performers': [
            {'agent_id': 'agent-3', 'roi': 15.2},
            {'agent_id': 'agent-7', 'roi': 12.8},
            {'agent_id': 'agent-1', 'roi': 11.5}
        ],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info(f"ROI Metrics: {json.dumps(metrics, indent=2)}")
    return metrics

def generate_economic_report(**context):
    """Generate comprehensive economic report."""
    ti = context['ti']
    
    # Gather all economic data
    allocations = ti.xcom_pull(task_ids='calculate_token_allocation')
    enforcement = ti.xcom_pull(task_ids='enforce_budget_limits')
    decay_results = ti.xcom_pull(task_ids='apply_budget_decay')
    roi_metrics = ti.xcom_pull(task_ids='calculate_roi_metrics')
    
    report = {
        'report_id': f"eco-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        'timestamp': datetime.utcnow().isoformat(),
        'summary': {
            'total_agents': len(allocations) if allocations else 0,
            'budget_violations': enforcement['enforced_count'] if enforcement else 0,
            'agents_with_decay': len(decay_results) if decay_results else 0,
            'overall_roi': roi_metrics['roi_percentage'] if roi_metrics else 0
        },
        'allocations': allocations,
        'enforcement': enforcement,
        'decay_results': decay_results,
        'roi_metrics': roi_metrics
    }
    
    logger.info(f"Generated economic report: {report['report_id']}")
    
    # In production, save to database and trigger alerts if needed
    return report

def trigger_economic_alerts(**context):
    """Trigger alerts based on economic thresholds."""
    ti = context['ti']
    report = ti.xcom_pull(task_ids='generate_economic_report')
    
    alerts = []
    
    # Check for critical conditions
    if report['summary']['budget_violations'] > 5:
        alerts.append({
            'level': 'critical',
            'type': 'budget_violation',
            'message': f"{report['summary']['budget_violations']} agents exceeded budget limits",
            'timestamp': datetime.utcnow().isoformat()
        })
    
    if report['summary']['overall_roi'] < 0:
        alerts.append({
            'level': 'warning',
            'type': 'negative_roi',
            'message': f"Overall ROI is negative: {report['summary']['overall_roi']:.2f}%",
            'timestamp': datetime.utcnow().isoformat()
        })
    
    if alerts:
        logger.warning(f"Economic alerts triggered: {json.dumps(alerts, indent=2)}")
        # In production, send alerts via email/Slack/PagerDuty
    else:
        logger.info("No economic alerts triggered")
    
    return alerts

# Define tasks
calculate_allocation_task = PythonOperator(
    task_id='calculate_token_allocation',
    python_callable=calculate_token_allocation,
    params={
        'total_budget': 100000
    },
    dag=dag,
)

enforce_budget_task = PythonOperator(
    task_id='enforce_budget_limits',
    python_callable=enforce_budget_limits,
    params={
        'mock_usage': {
            'agent-1': 5000,
            'agent-2': 3000,
            'agent-3': 2000
        }
    },
    dag=dag,
)

apply_decay_task = PythonOperator(
    task_id='apply_budget_decay',
    python_callable=apply_budget_decay,
    params={
        'decay_rate': 0.9,
        'generation_threshold': 5
    },
    dag=dag,
)

calculate_roi_task = PythonOperator(
    task_id='calculate_roi_metrics',
    python_callable=calculate_roi_metrics,
    dag=dag,
)

generate_report_task = PythonOperator(
    task_id='generate_economic_report',
    python_callable=generate_economic_report,
    dag=dag,
)

trigger_alerts_task = PythonOperator(
    task_id='trigger_economic_alerts',
    python_callable=trigger_economic_alerts,
    dag=dag,
)

# Database cleanup task
cleanup_old_metrics = PostgresOperator(
    task_id='cleanup_old_metrics',
    postgres_conn_id='dean_postgres',
    sql="""
        DELETE FROM agent_evolution.performance_metrics 
        WHERE recorded_at < NOW() - INTERVAL '30 days';
        
        VACUUM ANALYZE agent_evolution.performance_metrics;
    """,
    dag=dag,
)

# Define task dependencies
calculate_allocation_task >> [enforce_budget_task, apply_decay_task]
[enforce_budget_task, apply_decay_task] >> calculate_roi_task
calculate_roi_task >> generate_report_task >> trigger_alerts_task
generate_report_task >> cleanup_old_metrics