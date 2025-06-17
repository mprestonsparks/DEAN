"""Interactive CLI for DEAN orchestration.

Adapted from dean-agent-workspace/interact_with_dean.py
Provides interactive interface without direct repository dependencies.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

import click
import structlog
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...integration import ServicePool, create_service_pool
from ...orchestration import EvolutionTrialCoordinator, SystemDeployer

# Configure structured logging
logger = structlog.get_logger(__name__)
console = Console()


class InteractiveCLI:
    """Interactive command-line interface for DEAN system."""
    
    def __init__(self):
        """Initialize interactive CLI."""
        self.pool: Optional[ServicePool] = None
        self.logger = logger.bind(component="interactive_cli")
    
    async def start(self):
        """Start interactive CLI session."""
        console.print("\n[bold cyan]DEAN Orchestration Interactive CLI[/bold cyan]")
        console.print("Type 'help' for available commands or 'exit' to quit.\n")
        
        async with create_service_pool() as self.pool:
            while True:
                try:
                    command = console.input("[bold green]dean>[/bold green] ")
                    
                    if command.lower() in ['exit', 'quit']:
                        break
                    
                    await self._handle_command(command)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
    
    async def _handle_command(self, command: str):
        """Handle user command.
        
        Args:
            command: User input command
        """
        parts = command.strip().split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        commands = {
            'help': self._show_help,
            'status': self._show_status,
            'health': self._check_health,
            'deploy': self._deploy_system,
            'evolution': self._manage_evolution,
            'agents': self._manage_agents,
            'patterns': self._show_patterns,
            'metrics': self._show_metrics,
        }
        
        if cmd in commands:
            await commands[cmd](args)
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")
            console.print("Type 'help' for available commands.")
    
    async def _show_help(self, args: list):
        """Show help information."""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [bold]help[/bold]                          Show this help message
  [bold]status[/bold]                        Show system status
  [bold]health[/bold]                        Check service health
  [bold]deploy[/bold] [--check-only]         Deploy DEAN system
  [bold]evolution start[/bold] <repo>        Start evolution trial
  [bold]evolution status[/bold] [trial_id]   Show evolution status
  [bold]evolution stop[/bold] [trial_id]     Stop evolution trial
  [bold]agents list[/bold]                   List active agents
  [bold]agents show[/bold] <agent_id>        Show agent details
  [bold]patterns list[/bold]                 List discovered patterns
  [bold]metrics show[/bold]                  Show system metrics
  [bold]exit[/bold]                          Exit the CLI
"""
        console.print(help_text)
    
    async def _show_status(self, args: list):
        """Show system status."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Checking system status...", total=None)
            
            # Get health status
            health = await self.pool.health.check_all_services()
            
            progress.remove_task(task)
        
        # Create status table
        table = Table(title="DEAN System Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        for service, status in health['services'].items():
            status_text = "✓ Healthy" if status.get('status') == 'healthy' else "✗ Unhealthy"
            style = "green" if status.get('status') == 'healthy' else "red"
            details = status.get('error', '') if status.get('error') else ''
            table.add_row(service, status_text, details, style=style)
        
        console.print(table)
        console.print(f"\n[bold]Overall Status:[/bold] {health['status'].upper()}")
    
    async def _check_health(self, args: list):
        """Check service health."""
        await self._show_status(args)  # Reuse status display
    
    async def _deploy_system(self, args: list):
        """Deploy DEAN system."""
        check_only = '--check-only' in args
        
        console.print("[cyan]Starting system deployment...[/cyan]")
        
        deployer = SystemDeployer()
        if check_only:
            deployer.config.check_only = True
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Deploying system...", total=None)
            
            result = await deployer.deploy()
            
            progress.remove_task(task)
        
        if result.ready:
            console.print("[green]✓ System deployed successfully![/green]")
        else:
            console.print("[red]✗ Deployment failed[/red]")
            for error in result.errors:
                console.print(f"  - {error}")
    
    async def _manage_evolution(self, args: list):
        """Manage evolution trials."""
        if not args:
            console.print("[red]Usage: evolution <start|status|stop> [options][/red]")
            return
        
        action = args[0]
        
        if action == 'start':
            if len(args) < 2:
                console.print("[red]Usage: evolution start <repository_path>[/red]")
                return
            
            repo_path = args[1]
            console.print(f"[cyan]Starting evolution trial for: {repo_path}[/cyan]")
            
            coordinator = EvolutionTrialCoordinator(self.pool)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Running evolution trial...", total=None)
                
                result = await coordinator.run_trial(repo_path)
                
                progress.remove_task(task)
            
            # Display results
            if result.status == 'completed':
                console.print(f"[green]✓ Evolution trial completed: {result.trial_id}[/green]")
                console.print(f"  Improvements: {len(result.improvements)}")
                console.print(f"  Patterns: {len(result.metrics.get('patterns', []))}")
            else:
                console.print(f"[red]✗ Evolution trial failed: {result.status}[/red]")
                for error in result.errors:
                    console.print(f"  - {error}")
        
        elif action == 'status':
            trial_id = args[1] if len(args) > 1 else None
            
            try:
                status = await self.pool.evolution.get_evolution_status(trial_id)
                
                table = Table(title="Evolution Status")
                table.add_column("Property", style="cyan")
                table.add_column("Value")
                
                for key, value in status.items():
                    table.add_row(key, str(value))
                
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]Failed to get status: {str(e)}[/red]")
        
        elif action == 'stop':
            trial_id = args[1] if len(args) > 1 else None
            
            try:
                result = await self.pool.evolution.stop_evolution(trial_id)
                console.print("[green]✓ Evolution stopped[/green]")
                
            except Exception as e:
                console.print(f"[red]Failed to stop evolution: {str(e)}[/red]")
        
        else:
            console.print(f"[red]Unknown evolution action: {action}[/red]")
    
    async def _manage_agents(self, args: list):
        """Manage agents."""
        if not args:
            console.print("[red]Usage: agents <list|show> [options][/red]")
            return
        
        action = args[0]
        
        if action == 'list':
            try:
                agents = await self.pool.indexagent.list_agents(limit=20)
                
                table = Table(title="Active Agents")
                table.add_column("ID", style="cyan")
                table.add_column("Name")
                table.add_column("Type")
                table.add_column("Status")
                
                for agent in agents:
                    table.add_row(
                        agent.get('id', 'N/A'),
                        agent.get('name', 'N/A'),
                        agent.get('type', 'N/A'),
                        agent.get('status', 'N/A')
                    )
                
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]Failed to list agents: {str(e)}[/red]")
        
        elif action == 'show':
            if len(args) < 2:
                console.print("[red]Usage: agents show <agent_id>[/red]")
                return
            
            agent_id = args[1]
            
            try:
                agent = await self.pool.indexagent.get_agent(agent_id)
                
                table = Table(title=f"Agent Details: {agent_id}")
                table.add_column("Property", style="cyan")
                table.add_column("Value")
                
                for key, value in agent.items():
                    table.add_row(key, str(value))
                
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]Failed to get agent: {str(e)}[/red]")
        
        else:
            console.print(f"[red]Unknown agents action: {action}[/red]")
    
    async def _show_patterns(self, args: list):
        """Show discovered patterns."""
        try:
            patterns = await self.pool.evolution.get_patterns(min_effectiveness=0.5)
            
            table = Table(title="Discovered Patterns")
            table.add_column("ID", style="cyan")
            table.add_column("Type")
            table.add_column("Effectiveness")
            table.add_column("Discovered")
            
            for pattern in patterns[:10]:  # Show top 10
                table.add_row(
                    pattern.get('id', 'N/A'),
                    pattern.get('type', 'N/A'),
                    f"{pattern.get('effectiveness', 0):.2%}",
                    pattern.get('discovered_at', 'N/A')
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Failed to get patterns: {str(e)}[/red]")
    
    async def _show_metrics(self, args: list):
        """Show system metrics."""
        try:
            metrics = await self.pool.evolution.get_metrics()
            
            console.print("[bold cyan]System Metrics:[/bold cyan]")
            console.print(metrics)
            
        except Exception as e:
            console.print(f"[red]Failed to get metrics: {str(e)}[/red]")


def run_interactive_cli():
    """Run the interactive CLI."""
    cli = InteractiveCLI()
    asyncio.run(cli.start())