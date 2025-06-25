"""DEAN Pattern Discovery DAG - Pattern detection and cataloging workflows."""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
import json
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'dean-system',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

# Create DAG
dag = DAG(
    'dean_pattern_discovery',
    default_args=default_args,
    description='DEAN pattern detection, classification, and propagation',
    schedule_interval='*/30 * * * *',  # Every 30 minutes
    catchup=False,
    tags=['dean', 'patterns', 'ml'],
)

def detect_novel_patterns(**context):
    """Detect novel patterns in agent behaviors."""
    import httpx
    
    indexagent_url = "http://indexagent:8081"
    detected_patterns = []
    
    try:
        # Get recent agent activities
        response = httpx.get(f"{indexagent_url}/api/v1/agents")
        response.raise_for_status()
        agents = response.json()
        
        # Simulate pattern detection
        # In production, this would analyze actual agent behaviors
        for i, agent in enumerate(agents[:5]):  # Limit to first 5 for demo
            if np.random.random() > 0.7:  # 30% chance of pattern
                pattern = {
                    'id': f"pattern-{datetime.utcnow().timestamp()}-{i}",
                    'agent_id': agent['id'],
                    'type': np.random.choice(['optimization', 'refactoring', 'innovation']),
                    'confidence': np.random.uniform(0.6, 0.95),
                    'detected_at': datetime.utcnow().isoformat(),
                    'features': {
                        'token_reduction': np.random.uniform(0.1, 0.5),
                        'quality_improvement': np.random.uniform(0.1, 0.3),
                        'complexity': np.random.uniform(0.3, 0.8)
                    }
                }
                detected_patterns.append(pattern)
        
        logger.info(f"Detected {len(detected_patterns)} novel patterns")
        return detected_patterns
        
    except Exception as e:
        logger.error(f"Pattern detection failed: {e}")
        raise

def classify_patterns(**context):
    """Classify detected patterns as beneficial or gaming."""
    ti = context['ti']
    patterns = ti.xcom_pull(task_ids='detect_novel_patterns')
    
    if not patterns:
        logger.info("No patterns to classify")
        return []
    
    classified_patterns = []
    
    for pattern in patterns:
        # Simulate classification logic
        # In production, this would use ML models
        features = pattern['features']
        
        # Simple rule-based classification for demo
        is_beneficial = (
            features['token_reduction'] > 0.2 and
            features['quality_improvement'] > 0.15 and
            features['complexity'] < 0.7
        )
        
        effectiveness = 0.0
        if is_beneficial:
            effectiveness = (
                features['token_reduction'] * 0.4 +
                features['quality_improvement'] * 0.4 +
                (1 - features['complexity']) * 0.2
            )
        
        pattern['classification'] = 'beneficial' if is_beneficial else 'gaming'
        pattern['effectiveness'] = effectiveness
        pattern['approved'] = is_beneficial and effectiveness > 0.3
        
        classified_patterns.append(pattern)
        
        logger.info(f"Classified pattern {pattern['id']} as {pattern['classification']} "
                   f"with effectiveness {effectiveness:.3f}")
    
    return classified_patterns

def should_catalog_patterns(**context):
    """Decide whether to catalog patterns based on quality."""
    ti = context['ti']
    patterns = ti.xcom_pull(task_ids='classify_patterns')
    
    if not patterns:
        return 'skip_cataloging'
    
    approved_patterns = [p for p in patterns if p.get('approved', False)]
    
    if approved_patterns:
        logger.info(f"Found {len(approved_patterns)} patterns to catalog")
        return 'catalog_patterns'
    else:
        logger.info("No patterns meet cataloging criteria")
        return 'skip_cataloging'

def catalog_patterns(**context):
    """Store approved patterns in the pattern library."""
    ti = context['ti']
    patterns = ti.xcom_pull(task_ids='classify_patterns')
    approved_patterns = [p for p in patterns if p.get('approved', False)]
    
    cataloged_count = 0
    catalog_entries = []
    
    for pattern in approved_patterns:
        catalog_entry = {
            'pattern_id': pattern['id'],
            'agent_id': pattern['agent_id'],
            'pattern_type': pattern['type'],
            'effectiveness': pattern['effectiveness'],
            'features': json.dumps(pattern['features']),
            'metadata': json.dumps({
                'confidence': pattern['confidence'],
                'classification': pattern['classification'],
                'detected_at': pattern['detected_at']
            }),
            'created_at': datetime.utcnow().isoformat()
        }
        catalog_entries.append(catalog_entry)
        cataloged_count += 1
    
    # In production, insert into PostgreSQL
    logger.info(f"Cataloged {cataloged_count} patterns to library")
    
    # Store for next task
    return catalog_entries

