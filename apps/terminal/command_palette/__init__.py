"""Command Palette for the Enthropy Terminal.

Bloomberg-style command interface that parses and executes terminal
commands. Supports security lookups (e.g., ``AAPL EQUITY``,
``BBCA JK EQUITY``), slash commands (``/backtest``, ``/risk``), and
function key shortcuts.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CommandType(StrEnum):
    """Types of parsed commands."""

    SECURITY_LOOKUP = "SECURITY_LOOKUP"
    SLASH_COMMAND = "SLASH_COMMAND"
    FUNCTION_KEY = "FUNCTION_KEY"
    SEARCH = "SEARCH"
    UNKNOWN = "UNKNOWN"


@dataclass
class ParsedCommand:
    """Result of parsing a raw command string."""

    raw: str
    command_type: CommandType = CommandType.UNKNOWN
    action: str = ""
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    asset_class: Optional[str] = None
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandSuggestion:
    """Auto-complete suggestion for the command palette."""

    text: str
    description: str
    command_type: CommandType
    score: float = 1.0


# Well-known security suffixes and their asset classes
_ASSET_CLASS_KEYWORDS = {
    "EQUITY": "equity",
    "INDEX": "index",
    "COMDTY": "commodity",
    "CURNCY": "currency",
    "GOVT": "government_bond",
    "CORP": "corporate_bond",
    "MMKT": "money_market",
    "MTGE": "mortgage",
    "MUNI": "municipal",
    "PFD": "preferred",
}

# Built-in slash commands
_BUILTIN_COMMANDS: dict[str, str] = {
    "/backtest": "Open backtest configuration panel",
    "/risk": "Open risk monitor dashboard",
    "/portfolio": "Show portfolio overview",
    "/orders": "Show open orders and blotter",
    "/news": "Open news panel",
    "/chart": "Open chart panel",
    "/research": "Open research panel",
    "/settings": "Open user settings",
    "/help": "Show available commands",
    "/watchlist": "Open watchlist panel",
    "/screener": "Open equity screener",
    "/factor": "Open factor analysis lab",
}


class CommandPalette:
    """Bloomberg-style command interface for the Enthropy Terminal.

    Parses user input into structured commands for execution. Supports:
    - Security lookups: ``AAPL EQUITY``, ``BBCA JK EQUITY``, ``ESH5 INDEX``
    - Slash commands: ``/backtest``, ``/risk``, ``/portfolio``
    - Function keys: ``F3`` (quote), ``F5`` (chart)
    - Free-text search across securities and commands

    Parameters
    ----------
    data_client:
        Optional DataClient for executing security lookups and
        command-related API calls.
    """

    def __init__(self, data_client: Any = None) -> None:
        self._data_client = data_client
        self._command_handlers: dict[str, Callable[..., Any]] = {}
        self._command_history: list[str] = []
        self._security_cache: dict[str, dict[str, Any]] = {}
        logger.info("CommandPalette initialized")

    def register_handler(self, command: str, handler: Callable[..., Any]) -> None:
        """Register a handler function for a slash command.

        Parameters
        ----------
        command:
            Slash command string (e.g., ``/backtest``).
        handler:
            Callable to invoke when the command is executed.
        """
        self._command_handlers[command.lower()] = handler
        logger.info("Registered handler for '%s'", command)

    def parse_command(self, raw_input: str) -> ParsedCommand:
        """Parse a raw command string into a structured command.

        Parameters
        ----------
        raw_input:
            User input from the command palette (e.g., ``AAPL EQUITY``,
            ``/backtest momentum_strategy``).

        Returns
        -------
        ParsedCommand
            Parsed and classified command object.
        """
        text = raw_input.strip()
        if not text:
            return ParsedCommand(raw=raw_input, command_type=CommandType.UNKNOWN)

        self._command_history.append(text)

        # Slash commands: /backtest, /risk, etc.
        if text.startswith("/"):
            return self._parse_slash_command(text)

        # Function keys: F1, F3, F5, etc.
        if re.match(r"^F\d+$", text, re.IGNORECASE):
            return ParsedCommand(
                raw=raw_input,
                command_type=CommandType.FUNCTION_KEY,
                action=text.upper(),
            )

        # Security lookup: AAPL EQUITY, BBCA JK EQUITY, etc.
        security_cmd = self._parse_security_lookup(text)
        if security_cmd is not None:
            return security_cmd

        # Fallback: treat as search
        return ParsedCommand(
            raw=raw_input,
            command_type=CommandType.SEARCH,
            action="search",
            args={"query": text},
        )

    async def execute_command(self, command: ParsedCommand) -> dict[str, Any]:
        """Execute a parsed command.

        Parameters
        ----------
        command:
            A ``ParsedCommand`` object from ``parse_command``.

        Returns
        -------
        dict[str, Any]
            Execution result with status and any returned data.
        """
        result: dict[str, Any] = {
            "command_type": command.command_type.value,
            "action": command.action,
            "status": "OK",
        }

        if command.command_type == CommandType.SECURITY_LOOKUP:
            result["data"] = await self._execute_security_lookup(command)

        elif command.command_type == CommandType.SLASH_COMMAND:
            handler = self._command_handlers.get(command.action.lower())
            if handler is not None:
                try:
                    handler_result = handler(**command.args)
                    result["data"] = handler_result
                except Exception as exc:
                    logger.error("Command '%s' failed: %s", command.action, exc)
                    result["status"] = "ERROR"
                    result["error"] = str(exc)
            else:
                result["status"] = "UNKNOWN_COMMAND"
                result["error"] = f"No handler registered for '{command.action}'"

        elif command.command_type == CommandType.FUNCTION_KEY:
            result["data"] = {"key": command.action}

        elif command.command_type == CommandType.SEARCH:
            result["data"] = {"query": command.args.get("query", "")}

        logger.info("Executed command: %s -> %s", command.raw, result["status"])
        return result

    def get_suggestions(self, partial: str, limit: int = 10) -> list[CommandSuggestion]:
        """Get auto-complete suggestions for partial input.

        Parameters
        ----------
        partial:
            Partial command text typed by the user.
        limit:
            Maximum number of suggestions to return.

        Returns
        -------
        list[CommandSuggestion]
            Ranked list of suggestions.
        """
        suggestions: list[CommandSuggestion] = []
        partial_lower = partial.lower().strip()

        if not partial_lower:
            return suggestions

        # Match slash commands
        if partial_lower.startswith("/"):
            for cmd, desc in _BUILTIN_COMMANDS.items():
                if cmd.startswith(partial_lower):
                    suggestions.append(
                        CommandSuggestion(
                            text=cmd,
                            description=desc,
                            command_type=CommandType.SLASH_COMMAND,
                            score=1.0 if cmd == partial_lower else 0.8,
                        )
                    )

        # Match cached securities
        for ticker, info in self._security_cache.items():
            if partial_lower in ticker.lower():
                suggestions.append(
                    CommandSuggestion(
                        text=f"{ticker} EQUITY",
                        description=info.get("name", ticker),
                        command_type=CommandType.SECURITY_LOOKUP,
                        score=0.9 if ticker.lower().startswith(partial_lower) else 0.6,
                    )
                )

        # Match command history
        for hist_cmd in reversed(self._command_history[-100:]):
            if partial_lower in hist_cmd.lower() and not any(s.text == hist_cmd for s in suggestions):
                suggestions.append(
                    CommandSuggestion(
                        text=hist_cmd,
                        description="Recent command",
                        command_type=CommandType.UNKNOWN,
                        score=0.5,
                    )
                )

        suggestions.sort(key=lambda s: s.score, reverse=True)
        return suggestions[:limit]

    def _parse_slash_command(self, text: str) -> ParsedCommand:
        """Parse a slash command with optional arguments."""
        parts = text.split(maxsplit=1)
        action = parts[0].lower()
        args: dict[str, Any] = {}

        if len(parts) > 1:
            arg_text = parts[1]
            # Parse key=value pairs or positional arguments
            kv_matches = re.findall(r"(\w+)=(\S+)", arg_text)
            if kv_matches:
                args = {k: v for k, v in kv_matches}
            else:
                args["args"] = arg_text.split()

        return ParsedCommand(
            raw=text,
            command_type=CommandType.SLASH_COMMAND,
            action=action,
            args=args,
        )

    def _parse_security_lookup(self, text: str) -> Optional[ParsedCommand]:
        """Parse a Bloomberg-style security lookup."""
        tokens = text.upper().split()
        if len(tokens) < 2:
            return None

        last_token = tokens[-1]
        if last_token not in _ASSET_CLASS_KEYWORDS:
            return None

        asset_class = _ASSET_CLASS_KEYWORDS[last_token]

        # Handle exchange codes: BBCA JK EQUITY -> symbol=BBCA, exchange=JK
        if len(tokens) >= 3:
            symbol = tokens[0]
            exchange = tokens[1]
        else:
            symbol = tokens[0]
            exchange = None

        return ParsedCommand(
            raw=text,
            command_type=CommandType.SECURITY_LOOKUP,
            action="lookup",
            symbol=symbol,
            exchange=exchange,
            asset_class=asset_class,
        )

    async def _execute_security_lookup(self, command: ParsedCommand) -> dict[str, Any]:
        """Execute a security lookup via the data client."""
        result: dict[str, Any] = {
            "symbol": command.symbol,
            "exchange": command.exchange,
            "asset_class": command.asset_class,
        }

        if self._data_client is not None and command.symbol:
            try:
                data = await self._data_client.get_market_data(
                    symbol=command.symbol,
                    exchange=command.exchange,
                )
                if isinstance(data, dict):
                    result.update(data)
                    self._security_cache[command.symbol] = data
            except Exception as exc:
                logger.error("Security lookup failed for %s: %s", command.symbol, exc)
                result["error"] = str(exc)

        return result


__all__ = [
    "CommandPalette",
    "CommandType",
    "ParsedCommand",
    "CommandSuggestion",
]
