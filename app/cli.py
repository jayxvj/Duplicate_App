"""Command Line Interface for IADCS."""
from __future__ import annotations
import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.database.db import init_db
from app.database.repository import Repository
from app.scanner.directory_scanner import DirectoryScanner
from app.duplicate.candidate_matcher import CandidateMatcher
from app.duplicate.duplicate_detector import DuplicateDetector
from app.categorization.category_manager import CategoryManager
from app.removal.removal_manager import RemovalManager
from app.reporting.report_generator import ReportGenerator
from app.logging.audit_logger import AuditLogger

console = Console()


def format_bytes(bytes_count: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def cmd_scan(args: argparse.Namespace) -> None:
    init_db()
    repo = Repository()
    logger = AuditLogger()
    paths = args.path or []
    if not paths:
        console.print("[bold red]Error: No scan paths provided. Use --path <dir>[/bold red]")
        sys.exit(1)

    exclusions = args.exclude or []
    scan_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    console.print(Panel(f"[bold cyan]Starting IADCS Content-Based Scan[/bold cyan]\nScan ID: [green]{scan_id}[/green]\nTarget Paths: {', '.join(paths)}", expand=False))

    scanner = DirectoryScanner(exclusions=exclusions)
    apps = scanner.scan_directories([Path(p) for p in paths])

    if not apps:
        console.print("[yellow]No applications found in the specified paths.[/yellow]")
        return

    console.print(f"[green]Discovered {len(apps)} application candidates. Computing content fingerprints...[/green]")

    matcher = CandidateMatcher()
    apps = matcher.process_applications(apps)

    cat_mgr = CategoryManager(repo)
    apps = cat_mgr.categorize_applications(apps)

    # Save apps to repository
    for app in apps:
        app.scan_id = scan_id
        repo.save_application(app)

    detector = DuplicateDetector(auto_verify_bytes=True)
    dup_groups = detector.detect_duplicates(apps)

    repo.clear_duplicate_groups()
    for grp in dup_groups:
        repo.save_duplicate_group(grp)

    duration = time.time() - start_time
    total_size = sum(a.total_size for a in apps)
    reclaimable = sum(g.reclaimable_size for g in dup_groups)
    cat_counts = cat_mgr.get_category_counts(apps)

    repo.record_scan(
        scan_id=scan_id,
        started_at=time.ctime(start_time),
        completed_at=time.ctime(),
        total_apps=len(apps),
        duplicate_groups=len(dup_groups),
        total_size=total_size,
        reclaimable_size=reclaimable,
        paths_scanned=paths,
    )

    logger.log("scan_completed", details={"scan_id": scan_id, "apps": len(apps), "duplicate_groups": len(dup_groups), "reclaimable": reclaimable})

    # Summary table
    table = Table(title=f"Scan Summary (ID: {scan_id})")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")
    table.add_row("Total Applications Found", str(len(apps)))
    table.add_row("Total Files Scanned", str(sum(a.file_count for a in apps)))
    table.add_row("Duplicate Groups", str(len(dup_groups)))
    table.add_row("Total Size", format_bytes(total_size))
    table.add_row("Potential Storage Reclaimable", format_bytes(reclaimable))
    table.add_row("Scan Duration", f"{duration:.2f} seconds")
    console.print(table)


def cmd_duplicates(args: argparse.Namespace) -> None:
    init_db()
    repo = Repository()
    groups = repo.get_all_duplicate_groups()

    if not groups:
        console.print("[green]No duplicate application groups detected.[/green]")
        return

    console.print(f"[bold cyan]Found {len(groups)} Duplicate Application Groups:[/bold cyan]\n")
    for idx, grp in enumerate(groups, 1):
        table = Table(title=f"Group #{idx} (Reclaimable: {format_bytes(grp.reclaimable_size)}, Status: {grp.verification_status})")
        table.add_column("App ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Category", style="cyan")
        table.add_column("Size", style="yellow")
        table.add_column("Location", style="white")

        for app in grp.applications:
            table.add_row(str(app.id), app.name, app.category, format_bytes(app.total_size), app.root_path)

        console.print(table)
        console.print(f"[dim]Fingerprint: {grp.fingerprint}[/dim]\n")


def cmd_categories(args: argparse.Namespace) -> None:
    init_db()
    repo = Repository()
    apps = repo.get_all_applications()
    if not apps:
        console.print("[yellow]No applications in database. Run a scan first.[/yellow]")
        return

    cat_mgr = CategoryManager(repo)
    counts = cat_mgr.get_category_counts(apps)

    table = Table(title="Application Categories Breakdown")
    table.add_column("Category", style="bold cyan")
    table.add_column("Application Count", style="bold green")

    for cat, cnt in counts.items():
        table.add_row(cat, str(cnt))

    console.print(table)


def cmd_rules(args: argparse.Namespace) -> None:
    init_db()
    repo = Repository()
    cat_mgr = CategoryManager(repo)
    rules = cat_mgr.get_rules()

    table = Table(title="Configured Categorization Rules")
    table.add_column("ID", style="dim")
    table.add_column("Category", style="bold cyan")
    table.add_column("Field", style="yellow")
    table.add_column("Operator", style="magenta")
    table.add_column("Value", style="green")
    table.add_column("Priority", style="bold")
    table.add_column("Status", style="white")

    for r in rules:
        table.add_row(str(r.id), r.category, r.field, r.operator, r.value, str(r.priority), "Enabled" if r.enabled else "Disabled")

    console.print(table)


def cmd_report(args: argparse.Namespace) -> None:
    init_db()
    repo = Repository()
    apps = repo.get_all_applications()
    groups = repo.get_all_duplicate_groups()
    cat_mgr = CategoryManager(repo)
    cat_counts = cat_mgr.get_category_counts(apps)

    latest_scan = repo.get_latest_scan()
    scan_id = latest_scan["scan_id"] if latest_scan else "LATEST"
    paths = latest_scan["paths_scanned"] if latest_scan else []

    report = ReportGenerator.generate_full_report(
        scan_id=scan_id,
        scan_paths=paths,
        duration_seconds=0.0,
        applications=apps,
        duplicate_groups=groups,
        category_counts=cat_counts,
    )

    if args.output:
        ReportGenerator.export_to_json(report, args.output)
        console.print(f"[bold green]Report exported successfully to {args.output}[/bold green]")
    else:
        console.print(json.dumps(report, indent=2))


def cmd_remove(args: argparse.Namespace) -> None:
    if not args.confirm:
        console.print("[bold red]Action aborted: --confirm flag is required for removal operations.[/bold red]")
        sys.exit(1)

    init_db()
    repo = Repository()
    app = None

    if args.app_id:
        app = repo.get_application_by_id(args.app_id)
    elif args.path:
        for a in repo.get_all_applications():
            if a.root_path.lower() == args.path.lower():
                app = a
                break

    if not app:
        console.print("[bold red]Error: Target application not found in database.[/bold red]")
        sys.exit(1)

    rem_mgr = RemovalManager(repo)
    action = args.action or "quarantine"
    result = rem_mgr.remove_application(app, action=action)

    if result.status == "success":
        console.print(f"[bold green]Successfully removed '{result.app_name}' via {result.action}. Reclaimed {format_bytes(result.reclaimed_bytes)}.[/bold green]")
        if result.quarantine_path:
            console.print(f"[dim]Quarantined at: {result.quarantine_path}[/dim]")
    else:
        console.print(f"[bold red]Removal failed: {result.error_message}[/bold red]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IADCS - Intelligent Application Deduplication & Categorization System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan directories for applications and detect duplicates")
    scan_parser.add_argument("--path", "-p", action="append", required=True, help="Directory path to scan (can specify multiple)")
    scan_parser.add_argument("--exclude", "-e", action="append", help="Exclusion pattern")

    # Duplicates command
    subparsers.add_parser("duplicates", help="List detected duplicate application groups")

    # Categories command
    subparsers.add_parser("categories", help="List applications grouped by category")

    # Rules command
    subparsers.add_parser("rules", help="Manage categorization rules")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate machine-readable JSON report")
    report_parser.add_argument("--format", choices=["json"], default="json", help="Report format")
    report_parser.add_argument("--output", "-o", help="File path to save JSON report")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Safely remove or quarantine a duplicate application")
    remove_parser.add_argument("--app-id", type=int, help="ID of application to remove")
    remove_parser.add_argument("--path", help="Root path of application to remove")
    remove_parser.add_argument("--action", choices=["quarantine", "trash", "permanent"], default="quarantine", help="Removal action")
    remove_parser.add_argument("--confirm", action="store_true", help="Explicit confirmation required to proceed")

    # GUI command
    subparsers.add_parser("gui", help="Launch the Desktop GUI")

    return parser


def run_cli() -> None:
    parser = build_parser()
    if len(sys.argv) == 1:
        # Default: if no args, launch GUI
        from app.ui.app_window import launch_gui
        launch_gui()
        return

    args = parser.parse_args()
    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "duplicates":
        cmd_duplicates(args)
    elif args.command == "categories":
        cmd_categories(args)
    elif args.command == "rules":
        cmd_rules(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "remove":
        cmd_remove(args)
    elif args.command == "gui":
        from app.ui.app_window import launch_gui
        launch_gui()
    else:
        parser.print_help()
