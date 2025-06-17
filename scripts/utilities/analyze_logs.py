#!/usr/bin/env python3
"""
Log analysis tool for DEAN orchestration system.

Analyzes logs to identify patterns, errors, and performance issues.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import gzip
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import track

console = Console()

# Log patterns
LOG_PATTERNS = {
    'timestamp': re.compile(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})'),
    'level': re.compile(r'\b(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)\b'),
    'service': re.compile(r'service[_\s]*[:=]\s*"?([^"\s,]+)"?'),
    'error': re.compile(r'(error|exception|traceback|failed)', re.IGNORECASE),
    'api_call': re.compile(r'(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)\s+(\d{3})'),
    'duration': re.compile(r'duration[_\s]*[:=]\s*(\d+(?:\.\d+)?)\s*(?:ms|milliseconds)?'),
    'memory': re.compile(r'memory[_\s]*[:=]\s*(\d+(?:\.\d+)?)\s*(?:MB|mb)'),
}


class LogAnalyzer:
    """Analyzes log files for patterns and issues."""
    
    def __init__(self):
        self.logs = []
        self.errors = []
        self.api_calls = []
        self.performance_metrics = []
        
    def read_log_file(self, file_path: Path) -> List[str]:
        """Read log file, handling gzip compression."""
        lines = []
        
        if file_path.suffix == '.gz':
            with gzip.open(file_path, 'rt') as f:
                lines = f.readlines()
        else:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
        return lines
        
    def parse_log_line(self, line: str) -> Dict[str, any]:
        """Parse a single log line."""
        entry = {'raw': line.strip()}
        
        # Try to parse as JSON first
        if line.strip().startswith('{'):
            try:
                entry.update(json.loads(line))
                return entry
            except json.JSONDecodeError:
                pass
                
        # Fall back to regex parsing
        for key, pattern in LOG_PATTERNS.items():
            match = pattern.search(line)
            if match:
                if key == 'api_call':
                    entry['method'] = match.group(1)
                    entry['endpoint'] = match.group(2)
                    entry['status_code'] = int(match.group(3))
                elif key in ['duration', 'memory']:
                    entry[key] = float(match.group(1))
                else:
                    entry[key] = match.group(1)
                    
        return entry
        
    def analyze_files(self, file_paths: List[Path]):
        """Analyze multiple log files."""
        total_lines = 0
        
        for file_path in track(file_paths, description="Analyzing log files..."):
            if not file_path.exists():
                console.print(f"[yellow]Warning: File not found: {file_path}[/yellow]")
                continue
                
            lines = self.read_log_file(file_path)
            total_lines += len(lines)
            
            for line in lines:
                entry = self.parse_log_line(line)
                self.logs.append(entry)
                
                # Categorize entries
                if entry.get('level') in ['ERROR', 'CRITICAL']:
                    self.errors.append(entry)
                    
                if 'method' in entry and 'endpoint' in entry:
                    self.api_calls.append(entry)
                    
                if 'duration' in entry or 'memory' in entry:
                    self.performance_metrics.append(entry)
                    
        console.print(f"\n[green]Analyzed {total_lines:,} log lines from {len(file_paths)} file(s)[/green]")
        
    def get_error_summary(self) -> Dict[str, any]:
        """Summarize errors found in logs."""
        if not self.errors:
            return {'total': 0, 'by_service': {}, 'top_errors': []}
            
        # Group by service
        by_service = defaultdict(list)
        for error in self.errors:
            service = error.get('service', 'unknown')
            by_service[service].append(error)
            
        # Find common error messages
        error_messages = []
        for error in self.errors:
            msg = error.get('message', error.get('raw', ''))
            # Clean up the message
            msg = re.sub(r'\b\d+\b', 'N', msg)  # Replace numbers with N
            msg = re.sub(r'[0-9a-f]{8,}', 'HASH', msg)  # Replace hashes
            error_messages.append(msg)
            
        message_counts = Counter(error_messages)
        
        return {
            'total': len(self.errors),
            'by_service': {k: len(v) for k, v in by_service.items()},
            'top_errors': message_counts.most_common(10),
            'error_rate': len(self.errors) / len(self.logs) if self.logs else 0
        }
        
    def get_api_performance(self) -> Dict[str, any]:
        """Analyze API performance metrics."""
        if not self.api_calls:
            return {'total_calls': 0, 'by_endpoint': {}, 'by_status': {}}
            
        # Group by endpoint
        by_endpoint = defaultdict(list)
        for call in self.api_calls:
            endpoint = call.get('endpoint', 'unknown')
            # Normalize endpoint (remove IDs)
            endpoint = re.sub(r'/[0-9a-f-]{36}', '/{id}', endpoint)
            endpoint = re.sub(r'/\d+', '/{id}', endpoint)
            by_endpoint[endpoint].append(call)
            
        # Calculate statistics per endpoint
        endpoint_stats = {}
        for endpoint, calls in by_endpoint.items():
            durations = [c.get('duration', 0) for c in calls if 'duration' in c]
            status_codes = [c.get('status_code', 0) for c in calls]
            
            endpoint_stats[endpoint] = {
                'count': len(calls),
                'avg_duration': sum(durations) / len(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0,
                'success_rate': sum(1 for s in status_codes if 200 <= s < 300) / len(status_codes) if status_codes else 0,
                'status_distribution': dict(Counter(status_codes))
            }
            
        # Overall status distribution
        all_status_codes = [c.get('status_code', 0) for c in self.api_calls]
        
        return {
            'total_calls': len(self.api_calls),
            'by_endpoint': endpoint_stats,
            'by_status': dict(Counter(all_status_codes)),
            'overall_success_rate': sum(1 for s in all_status_codes if 200 <= s < 300) / len(all_status_codes) if all_status_codes else 0
        }
        
    def get_performance_analysis(self) -> Dict[str, any]:
        """Analyze performance metrics."""
        if not self.performance_metrics:
            return {'duration': {}, 'memory': {}}
            
        durations = [m.get('duration', 0) for m in self.performance_metrics if 'duration' in m]
        memory_usage = [m.get('memory', 0) for m in self.performance_metrics if 'memory' in m]
        
        def calculate_stats(values):
            if not values:
                return {}
            values = sorted(values)
            return {
                'min': values[0],
                'max': values[-1],
                'avg': sum(values) / len(values),
                'median': values[len(values) // 2],
                'p95': values[int(len(values) * 0.95)] if len(values) > 20 else values[-1],
                'p99': values[int(len(values) * 0.99)] if len(values) > 100 else values[-1],
            }
            
        return {
            'duration': calculate_stats(durations),
            'memory': calculate_stats(memory_usage),
            'slow_operations': [
                m for m in self.performance_metrics 
                if m.get('duration', 0) > 1000  # Operations over 1 second
            ][:10]
        }
        
    def get_timeline_analysis(self) -> Dict[str, any]:
        """Analyze log timeline."""
        if not self.logs:
            return {}
            
        # Parse timestamps
        timestamps = []
        for log in self.logs:
            if 'timestamp' in log:
                try:
                    ts = datetime.fromisoformat(log['timestamp'].replace('T', ' '))
                    timestamps.append(ts)
                except:
                    pass
                    
        if not timestamps:
            return {}
            
        timestamps.sort()
        
        # Calculate log rate over time
        start_time = timestamps[0]
        end_time = timestamps[-1]
        duration = (end_time - start_time).total_seconds()
        
        # Group by hour
        hourly_counts = defaultdict(int)
        for ts in timestamps:
            hour_key = ts.strftime('%Y-%m-%d %H:00')
            hourly_counts[hour_key] += 1
            
        return {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_hours': duration / 3600,
            'total_logs': len(timestamps),
            'avg_logs_per_hour': len(timestamps) / (duration / 3600) if duration > 0 else 0,
            'peak_hour': max(hourly_counts.items(), key=lambda x: x[1]) if hourly_counts else None
        }


def render_error_summary(summary: Dict[str, any]):
    """Render error summary table."""
    if summary['total'] == 0:
        console.print("[green]No errors found![/green]")
        return
        
    # Error overview
    panel = Panel(
        f"Total Errors: [red]{summary['total']}[/red]\n"
        f"Error Rate: [yellow]{summary['error_rate']:.2%}[/yellow]",
        title="Error Summary",
        border_style="red"
    )
    console.print(panel)
    
    # Errors by service
    if summary['by_service']:
        table = Table(title="Errors by Service")
        table.add_column("Service", style="cyan")
        table.add_column("Count", justify="right", style="red")
        
        for service, count in sorted(summary['by_service'].items(), key=lambda x: x[1], reverse=True):
            table.add_row(service, str(count))
            
        console.print(table)
        
    # Top error messages
    if summary['top_errors']:
        console.print("\n[bold]Top Error Messages:[/bold]")
        for i, (msg, count) in enumerate(summary['top_errors'][:5], 1):
            console.print(f"{i}. ({count}x) {msg[:100]}{'...' if len(msg) > 100 else ''}")


def render_api_performance(analysis: Dict[str, any]):
    """Render API performance analysis."""
    if analysis['total_calls'] == 0:
        console.print("[yellow]No API calls found in logs[/yellow]")
        return
        
    # Overview
    panel = Panel(
        f"Total API Calls: [blue]{analysis['total_calls']}[/blue]\n"
        f"Overall Success Rate: [green]{analysis['overall_success_rate']:.1%}[/green]",
        title="API Performance",
        border_style="blue"
    )
    console.print(panel)
    
    # Top endpoints
    table = Table(title="Endpoint Statistics")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Calls", justify="right")
    table.add_column("Avg Duration (ms)", justify="right")
    table.add_column("Success Rate", justify="right")
    
    sorted_endpoints = sorted(
        analysis['by_endpoint'].items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )[:10]
    
    for endpoint, stats in sorted_endpoints:
        success_rate = f"{stats['success_rate']:.1%}"
        if stats['success_rate'] < 0.95:
            success_rate = f"[red]{success_rate}[/red]"
        else:
            success_rate = f"[green]{success_rate}[/green]"
            
        table.add_row(
            endpoint,
            str(stats['count']),
            f"{stats['avg_duration']:.1f}",
            success_rate
        )
        
    console.print(table)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze DEAN log files")
    
    parser.add_argument('files', nargs='+', help='Log files to analyze')
    parser.add_argument('--errors-only', action='store_true',
                       help='Show only error analysis')
    parser.add_argument('--api-only', action='store_true',
                       help='Show only API performance analysis')
    parser.add_argument('--timeline', action='store_true',
                       help='Show timeline analysis')
    parser.add_argument('--output', choices=['console', 'json'],
                       default='console', help='Output format')
    
    args = parser.parse_args()
    
    # Convert file paths
    file_paths = [Path(f) for f in args.files]
    
    # Create analyzer
    analyzer = LogAnalyzer()
    
    # Analyze files
    analyzer.analyze_files(file_paths)
    
    # Get analyses
    error_summary = analyzer.get_error_summary()
    api_performance = analyzer.get_api_performance()
    performance_analysis = analyzer.get_performance_analysis()
    timeline = analyzer.get_timeline_analysis()
    
    if args.output == 'json':
        # JSON output
        output = {
            'summary': {
                'total_logs': len(analyzer.logs),
                'total_errors': error_summary['total'],
                'total_api_calls': api_performance['total_calls']
            },
            'errors': error_summary,
            'api_performance': api_performance,
            'performance': performance_analysis,
            'timeline': timeline
        }
        print(json.dumps(output, indent=2))
    else:
        # Console output
        console.print("\n[bold]Log Analysis Report[/bold]")
        console.print("=" * 50)
        
        if not args.api_only:
            console.print("\n")
            render_error_summary(error_summary)
            
        if not args.errors_only:
            console.print("\n")
            render_api_performance(api_performance)
            
        if args.timeline and timeline:
            console.print("\n[bold]Timeline Analysis:[/bold]")
            console.print(f"Period: {timeline['start_time']} to {timeline['end_time']}")
            console.print(f"Duration: {timeline['duration_hours']:.1f} hours")
            console.print(f"Average logs/hour: {timeline['avg_logs_per_hour']:.0f}")
            if timeline.get('peak_hour'):
                console.print(f"Peak hour: {timeline['peak_hour'][0]} ({timeline['peak_hour'][1]} logs)")


if __name__ == "__main__":
    main()