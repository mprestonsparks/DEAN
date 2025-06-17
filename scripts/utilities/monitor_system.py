#!/usr/bin/env python3
"""
System monitoring tool for DEAN orchestration.

Provides real-time monitoring of all DEAN services with metrics collection,
alerting, and reporting capabilities.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
import structlog

# Configure logging
logger = structlog.get_logger()
console = Console()

class ServiceMonitor:
    """Monitors DEAN services and collects metrics."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.services = {
            'orchestration': config.get('orchestration_url', 'http://localhost:8082'),
            'indexagent': config.get('indexagent_url', 'http://localhost:8081'),
            'airflow': config.get('airflow_url', 'http://localhost:8080'),
            'evolution': config.get('evolution_url', 'http://localhost:8083'),
        }
        self.metrics_history: Dict[str, List[Dict]] = {
            service: [] for service in self.services
        }
        self.alert_thresholds = {
            'response_time': 2.0,  # seconds
            'error_rate': 0.1,     # 10%
            'cpu_usage': 0.8,      # 80%
            'memory_usage': 0.9,   # 90%
        }
        
    async def check_service_health(self, name: str, url: str) -> Dict[str, Any]:
        """Check health of a single service."""
        start_time = datetime.now()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health", timeout=5) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds()
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'name': name,
                            'status': 'healthy',
                            'response_time': response_time,
                            'details': data,
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        return {
                            'name': name,
                            'status': 'unhealthy',
                            'response_time': response_time,
                            'error': f'HTTP {response.status}',
                            'timestamp': datetime.now().isoformat()
                        }
                        
        except asyncio.TimeoutError:
            return {
                'name': name,
                'status': 'timeout',
                'error': 'Request timeout',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'name': name,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all services."""
        tasks = [
            self.check_service_health(name, url)
            for name, url in self.services.items()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Store in history
        for result in results:
            service_name = result['name']
            self.metrics_history[service_name].append(result)
            
            # Keep only last hour of data
            cutoff_time = datetime.now() - timedelta(hours=1)
            self.metrics_history[service_name] = [
                m for m in self.metrics_history[service_name]
                if datetime.fromisoformat(m['timestamp']) > cutoff_time
            ]
            
        return {
            'timestamp': datetime.now().isoformat(),
            'services': {r['name']: r for r in results},
            'summary': self._calculate_summary(results)
        }
        
    def _calculate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics."""
        healthy_count = sum(1 for r in results if r['status'] == 'healthy')
        total_count = len(results)
        
        avg_response_time = sum(
            r.get('response_time', 0) for r in results if 'response_time' in r
        ) / max(sum(1 for r in results if 'response_time' in r), 1)
        
        return {
            'health_percentage': (healthy_count / total_count * 100) if total_count > 0 else 0,
            'healthy_services': healthy_count,
            'total_services': total_count,
            'average_response_time': avg_response_time
        }
        
    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        
        for service_name, service_data in metrics['services'].items():
            # Response time alert
            if 'response_time' in service_data:
                if service_data['response_time'] > self.alert_thresholds['response_time']:
                    alerts.append({
                        'service': service_name,
                        'type': 'response_time',
                        'message': f"High response time: {service_data['response_time']:.2f}s",
                        'severity': 'warning'
                    })
                    
            # Service down alert
            if service_data['status'] != 'healthy':
                alerts.append({
                    'service': service_name,
                    'type': 'service_down',
                    'message': f"Service is {service_data['status']}",
                    'severity': 'critical'
                })
                
        return alerts


def create_dashboard_layout() -> Layout:
    """Create the dashboard layout."""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    layout["body"].split_row(
        Layout(name="services", ratio=2),
        Layout(name="metrics", ratio=1)
    )
    
    return layout


def render_services_table(services: Dict[str, Any]) -> Table:
    """Render services status table."""
    table = Table(title="Service Status", expand=True)
    
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Response Time", justify="right")
    table.add_column("Details")
    
    for name, data in services.items():
        status = data['status']
        
        # Color code status
        if status == 'healthy':
            status_text = Text(status.upper(), style="green")
        elif status == 'unhealthy':
            status_text = Text(status.upper(), style="red")
        else:
            status_text = Text(status.upper(), style="yellow")
            
        response_time = f"{data.get('response_time', 0):.3f}s" if 'response_time' in data else "N/A"
        
        details = data.get('error', 'OK')
        if 'details' in data and isinstance(data['details'], dict):
            details = json.dumps(data['details'], indent=2)[:50] + "..."
            
        table.add_row(name, status_text, response_time, details)
        
    return table


def render_metrics_panel(summary: Dict[str, Any], alerts: List[Dict]) -> Panel:
    """Render metrics summary panel."""
    content = []
    
    # Summary metrics
    content.append(f"[bold]System Health:[/bold] {summary['health_percentage']:.1f}%")
    content.append(f"[bold]Healthy Services:[/bold] {summary['healthy_services']}/{summary['total_services']}")
    content.append(f"[bold]Avg Response Time:[/bold] {summary['average_response_time']:.3f}s")
    
    # Alerts
    if alerts:
        content.append("\n[bold red]Alerts:[/bold red]")
        for alert in alerts[:5]:  # Show max 5 alerts
            icon = "🔴" if alert['severity'] == 'critical' else "🟡"
            content.append(f"{icon} {alert['service']}: {alert['message']}")
    else:
        content.append("\n[bold green]No active alerts[/bold green]")
        
    return Panel("\n".join(content), title="Metrics & Alerts", border_style="blue")


async def monitor_loop(monitor: ServiceMonitor, interval: int, output_format: str):
    """Main monitoring loop."""
    if output_format == 'dashboard':
        layout = create_dashboard_layout()
        
        with Live(layout, refresh_per_second=1, console=console) as live:
            while True:
                try:
                    # Collect metrics
                    metrics = await monitor.collect_metrics()
                    alerts = monitor.check_alerts(metrics)
                    
                    # Update dashboard
                    layout["header"].update(
                        Panel(
                            f"[bold]DEAN System Monitor[/bold] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            style="white on blue"
                        )
                    )
                    
                    layout["services"].update(render_services_table(metrics['services']))
                    layout["metrics"].update(render_metrics_panel(metrics['summary'], alerts))
                    
                    layout["footer"].update(
                        Panel(
                            f"Press Ctrl+C to exit | Refresh interval: {interval}s",
                            style="dim"
                        )
                    )
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error("Monitoring error", error=str(e))
                    
                await asyncio.sleep(interval)
                
    else:  # JSON output
        while True:
            try:
                metrics = await monitor.collect_metrics()
                alerts = monitor.check_alerts(metrics)
                
                output = {
                    'metrics': metrics,
                    'alerts': alerts
                }
                
                print(json.dumps(output, indent=2))
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("Monitoring error", error=str(e))
                
            await asyncio.sleep(interval)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor DEAN system services")
    
    parser.add_argument(
        '--orchestration-url',
        default='http://localhost:8082',
        help='Orchestration server URL'
    )
    parser.add_argument(
        '--indexagent-url',
        default='http://localhost:8081',
        help='IndexAgent API URL'
    )
    parser.add_argument(
        '--airflow-url',
        default='http://localhost:8080',
        help='Airflow API URL'
    )
    parser.add_argument(
        '--evolution-url',
        default='http://localhost:8083',
        help='Evolution API URL'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Monitoring interval in seconds'
    )
    parser.add_argument(
        '--output',
        choices=['dashboard', 'json'],
        default='dashboard',
        help='Output format'
    )
    
    args = parser.parse_args()
    
    # Create monitor configuration
    config = {
        'orchestration_url': args.orchestration_url,
        'indexagent_url': args.indexagent_url,
        'airflow_url': args.airflow_url,
        'evolution_url': args.evolution_url,
    }
    
    # Create and run monitor
    monitor = ServiceMonitor(config)
    
    try:
        asyncio.run(monitor_loop(monitor, args.interval, args.output))
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()