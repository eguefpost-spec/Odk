#!/usr/bin/env python3
"""ODK — Automatisation de recherche d'emploi LinkedIn."""

import sys
import yaml
import click
from pathlib import Path
from rich.console import Console

from src.db import get_connection, upsert_job, update_status, get_jobs, log_run
from src.display import print_jobs_table, print_stats

console = Console()


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


@click.group()
@click.option("--config", default="config.yaml", show_default=True, help="Fichier de configuration")
@click.pass_context
def cli(ctx, config):
    ctx.ensure_object(dict)
    try:
        ctx.obj["cfg"] = load_config(config)
    except FileNotFoundError:
        console.print(f"[red]Fichier de config introuvable : {config}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--apply", is_flag=True, default=False, help="Postuler automatiquement (Easy Apply)")
@click.option("--headless", is_flag=True, default=False, help="Navigateur invisible")
@click.pass_context
def scan(ctx, apply, headless):
    """Scrape LinkedIn et enregistre les nouvelles offres."""
    from src.scraper import create_browser_session, login, scrape_jobs, apply_easy_apply
    from src.notifier import send_email

    cfg = ctx.obj["cfg"]
    conn = get_connection(cfg["database"]["path"])

    pw, browser, page = create_browser_session(headless=headless)
    try:
        console.print("[bold]Connexion à LinkedIn…[/bold]")
        login(page, cfg["linkedin"]["email"], cfg["linkedin"]["password"])

        new_jobs = []
        applied_count = 0
        auto_cfg = cfg.get("auto_apply", {})
        max_apply = auto_cfg.get("max_per_run", 10)
        do_apply = apply or auto_cfg.get("enabled", False)

        for job in scrape_jobs(page, cfg["search"]):
            is_new = upsert_job(conn, job)
            if is_new:
                new_jobs.append(job)
                status = "new"
                if do_apply and job["easy_apply"] and applied_count < max_apply:
                    console.print(f"  [yellow]Candidature :[/yellow] {job['title']} @ {job['company']}")
                    success = apply_easy_apply(page, job)
                    if success:
                        status = "applied"
                        applied_count += 1
                        console.print("    [green]✓ Candidature envoyée[/green]")
                    else:
                        console.print("    [red]✗ Échec Easy Apply[/red]")
                update_status(conn, job["id"], status)

        log_run(conn, len(new_jobs), applied_count)

        console.print(f"\n[bold green]{len(new_jobs)} nouvelles offres[/bold green] | [bold]{applied_count} candidatures envoyées[/bold]")

        notif_cfg = cfg.get("notifications", {}).get("email", {})
        min_jobs = cfg.get("notifications", {}).get("min_jobs_to_notify", 1)
        if notif_cfg.get("enabled") and len(new_jobs) >= min_jobs:
            send_email(notif_cfg, new_jobs)

        if new_jobs:
            print_jobs_table(new_jobs, title="Nouvelles offres")
    finally:
        browser.close()
        pw.stop()


@cli.command()
@click.option("--status", default=None, help="Filtrer par statut (new, applied, rejected, interview, offer)")
@click.pass_context
def list_jobs(ctx, status):
    """Affiche les offres enregistrées."""
    cfg = ctx.obj["cfg"]
    conn = get_connection(cfg["database"]["path"])
    jobs = get_jobs(conn, status)
    if not jobs:
        console.print("[yellow]Aucune offre trouvée.[/yellow]")
        return
    print_jobs_table(jobs, title=f"Offres ({status or 'toutes'})")
    print_stats(jobs)


@cli.command()
@click.argument("job_id")
@click.argument("status", type=click.Choice(["new", "applied", "rejected", "interview", "offer", "ignored"]))
@click.option("--notes", default="", help="Notes sur cette candidature")
@click.pass_context
def update(ctx, job_id, status, notes):
    """Met à jour le statut d'une offre."""
    cfg = ctx.obj["cfg"]
    conn = get_connection(cfg["database"]["path"])
    update_status(conn, job_id, status, notes)
    console.print(f"[green]Offre {job_id} mise à jour → {status}[/green]")


@cli.command()
@click.pass_context
def stats(ctx):
    """Affiche les statistiques de recherche."""
    cfg = ctx.obj["cfg"]
    conn = get_connection(cfg["database"]["path"])
    jobs = get_jobs(conn)
    if not jobs:
        console.print("[yellow]Aucune donnée.[/yellow]")
        return
    print_stats(jobs)
    runs = conn.execute("SELECT * FROM runs ORDER BY ran_at DESC LIMIT 5").fetchall()
    if runs:
        console.print("[bold]Dernières exécutions :[/bold]")
        for r in runs:
            console.print(f"  {r['ran_at'][:16]}  {r['jobs_found']} offres  {r['jobs_applied']} candidatures")


if __name__ == "__main__":
    cli()
