"""Airflow API client implementation."""

import base64
from typing import Any, Dict, List, Optional
from datetime import datetime
from .base import ServiceClient


class AirflowClient(ServiceClient):
    """Client for Airflow API communication.
    
    Provides methods for:
    - DAG management (list, get, pause/unpause)
    - DAG execution (trigger, monitor)
    - Task information retrieval
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        username: str = "airflow",
        password: str = "airflow",
        **kwargs
    ):
        """Initialize Airflow client.
        
        Args:
            base_url: Airflow API base URL
            username: Airflow username for basic auth
            password: Airflow password for basic auth
            **kwargs: Additional arguments for ServiceClient
        """
        super().__init__(base_url, "Airflow", **kwargs)
        
        # Configure basic authentication
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self._session.headers.update({
            'Authorization': f'Basic {encoded_credentials}'
        })
        
        # API base path
        self.api_base = "/api/v1"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Airflow service health.
        
        Returns:
            Health status with component details
        """
        return await self.get(f"{self.api_base}/health")
    
    # DAG Management
    
    async def list_dags(
        self,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        only_active: bool = True,
    ) -> Dict[str, Any]:
        """List all available DAGs.
        
        Args:
            limit: Maximum number of DAGs to return
            offset: Number of DAGs to skip
            tags: Filter by DAG tags
            only_active: Only return active (unpaused) DAGs
            
        Returns:
            Paginated list of DAGs
        """
        params = {
            'limit': limit,
            'offset': offset,
            'only_active': str(only_active).lower(),
        }
        if tags:
            params['tags'] = ','.join(tags)
            
        return await self.get(f"{self.api_base}/dags", params=params)
    
    async def get_dag(self, dag_id: str) -> Dict[str, Any]:
        """Get details for a specific DAG.
        
        Args:
            dag_id: DAG identifier
            
        Returns:
            DAG configuration and metadata
        """
        return await self.get(f"{self.api_base}/dags/{dag_id}")
    
    async def update_dag(self, dag_id: str, is_paused: bool) -> Dict[str, Any]:
        """Update DAG state (pause/unpause).
        
        Args:
            dag_id: DAG identifier
            is_paused: Whether to pause (True) or unpause (False) the DAG
            
        Returns:
            Updated DAG details
        """
        payload = {"is_paused": is_paused}
        return await self.patch(f"{self.api_base}/dags/{dag_id}", json=payload)
    
    async def pause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Pause a DAG.
        
        Args:
            dag_id: DAG identifier
            
        Returns:
            Updated DAG details
        """
        return await self.update_dag(dag_id, is_paused=True)
    
    async def unpause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Unpause a DAG.
        
        Args:
            dag_id: DAG identifier
            
        Returns:
            Updated DAG details
        """
        return await self.update_dag(dag_id, is_paused=False)
    
    # DAG Execution
    
    async def trigger_dag(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
        execution_date: Optional[datetime] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger a new DAG run.
        
        Args:
            dag_id: DAG identifier
            conf: Configuration dictionary for the DAG run
            execution_date: Execution date for the DAG run
            run_id: Custom run ID (auto-generated if not provided)
            
        Returns:
            DAG run details including run_id
        """
        if execution_date is None:
            execution_date = datetime.utcnow()
            
        if run_id is None:
            run_id = f"manual__{execution_date.strftime('%Y-%m-%dT%H:%M:%S')}"
        
        payload = {
            "conf": conf or {},
            "dag_run_id": run_id,
            "execution_date": execution_date.isoformat(),
        }
        
        return await self.post(f"{self.api_base}/dags/{dag_id}/dagRuns", json=payload)
    
    async def get_dag_run(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Get status of a specific DAG run.
        
        Args:
            dag_id: DAG identifier
            dag_run_id: DAG run identifier
            
        Returns:
            DAG run status and details
        """
        return await self.get(f"{self.api_base}/dags/{dag_id}/dagRuns/{dag_run_id}")
    
    async def list_dag_runs(
        self,
        dag_id: str,
        limit: int = 25,
        offset: int = 0,
        state: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """List DAG runs for a specific DAG.
        
        Args:
            dag_id: DAG identifier
            limit: Maximum number of runs to return
            offset: Number of runs to skip
            state: Filter by run states (success, failed, running)
            
        Returns:
            Paginated list of DAG runs
        """
        params = {
            'limit': limit,
            'offset': offset,
        }
        if state:
            params['state'] = state
            
        return await self.get(f"{self.api_base}/dags/{dag_id}/dagRuns", params=params)
    
    async def cancel_dag_run(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Cancel a running DAG.
        
        Args:
            dag_id: DAG identifier
            dag_run_id: DAG run identifier
            
        Returns:
            Updated DAG run status
        """
        payload = {"state": "failed"}
        return await self.patch(
            f"{self.api_base}/dags/{dag_id}/dagRuns/{dag_run_id}",
            json=payload
        )
    
    # Task Information
    
    async def list_tasks(self, dag_id: str) -> Dict[str, Any]:
        """List all tasks in a DAG.
        
        Args:
            dag_id: DAG identifier
            
        Returns:
            List of task definitions
        """
        return await self.get(f"{self.api_base}/dags/{dag_id}/tasks")
    
    async def get_task(self, dag_id: str, task_id: str) -> Dict[str, Any]:
        """Get details for a specific task.
        
        Args:
            dag_id: DAG identifier
            task_id: Task identifier
            
        Returns:
            Task configuration and metadata
        """
        return await self.get(f"{self.api_base}/dags/{dag_id}/tasks/{task_id}")
    
    async def get_task_instances(
        self,
        dag_id: str,
        dag_run_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get task instances for a DAG run.
        
        Args:
            dag_id: DAG identifier
            dag_run_id: DAG run identifier
            limit: Maximum number of instances to return
            offset: Number of instances to skip
            
        Returns:
            List of task instance statuses
        """
        params = {
            'limit': limit,
            'offset': offset,
        }
        return await self.get(
            f"{self.api_base}/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
            params=params
        )
    
    async def get_task_instance(
        self,
        dag_id: str,
        dag_run_id: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """Get a specific task instance.
        
        Args:
            dag_id: DAG identifier
            dag_run_id: DAG run identifier
            task_id: Task identifier
            
        Returns:
            Task instance details and logs
        """
        return await self.get(
            f"{self.api_base}/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}"
        )
    
    # Utility Methods
    
    async def wait_for_dag_completion(
        self,
        dag_id: str,
        dag_run_id: str,
        check_interval: int = 5,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Wait for a DAG run to complete.
        
        Args:
            dag_id: DAG identifier
            dag_run_id: DAG run identifier
            check_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Returns:
            Final DAG run status
            
        Raises:
            ServiceTimeout: If DAG doesn't complete within timeout
        """
        import asyncio
        from .base import ServiceTimeout
        
        start_time = datetime.utcnow()
        
        while True:
            dag_run = await self.get_dag_run(dag_id, dag_run_id)
            state = dag_run.get('state')
            
            if state in ['success', 'failed', 'skipped']:
                return dag_run
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                raise ServiceTimeout(
                    f"DAG run {dag_run_id} did not complete within {timeout} seconds",
                    self.service_name,
                    {'dag_id': dag_id, 'dag_run_id': dag_run_id}
                )
            
            await asyncio.sleep(check_interval)
    
    async def get_dag_code(self, dag_id: str) -> Dict[str, Any]:
        """Get the source code of a DAG.
        
        Args:
            dag_id: DAG identifier
            
        Returns:
            DAG source code
        """
        return await self.get(f"{self.api_base}/dags/{dag_id}/source")