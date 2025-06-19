#!/usr/bin/env python3
"""
Monitoring Client for DEAN Infrastructure
Provides metrics export, alerting, and monitoring capabilities
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    CollectorRegistry, generate_latest,
    push_to_gateway, REGISTRY
)
from prometheus_client.core import Metric

logger = logging.getLogger(__name__)


class MetricType:
    """Metric type constants"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MonitoringClient:
    """
    Monitoring client for DEAN system.
    Provides Prometheus metrics export and custom monitoring capabilities.
    """
    
    def __init__(
        self,
        service_name: str,
        pushgateway_url: Optional[str] = None,
        push_interval: int = 60,
        custom_labels: Optional[Dict[str, str]] = None
    ):
        """
        Initialize monitoring client.
        
        Args:
            service_name: Name of the service
            pushgateway_url: URL of Prometheus pushgateway
            push_interval: Interval to push metrics (seconds)
            custom_labels: Additional labels for all metrics
        """
        self.service_name = service_name
        self.pushgateway_url = pushgateway_url
        self.push_interval = push_interval
        self.custom_labels = custom_labels or {}
        
        # Metric storage
        self.metrics: Dict[str, Metric] = {}
        self.custom_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Alert rules
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_handlers: List[Callable] = []
        
        # Background tasks
        self._push_task: Optional[asyncio.Task] = None
        self._alert_task: Optional[asyncio.Task] = None
        
        # Initialize default metrics
        self._init_default_metrics()
    
    def _init_default_metrics(self):
        """Initialize default system metrics"""
        # Request metrics
        self.create_counter(
            "requests_total",
            "Total number of requests",
            ["method", "endpoint", "status"]
        )
        
        self.create_histogram(
            "request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"]
        )
        
        # Error metrics
        self.create_counter(
            "errors_total",
            "Total number of errors",
            ["error_type", "component"]
        )
        
        # System metrics
        self.create_gauge(
            "active_connections",
            "Number of active connections",
            ["connection_type"]
        )
        
        self.create_gauge(
            "memory_usage_bytes",
            "Memory usage in bytes",
            []
        )
        
        # Business metrics
        self.create_counter(
            "agents_created_total",
            "Total number of agents created",
            ["agent_type"]
        )
        
        self.create_histogram(
            "agent_fitness_score",
            "Agent fitness score distribution",
            ["generation"]
        )
    
    # Metric creation methods
    
    def create_counter(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Counter:
        """Create a counter metric"""
        full_name = f"{self.service_name}_{name}"
        
        if full_name in self.metrics:
            return self.metrics[full_name]
        
        all_labels = list(self.custom_labels.keys())
        if labels:
            all_labels.extend(labels)
        
        metric = Counter(
            full_name,
            description,
            all_labels
        )
        
        self.metrics[full_name] = metric
        return metric
    
    def create_gauge(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Gauge:
        """Create a gauge metric"""
        full_name = f"{self.service_name}_{name}"
        
        if full_name in self.metrics:
            return self.metrics[full_name]
        
        all_labels = list(self.custom_labels.keys())
        if labels:
            all_labels.extend(labels)
        
        metric = Gauge(
            full_name,
            description,
            all_labels
        )
        
        self.metrics[full_name] = metric
        return metric
    
    def create_histogram(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None
    ) -> Histogram:
        """Create a histogram metric"""
        full_name = f"{self.service_name}_{name}"
        
        if full_name in self.metrics:
            return self.metrics[full_name]
        
        all_labels = list(self.custom_labels.keys())
        if labels:
            all_labels.extend(labels)
        
        metric = Histogram(
            full_name,
            description,
            all_labels,
            buckets=buckets
        )
        
        self.metrics[full_name] = metric
        return metric
    
    def create_summary(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Summary:
        """Create a summary metric"""
        full_name = f"{self.service_name}_{name}"
        
        if full_name in self.metrics:
            return self.metrics[full_name]
        
        all_labels = list(self.custom_labels.keys())
        if labels:
            all_labels.extend(labels)
        
        metric = Summary(
            full_name,
            description,
            all_labels
        )
        
        self.metrics[full_name] = metric
        return metric
    
    # Metric recording methods
    
    def increment_counter(
        self,
        name: str,
        value: float = 1,
        labels: Optional[Dict[str, str]] = None
    ):
        """Increment a counter metric"""
        full_name = f"{self.service_name}_{name}"
        
        if full_name not in self.metrics:
            raise ValueError(f"Metric {name} not found")
        
        metric = self.metrics[full_name]
        label_values = self._get_label_values(labels)
        
        if label_values:
            metric.labels(**label_values).inc(value)
        else:
            metric.inc(value)
    
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Set a gauge metric value"""
        full_name = f"{self.service_name}_{name}"
        
        if full_name not in self.metrics:
            raise ValueError(f"Metric {name} not found")
        
        metric = self.metrics[full_name]
        label_values = self._get_label_values(labels)
        
        if label_values:
            metric.labels(**label_values).set(value)
        else:
            metric.set(value)
    
    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Observe a histogram metric value"""
        full_name = f"{self.service_name}_{name}"
        
        if full_name not in self.metrics:
            raise ValueError(f"Metric {name} not found")
        
        metric = self.metrics[full_name]
        label_values = self._get_label_values(labels)
        
        if label_values:
            metric.labels(**label_values).observe(value)
        else:
            metric.observe(value)
    
    def time_histogram(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ):
        """Context manager to time operations with histogram"""
        full_name = f"{self.service_name}_{name}"
        
        if full_name not in self.metrics:
            raise ValueError(f"Metric {name} not found")
        
        metric = self.metrics[full_name]
        label_values = self._get_label_values(labels)
        
        if label_values:
            return metric.labels(**label_values).time()
        else:
            return metric.time()
    
    # Custom metrics
    
    def record_custom_metric(
        self,
        name: str,
        value: float,
        metric_type: str = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None
    ):
        """Record a custom metric"""
        key = f"{name}:{self._tags_to_string(tags)}"
        self.custom_metrics[metric_type][key] = value
    
    def get_custom_metric(
        self,
        name: str,
        metric_type: str = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get a custom metric value"""
        key = f"{name}:{self._tags_to_string(tags)}"
        return self.custom_metrics[metric_type].get(key)
    
    # Alert rules
    
    def add_alert_rule(
        self,
        name: str,
        condition: Callable[[], bool],
        message: str,
        severity: str = "warning",
        cooldown: int = 300
    ):
        """
        Add an alert rule.
        
        Args:
            name: Alert name
            condition: Function that returns True when alert should fire
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
            cooldown: Cooldown period in seconds
        """
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "message": message,
            "severity": severity,
            "cooldown": cooldown,
            "last_fired": None
        })
    
    def add_alert_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add an alert handler"""
        self.alert_handlers.append(handler)
    
    async def check_alerts(self):
        """Check alert rules and fire alerts"""
        current_time = time.time()
        
        for rule in self.alert_rules:
            # Check cooldown
            if rule["last_fired"]:
                if current_time - rule["last_fired"] < rule["cooldown"]:
                    continue
            
            # Check condition
            try:
                if asyncio.iscoroutinefunction(rule["condition"]):
                    should_alert = await rule["condition"]()
                else:
                    should_alert = rule["condition"]()
                
                if should_alert:
                    # Fire alert
                    alert = {
                        "name": rule["name"],
                        "message": rule["message"],
                        "severity": rule["severity"],
                        "timestamp": datetime.utcnow().isoformat(),
                        "service": self.service_name
                    }
                    
                    # Call handlers
                    for handler in self.alert_handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(alert)
                            else:
                                handler(alert)
                        except Exception as e:
                            logger.error(f"Error in alert handler: {e}")
                    
                    # Update last fired time
                    rule["last_fired"] = current_time
                    
                    logger.warning(f"Alert fired: {alert}")
                    
            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {e}")
    
    # Background tasks
    
    async def start(self):
        """Start background tasks"""
        if self.pushgateway_url:
            self._push_task = asyncio.create_task(self._push_metrics_loop())
        
        if self.alert_rules:
            self._alert_task = asyncio.create_task(self._check_alerts_loop())
    
    async def stop(self):
        """Stop background tasks"""
        if self._push_task:
            self._push_task.cancel()
            try:
                await self._push_task
            except asyncio.CancelledError:
                pass
        
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass
    
    async def _push_metrics_loop(self):
        """Background loop to push metrics"""
        while True:
            try:
                await asyncio.sleep(self.push_interval)
                self.push_metrics()
            except Exception as e:
                logger.error(f"Error pushing metrics: {e}")
    
    async def _check_alerts_loop(self):
        """Background loop to check alerts"""
        while True:
            try:
                await self.check_alerts()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error checking alerts: {e}")
    
    # Metrics export
    
    def push_metrics(self):
        """Push metrics to Prometheus pushgateway"""
        if not self.pushgateway_url:
            return
        
        try:
            push_to_gateway(
                self.pushgateway_url,
                job=self.service_name,
                registry=REGISTRY,
                grouping_key=self.custom_labels
            )
            logger.debug("Metrics pushed to gateway")
        except Exception as e:
            logger.error(f"Failed to push metrics: {e}")
    
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format"""
        return generate_latest(REGISTRY).decode('utf-8')
    
    # Utility methods
    
    def _get_label_values(
        self,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Get combined label values"""
        result = dict(self.custom_labels)
        
        if labels:
            result.update(labels)
        
        return result
    
    def _tags_to_string(self, tags: Optional[Dict[str, str]] = None) -> str:
        """Convert tags to string for key"""
        if not tags:
            return ""
        
        return ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
    
    # Common metric helpers
    
    def record_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ):
        """Record HTTP request metrics"""
        labels = {"method": method, "endpoint": endpoint, "status": str(status)}
        
        self.increment_counter("requests_total", labels=labels)
        self.observe_histogram(
            "request_duration_seconds",
            duration,
            labels={"method": method, "endpoint": endpoint}
        )
    
    def record_error(
        self,
        error_type: str,
        component: str,
        error: Optional[Exception] = None
    ):
        """Record error metrics"""
        self.increment_counter(
            "errors_total",
            labels={"error_type": error_type, "component": component}
        )
        
        if error:
            logger.error(f"Error in {component}: {error_type} - {error}")
    
    def record_agent_created(self, agent_type: str = "default"):
        """Record agent creation"""
        self.increment_counter(
            "agents_created_total",
            labels={"agent_type": agent_type}
        )
    
    def record_agent_fitness(self, fitness: float, generation: int):
        """Record agent fitness score"""
        self.observe_histogram(
            "agent_fitness_score",
            fitness,
            labels={"generation": str(generation)}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform monitoring health check"""
        try:
            # Count metrics
            metric_count = len(self.metrics)
            custom_metric_count = sum(len(m) for m in self.custom_metrics.values())
            
            # Check pushgateway if configured
            pushgateway_healthy = True
            if self.pushgateway_url:
                # Simple check - in production would do actual health check
                pushgateway_healthy = self._push_task and not self._push_task.done()
            
            return {
                "status": "healthy",
                "service": self.service_name,
                "metrics": metric_count,
                "custom_metrics": custom_metric_count,
                "alert_rules": len(self.alert_rules),
                "pushgateway_healthy": pushgateway_healthy,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Monitoring health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }