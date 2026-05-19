"""
Kabbalah CLI - Command-line interface for the Kabbalah orchestration system.
"""

import sys
import argparse
import logging
from typing import Optional
from pathlib import Path

from kabbalah.intake_node import IntakeNode
from kabbalah.models import UserRequest
from kabbalah.configuration_manager import ConfigurationManager
from kabbalah.specification_pretty_printer import SpecificationPrettyPrinter, OutputFormat


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
  kabbalah config --show
  kabbalah version
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

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
        output_format = OutputFormat(args.output.upper())

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
        config_manager = ConfigurationManager()
        config_manager.load_defaults()

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


def cmd_version(args: argparse.Namespace) -> int:
    """Handle version command."""
    print("Kabbalah v1.0.0")
    print("Multi-agent orchestration system")
    return 0


def main() -> int:
    """Main entry point."""
    try:
        args = parse_arguments()
        setup_logging(args.log_level)

        if not args.command:
            print("No command specified. Use --help for usage information.")
            return 1

        if args.command == "parse":
            return cmd_parse(args)
        elif args.command == "config":
            return cmd_config(args)
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
