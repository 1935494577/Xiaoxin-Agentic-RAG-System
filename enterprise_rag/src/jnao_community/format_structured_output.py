"""format_structured_output LangChain tool — Jnao config registration."""

from __future__ import annotations

from langchain.tools import tool


@tool("format_structured_output", parse_docstring=True)
def format_structured_output_tool(content: str, schema_id: str) -> str:
    """Format draft content into a named output schema (selling points, DM script, etc.).

    Args:
        content: Draft text to structure.
        schema_id: Output schema id (e.g. parent_dm_script, selling_points).
    """
    from agent.tools.builtins.format_structured_output import format_structured_output

    return format_structured_output(content or "", schema_id or "")
