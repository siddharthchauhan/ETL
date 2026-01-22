#!/usr/bin/env python3
"""
SDTM Deep Agent Pipeline Runner
===============================
Entry point for running the SDTM transformation pipeline using DeepAgents architecture.

This script demonstrates how to use the DeepAgents-based SDTM pipeline.

Usage:
    python run_sdtm_deepagent.py

    # Or with custom options
    python run_sdtm_deepagent.py --study-id MAXIS-08 --no-hitl

Architecture:
    - Main orchestrator agent with planning (write_todos)
    - 5 specialized subagents for domain expertise
    - Custom middleware for validation, Neo4j, and S3
    - Filesystem backend for context management
    - Human-in-the-loop for critical operations
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdtm_pipeline.deepagents import (
    create_sdtm_deep_agent,
    run_sdtm_pipeline,
    SDTMAgentConfig,
    get_agent_info,
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SDTM transformation pipeline using DeepAgents"
    )
    parser.add_argument(
        "--study-id",
        default="MAXIS-08",
        help="Study identifier (default: MAXIS-08)"
    )
    parser.add_argument(
        "--s3-bucket",
        default=os.getenv("S3_ETL_BUCKET", "s3dcri"),
        help="S3 bucket for data storage"
    )
    parser.add_argument(
        "--s3-key",
        default="incoming/EDC Data.zip",
        help="S3 key for source data"
    )
    parser.add_argument(
        "--workspace",
        default="./sdtm_workspace",
        help="Workspace directory for intermediate files"
    )
    parser.add_argument(
        "--output",
        default="./sdtm_deepagent_output",
        help="Output directory for final results"
    )
    parser.add_argument(
        "--no-hitl",
        action="store_true",
        help="Disable human-in-the-loop approvals"
    )
    parser.add_argument(
        "--no-neo4j",
        action="store_true",
        help="Disable Neo4j loading"
    )
    parser.add_argument(
        "--no-s3",
        action="store_true",
        help="Disable S3 upload"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (chat with agent)"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Display agent architecture information"
    )
    return parser.parse_args()


async def run_interactive_session(agent, config: SDTMAgentConfig):
    """Run interactive chat session with the agent."""
    print("\n" + "=" * 70)
    print("   SDTM DEEP AGENT - INTERACTIVE MODE")
    print("=" * 70)
    print("\nType your commands or questions. Type 'exit' to quit.")
    print("Example commands:")
    print("  - Scan the source files in /path/to/data")
    print("  - Transform DEMO.csv to SDTM DM domain")
    print("  - Validate the DM dataset")
    print("  - Generate SAS code for AE transformation")
    print("")

    thread_id = f"interactive_{config.study_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            # Invoke agent
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config={"configurable": {"thread_id": thread_id}}
            )

            # Print response
            if result.get("messages"):
                response = result["messages"][-1]
                print(f"\nAgent: {response.content}")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


async def run_full_pipeline(args):
    """Run the full SDTM transformation pipeline."""

    # Create configuration
    config = SDTMAgentConfig(
        study_id=args.study_id,
        workspace_dir=args.workspace,
        output_dir=args.output,
        s3_bucket=args.s3_bucket,
        enable_human_review=not args.no_hitl,
        enable_neo4j=not args.no_neo4j,
        enable_s3=not args.no_s3,
    )

    print("\n" + "=" * 70)
    print("   SDTM DEEP AGENT PIPELINE")
    print("=" * 70)
    print(f"\n  Study ID:        {config.study_id}")
    print(f"  S3 Bucket:       {config.s3_bucket}")
    print(f"  S3 Key:          {args.s3_key}")
    print(f"  Workspace:       {config.workspace_dir}")
    print(f"  Output:          {config.output_dir}")
    print(f"  Human Review:    {'Enabled' if config.enable_human_review else 'Disabled'}")
    print(f"  Neo4j:           {'Enabled' if config.enable_neo4j else 'Disabled'}")
    print(f"  S3 Upload:       {'Enabled' if config.enable_s3 else 'Disabled'}")
    print("\n" + "=" * 70)

    # Prepare source files (in a real scenario, these would be scanned from S3)
    # For demo, we'll let the agent handle the discovery
    source_files = [
        {"name": "EDC Data.zip", "path": f"s3://{config.s3_bucket}/{args.s3_key}", "target_domain": None},
    ]

    # Run the pipeline
    result = await run_sdtm_pipeline(
        study_id=config.study_id,
        source_files=source_files,
        config=config,
    )

    # Print results
    print("\n" + "=" * 70)
    print("   PIPELINE RESULTS")
    print("=" * 70)
    print(f"\n  Status:          {result.get('status', 'unknown')}")
    print(f"  Thread ID:       {result.get('thread_id', 'unknown')}")
    print(f"  Generated At:    {result.get('generated_at', 'unknown')}")

    if result.get("agent_response"):
        print("\n  Agent Response:")
        print("  " + "-" * 60)
        # Print first 500 chars of response
        response = result["agent_response"][:500]
        for line in response.split('\n'):
            print(f"  {line}")
        if len(result["agent_response"]) > 500:
            print("  ...")

    print("\n" + "=" * 70)

    return result


def display_agent_info():
    """Display agent architecture information."""
    info = get_agent_info()

    print("\n" + "=" * 70)
    print("   SDTM DEEP AGENT ARCHITECTURE")
    print("=" * 70)
    print(f"\n  Name:            {info['name']}")
    print(f"  Version:         {info['version']}")
    print(f"  Architecture:    {info['architecture']}")

    print("\n  Features:")
    for feature, desc in info['features'].items():
        if isinstance(desc, list):
            print(f"    - {feature}: {', '.join(desc)}")
        else:
            print(f"    - {feature}: {desc}")

    print(f"\n  Supported Domains: {', '.join(info['supported_domains'])}")
    print("\n" + "=" * 70)


async def main():
    """Main entry point."""
    args = parse_args()

    # Display info and exit
    if args.info:
        display_agent_info()
        return

    # Interactive mode
    if args.interactive:
        config = SDTMAgentConfig(
            study_id=args.study_id,
            workspace_dir=args.workspace,
            output_dir=args.output,
            enable_human_review=not args.no_hitl,
            enable_neo4j=not args.no_neo4j,
            enable_s3=not args.no_s3,
        )
        agent = create_sdtm_deep_agent(config)
        await run_interactive_session(agent, config)
        return

    # Full pipeline mode
    await run_full_pipeline(args)


if __name__ == "__main__":
    asyncio.run(main())
