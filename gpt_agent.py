"""Legacy compatibility entrypoint.

This script is kept for backward compatibility and now delegates to the
modular implementation under `agent_search.legacy_agent`.
"""

from agent_search.legacy_agent import chat_with_agent, main, save_result_markdown

__all__ = ["chat_with_agent", "save_result_markdown", "main"]


if __name__ == "__main__":
    main()
