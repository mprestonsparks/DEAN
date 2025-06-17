"""
Integration test for monitoring workflow.

Tests the monitoring data flow from services to dashboard.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from integration import ServicePool
from orchestration.monitoring.metrics_collector import (
    MetricsCollector,
    MetricType,
    ServiceMetrics
)
from interfaces.web.websocket_handler import WebSocketManager


@pytest.mark.integration
class TestMonitoringWorkflow:
    """Test complete monitoring data flow."""
    
    @pytest.fixture
    def mock_service_pool(self):
        """Create mock service pool for testing."""
        pool = Mock(spec=ServicePool)
        
        # Mock health check adapter
        pool.health = AsyncMock()
        pool.health.check_all_services = AsyncMock(return_value={
            "indexagent": {"status": "healthy", "latency_ms": 45},
            "airflow": {"status": "healthy", "latency_ms": 120},
            "evolution": {"status": "degraded", "latency_ms": 350},
            "orchestration": {"status": "healthy", "latency_ms": 20}
        })
        
        # Mock service metrics endpoints
        pool.indexagent.get_metrics = AsyncMock(return_value={
            "agents_created": 150,
            "patterns_extracted": 42,
            "search_queries": 1250,
            "avg_query_time_ms": 85
        })
        
        pool.airflow.get_metrics = AsyncMock(return_value={
            "dags_running": 3,
            "dags_completed": 47,
            "tasks_queued": 12,
            "executor_slots_available": 8
        })
        
        pool.evolution.get_metrics = AsyncMock(return_value={
            "trials_active": 2,
            "generations_completed": 145,
            "best_fitness": 0.92,
            "patterns_discovered": 18
        })
        
        return pool
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        manager = Mock(spec=WebSocketManager)
        manager.broadcast = AsyncMock()
        manager.send_to_connection = AsyncMock()
        manager.connection_count = 3
        return manager
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, mock_service_pool):
        """Test that metrics are collected from all services."""
        collector = MetricsCollector(service_pool=mock_service_pool)
        
        # Collect metrics
        metrics = await collector.collect_all_metrics()
        
        # Verify structure
        assert isinstance(metrics, dict)
        assert "timestamp" in metrics
        assert "services" in metrics
        
        # Verify all services were queried
        mock_service_pool.health.check_all_services.assert_called_once()
        mock_service_pool.indexagent.get_metrics.assert_called_once()
        mock_service_pool.airflow.get_metrics.assert_called_once()
        mock_service_pool.evolution.get_metrics.assert_called_once()
        
        # Verify service data
        services = metrics["services"]
        assert "indexagent" in services
        assert "airflow" in services
        assert "evolution" in services
        
        # Check IndexAgent metrics
        assert services["indexagent"]["health"]["status"] == "healthy"
        assert services["indexagent"]["metrics"]["agents_created"] == 150
        
    @pytest.mark.asyncio
    async def test_websocket_broadcast(self, mock_service_pool, mock_websocket_manager):
        """Test that metrics are broadcast via WebSocket."""
        collector = MetricsCollector(
            service_pool=mock_service_pool,
            websocket_manager=mock_websocket_manager
        )
        
        # Start monitoring (single iteration)
        await collector._broadcast_metrics()
        
        # Verify broadcast was called
        mock_websocket_manager.broadcast.assert_called_once()
        
        # Check broadcast data
        call_args = mock_websocket_manager.broadcast.call_args
        broadcast_data = json.loads(call_args[0][0])
        
        assert broadcast_data["type"] == "metrics_update"
        assert "data" in broadcast_data
        assert "timestamp" in broadcast_data["data"]
        assert "services" in broadcast_data["data"]
        
    @pytest.mark.asyncio
    async def test_monitoring_interval(self, mock_service_pool):
        """Test that monitoring respects configured interval."""
        collector = MetricsCollector(
            service_pool=mock_service_pool,
            interval_seconds=0.1  # 100ms for testing
        )
        
        start_time = time.time()
        
        # Run monitoring for a short period
        monitoring_task = asyncio.create_task(collector.start_monitoring())
        await asyncio.sleep(0.35)  # Should allow 3 collections
        collector.stop_monitoring()
        await monitoring_task
        
        # Verify collection count
        call_count = mock_service_pool.health.check_all_services.call_count
        assert 3 <= call_count <= 4  # Allow some timing variance
        
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_service_pool):
        """Test monitoring continues despite service errors."""
        # Make one service fail
        mock_service_pool.airflow.get_metrics.side_effect = Exception("Airflow error")
        
        collector = MetricsCollector(service_pool=mock_service_pool)
        
        # Collect metrics
        metrics = await collector.collect_all_metrics()
        
        # Verify other services still collected
        assert "indexagent" in metrics["services"]
        assert "evolution" in metrics["services"]
        
        # Verify error is captured
        assert "airflow" in metrics["services"]
        assert metrics["services"]["airflow"]["error"] is not None
        assert "Airflow error" in metrics["services"]["airflow"]["error"]
        
    @pytest.mark.asyncio
    async def test_metrics_aggregation(self, mock_service_pool):
        """Test that metrics are properly aggregated."""
        collector = MetricsCollector(service_pool=mock_service_pool)
        
        # Collect metrics multiple times
        metrics_list = []
        for _ in range(5):
            metrics = await collector.collect_all_metrics()
            metrics_list.append(metrics)
            await asyncio.sleep(0.01)
            
        # Get aggregated metrics
        aggregated = collector.get_aggregated_metrics(
            time_window_minutes=1
        )
        
        # Verify aggregation
        assert "summary" in aggregated
        assert "time_range" in aggregated
        assert "services" in aggregated
        
        # Check summary stats
        summary = aggregated["summary"]
        assert "total_health_checks" in summary
        assert "healthy_services" in summary
        assert "degraded_services" in summary
        
    @pytest.mark.asyncio
    async def test_alert_generation(self, mock_service_pool):
        """Test that alerts are generated for unhealthy services."""
        # Configure unhealthy service
        mock_service_pool.health.check_all_services.return_value = {
            "indexagent": {"status": "unhealthy", "error": "Connection refused"},
            "airflow": {"status": "healthy", "latency_ms": 50},
            "evolution": {"status": "unhealthy", "error": "Timeout"},
            "orchestration": {"status": "healthy", "latency_ms": 20}
        }
        
        collector = MetricsCollector(service_pool=mock_service_pool)
        
        # Collect metrics
        metrics = await collector.collect_all_metrics()
        
        # Check for alerts
        alerts = collector.get_active_alerts()
        
        assert len(alerts) == 2
        alert_services = [alert["service"] for alert in alerts]
        assert "indexagent" in alert_services
        assert "evolution" in alert_services
        
        # Verify alert structure
        for alert in alerts:
            assert "service" in alert
            assert "severity" in alert
            assert "message" in alert
            assert "timestamp" in alert
            
    @pytest.mark.asyncio
    async def test_performance_metrics(self, mock_service_pool):
        """Test collection of performance metrics."""
        collector = MetricsCollector(service_pool=mock_service_pool)
        
        # Collect metrics with timing
        start = time.time()
        metrics = await collector.collect_all_metrics()
        duration = time.time() - start
        
        # Verify collection is fast
        assert duration < 1.0  # Should complete in under 1 second
        
        # Verify performance data included
        assert "collection_time_ms" in metrics
        assert metrics["collection_time_ms"] < 1000
        
    @pytest.mark.asyncio
    async def test_dashboard_api_integration(self, mock_service_pool):
        """Test integration with dashboard API endpoints."""
        from interfaces.web.app import app
        
        # Mock the collector in the app
        with patch('interfaces.web.app.metrics_collector') as mock_collector:
            mock_collector.collect_all_metrics = AsyncMock(return_value={
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "indexagent": {
                        "health": {"status": "healthy"},
                        "metrics": {"agents_created": 100}
                    }
                }
            })
            
            # Verify API endpoint exists
            routes = [r.path for r in app.routes if hasattr(r, 'path')]
            assert any('/api/system/metrics' in str(r) for r in routes)
            
    @pytest.mark.asyncio
    async def test_historical_metrics_storage(self, mock_service_pool):
        """Test that metrics are stored for historical analysis."""
        collector = MetricsCollector(
            service_pool=mock_service_pool,
            enable_history=True,
            history_retention_hours=24
        )
        
        # Collect metrics over time
        for i in range(10):
            await collector.collect_all_metrics()
            await asyncio.sleep(0.01)
            
        # Get historical data
        history = collector.get_metrics_history(
            service="indexagent",
            metric="agents_created",
            hours=1
        )
        
        assert len(history) == 10
        assert all("timestamp" in entry for entry in history)
        assert all("value" in entry for entry in history)
        
    @pytest.mark.asyncio
    async def test_custom_metric_handlers(self, mock_service_pool):
        """Test registration of custom metric handlers."""
        collector = MetricsCollector(service_pool=mock_service_pool)
        
        # Register custom handler
        custom_metrics = {}
        
        async def custom_handler(service_name, raw_metrics):
            custom_metrics[service_name] = {
                "processed": True,
                "custom_value": raw_metrics.get("agents_created", 0) * 2
            }
            return custom_metrics[service_name]
            
        collector.register_metric_handler("indexagent", custom_handler)
        
        # Collect metrics
        metrics = await collector.collect_all_metrics()
        
        # Verify custom handler was used
        assert metrics["services"]["indexagent"]["custom"]["processed"] is True
        assert metrics["services"]["indexagent"]["custom"]["custom_value"] == 300


@pytest.mark.integration 
class TestMonitoringCLI:
    """Test monitoring from CLI perspective."""
    
    def test_monitoring_cli_commands(self):
        """Test that monitoring CLI commands exist."""
        from interfaces.cli.dean_cli import cli, monitoring
        
        # Check monitoring command group
        assert 'monitoring' in cli.commands
        
        # Check subcommands
        monitoring_cmd = cli.commands['monitoring']
        assert hasattr(monitoring_cmd, 'commands')
        assert 'status' in monitoring_cmd.commands
        assert 'metrics' in monitoring_cmd.commands
        assert 'alerts' in monitoring_cmd.commands
        
    @pytest.mark.asyncio
    async def test_cli_status_command(self, mock_service_pool):
        """Test monitoring status command."""
        from interfaces.cli.dean_cli import monitoring
        
        # Mock the service pool
        with patch('interfaces.cli.dean_cli.create_service_pool') as mock_create:
            mock_create.return_value.__aenter__.return_value = mock_service_pool
            mock_create.return_value.__aexit__.return_value = None
            
            # Check command structure
            status_cmd = monitoring.commands['status']
            assert status_cmd is not None
            
            # Verify it accepts formatting options
            param_names = [p.name for p in status_cmd.params]
            assert 'format' in param_names or 'json' in param_names