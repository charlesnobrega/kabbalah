# SillyTavern Group Chat Bridge Design

Status: design-first draft for Wave 8.2.

## Goal

Map Kabbalah orchestration into a SillyTavern group chat without weakening the
security pipeline. The target UX is:

- each Kabbalah domain appears as a SillyTavern group member / Blank Card bot;
- tool calls still go through the Kabbalah MCP bridge;
- Firewall, HITL, contract and budget decisions are visible as chat events;
- the implementation works even when a provider key is missing by returning an
  honest status/error message instead of fake output.

## Relevant SillyTavern constraints

From the current SillyTavern docs:

- Group chats are multi-character rooms; the selected reply strategy can be
  manual, natural order, list order, or pooled order.
- Group chat history is shared by all group members.
- Group generation can swap the active character card or join character cards.
- Prompt Manager has a "New Group Chat" prompt slot and group nudge prompt.
- MCP integration in the current ecosystem is extension/plugin based and
  requires function calling enabled; server config may be in an MCP settings
  file rather than a first-party built-in UI, depending on the installed client.

References:

- https://docs.sillytavern.app/usage/core-concepts/groupchats/
- https://docs.sillytavern.app/usage/core-concepts/chatfilemanagement/
- https://docs.sillytavern.app/usage/prompts/prompt-manager/
- https://mcp.pizza/mcp-client/sTvK/SillyTavern-MCP-Client

## Proposed mapping

| Kabbalah concept | SillyTavern representation | Notes |
|---|---|---|
| `Root_Orchestrator` | optional coordinator Blank Card | Should summarize task, assign domains, and read MCP status messages. |
| Domain agent | one group member / Blank Card per domain | Example: Backend, Security, Infra, QA, Docs. |
| Leaf execution | hidden provider/tool call behind a domain message | Leaf result should be summarized by the domain card, not exposed as raw logs. |
| Firewall deny | system-style chat event from Kabbalah | Message format: action blocked, reason, next step. |
| HITL pending | system-style chat event with ticket ID | User checks status through `check_hitl_status`; no silent auto-approval. |
| Budget status | `get_budget_stats` tool message | Used before expensive compare/routing. |
| Config status | `get_config_status` tool message | Shows provider key presence without values. |
| Model comparison | `compare_models` tool message | Renders table rows for provider/model/cost/latency/error. |

## Recommended group chat mode

Use Manual or List Order initially.

Natural/Pooled order is attractive for roleplay, but it makes deterministic
security evidence harder because arbitrary agents may speak before the
coordinator has gated the action. The first implementation should be:

1. user sends request;
2. coordinator card asks Kabbalah MCP for config/budget/status as needed;
3. coordinator triggers one domain card at a time;
4. domain card calls MCP tools through the bridge;
5. bridge returns either result, block, HITL ticket, or provider error;
6. coordinator summarizes the final state.

Natural/Pooled can be enabled later as a UI preset after the audit transcript is
stable.

## Message contracts

Kabbalah-originated status messages should use stable prefixes so they are easy
to filter in SillyTavern history:

- `[KABBALAH:ALLOW]` action executed.
- `[KABBALAH:DENY]` action blocked by policy/contract/risk.
- `[KABBALAH:HITL]` human approval required, includes ticket ID.
- `[KABBALAH:BUDGET]` cost/budget state.
- `[KABBALAH:CONFIG]` provider/key status without values.
- `[KABBALAH:ERROR]` recoverable runtime/config error.

Every error follows: what happened → why → what to do.

## Initial implementation slice

The first code slice should avoid writing a SillyTavern browser extension.
Implement MCP-side support first:

1. Add a bridge tool `render_group_event`.
   - Input: `event_type`, `agent/domain`, `summary`, `details`, optional
     `ticket_id`, optional `next_step`.
   - Output: JSON with `display_text` plus structured fields.
   - Pipeline: normal Qlipot → Firewall → HITL/contract path unless event is
     strictly read-only status.
2. Add a small renderer module in `src/kabbalah/sillytavern_group_chat.py`.
3. Provide example Blank Card definitions in docs only, not runtime fixtures.
4. Document a SillyTavern setup recipe:
   - create group;
   - add coordinator/domain Blank Cards;
   - use Manual/List Order;
   - enable function calling/MCP client;
   - connect `kabbalah_mcp_bridge.py`.

## Acceptance criteria

- Design doc exists before implementation.
- No tool result is injected into chat without passing the bridge pipeline.
- HITL pending appears as visible chat text with ticket ID.
- Denials include reason and next command/tool to use.
- Provider/config failures are shown as honest operational errors.
- A deterministic test validates `render_group_event` output for at least:
  allow, deny, HITL, budget, config and provider-error events.

## Open decisions

- Whether Kabbalah should eventually ship a SillyTavern extension or remain
  MCP-only.
- Whether group members should be generated as Character Card v2 JSON examples.
- Whether Natural/Pooled reply order should ever be enabled for autonomous
  runs, or only for demo/roleplay mode.
