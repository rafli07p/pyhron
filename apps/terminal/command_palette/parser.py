"""Bloomberg-style command parser for the Pyhron terminal.

Parses commands like:
    BBCA EQUITY GO   -> load equity quote
    BUY BBCA 10 L    -> submit buy limit order
    PORT             -> show portfolio
    RISK             -> switch to risk layout
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class TerminalCommand:
    """Parsed terminal command."""

    command_type: str
    symbol: str | None
    params: dict[str, object]
    raw: str


_LAYOUT_COMMANDS: dict[str, str] = {
    "RISK": "risk",
    "NEWS": "news",
    "PORT": "trading",
    "RESEARCH": "research",
}

_PANEL_COMMANDS: dict[str, str] = {
    "PORT": "SHOW_PORTFOLIO",
    "ORD": "SHOW_ORDERS",
    "MOM": "SHOW_MOMENTUM",
    "HELP": "SHOW_HELP",
    "QUIT": "QUIT",
}

_PAPER_COMMANDS: dict[str, str] = {
    "START": "PAPER_START",
    "STOP": "PAPER_STOP",
    "PAUSE": "PAPER_PAUSE",
    "RESUME": "PAPER_RESUME",
    "STATUS": "PAPER_STATUS",
}


class CommandParser:
    """Stateless Bloomberg-style command parser.

    Never raises exceptions — returns ``None`` for unrecognised input.
    """

    def parse(self, raw_input: str) -> TerminalCommand | None:
        """Parse a raw command string into a TerminalCommand."""
        text = raw_input.strip()
        if not text:
            return None

        upper = text.upper()
        tokens = upper.split()

        # ── Order commands: BUY / SELL ──────────────────────
        if tokens[0] in ("BUY", "SELL"):
            return self._parse_order(tokens, text)

        # ── Equity lookup: SYMBOL EQUITY GO/GP/GF ──────────
        if len(tokens) >= 2 and tokens[1] == "EQUITY":
            return self._parse_equity(tokens, text)

        # ── Layout switch ──────────────────────────────────
        if len(tokens) == 1 and tokens[0] in _LAYOUT_COMMANDS:
            layout = _LAYOUT_COMMANDS[tokens[0]]
            return TerminalCommand(
                command_type="SWITCH_LAYOUT",
                symbol=None,
                params={"layout": layout},
                raw=text,
            )

        # ── Panel commands ─────────────────────────────────
        if len(tokens) == 1 and tokens[0] in _PANEL_COMMANDS:
            return TerminalCommand(
                command_type=_PANEL_COMMANDS[tokens[0]],
                symbol=None,
                params={},
                raw=text,
            )

        # ── Paper trading: PAPER <action> [args] ─────────
        if tokens[0] == "PAPER" and len(tokens) >= 2:
            return self._parse_paper_command(tokens, text)

        # ── Simulation: SIM <strategy_id> [start] [end] ──
        if tokens[0] == "SIM" and len(tokens) >= 2:
            return self._parse_sim_command(tokens, text)

        return None

    # ── Private helpers ────────────────────────────────────

    def _parse_order(self, tokens: list[str], raw: str) -> TerminalCommand | None:
        """Parse BUY/SELL commands.

        Format: ``BUY SYMBOL LOTS TYPE``
        where TYPE is L (limit) or M (market).
        """
        if len(tokens) < 4:
            return None

        side = tokens[0]
        symbol = tokens[1]
        try:
            quantity = int(tokens[2])
        except ValueError:
            return None

        if quantity <= 0:
            return None

        order_type_code = tokens[3]
        order_type_map = {"L": "LIMIT", "M": "MARKET"}
        order_type = order_type_map.get(order_type_code)
        if order_type is None:
            return None

        return TerminalCommand(
            command_type="SUBMIT_ORDER",
            symbol=symbol,
            params={
                "side": side,
                "quantity_lots": quantity,
                "order_type": order_type,
            },
            raw=raw,
        )

    def _parse_equity(self, tokens: list[str], raw: str) -> TerminalCommand | None:
        """Parse SYMBOL EQUITY [GO|GP|GF] commands."""
        symbol = tokens[0]
        action = tokens[2] if len(tokens) >= 3 else "GO"

        action_map: dict[str, str] = {
            "GO": "LOAD_EQUITY",
            "GP": "SHOW_PRICE_CHART",
            "GF": "SHOW_FINANCIALS",
        }
        cmd_type = action_map.get(action, "LOAD_EQUITY")

        return TerminalCommand(
            command_type=cmd_type,
            symbol=symbol,
            params={},
            raw=raw,
        )

    def _parse_paper_command(self, tokens: list[str], raw: str) -> TerminalCommand | None:
        """Parse PAPER <action> commands.

        Format: ``PAPER START|STOP|PAUSE|RESUME|STATUS [session_id]``
        """
        action = tokens[1]
        cmd_type = _PAPER_COMMANDS.get(action)
        if cmd_type is None:
            return None

        params: dict[str, object] = {}
        if len(tokens) >= 3:
            params["session_id"] = tokens[2]

        return TerminalCommand(
            command_type=cmd_type,
            symbol=None,
            params=params,
            raw=raw,
        )

    def _parse_sim_command(self, tokens: list[str], raw: str) -> TerminalCommand | None:
        """Parse SIM commands.

        Format: ``SIM <strategy_id> [start_date] [end_date]``
        """
        params: dict[str, object] = {"strategy_id": tokens[1]}
        if len(tokens) >= 3:
            params["start_date"] = tokens[2]
        if len(tokens) >= 4:
            params["end_date"] = tokens[3]

        return TerminalCommand(
            command_type="RUN_SIMULATION",
            symbol=None,
            params=params,
            raw=raw,
        )

    @staticmethod
    def suggest_symbols(query: str, universe: list[str], max_results: int = 5) -> list[str]:
        """Return fuzzy-matched symbol suggestions.

        Uses substring matching first, then SequenceMatcher similarity.
        """
        query_upper = query.upper()
        if not query_upper:
            return []

        # Exact prefix match first
        prefix_matches = [s for s in universe if s.startswith(query_upper)]

        # Substring match
        sub_matches = [s for s in universe if query_upper in s and s not in prefix_matches]

        # Fuzzy similarity for the rest
        remaining = [s for s in universe if s not in prefix_matches and s not in sub_matches]
        scored = [(s, SequenceMatcher(None, query_upper, s).ratio()) for s in remaining]
        scored.sort(key=lambda x: x[1], reverse=True)
        fuzzy = [s for s, score in scored if score >= 0.4]

        result = prefix_matches + sub_matches + fuzzy
        return result[:max_results]


def get_market_status(dt: object) -> str:
    """Determine IDX market status for a given datetime.

    Parameters
    ----------
    dt:
        A timezone-aware datetime in WIB (Asia/Jakarta).

    Returns
    -------
    str
        One of: ``"OPEN"``, ``"CLOSED"``, ``"PRE_OPEN"``, ``"LUNCH_BREAK"``.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if not isinstance(dt, datetime):
        return "CLOSED"

    wib = ZoneInfo("Asia/Jakarta")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=wib)
    else:
        dt = dt.astimezone(wib)

    # Weekend
    if dt.weekday() >= 5:
        return "CLOSED"

    hour, minute = dt.hour, dt.minute
    time_minutes = hour * 60 + minute

    # IDX session times (WIB)
    pre_open_start = 8 * 60 + 45  # 08:45
    session1_start = 9 * 60  # 09:00
    session1_end = 11 * 60 + 30  # 11:30
    session2_start = 13 * 60 + 30  # 13:30
    session2_end = 15 * 60 + 0  # 15:00 (Mon-Thu) or 14:30 (Fri)

    # Friday closes at 14:30
    if dt.weekday() == 4:
        session1_end = 11 * 60 + 30
        session2_start = 14 * 60
        session2_end = 14 * 60 + 30

    if pre_open_start <= time_minutes < session1_start:
        return "PRE_OPEN"

    if session1_start <= time_minutes < session1_end:
        return "OPEN"

    if session1_end <= time_minutes < session2_start:
        return "LUNCH_BREAK"

    if session2_start <= time_minutes < session2_end:
        return "OPEN"

    return "CLOSED"
