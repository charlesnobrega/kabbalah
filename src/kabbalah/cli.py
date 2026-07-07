"""
Kabbalah CLI - Command-line interface for the Kabbalah orchestration system.
"""

import argparse
import getpass
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

from kabbalah import __version__
from kabbalah.budget_manager import BudgetLedger, BudgetManager
from kabbalah.configuration_manager import ConfigurationManager
from kabbalah.hardware_profile import HardwareProfiler
from kabbalah.intake_node import IntakeNode
from kabbalah.models import UserRequest
from kabbalah.onboarding import ProviderKeyValidator, run_setup_wizard
from kabbalah.specification_pretty_printer import OutputFormat, SpecificationPrettyPrinter

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Kabbalah - Multi-agent orchestration system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kabbalah parse --name "My Project" --description "Project description"
  kabbalah setup
  kabbalah config --show
  kabbalah config list --json
  kabbalah status --json
  kabbalah version
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (-v=INFO, -vv=DEBUG)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Interactive first-boot setup")
    setup_parser.add_argument(
        "--providers",
        help="Comma-separated provider names to configure non-interactively",
    )
    setup_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse a project request")
    parse_parser.add_argument(
        "--name",
        required=True,
        help="Project name",
    )
    parse_parser.add_argument(
        "--description",
        required=True,
        help="Project description",
    )
    parse_parser.add_argument(
        "--scope",
        help="Project scope",
    )
    parse_parser.add_argument(
        "--constraints",
        nargs="*",
        default=[],
        help="Project constraints",
    )
    parse_parser.add_argument(
        "--output",
        choices=["json", "yaml", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration",
    )
    config_parser.add_argument(
        "--set",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Set configuration value",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_list = config_subparsers.add_parser("list", help="List safe provider/config status")
    config_list.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    config_add = config_subparsers.add_parser("add-key", help="Add or replace a provider API key")
    config_add.add_argument("provider", help="Provider name")
    config_add.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    config_remove = config_subparsers.add_parser("remove-key", help="Remove a provider API key from keyring")
    config_remove.add_argument("provider", help="Provider name")
    config_remove.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    config_test = config_subparsers.add_parser("test-key", help="Validate an installed provider API key")
    config_test.add_argument("provider", help="Provider name")
    config_test.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    config_budget = config_subparsers.add_parser("set-budget", help="Persist non-secret budget limits")
    config_budget.add_argument("--mode", choices=["warn", "block"], help="Budget enforcement mode")
    config_budget.add_argument("--run-usd", type=float, help="Run budget in USD")
    config_budget.add_argument("--daily-usd", type=float, help="Daily budget in USD")
    config_budget.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    config_routing = config_subparsers.add_parser("set-routing", help="Persist routing policy")
    config_routing.add_argument(
        "policy",
        choices=["balanced", "budget_first", "quality_first", "local_first"],
        help="Routing policy",
    )
    config_routing.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    config_network = config_subparsers.add_parser("set-network", help="Persist federated network mode")
    config_network.add_argument("mode", choices=["off", "receber", "receber+contribuir"], help="Network mode")
    config_network.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    config_trust_add = config_subparsers.add_parser("trust-add", help="Trust a federated publisher public key")
    config_trust_add.add_argument("public_key", help="Publisher Ed25519 public key")
    config_trust_add.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    config_trust_remove = config_subparsers.add_parser("trust-remove", help="Remove a trusted publisher public key")
    config_trust_remove.add_argument("public_key", help="Publisher Ed25519 public key")
    config_trust_remove.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    # Version command
    status_parser = subparsers.add_parser("status", help="Show safe runtime status")
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )

    # Version command
    subparsers.add_parser("version", help="Show version information")

    return parser.parse_args()


def cmd_parse(args: argparse.Namespace) -> int:
    """Handle parse command."""
    try:
        # Create user request
        request = UserRequest(
            project_name=args.name,
            project_description=args.description,
            scope=args.scope or "",
            constraints=args.constraints,
        )

        # Parse request
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)

        # Format output
        printer = SpecificationPrettyPrinter()
        output_format = OutputFormat(args.output.lower())

        if output_format == OutputFormat.JSON:
            output = printer.format_json(spec.__dict__)
        elif output_format == OutputFormat.YAML:
            output = printer.format_yaml(spec.__dict__)
        else:
            output = printer.format_text(spec.__dict__)

        print(output)
        logger.info(f"Successfully parsed project: {args.name} (run_id: {run_id})")
        return 0

    except Exception as e:
        logger.error(f"Error parsing project: {str(e)}")
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


