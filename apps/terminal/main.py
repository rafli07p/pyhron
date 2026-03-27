"""Pyhron Terminal — Bloomberg-style CLI for IDX trading.

Usage:
    poetry run python -m apps.terminal.main
    poetry run python -m apps.terminal.main --env paper
    poetry run python -m apps.terminal.main --layout research
    poetry run python -m apps.terminal.main --symbols BBCA,BBRI,BMRI,TLKM
    poetry run python -m apps.terminal.main --demo

Options:
    --env       paper|live (default: paper)
    --layout    trading|research|risk|news (default: trading)
    --symbols   comma-separated watchlist symbols
    --url       API base URL override
    --demo      launch with synthetic data, no API required
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Label, Static

from apps.terminal.command_palette.parser import CommandParser, TerminalCommand, get_market_status
from apps.terminal.demo import DEFAULT_SYMBOLS, DemoDataProvider
from apps.terminal.panels.watchlist_panel import WatchlistPanel
from apps.terminal.widgets import (
    ChartWidget,
    MomentumWidget,
    OrderbookWidget,
    OrderConfirmDialog,
    OrdersWidget,
    PositionsWidget,
    fmt_pct,
)

WIB = ZoneInfo("Asia/Jakarta")

_MIN_WIDTH = 120
_MIN_HEIGHT = 40
_REFRESH_INTERVAL = 2.0  # seconds


class PyhronTerminal(App[None]):
    """Main Textual application for the Pyhron trading terminal."""

    CSS_PATH = "pyhron.tcss"
    TITLE = "PYHRON TERMINAL"

    BINDINGS = [
        Binding("ctrl+q", "quit_confirm", "Quit", show=True),
        Binding("ctrl+1", "layout_trading", "Trading", show=False),
        Binding("ctrl+2", "layout_research", "Research", show=False),
        Binding("ctrl+3", "layout_risk", "Risk", show=False),
        Binding("ctrl+4", "layout_news", "News", show=False),
        Binding("ctrl+r", "refresh_all", "Refresh", show=True),
        Binding("ctrl+t", "cycle_timeframe", "Timeframe", show=False),
        Binding("ctrl+h", "toggle_help", "Help", show=True),
        Binding("ctrl+l", "clear_command", "Clear", show=False),
        Binding("f1", "focus_watchlist", "Watchlist", show=False),
        Binding("f2", "focus_chart", "Chart", show=False),
        Binding("f3", "focus_orderbook", "Orderbook", show=False),
        Binding("f4", "focus_positions", "Positions", show=False),
        Binding("f5", "focus_orders", "Orders", show=False),
        Binding("slash", "focus_command", "Command", show=False),
    ]

    def __init__(
        self,
        demo_mode: bool = False,
        initial_layout: str = "trading",
        symbols: list[str] | None = None,
        api_url: str = "http://localhost:8000",
        jwt_token: str = "",
        env: str = "paper",
    ) -> None:
        super().__init__()
        self._demo_mode = demo_mode
        self._current_layout = initial_layout
        self._symbols = symbols or list(DEFAULT_SYMBOLS)
        self._api_url = api_url
        self._jwt_token = jwt_token
        self._env = env
        self._parser = CommandParser()
        self._demo: DemoDataProvider | None = None
        self._command_history: list[str] = []
        self._history_index = -1
        self._timeframes = ["D1", "W1", "M1", "H1", "15M"]
        self._current_tf_idx = 0
        self._help_visible = False
        self._refresh_task: asyncio.Task[None] | None = None

        if demo_mode:
            self._demo = DemoDataProvider()

    def compose(self) -> ComposeResult:
        yield Static("", id="status-bar")
        yield Static("", id="offline-banner")

        with Container(id="main-content"):
            with Horizontal(id="top-row"):
                with Vertical(classes="column-left panel", id="watchlist-panel"):
                    yield Static("WATCHLIST", classes="panel-header")
                    yield WatchlistPanel(id="watchlist-widget")

                with Vertical(classes="column-center panel", id="chart-panel"):
                    yield Static("CHART", classes="panel-header")
                    yield ChartWidget(id="chart-widget")

                with Vertical(classes="column-right panel", id="orderbook-panel"):
                    yield Static("ORDER BOOK", classes="panel-header")
                    yield OrderbookWidget(id="orderbook-widget")

            with Horizontal(id="bottom-row"):
                with Vertical(classes="column-left panel", id="positions-panel"):
                    yield Static("POSITIONS", classes="panel-header")
                    yield PositionsWidget(id="positions-widget")

                with Vertical(classes="column-right panel", id="orders-panel"):
                    yield Static("ORDERS (TODAY)", classes="panel-header")
                    yield OrdersWidget(id="orders-widget")

        # Momentum panel (hidden by default, shown in research layout)
        with Vertical(id="momentum-panel", classes="panel"):
            yield Static("MOMENTUM SIGNALS", classes="panel-header")
            yield MomentumWidget(id="momentum-widget")

        # Command bar
        with Horizontal(id="command-bar"):
            yield Label("> ", id="command-prompt")
            yield Input(placeholder="Type command... (HELP for reference)", id="command-input")

        # Help overlay
        yield Static(self._help_text(), id="help-overlay")

    def on_mount(self) -> None:
        # Hide momentum panel initially
        momentum = self.query_one("#momentum-panel")
        momentum.display = False

        # Start refresh loop
        self._refresh_task = asyncio.ensure_future(self._refresh_loop())

        # Initial data load
        self.call_later(self._initial_load)

    async def _initial_load(self) -> None:
        """Load initial data for all panels."""
        self._update_status_bar()
        await self._refresh_all_panels()

    async def _refresh_loop(self) -> None:
        """Periodic data refresh every 2 seconds."""
        while True:
            await asyncio.sleep(_REFRESH_INTERVAL)
            with contextlib.suppress(Exception):
                await self._refresh_all_panels()

    async def _refresh_all_panels(self) -> None:
        """Refresh all visible panels with latest data."""
        self._update_status_bar()

        if self._demo:
            self._refresh_demo_panels()

    def _refresh_demo_panels(self) -> None:
        """Refresh all panels from demo data."""
        assert self._demo is not None

        # Watchlist
        quotes = [self._demo.get_quote(s) for s in self._symbols]
        quote_dicts = [
            {
                "symbol": q.symbol,
                "last": q.last,
                "change": q.change,
                "change_pct": q.change_pct,
                "volume_lots": q.volume_lots,
                "value_billion": q.value_billion,
            }
            for q in quotes
        ]
        with contextlib.suppress(Exception):
            self.query_one("#watchlist-widget", WatchlistPanel).update_quotes(quote_dicts)

        # Chart
        if self._symbols:
            sym = self._symbols[0]
            bars = self._demo.get_ohlcv(sym, n_bars=50)
            with contextlib.suppress(Exception):
                self.query_one("#chart-widget", ChartWidget).render_chart(
                    bars, sym, self._timeframes[self._current_tf_idx]
                )

        # Orderbook
        if self._symbols:
            book = self._demo.get_orderbook(self._symbols[0])
            with contextlib.suppress(Exception):
                self.query_one("#orderbook-widget", OrderbookWidget).render_book(book, self._symbols[0])

        # Positions
        positions = self._demo.get_positions()
        with contextlib.suppress(Exception):
            self.query_one("#positions-widget", PositionsWidget).render_positions(positions)

        # Orders
        orders = self._demo.get_orders()
        with contextlib.suppress(Exception):
            self.query_one("#orders-widget", OrdersWidget).render_orders(orders)

        # Momentum (if visible)
        with contextlib.suppress(Exception):
            mp = self.query_one("#momentum-panel")
            if mp.display:
                signals = self._demo.get_momentum_signals()
                self.query_one("#momentum-widget", MomentumWidget).render_signals(signals)

    def _update_status_bar(self) -> None:
        """Update the top status bar."""
        now = datetime.now(tz=WIB)
        time_str = now.strftime("%H:%M:%S") + " WIB"
        market = get_market_status(now)

        parts = ["PYHRON v1.0", f"IDX {market}", time_str]

        if self._demo:
            ihsg, ihsg_chg = self._demo.get_ihsg()
            ihsg_str = f"{ihsg:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            parts.append(f"IHSG {ihsg_str} {fmt_pct(ihsg_chg)}")

        if self._demo:
            parts.append("DEMO")
        else:
            parts.append("Connected" if self._jwt_token != "" else "Offline")

        with contextlib.suppress(Exception):
            bar = self.query_one("#status-bar", Static)
            bar.update("  |  ".join(parts))

    # Command handling

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "command-input":
            return

        raw = event.value.strip()
        event.input.value = ""

        if not raw:
            return

        # Add to history
        self._command_history.append(raw)
        if len(self._command_history) > 50:
            self._command_history.pop(0)
        self._history_index = -1

        cmd = self._parser.parse(raw)
        if cmd is None:
            self._show_status_message(f"Unknown command: {raw}")
            return

        self._execute_command(cmd)

    def _execute_command(self, cmd: TerminalCommand) -> None:
        """Execute a parsed terminal command."""
        if cmd.command_type == "SUBMIT_ORDER":
            self._handle_order(cmd)
        elif cmd.command_type == "LOAD_EQUITY":
            if cmd.symbol and cmd.symbol not in self._symbols:
                self._symbols.insert(0, cmd.symbol)
            self._show_status_message(f"Loaded {cmd.symbol}")
            self.call_later(self._refresh_all_panels)
        elif cmd.command_type == "SHOW_PRICE_CHART":
            if cmd.symbol:
                self._symbols.insert(0, cmd.symbol)
            self.call_later(self._refresh_all_panels)
        elif cmd.command_type == "SWITCH_LAYOUT":
            layout = str(cmd.params.get("layout", "trading"))
            self._switch_layout(layout)
        elif cmd.command_type in ("SHOW_PORTFOLIO", "SHOW_ORDERS"):
            self._switch_layout("trading")
        elif cmd.command_type == "SHOW_MOMENTUM":
            self._switch_layout("research")
        elif cmd.command_type == "SHOW_HELP":
            self._toggle_help()
        elif cmd.command_type == "QUIT":
            self.action_quit_confirm()
        elif cmd.command_type == "PAPER_START":
            self._handle_paper_start(cmd)
        elif cmd.command_type == "PAPER_STOP":
            self._handle_paper_stop(cmd)
        elif cmd.command_type == "PAPER_PAUSE":
            self._handle_paper_pause(cmd)
        elif cmd.command_type == "PAPER_RESUME":
            self._handle_paper_resume(cmd)
        elif cmd.command_type == "PAPER_STATUS":
            self._handle_paper_status(cmd)
        elif cmd.command_type == "RUN_SIMULATION":
            self._handle_sim(cmd)

    def _handle_order(self, cmd: TerminalCommand) -> None:
        """Show order confirmation dialog."""
        symbol = cmd.symbol or ""
        side = str(cmd.params.get("side", ""))
        raw_lots = cmd.params.get("quantity_lots", 0)
        lots = int(raw_lots) if isinstance(raw_lots, int | float | str) else 0
        order_type = str(cmd.params.get("order_type", ""))

        # Estimate value from current price
        estimated_value = 0
        if self._demo:
            q = self._demo.get_quote(symbol)
            estimated_value = q.last * lots * 100

        estimated_cost = int(estimated_value * 0.0015)  # 0.15% commission

        current_lots = 0
        if self._demo:
            for p in self._demo.get_positions():
                if p.symbol == symbol:
                    current_lots = p.lots
                    break

        dialog = OrderConfirmDialog(
            symbol=symbol,
            side=side,
            lots=lots,
            order_type=order_type,
            estimated_value=estimated_value,
            estimated_cost=estimated_cost,
            current_lots=current_lots,
        )

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._submit_order(symbol, side, order_type, lots)
            else:
                self._show_status_message("Order cancelled")

        self.push_screen(dialog, on_confirm)

    def _submit_order(self, symbol: str, side: str, order_type: str, lots: int) -> None:
        """Submit the order after confirmation."""
        if self._demo:
            result = self._demo.submit_order(symbol, side, order_type, lots, None)
            self._show_status_message(f"Order submitted: {symbol} {side} {lots}L {order_type} [{result.order_id}]")
            self.call_later(self._refresh_all_panels)
        else:
            self._show_status_message("Order submission requires API connection")

    # Paper trading command handlers

    def _handle_paper_start(self, cmd: TerminalCommand) -> None:
        """Handle PAPER START command — start a paper trading session."""
        session_id = str(cmd.params.get("session_id", ""))
        if not session_id:
            self._show_status_message("Usage: PAPER START <session_id>")
            return
        self._show_status_message(f"Starting paper session {session_id}...")
        self.call_later(self._api_paper_action, "start", session_id)

    def _handle_paper_stop(self, cmd: TerminalCommand) -> None:
        """Handle PAPER STOP command — stop a paper trading session."""
        session_id = str(cmd.params.get("session_id", ""))
        if not session_id:
            self._show_status_message("Usage: PAPER STOP <session_id>")
            return
        self._show_status_message(f"Stopping paper session {session_id}...")
        self.call_later(self._api_paper_action, "stop", session_id)

    def _handle_paper_pause(self, cmd: TerminalCommand) -> None:
        """Handle PAPER PAUSE command — pause a paper trading session."""
        session_id = str(cmd.params.get("session_id", ""))
        if not session_id:
            self._show_status_message("Usage: PAPER PAUSE <session_id>")
            return
        self._show_status_message(f"Pausing paper session {session_id}...")
        self.call_later(self._api_paper_action, "pause", session_id)

    def _handle_paper_resume(self, cmd: TerminalCommand) -> None:
        """Handle PAPER RESUME command — resume a paused session."""
        session_id = str(cmd.params.get("session_id", ""))
        if not session_id:
            self._show_status_message("Usage: PAPER RESUME <session_id>")
            return
        self._show_status_message(f"Resuming paper session {session_id}...")
        self.call_later(self._api_paper_action, "resume", session_id)

    def _handle_paper_status(self, cmd: TerminalCommand) -> None:
        """Handle PAPER STATUS command — show session status."""
        session_id = str(cmd.params.get("session_id", ""))
        if session_id:
            self._show_status_message(f"Fetching status for session {session_id}...")
            self.call_later(self._api_paper_status, session_id)
        else:
            self._show_status_message("Fetching paper trading sessions...")
            self.call_later(self._api_paper_status, None)

    def _handle_sim(self, cmd: TerminalCommand) -> None:
        """Handle SIM command — run a backtest simulation."""
        strategy_id = str(cmd.params.get("strategy_id", ""))
        if not strategy_id:
            self._show_status_message("Usage: SIM <strategy_id> [start_date] [end_date]")
            return
        start = str(cmd.params.get("start_date", ""))
        end = str(cmd.params.get("end_date", ""))
        date_range = f" {start}→{end}" if start and end else ""
        self._show_status_message(f"Running simulation for {strategy_id}{date_range}...")
        self.call_later(self._api_run_simulation, strategy_id, start, end)

    async def _api_paper_action(self, action: str, session_id: str) -> None:
        """Call paper trading API for start/stop/pause/resume."""
        import httpx

        url = f"{self._api_url}/v1/paper-trading/sessions/{session_id}/{action}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._jwt_token}"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    self._show_status_message(f"Paper session {session_id}: {action} OK")
                else:
                    self._show_status_message(f"Paper {action} failed: {resp.status_code}")
        except Exception as exc:
            self._show_status_message(f"Paper {action} error: {exc}")

    async def _api_paper_status(self, session_id: str | None) -> None:
        """Fetch paper trading session status from API."""
        import httpx

        if session_id:
            url = f"{self._api_url}/v1/paper-trading/sessions/{session_id}"
        else:
            url = f"{self._api_url}/v1/paper-trading/sessions"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self._jwt_token}"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if session_id:
                        status = data.get("status", "UNKNOWN")
                        nav = data.get("current_nav_idr", "?")
                        self._show_status_message(f"Session {session_id}: {status} | NAV: IDR {nav}")
                    else:
                        count = len(data) if isinstance(data, list) else 0
                        self._show_status_message(f"Paper sessions: {count} found")
                else:
                    self._show_status_message(f"Status fetch failed: {resp.status_code}")
        except Exception as exc:
            self._show_status_message(f"Status error: {exc}")

    async def _api_run_simulation(self, strategy_id: str, start_date: str, end_date: str) -> None:
        """Call simulation API endpoint."""
        import httpx

        url = f"{self._api_url}/v1/paper-trading/simulate"
        body: dict[str, str] = {"strategy_id": strategy_id}
        if start_date:
            body["start_date"] = start_date
        if end_date:
            body["end_date"] = end_date
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json=body,
                    headers={"Authorization": f"Bearer {self._jwt_token}"},
                    timeout=120.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    total_return = data.get("total_return_pct", "?")
                    self._show_status_message(f"Simulation complete: return={total_return}%")
                else:
                    self._show_status_message(f"Simulation failed: {resp.status_code}")
        except Exception as exc:
            self._show_status_message(f"Simulation error: {exc}")

    def _show_status_message(self, msg: str) -> None:
        """Display a message in the status bar temporarily."""
        with contextlib.suppress(Exception):
            bar = self.query_one("#status-bar", Static)
            bar.update(msg)
        # Restore status bar after 3 seconds
        self.set_timer(3.0, self._update_status_bar)

    # Layout switching

    def _switch_layout(self, layout: str) -> None:
        self._current_layout = layout

        with contextlib.suppress(Exception):
            top = self.query_one("#top-row")
            bottom = self.query_one("#bottom-row")
            momentum = self.query_one("#momentum-panel")

            if layout == "trading":
                top.display = True
                bottom.display = True
                momentum.display = False
            elif layout == "research":
                top.display = True
                bottom.display = False
                momentum.display = True
            elif layout == "risk":
                top.display = True
                bottom.display = True
                momentum.display = False
            elif layout == "news":
                top.display = True
                bottom.display = False
                momentum.display = False

            self._show_status_message(f"Layout: {layout.upper()}")

    # Actions

    def action_quit_confirm(self) -> None:
        """Quit with confirmation if open orders exist."""
        open_orders = 0
        if self._demo:
            open_orders = sum(1 for o in self._demo.get_orders() if o.status in ("PENDING", "PARTIALLY_FILLED"))

        if open_orders > 0:
            self._show_status_message(f"You have {open_orders} open orders. Press Ctrl+Q again to quit.")
        self.exit()

    def action_layout_trading(self) -> None:
        self._switch_layout("trading")

    def action_layout_research(self) -> None:
        self._switch_layout("research")

    def action_layout_risk(self) -> None:
        self._switch_layout("risk")

    def action_layout_news(self) -> None:
        self._switch_layout("news")

    def action_refresh_all(self) -> None:
        self.call_later(self._refresh_all_panels)

    def action_cycle_timeframe(self) -> None:
        self._current_tf_idx = (self._current_tf_idx + 1) % len(self._timeframes)
        self._show_status_message(f"Timeframe: {self._timeframes[self._current_tf_idx]}")
        self.call_later(self._refresh_all_panels)

    def action_toggle_help(self) -> None:
        self._toggle_help()

    def _toggle_help(self) -> None:
        with contextlib.suppress(Exception):
            overlay = self.query_one("#help-overlay")
            self._help_visible = not self._help_visible
            overlay.display = self._help_visible

    def action_clear_command(self) -> None:
        with contextlib.suppress(Exception):
            inp = self.query_one("#command-input", Input)
            inp.value = ""

    def action_focus_watchlist(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#watchlist-panel").focus()

    def action_focus_chart(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#chart-panel").focus()

    def action_focus_orderbook(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#orderbook-panel").focus()

    def action_focus_positions(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#positions-panel").focus()

    def action_focus_orders(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#orders-panel").focus()

    def action_focus_command(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#command-input", Input).focus()

    # Help text

    @staticmethod
    def _help_text() -> str:
        return "\n".join(
            [
                "  PYHRON TERMINAL — COMMAND REFERENCE",
                "",
                "  COMMANDS:",
                "  BBCA EQUITY GO     Load equity quote",
                "  BBCA EQUITY GP     Show price chart",
                "  BUY BBCA 10 L      Buy 10 lots limit",
                "  SELL BBCA 5 M      Sell 5 lots market",
                "  PORT               Portfolio overview",
                "  ORD                Orders panel",
                "  MOM                Momentum signals",
                "  RISK               Risk view",
                "",
                "  PAPER TRADING:",
                "  PAPER START <id>   Start paper session",
                "  PAPER STOP <id>    Stop paper session",
                "  PAPER PAUSE <id>   Pause paper session",
                "  PAPER RESUME <id>  Resume paper session",
                "  PAPER STATUS [id]  Session status",
                "  SIM <strat> [s] [e] Run simulation",
                "",
                "  GENERAL:",
                "  HELP               This screen",
                "  QUIT               Exit terminal",
                "",
                "  KEYBOARD SHORTCUTS:",
                "  Ctrl+1-4           Switch layouts",
                "  Ctrl+R             Refresh all data",
                "  Ctrl+T             Cycle chart timeframe",
                "  Ctrl+H             Toggle help",
                "  Ctrl+Q             Quit",
                "  F1-F5              Focus panels",
                "  /                  Focus command bar",
                "  Tab                Cycle panel focus",
            ]
        )


def _check_terminal_size() -> bool:
    """Check if terminal meets minimum size requirements."""
    try:
        size = os.get_terminal_size()
        if size.columns < _MIN_WIDTH or size.lines < _MIN_HEIGHT:
            sys.stdout.write(
                f"\nPyhron Terminal requires minimum {_MIN_WIDTH}x{_MIN_HEIGHT}.\n"
                f"Current size: {size.columns}x{size.lines}.\n"
                f"Please resize your terminal and try again.\n\n"
            )
            return False
    except OSError:
        pass  # Not a TTY, proceed anyway
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Pyhron Terminal")
    parser.add_argument("--env", choices=["paper", "live"], default="paper")
    parser.add_argument("--layout", choices=["trading", "research", "risk", "news"], default="trading")
    parser.add_argument("--symbols", type=str, default="")
    parser.add_argument("--url", type=str, default="http://localhost:8000")
    parser.add_argument("--demo", action="store_true", help="Launch with synthetic data")
    args = parser.parse_args()

    if not _check_terminal_size():
        sys.exit(1)

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] if args.symbols else None

    jwt_token = ""
    if not args.demo:
        from apps.terminal.auth import load_credentials

        creds = load_credentials(args.env)
        if creds:
            jwt_token = creds["access_token"]
        else:
            # Fall back to demo mode if no credentials
            args.demo = True
            sys.stdout.write("No credentials found. Starting in demo mode.\n")

    app = PyhronTerminal(
        demo_mode=args.demo,
        initial_layout=args.layout,
        symbols=symbols,
        api_url=args.url,
        jwt_token=jwt_token,
        env=args.env,
    )

    # Profiling support
    if os.environ.get("PYHRON_PROFILE") == "1":
        import cProfile

        profile_path = Path.home() / ".pyhron" / "terminal_profile.stats"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        cProfile.run("app.run()", str(profile_path))
    else:
        app.run()


if __name__ == "__main__":
    main()