def analyze_pattern_trends(**context):
    """Analyze trends in pattern discovery."""
    ti = context['ti']
    current_patterns = ti.xcom_pull(task_ids='classify_patterns') or []
    
    # Calculate trend metrics
    trend_analysis = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_patterns_detected': len(current_patterns),
        'beneficial_patterns': sum(1 for p in current_patterns if p.get('classification') == 'beneficial'),
        'gaming_patterns': sum(1 for p in current_patterns if p.get('classification') == 'gaming'),
        'average_effectiveness': np.mean([p.get('effectiveness', 0) for p in current_patterns]) if current_patterns else 0,
        'pattern_types': {}
    }
    
    # Count by type
    for pattern in current_patterns:
        p_type = pattern.get('type', 'unknown')
        trend_analysis['pattern_types'][p_type] = trend_analysis['pattern_types'].get(p_type, 0) + 1
    
    logger.info(f"Pattern trend analysis: {json.dumps(trend_analysis, indent=2)}")
    return trend_analysis

def propagate_effective_patterns(**context):
    """Propagate highly effective patterns to other agents."""
    ti = context['ti']
    catalog_entries = ti.xcom_pull(task_ids='catalog_patterns')
    
    if not catalog_entries:
        logger.info("No patterns to propagate")
        return {'propagated_count': 0}
    
    # Select top patterns for propagation
    top_patterns = sorted(
        catalog_entries,
        key=lambda x: json.loads(x['metadata'])['confidence'] * x['effectiveness'],
        reverse=True
    )[:3]  # Top 3 patterns
    
    propagation_results = {
        'propagated_patterns': [],
        'target_agents': [],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    for pattern in top_patterns:
        # In production, this would update agent configurations
        propagation_results['propagated_patterns'].append({
            'pattern_id': pattern['pattern_id'],
            'effectiveness': pattern['effectiveness'],
            'type': pattern['pattern_type']
        })
        
        # Simulate selecting target agents
        propagation_results['target_agents'].extend([
            f"agent-{i}" for i in range(5)
        ])
    
    propagation_results['propagated_count'] = len(top_patterns)
    logger.info(f"Propagated {len(top_patterns)} patterns to {len(set(propagation_results['target_agents']))} agents")
    
    return propagation_results

def cleanup_old_patterns(**context):
    """Clean up old or ineffective patterns."""
    # In production, this would query and clean the database
    cleanup_stats = {
        'patterns_before': 150,  # Mock data
        'patterns_removed': 23,
        'patterns_after': 127,
        'cleanup_criteria': {
            'max_age_days': 90,
            'min_effectiveness': 0.1,
            'min_reuse_count': 1
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info(f"Pattern cleanup completed: {cleanup_stats['patterns_removed']} patterns removed")
    return cleanup_stats

# Define tasks
detect_patterns_task = PythonOperator(
    task_id='detect_novel_patterns',
    python_callable=detect_novel_patterns,
    dag=dag,
)

classify_patterns_task = PythonOperator(
    task_id='classify_patterns',
    python_callable=classify_patterns,
    dag=dag,
)

branch_task = BranchPythonOperator(
    task_id='should_catalog',
    python_callable=should_catalog_patterns,
    dag=dag,
)

catalog_patterns_task = PythonOperator(
    task_id='catalog_patterns',
    python_callable=catalog_patterns,
    dag=dag,
)

skip_cataloging_task = PythonOperator(
    task_id='skip_cataloging',
    python_callable=lambda: logger.info("Skipping pattern cataloging"),
    dag=dag,
)

analyze_trends_task = PythonOperator(
    task_id='analyze_pattern_trends',
    python_callable=analyze_pattern_trends,
    trigger_rule='none_failed_min_one_success',
    dag=dag,
)

propagate_patterns_task = PythonOperator(
    task_id='propagate_effective_patterns',
    python_callable=propagate_effective_patterns,
    dag=dag,
)

cleanup_patterns_task = PythonOperator(
    task_id='cleanup_old_patterns',
    python_callable=cleanup_old_patterns,
    dag=dag,
)

# Database operations
update_pattern_stats = PostgresOperator(
    task_id='update_pattern_statistics',
    postgres_conn_id='dean_postgres',
    sql="""
        -- Update pattern reuse counts
        UPDATE agent_evolution.discovered_patterns
        SET reuse_count = reuse_count + 1
        WHERE pattern_id IN (
            SELECT pattern_id 
            FROM agent_evolution.pattern_applications
            WHERE applied_at > NOW() - INTERVAL '30 minutes'
        );
        
        -- Update effectiveness scores based on outcomes
        UPDATE agent_evolution.discovered_patterns dp
        SET effectiveness_score = (
            SELECT AVG(outcome_score)
            FROM agent_evolution.pattern_applications pa
            WHERE pa.pattern_id = dp.pattern_id
            AND pa.applied_at > NOW() - INTERVAL '7 days'
        )
        WHERE EXISTS (
            SELECT 1 
            FROM agent_evolution.pattern_applications pa
            WHERE pa.pattern_id = dp.pattern_id
            AND pa.applied_at > NOW() - INTERVAL '30 minutes'
        );
    """,
    dag=dag,
)

# Define task dependencies
detect_patterns_task >> classify_patterns_task >> branch_task
branch_task >> [catalog_patterns_task, skip_cataloging_task]
[catalog_patterns_task, skip_cataloging_task] >> analyze_trends_task

catalog_patterns_task >> propagate_patterns_task
propagate_patterns_task >> update_pattern_stats
analyze_trends_task >> cleanup_patterns_task