"""Command-line interface for the migration tool."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from hooting_yard_migration import (
    Config,
    ArchiveRetriever,
    VideoConverter,
    YouTubeUploader,
    StateManager,
)
from hooting_yard_migration.utils.logging import setup_logging
from hooting_yard_migration.keyword_analysis import analyze_keywords

console = Console()


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config.yaml",
    help="Configuration file path",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, config: Path, verbose: bool) -> None:
    """Hooting Yard Migration Tool - Migrate episodes from Archive.org to YouTube."""
    # Setup logging
    setup_logging(verbose=verbose)

    # Load configuration
    cfg = Config.from_yaml(config)
    # Note: Not using Config.from_env() to avoid overriding YAML config
    cfg.ensure_directories()

    # Store in context
    ctx.obj = {
        "config": cfg,
        "state_manager": StateManager(cfg.paths.processed),
    }


@cli.command()
@click.pass_context
def discover(ctx: click.Context) -> None:
    """Discover all episodes from Archive.org."""
    config: Config = ctx.obj["config"]
    state_manager: StateManager = ctx.obj["state_manager"]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Discovering episodes...", total=None)

        retriever = ArchiveRetriever(config)
        episodes = asyncio.run(retriever.discover_episodes())

        progress.update(task, completed=True)

    # Display results
    table = Table(title=f"Discovered {len(episodes)} Episodes")
    table.add_column("Date", style="cyan")
    table.add_column("Identifier", style="green")
    table.add_column("Title")

    for episode in episodes[:10]:  # Show first 10
        table.add_row(
            str(episode.date)[:10],
            episode.identifier,
            episode.title[:50] + "..." if len(episode.title) > 50 else episode.title,
        )

    if len(episodes) > 10:
        table.add_row("...", "...", f"... and {len(episodes) - 10} more")

    console.print(table)

    # Update state
    for episode in episodes:
        state_manager.register_episode(episode)

    console.print(f"✅ Registered {len(episodes)} episodes in state database")


@cli.command()
@click.option("--limit", "-l", type=int, help="Limit number of downloads")
@click.option("--start-date", type=str, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", type=str, help="End date (YYYY-MM-DD)")
@click.pass_context
def download(
    ctx: click.Context,
    limit: Optional[int],
    start_date: Optional[str],
    end_date: Optional[str],
) -> None:
    """Download episodes from Archive.org."""
    config: Config = ctx.obj["config"]
    state_manager: StateManager = ctx.obj["state_manager"]

    # Get episodes to download
    episodes = state_manager.get_pending_downloads(
        limit=limit,
        start_date=start_date,
        end_date=end_date,
    )

    if not episodes:
        console.print("No episodes to download")
        return

    console.print(f"Downloading {len(episodes)} episodes...")

    retriever = ArchiveRetriever(config)

    with Progress(console=console) as progress:
        download_task = progress.add_task(
            "[cyan]Downloading episodes...", total=len(episodes)
        )

        for episode in episodes:
            try:
                path = asyncio.run(retriever.download_episode(episode))
                state_manager.mark_downloaded(episode.identifier, path)
                progress.update(download_task, advance=1)
                console.print(f"✅ Downloaded: {episode.identifier}")
            except Exception as e:
                console.print(f"❌ Failed to download {episode.identifier}: {e}")
                state_manager.mark_failed(episode.identifier, str(e))


@cli.command()
@click.option("--limit", "-l", type=int, help="Limit number of conversions")
@click.pass_context
def convert(ctx: click.Context, limit: Optional[int]) -> None:
    """Convert audio files to video format."""
    config: Config = ctx.obj["config"]
    state_manager: StateManager = ctx.obj["state_manager"]

    # Get episodes to convert
    episodes = state_manager.get_pending_conversions(limit=limit)

    if not episodes:
        console.print("No episodes to convert")
        return

    console.print(f"Converting {len(episodes)} episodes...")

    converter = VideoConverter(config)

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Converting episodes...", total=len(episodes))

        for episode in episodes:
            try:
                result = asyncio.run(converter.convert_episode(episode))
                state_manager.mark_converted(episode.identifier, result.output_video)
                progress.update(task, advance=1)
                console.print(f"✅ Converted: {episode.identifier}")
            except Exception as e:
                console.print(f"❌ Failed to convert {episode.identifier}: {e}")
                state_manager.mark_failed(episode.identifier, str(e))


@cli.command()
@click.option("--limit", "-l", type=int, help="Limit number of uploads")
@click.option("--dry-run", is_flag=True, help="Simulate upload without executing")
@click.pass_context
def upload(ctx: click.Context, limit: Optional[int], dry_run: bool) -> None:
    """Upload videos to YouTube."""
    config: Config = ctx.obj["config"]
    state_manager: StateManager = ctx.obj["state_manager"]

    # Get episodes to upload
    episodes = state_manager.get_pending_uploads(limit=limit)

    if not episodes:
        console.print("No episodes to upload")
        return

    if dry_run:
        console.print(f"[yellow]DRY RUN - Would upload {len(episodes)} episodes")
        for episode in episodes[:5]:
            console.print(f"  - {episode.identifier}: {episode.title}")
        return

    console.print(f"Uploading {len(episodes)} episodes...")

    uploader = YouTubeUploader(config)

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Uploading episodes...", total=len(episodes))

        for episode in episodes:
            try:
                video_id = asyncio.run(uploader.upload_video(episode))
                state_manager.mark_uploaded(episode.identifier, video_id)
                progress.update(task, advance=1)
                console.print(f"✅ Uploaded: {episode.identifier} -> {video_id}")
            except Exception as e:
                console.print(f"❌ Failed to upload {episode.identifier}: {e}")
                state_manager.mark_failed(episode.identifier, str(e))


@cli.command()
@click.option("--dry-run", is_flag=True, help="Simulate without executing")
@click.pass_context
def run(ctx: click.Context, dry_run: bool) -> None:
    """Run the complete migration pipeline."""
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made")

    # Run all stages
    ctx.invoke(discover)

    if not dry_run:
        ctx.invoke(download)
        ctx.invoke(convert)
        ctx.invoke(upload)


@cli.command()
@click.pass_context
def resume(ctx: click.Context) -> None:
    """Resume processing from last known state."""
    state_manager: StateManager = ctx.obj["state_manager"]

    # Find incomplete work
    stats = state_manager.get_statistics()

    console.print("Resuming from last state...")
    console.print(f"  Downloaded: {stats['downloaded']}")
    console.print(f"  Converted: {stats['converted']}")
    console.print(f"  Uploaded: {stats['uploaded']}")
    console.print(f"  Failed: {stats['failed']}")

    # Resume each stage
    if stats["pending_downloads"] > 0:
        ctx.invoke(download)

    if stats["pending_conversions"] > 0:
        ctx.invoke(convert)

    if stats["pending_uploads"] > 0:
        ctx.invoke(upload)


@cli.command()
@click.pass_context
def report(ctx: click.Context) -> None:
    """Generate progress report."""
    state_manager: StateManager = ctx.obj["state_manager"]

    stats = state_manager.get_statistics()
    report = state_manager.generate_report()

    # Display summary table
    table = Table(title="Migration Progress Report")
    table.add_column("Stage", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")

    total = stats["total"]
    for stage, count in stats.items():
        if stage != "total":
            percentage = (count / total * 100) if total > 0 else 0
            table.add_row(stage.replace("_", " ").title(), str(count), f"{percentage:.1f}%")

    console.print(table)

    # Save detailed report
    report_path = Path("reports") / "migration_report.html"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report)

    console.print(f"✅ Detailed report saved to {report_path}")


@cli.command()
@click.pass_context
def verify(ctx: click.Context) -> None:
    """Verify all downloaded and converted files."""
    config: Config = ctx.obj["config"]
    state_manager: StateManager = ctx.obj["state_manager"]

    console.print("Verifying files...")

    errors = []

    # Verify downloads
    for episode in state_manager.get_downloaded_episodes():
        if not episode.audio_file or not episode.audio_file.exists():
            errors.append(f"Missing audio file: {episode.identifier}")

    # Verify conversions
    for episode in state_manager.get_converted_episodes():
        if not episode.video_file or not episode.video_file.exists():
            errors.append(f"Missing video file: {episode.identifier}")

    if errors:
        console.print(f"[red]Found {len(errors)} errors:")
        for error in errors[:10]:
            console.print(f"  - {error}")
    else:
        console.print("✅ All files verified successfully")


@cli.command()
@click.pass_context
def keywords(ctx: click.Context) -> None:
    """Analyze word frequencies across all episodes for keyword extraction."""
    config: Config = ctx.obj["config"]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing keyword frequencies...", total=None)

        try:
            # Config now automatically resolves paths relative to config.yaml
            keywords_file = analyze_keywords(str(config.paths.processed))
            progress.update(task, completed=True)

            if keywords_file:
                console.print(f"✅ Keyword analysis complete")
                console.print(f"📁 Results saved to: {keywords_file}")
            else:
                console.print("❌ No episodes found for keyword analysis")

        except Exception as e:
            console.print(f"❌ Keyword analysis failed: {e}")
            raise


def main() -> None:
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()