from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from datetime import datetime

console = Console(width=200)


def render_dashboard(recommendations: list[dict], prop_recommendations: list[dict],
                     api_calls_remaining, mode: str = "both"):
    console.clear()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    console.print(
        Panel(
            f"[bold cyan]LIVE BETTING MODEL[/bold cyan]  |  {now}  |  "
            f"Mode: [magenta]{mode.upper()}[/magenta]  |  "
            f"API calls left: [yellow]{api_calls_remaining}[/yellow]",
            box=box.HORIZONTALS,
        )
    )

    live_recs = [r for r in recommendations if r["game_mode"] == "live"]
    upcoming_recs = [r for r in recommendations if r["game_mode"] == "upcoming"]
    tomorrow_recs = [r for r in recommendations if r["game_mode"] == "tomorrow"]

    if not recommendations and not prop_recommendations:
        console.print("\n[dim]No value bets found right now. Watching...[/dim]")
        return

    if live_recs:
        console.print("\n[bold green]🔴 LIVE GAMES[/bold green]")
        _render_table(live_recs)

    if upcoming_recs:
        console.print("\n[bold yellow]📅 TODAY — UPCOMING[/bold yellow]")
        _render_table(upcoming_recs)

    if tomorrow_recs:
        console.print("\n[bold blue]📆 TOMORROW[/bold blue]")
        _render_table(tomorrow_recs)

    if prop_recommendations:
        console.print("\n[bold magenta]🎯 PLAYER PROPS (FanDuel)[/bold magenta]")
        _render_props_table(prop_recommendations[:20])  # cap at 20 to keep display clean

    console.print(
        "\n[dim]Edge = fair prob (vig removed) - implied prob. "
        "Positive edge = value. Bet responsibly.[/dim]"
    )


def _render_table(recs: list[dict]):
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold white")
    table.add_column("Sport", style="cyan", width=6)
    table.add_column("Game", width=32)
    table.add_column("Bet", width=22)
    table.add_column("Book", width=12)
    table.add_column("Odds", justify="right", width=7)
    table.add_column("Model%", justify="right", width=8)
    table.add_column("Line%", justify="right", width=7)
    table.add_column("Edge", justify="right", width=7)
    table.add_column("EV", justify="right", width=9)
    table.add_column("Time", width=7)
    table.add_column("Conf%", justify="right", width=7)
    table.add_column("Units", justify="right", width=6)

    for rec in sorted(recs, key=lambda x: x["edge"], reverse=True):
        edge = rec["edge"]
        edge_str = f"{edge:.1%}"
        edge_color = "green" if edge >= 0.08 else "yellow"
        conf = rec.get("confidence", 0)
        conf_color = "green" if conf >= 70 else ("yellow" if conf >= 45 else "red")

        table.add_row(
            rec["sport"],
            f"{rec['away']} @ {rec['home']}",
            rec["bet"],
            rec.get("best_book", "?"),
            str(rec["odds"]),
            f"{rec['model_prob']:.1%}",
            f"{rec['implied_prob']:.1%}",
            f"[{edge_color}]{edge_str}[/{edge_color}]",
            f"${rec['ev']:.2f}",
            rec.get("time_label", ""),
            f"[{conf_color}]{conf}%[/{conf_color}]",
            f"{rec.get('units', 0):.2f}u",
        )

    console.print(table)


def _render_props_table(props: list[dict]):
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold white")
    table.add_column("Sport", style="cyan", width=6)
    table.add_column("Game", width=28)
    table.add_column("Prop Bet", width=38)
    table.add_column("Odds", justify="right", width=7)
    table.add_column("Fair%", justify="right", width=7)
    table.add_column("Line%", justify="right", width=7)
    table.add_column("Edge", justify="right", width=7)
    table.add_column("EV", justify="right", width=9)
    table.add_column("Signal", width=10)

    for rec in props:
        edge = rec["edge"]
        edge_color = "green" if edge >= 0.08 else "yellow"
        signal = "🔥 STRONG" if edge >= 0.10 else ("✅ VALUE" if edge >= 0.07 else "👀 WATCH")

        table.add_row(
            rec["sport"],
            f"{rec['away']} @ {rec['home']}",
            rec["bet"],
            str(rec["odds"]),
            f"{rec['model_prob']:.1%}",
            f"{rec['implied_prob']:.1%}",
            f"[{edge_color}]{edge:.1%}[/{edge_color}]",
            f"${rec['ev']:.2f}",
            signal,
        )

    console.print(table)
