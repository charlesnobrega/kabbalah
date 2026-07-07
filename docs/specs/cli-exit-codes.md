# Kabbalah CLI exit codes

The CLI uses stable exit codes for scripting:

| Code | Meaning | Typical action |
|---:|---|---|
| 0 | Success | Continue. |
| 1 | Recoverable command/config/runtime error | Read stderr/JSON error and follow `what_to_do`. |
| 2 | Argument parsing error from `argparse` | Fix command syntax and rerun. |
| 130 | Interrupted by user | Rerun when ready. |

Error output should follow:

```text
what happened -> why -> what to do
```

For JSON commands, the shape is:

```json
{
  "ok": false,
  "error": {
    "what_happened": "...",
    "why": "...",
    "what_to_do": "..."
  }
}
```
