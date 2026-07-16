# src/ea_agent/cli.py
"""Console entry point (Presentation layer). Interaction only, no business logic."""
import asyncio


def main() -> None:
    """Synchronous entry point for the `ea-agent` console script."""
    from ea_agent.bootstrap import run   # your async composition-root coroutine
    asyncio.run(run())


if __name__ == "__main__":
    main()