def cmd_config(args: argparse.Namespace) -> int:
    """Handle config command."""
    try:
        config_manager = _load_config_manager()

        if args.config_command == "list":
            status = config_manager.get_config_status()
            status["hardware"] = _hardware_status(_state_db_path())
            return _emit_success(status, json_output=args.json)

        if args.config_command == "add-key":
            api_key = getpass.getpass(f"{args.provider} API key: ")
            validation = ProviderKeyValidator().validate(args.provider, api_key)
            if not validation.valid:
                return _emit_error(
                    what_happened="Provider key validation failed.",
                    why=validation.message,
                    what_to_do="Check the key/provider and run `kabbalah config add-key` again.",
                    json_output=args.json,
                )
            config_manager.set_provider_api_key(args.provider, api_key, storage="keyring")
            status = config_manager.get_provider_key_status(args.provider)
            return _emit_success(
                {
                    "provider": args.provider,
                    "stored": True,
                    "source": status["source"],
                    "last4": status["last4"],
                    "validation": validation.message,
                },
                json_output=args.json,
            )

        if args.config_command == "remove-key":
            config_manager.remove_provider_api_key(args.provider, storage="keyring")
            return _emit_success(
                {"provider": args.provider, "removed": True},
                json_output=args.json,
            )

        if args.config_command == "test-key":
            api_key = config_manager.get_provider_api_key(args.provider)
            if not api_key:
                return _emit_error(
                    what_happened="Provider key is not configured.",
                    why=f"No key found for {args.provider}.",
                    what_to_do=f"Run `kabbalah config add-key {args.provider}` first.",
                    json_output=args.json,
                )
            validation = ProviderKeyValidator().validate(args.provider, api_key)
            return (
                _emit_success(
                    {
                        "provider": args.provider,
                        "valid": validation.valid,
                        "message": validation.message,
                    },
                    json_output=args.json,
                )
                if validation.valid
                else _emit_error(
                    what_happened="Provider key validation failed.",
                    why=validation.message,
                    what_to_do=f"Run `kabbalah config add-key {args.provider}` with a valid key.",
                    json_output=args.json,
                )
            )

        if args.config_command == "set-budget":
            config_manager.set_budget_limits(
                mode=args.mode,
                run_limit_usd=args.run_usd,
                daily_limit_usd=args.daily_usd,
            )
            return _emit_success(
                {"budget": config_manager.get_config_status()["budget"]},
                json_output=args.json,
            )

        if args.config_command == "set-routing":
            config_manager.set_routing_policy(args.policy)
            return _emit_success(
                {"routing": config_manager.get_config_status()["routing"]},
                json_output=args.json,
            )

        if args.config_command == "set-network":
            identity = config_manager.ensure_federation_identity()
            config_manager.set_network_mode(args.mode)
            return _emit_success(
                {
                    "network": config_manager.get_config_status()["network"],
                    "identity": identity,
                },
                json_output=args.json,
            )

        if args.config_command == "trust-add":
            config_manager.add_trusted_publisher(args.public_key)
            return _emit_success(
                {"network": config_manager.get_config_status()["network"]},
                json_output=args.json,
            )

        if args.config_command == "trust-remove":
            config_manager.remove_trusted_publisher(args.public_key)
            return _emit_success(
                {"network": config_manager.get_config_status()["network"]},
                json_output=args.json,
            )

        if args.show:
            config_dict = config_manager.to_dict()
            printer = SpecificationPrettyPrinter()
            output = printer.format_json(config_dict)
            print(output)
            logger.info("Configuration displayed")
            return 0

        elif args.set:
            key, value = args.set
            config_manager.set_config(key, value)
            logger.info(f"Configuration updated: {key} = {value}")
            print(f"Configuration updated: {key} = {value}")
            return 0

        else:
            print("Use --show to display configuration or --set KEY VALUE to update")
            return 1

    except Exception as e:
        logger.error(f"Error managing configuration: {str(e)}")
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


