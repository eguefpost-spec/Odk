from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

STATUS_COLORS = {
    "new": "white",
    "applied": "green",
    "rejected": "red",
    "interview": "yellow",
    "offer": "bold green",
    "ignored": "dim",
}


def print_jobs_table(jobs: list, title: str = "Offres"):
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("Titre", style="cyan", max_width=40)
    table.add_column("Entreprise", style="magenta", max_width=25)
    table.add_column("Lieu", max_width=20)
    table.add_column("Easy Apply", justify="center")
    table.add_column("Statut", justify="center")
    table.add_column("Date", max_width=16)

    for j in jobs:
        color = STATUS_COLORS.get(j["status"], "white")
        table.add_row(
            j["title"],
            j["company"],
            j["location"] or "-",
            "✅" if j["easy_apply"] else "",
            f"[{color}]{j['status']}[/{color}]",
            (j["discovered_at"] or "")[:10],
        )
    console.print(table)


def print_stats(jobs: list):
    from collections import Counter
    counts = Counter(j["status"] for j in jobs)
    console.print("\n[bold]Résumé :[/bold]")
    for status, n in sorted(counts.items()):
        color = STATUS_COLORS.get(status, "white")
        console.print(f"  [{color}]{status}[/{color}] : {n}")
    console.print()
