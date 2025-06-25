"""DEAN Evolution DAG - Main evolution orchestration workflow."""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
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
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create DAG
dag = DAG(
    'dean_evolution',
    default_args=default_args,
    description='DEAN agent evolution orchestration',
    schedule_interval='0 */6 * * *',  # Every 6 hours
    catchup=False,
    tags=['dean', 'evolution', 'automated'],
)

def check_token_budget(**context):
    """Check global token budget before starting evolution."""
    # In production, this would query the database
    # For now, simulate budget check
    budget_available = 100000
    budget_required = 50000
    
    if budget_available < budget_required:
        raise ValueError(f"Insufficient token budget: {budget_available} < {budget_required}")
    
    logger.info(f"Token budget check passed: {budget_available} available")
    return {'budget_available': budget_available}

def initialize_population(**context):
    """Initialize agent population via IndexAgent."""
    import httpx
    
    indexagent_url = "http://indexagent:8081"
    population_size = context['params'].get('population_size', 10)
    diversity_threshold = context['params'].get('diversity_threshold', 0.3)
    
    try:
        response = httpx.post(
            f"{indexagent_url}/api/v1/agents/population/initialize",
            json={
                "size": population_size,
                "diversity_threshold": diversity_threshold
            }
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Initialized population with {len(result['agent_ids'])} agents")
        return result
    except Exception as e:
        logger.error(f"Failed to initialize population: {e}")
        raise

def start_evolution(**context):
    """Start evolution process via Evolution API."""
    import httpx
    
    evolution_api_url = "http://evolution-api:8090"
    ti = context['ti']
    
    # Get population data from previous task
    population_data = ti.xcom_pull(task_ids='initialize_population')
    agent_ids = population_data['agent_ids']
    
    # Evolution parameters
    generations = context['params'].get('generations', 50)
    token_budget = context['params'].get('token_budget', 50000)
    
    try:
        response = httpx.post(
            f"{evolution_api_url}/api/v1/evolution/start",
            json={
                "population_ids": agent_ids,
                "generations": generations,
                "token_budget": token_budget
            }
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Started evolution job: {result['job_id']}")
        return result
    except Exception as e:
        logger.error(f"Failed to start evolution: {e}")
        raise

def monitor_evolution(**context):
    """Monitor evolution progress."""
    import httpx
    import time
    
    evolution_api_url = "http://evolution-api:8090"
    ti = context['ti']
    
    # Get job ID from previous task
    evolution_data = ti.xcom_pull(task_ids='start_evolution')
    job_id = evolution_data['job_id']
    
    max_checks = 60  # Maximum number of checks
    check_interval = 30  # Seconds between checks
    
    for i in range(max_checks):
        try:
            response = httpx.get(f"{evolution_api_url}/api/v1/evolution/jobs/{job_id}")
            response.raise_for_status()
            job_status = response.json()
            
            logger.info(f"Evolution job {job_id} - Generation {job_status['current_generation']}/{job_status['total_generations']}")
            logger.info(f"Best fitness: {job_status['best_fitness']}, Diversity: {job_status['diversity_score']}")
            
            if job_status['status'] == 'completed':
                logger.info(f"Evolution completed successfully")
                return job_status
            elif job_status['status'] == 'failed':
                raise ValueError(f"Evolution job failed: {job_status.get('error', 'Unknown error')}")
            
            if i < max_checks - 1:
                time.sleep(check_interval)
                
        except Exception as e:
            logger.error(f"Error monitoring evolution: {e}")
            raise
    
    raise TimeoutError(f"Evolution job {job_id} did not complete within expected time")

def analyze_results(**context):
    """Analyze evolution results and create summary."""
    ti = context['ti']
    
    # Get final job status
    job_status = ti.xcom_pull(task_ids='monitor_evolution')
    
    summary = {
        'job_id': job_status['id'],
        'generations_completed': job_status['current_generation'],
        'final_fitness': job_status['best_fitness'],
        'final_diversity': job_status['diversity_score'],
        'tokens_consumed': job_status['tokens_consumed'],
        'efficiency': job_status['best_fitness'] / job_status['tokens_consumed'] if job_status['tokens_consumed'] > 0 else 0,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info(f"Evolution analysis complete: {json.dumps(summary, indent=2)}")
    return summary

def cleanup_resources(**context):
    """Clean up resources after evolution."""
    logger.info("Cleaning up evolution resources")
    # In production, this would:
    # - Clean git worktrees
    # - Archive logs
    # - Update metrics database
    return {'cleanup_status': 'completed'}

# Define tasks
check_budget_task = PythonOperator(
    task_id='check_token_budget',
    python_callable=check_token_budget,
    dag=dag,
)

initialize_population_task = PythonOperator(
    task_id='initialize_population',
    python_callable=initialize_population,
    params={
        'population_size': 10,
        'diversity_threshold': 0.3
    },
    dag=dag,
)

start_evolution_task = PythonOperator(
    task_id='start_evolution',
    python_callable=start_evolution,
    params={
        'generations': 50,
        'token_budget': 50000
    },
    dag=dag,
)

monitor_evolution_task = PythonOperator(
    task_id='monitor_evolution',
    python_callable=monitor_evolution,
    dag=dag,
)

analyze_results_task = PythonOperator(
    task_id='analyze_results',
    python_callable=analyze_results,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_resources',
    python_callable=cleanup_resources,
    trigger_rule='all_done',  # Run even if previous tasks fail
    dag=dag,
)

# Define task dependencies
check_budget_task >> initialize_population_task >> start_evolution_task
start_evolution_task >> monitor_evolution_task >> analyze_results_task
analyze_results_task >> cleanup_task