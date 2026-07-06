# Federated SyncHub Network

This is SyncHub phase 2: signed threat-intelligence bundles, not a social
network and not background synchronization.

## Modes

- `off` is the default. No import, export, fetch, or background network action.
- `receber` allows explicit bundle import from trusted publishers.
- `receber+contribuir` allows explicit export of local anonymized synapses.

## Identity

The instance identity is an Ed25519 public key. The private key is stored only in
the secure local backend (`keyring` today, Bitwarden later). Hardware hashes are
telemetry, never identity.

## Bundle format

Bundles are canonical JSON signed without the `signature` field:

```json
{
  "schema_version": 1,
  "publisher_public_key": "...base64...",
  "publisher_id": "sha256(public_key)",
  "created_at": "2026-07-06T00:00:00Z",
  "risk_assessor_version": "wave3-2026.07",
  "records": [
    {
      "action_hash": "sha256(canonical_action)",
      "delta": 0.3,
      "count": 3,
      "window": "2026-07-01/2026-07-06"
    }
  ],
  "signature": "...base64..."
}
```

Records never contain raw prompts, parameters, paths, tokens, or tool payloads.

## Import pipeline

1. Parse and size-limit the bundle.
2. Verify Ed25519 signature over canonical JSON without `signature`.
3. Require `publisher_public_key` in the local trust list.
4. Require compatible `RISK_ASSESSOR_VERSION`.
5. Reject replayed signatures.
6. Quarantine records by `action_hash`.
7. Internalize only when `count >= 3` or three independent trusted publishers
   agree.
8. Apply via `Qlipot.aplicar_correcao(origem="sync_hub")`, preserving clamp and
   audit behavior.

## Threat model

- Spoofing: blocked by Ed25519 signature and trust list.
- Tampering: blocked by signature verification.
- Replay: blocked by local imported-signature cache.
- Poisoning: reduced by trust list, quorum/count, delta clamp, version matching,
  and Kabbalah-Bench before/after checks.
- Privacy leak: blocked by exporting action hashes and aggregate counters only.

## Measurement gate

Promotion requires Kabbalah-Bench before/after evidence showing better
containment without increased false-positive rate.

