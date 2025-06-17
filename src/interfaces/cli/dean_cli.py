"""Main CLI entry point for DEAN orchestration."""

import click
import asyncio
from .interactive import run_interactive_cli


@click.group()
@click.version_option(version='0.1.0', prog_name='dean')
def cli():
    """DEAN Orchestration CLI - Coordinate the Distributed Evolutionary Agent Network."""
    pass


@cli.command()
def interactive():
    """Start interactive CLI session."""
    run_interactive_cli()


@cli.command()
@click.option('--check-only', is_flag=True, help='Only check prerequisites')
def deploy(check_only):
    """Deploy the DEAN system."""
    from ...orchestration import SystemDeployer
    
    async def run_deploy():
        deployer = SystemDeployer()
        if check_only:
            deployer.config.check_only = True
        result = await deployer.deploy()
        
        if result.ready:
            click.echo("✓ System deployed successfully!")
        else:
            click.echo("✗ Deployment failed")
            for error in result.errors:
                click.echo(f"  - {error}")
    
    asyncio.run(run_deploy())


@cli.command()
def status():
    """Check system status."""
    from ...integration import create_service_pool
    
    async def check_status():
        async with create_service_pool() as pool:
            health = await pool.health.check_all_services()
            
            click.echo("\nDEAN System Status")
            click.echo("=" * 40)
            
            for service, status in health['services'].items():
                if status.get('status') == 'healthy':
                    click.echo(f"✓ {service}: Healthy")
                else:
                    click.echo(f"✗ {service}: Unhealthy - {status.get('error', 'Unknown')}")
            
            click.echo(f"\nOverall Status: {health['status'].upper()}")
    
    asyncio.run(check_status())


@cli.group()
def evolution():
    """Manage evolution trials."""
    pass


@evolution.command()
@click.argument('repository')
@click.option('--generations', default=5, help='Number of generations')
@click.option('--population', default=10, help='Population size')
def start(repository, generations, population):
    """Start an evolution trial."""
    from ...orchestration import EvolutionTrialCoordinator
    
    async def run_trial():
        coordinator = EvolutionTrialCoordinator()
        
        click.echo(f"Starting evolution trial for: {repository}")
        click.echo(f"Generations: {generations}, Population: {population}")
        
        async with coordinator:
            result = await coordinator.run_trial(
                repository,
                config_overrides={
                    'generations': generations,
                    'population_size': population
                }
            )
            
            if result.status == 'completed':
                click.echo(f"✓ Trial completed: {result.trial_id}")
                click.echo(f"  Improvements: {len(result.improvements)}")
            else:
                click.echo(f"✗ Trial failed: {result.status}")
                for error in result.errors:
                    click.echo(f"  - {error}")
    
    asyncio.run(run_trial())


@evolution.command()
def list():
    """List recent evolution trials."""
    from ...integration import create_service_pool
    
    async def list_trials():
        async with create_service_pool() as pool:
            try:
                # Get recent evolution results
                response = await pool.evolution.get_evolution_results(limit=10)
                
                if not response:
                    click.echo("No evolution trials found")
                    return
                
                click.echo("\nRecent Evolution Trials")
                click.echo("=" * 60)
                click.echo(f"{'Trial ID':<20} {'Status':<12} {'Repository':<20} {'Score':<8}")
                click.echo("-" * 60)
                
                for trial in response:
                    click.echo(
                        f"{trial.get('trial_id', 'N/A'):<20} "
                        f"{trial.get('status', 'unknown'):<12} "
                        f"{trial.get('repository', 'N/A'):<20} "
                        f"{trial.get('best_score', 0):<8.2f}"
                    )
                    
            except Exception as e:
                click.echo(f"Error fetching trials: {e}")
    
    asyncio.run(list_trials())


@cli.group()
def config():
    """Manage DEAN configuration."""
    pass


@config.command()
def show():
    """Show current configuration."""
    import yaml
    from pathlib import Path
    
    config_file = Path.home() / ".dean" / "config.yaml"
    
    if not config_file.exists():
        click.echo("No configuration file found. Using default settings.")
        click.echo(f"Configuration would be loaded from: {config_file}")
        return
    
    with open(config_file) as f:
        config_data = yaml.safe_load(f)
    
    click.echo("\nCurrent Configuration")
    click.echo("=" * 40)
    click.echo(yaml.dump(config_data, default_flow_style=False))


@config.command()
@click.option('--indexagent-url', help='IndexAgent API URL')
@click.option('--airflow-url', help='Airflow API URL')
@click.option('--evolution-url', help='Evolution API URL')
def set(indexagent_url, airflow_url, evolution_url):
    """Update configuration values."""
    import yaml
    from pathlib import Path
    
    config_file = Path.home() / ".dean" / "config.yaml"
    config_file.parent.mkdir(exist_ok=True)
    
    # Load existing config or create new
    if config_file.exists():
        with open(config_file) as f:
            config_data = yaml.safe_load(f) or {}
    else:
        config_data = {}
    
    # Update provided values
    if 'services' not in config_data:
        config_data['services'] = {}
    
    if indexagent_url:
        config_data['services']['indexagent_url'] = indexagent_url
        click.echo(f"✓ Updated IndexAgent URL: {indexagent_url}")
    
    if airflow_url:
        config_data['services']['airflow_url'] = airflow_url
        click.echo(f"✓ Updated Airflow URL: {airflow_url}")
    
    if evolution_url:
        config_data['services']['evolution_url'] = evolution_url
        click.echo(f"✓ Updated Evolution URL: {evolution_url}")
    
    # Save config
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    click.echo(f"\nConfiguration saved to: {config_file}")


if __name__ == '__main__':
    cli()