def cmd_setup(args: argparse.Namespace) -> int:
    """Handle first-boot setup command."""
    try:
        config_manager = _load_config_manager()
        input_func = (lambda _: args.providers) if args.providers else input
        result = run_setup_wizard(
            config_manager=config_manager,
            validator=ProviderKeyValidator(),
            provider_names=sorted(config_manager.PROVIDER_KEY_ENVS),
            input_func=input_func,
            secret_input_func=getpass.getpass,
            output_func=(lambda message: None) if args.json else print,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    except Exception as e:
        logger.error(f"Error running setup: {str(e)}")
        if args.json:
            return _emit_error(
                what_happened="Setup failed.",
                why=str(e),
                what_to_do="Install keyring or configure Bitwarden, then rerun `kabbalah setup`.",
                json_output=True,
            )
        print(f"Setup failed. Why: {e}. What to do: install keyring or configure Bitwarden.", file=sys.stderr)
        return 1


def cmd_version(args: argparse.Namespace) -> int:
    """Handle version command."""
    print(f"Kabbalah v{__version__}")
    print("Multi-agent orchestration system")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle status command."""
    try:
        config_manager = _load_config_manager()
        state_db = _state_db_path()
        budget_manager = BudgetManager.from_env(BudgetLedger(state_db))
        result = {
            "config": config_manager.get_config_status(),
            "budget": budget_manager.get_budget_stats(),
            "hardware": _hardware_status(state_db),
            "governance": _governance_status(state_db),
        }
        if args.json:
            print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
        else:
            _print_status_text(result)
        return 0
    except Exception as e:
        logger.error(f"Error reading status: {str(e)}")
        payload = {
            "ok": False,
            "error": {
                "what_happened": "Could not read Kabbalah status.",
                "why": str(e),
                "what_to_do": "Run `kabbalah setup` or check KABBALAH_BRIDGE_STATE_DB.",
            },
        }
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        else:
            print(
                "Could not read Kabbalah status. "
                f"Why: {e}. What to do: run `kabbalah setup` or check KABBALAH_BRIDGE_STATE_DB.",
                file=sys.stderr,
            )
        return 1


def _load_config_manager() -> ConfigurationManager:
    manager = ConfigurationManager()
    manager.load_defaults()
    manager.load_from_env()
    manager.load_installation_config()
    return manager


def _state_db_path() -> Path:
    return Path(
        os.environ.get(
            "KABBALAH_BRIDGE_STATE_DB",
            str(Path.cwd() / ".kabbalah_bridge_state.sqlite3"),
        )
    )


def _hardware_status(state_db: Path) -> dict:
    profiles = HardwareProfiler(state_db).list_profiles()
    if not profiles:
        return {
            "active": False,
            "message": "No hardware profile recorded yet.",
        }
    latest = profiles[-1]
    return {
        "active": True,
        "fingerprint": latest.fingerprint,
        "backend": latest.backend,
        "gpu_count": len(latest.gpus),
        "ram_total_mb": latest.ram_total_mb,
        "created_at": latest.created_at,
    }


def _governance_status(state_db: Path) -> dict:
    if not state_db.exists():
        return {
            "active_contracts": 0,
            "pending_hitl_tickets": 0,
        }
    with sqlite3.connect(state_db) as conn:
        active_contracts = _count_rows(
            conn,
            "SELECT COUNT(*) FROM contratos WHERE status = 'ATIVO'",
        )
        pending_hitl = _count_rows(
            conn,
            "SELECT COUNT(*) FROM hitl_tickets WHERE json_extract(payload, '$.status') = 'pending'",
        )
    return {
        "active_contracts": active_contracts,
        "pending_hitl_tickets": pending_hitl,
    }


def _count_rows(conn: sqlite3.Connection, query: str) -> int:
    try:
        row = conn.execute(query).fetchone()
    except sqlite3.Error:
        return 0
    return int(row[0]) if row else 0


def _print_status_text(result: dict) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
    except Exception:
        print("Kabbalah status")
        print(f"- Mode: {result['config']['mode']}")
        print(f"- Environment: {result['config']['environment']}")
        print(f"- Budget mode: {result['budget']['mode']}")
        print(f"- Active contracts: {result['governance']['active_contracts']}")
        print(f"- Pending HITL tickets: {result['governance']['pending_hitl_tickets']}")
        return

    console = Console()
    table = Table(title="Kabbalah status")
    table.add_column("Area")
    table.add_column("Value")
    table.add_row("Mode", str(result["config"]["mode"]))
    table.add_row("Environment", str(result["config"]["environment"]))
    table.add_row("Budget mode", str(result["budget"]["mode"]))
    table.add_row("Hardware active", str(result["hardware"]["active"]))
    table.add_row("Active contracts", str(result["governance"]["active_contracts"]))
    table.add_row("Pending HITL tickets", str(result["governance"]["pending_hitl_tickets"]))
    console.print(table)


def _emit_success(result: dict, *, json_output: bool) -> int:
    if json_output:
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _emit_error(
    *,
    what_happened: str,
    why: str,
    what_to_do: str,
    json_output: bool,
) -> int:
    payload = {
        "ok": False,
        "error": {
            "what_happened": what_happened,
            "why": why,
            "what_to_do": what_to_do,
        },
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
    else:
        print(f"{what_happened} Why: {why}. What to do: {what_to_do}", file=sys.stderr)
    return 1


def main() -> int:
    """Main entry point."""
    try:
        args = parse_arguments()
        log_level = "DEBUG" if args.verbose >= 2 else "INFO" if args.verbose == 1 else args.log_level
        setup_logging(log_level)

        if not args.command:
            print("No command specified. Use --help for usage information.")
            return 1

        if args.command == "setup":
            return cmd_setup(args)
        elif args.command == "parse":
            return cmd_parse(args)
        elif args.command == "config":
            return cmd_config(args)
        elif args.command == "status":
            return cmd_status(args)
        elif args.command == "version":
            return cmd_version(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
