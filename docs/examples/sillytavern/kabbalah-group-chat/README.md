# Kabbalah SillyTavern Group Chat Example

This is the MCP-only group-chat setup for Kabbalah Wave 8.2. It does not require
a custom SillyTavern extension in the first implementation slice; all execution
still passes through `kabbalah_mcp_bridge.py`.

## Setup

1. Connect the `kabbalah-firewall` MCP server using `sillytavern_mcp_config.json`.
2. Create a SillyTavern group chat.
3. Add the Blank Card members described in `blank-cards.json`.
4. Use Manual or List Order reply mode for deterministic audit history.
5. Keep Natural/Pooled order for demos only until the audit transcript is
   proven stable.

## Runtime flow

1. User sends a request.
2. Root Orchestrator checks `get_config_status` and `get_budget_stats`.
3. Root Orchestrator delegates to one domain card at a time.
4. Domain cards call MCP tools through Kabbalah.
5. Kabbalah returns result, denial, provider error, or HITL ticket.
6. Domain cards use `render_group_event` to surface decisions in chat.

Expected event examples:

- `[KABBALAH:ALLOW] Backend Domain: file read completed`
- `[KABBALAH:DENY] Security Domain: contract missing`
- `[KABBALAH:HITL] Security Domain: Ação requer aprovação humana. Ticket: hitl_...`
- `[KABBALAH:BUDGET] Root Orchestrator: daily budget near limit`
- `[KABBALAH:CONFIG] Root Orchestrator: provider key present`
- `[KABBALAH:ERROR] QA Domain: provider unavailable`

## Acceptance notes

- MCP-only is the supported first slice.
- No tool result should be pasted into group chat unless it came from the MCP
  bridge.
- `render_group_event` redacts secret-like detail keys before producing display
  text.
- The group is intentionally deterministic: Manual/List Order first, Natural
  order only after additional audit tests.
