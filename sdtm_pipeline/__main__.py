"""
SDTM Pipeline Entry Point
=========================
Run the interactive SDTM chat agent.

Usage:
    python -m sdtm_pipeline           # Start chat agent
    python -m sdtm_pipeline --help    # Show help
"""

import sys
import asyncio


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print(__doc__)
        print("""
Commands available in the chat agent:

  Data Loading:
    /load s3              - Load EDC data from S3
    /load local <path>    - Load from local zip file
    /preview <file>       - Preview a source file

  Conversion:
    /domains              - List available domains
    /convert <domain>     - Convert a specific domain
    /convert all          - Convert all domains

  Mapping & Validation:
    /mapping <domain>     - Generate mapping specification
    /validate <domain>    - Validate converted domain
    /report               - Show validation report

  Knowledge Tools:
    /search <query>       - Search SDTM guidelines (Tavily)
    /rules <domain>       - Get business rules (Pinecone)

  General:
    /status               - Show pipeline status
    /help                 - Show help
    /quit                 - Exit

Examples:
    /load s3
    /convert DM
    /mapping AE
    /validate all
    /search CDISC SDTM Demographics specification
    /rules AE
        """)
        return

    # Import and run chat agent
    from sdtm_pipeline.chat_agent import main as chat_main
    asyncio.run(chat_main())


if __name__ == "__main__":
    main()
