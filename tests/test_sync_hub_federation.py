import pytest

from kabbalah.qlipot import RISK_ASSESSOR_VERSION, Qlipot
from kabbalah.sync_hub import (
    FEDERATED_BUNDLE_SCHEMA_VERSION,
    Sinapse,
    SyncHub,
    gerar_par_chaves_federacao,
    sign_bundle_payload,
)


def _token_action_kwargs():
    return {
        "pedido": "Copy the API token inventory to the approved offsite vault.",
        "ferramenta": "call_tool",
        "argumentos": {
            "action": "copy_token_inventory",
            "destination": "approved-vault",
        },
    }


def _bundle_for(action_hash, *, delta=0.30, count=3):
    public_key, private_key = gerar_par_chaves_federacao()
    hub = SyncHub(hardware_hash="publisher")
    hub.fila_sinapses.append(
        Sinapse(
            id="syn-local",
            tipo="qlipot_correcao",
            dominio_origem="security",
            hash_instancia="publisher",
            assinatura_acao=action_hash,
            qlipot_delta=delta,
            metadados={"count": count, "window": "2026-07-01/2026-07-06"},
            timestamp=1.0,
            assinatura="local",
        )
    )
    return public_key, private_key, hub.exportar_bundle(publisher_public_key=public_key, private_key=private_key)


def test_signed_bundle_import_applies_trusted_qlipot_correction():
    qlipot = Qlipot()
    action_hash = qlipot.assinar_acao(**_token_action_kwargs())
    public_key, _, bundle = _bundle_for(action_hash)
    importer = SyncHub(qlipot=qlipot, hardware_hash="receiver")

    before = qlipot.avaliar_intencao(**_token_action_kwargs()).risco
    result = importer.importar_bundle(bundle, trusted_publishers={public_key})
    after = qlipot.avaliar_intencao(**_token_action_kwargs()).risco

    assert result == {"accepted": True, "reason": "accepted", "imported": 1}
    assert before == 0.50
    assert after == 0.80
    assert qlipot.correcoes_log[-1]["origem"] == "sync_hub"


def test_tampered_bundle_is_rejected():
    qlipot = Qlipot()
    action_hash = qlipot.assinar_acao(**_token_action_kwargs())
    public_key, _, bundle = _bundle_for(action_hash)
    bundle["records"][0]["delta"] = -0.30

    with pytest.raises(ValueError, match="signature"):
        SyncHub(qlipot=qlipot).importar_bundle(bundle, trusted_publishers={public_key})


def test_untrusted_publisher_is_rejected_before_internalization():
    qlipot = Qlipot()
    action_hash = qlipot.assinar_acao(**_token_action_kwargs())
    _, _, bundle = _bundle_for(action_hash)

    result = SyncHub(qlipot=qlipot).importar_bundle(bundle, trusted_publishers=set())

    assert result == {"accepted": False, "reason": "untrusted_publisher", "imported": 0}
    assert qlipot.avaliar_intencao(**_token_action_kwargs()).risco == 0.50


def test_replayed_bundle_does_not_reapply_correction():
    qlipot = Qlipot()
    action_hash = qlipot.assinar_acao(**_token_action_kwargs())
    public_key, _, bundle = _bundle_for(action_hash)
    importer = SyncHub(qlipot=qlipot)

    assert importer.importar_bundle(bundle, trusted_publishers={public_key})["accepted"] is True
    replay = importer.importar_bundle(bundle, trusted_publishers={public_key})

    assert replay == {"accepted": False, "reason": "replay", "imported": 0}
    assert len(qlipot.correcoes_log) == 1


def test_incompatible_risk_assessor_version_is_rejected():
    qlipot = Qlipot()
    action_hash = qlipot.assinar_acao(**_token_action_kwargs())
    public_key, private_key, bundle = _bundle_for(action_hash)
    bundle["risk_assessor_version"] = "old"
    bundle["signature"] = sign_bundle_payload(private_key, bundle)

    result = SyncHub(qlipot=qlipot).importar_bundle(bundle, trusted_publishers={public_key})

    assert result == {"accepted": False, "reason": "incompatible_risk_assessor", "imported": 0}


def test_exported_bundle_contains_only_anonymized_records():
    qlipot = Qlipot()
    action_hash = qlipot.assinar_acao(**_token_action_kwargs())
    public_key, _, bundle = _bundle_for(action_hash)
    serialized = str(bundle)

    assert bundle["schema_version"] == FEDERATED_BUNDLE_SCHEMA_VERSION
    assert bundle["risk_assessor_version"] == RISK_ASSESSOR_VERSION
    assert bundle["publisher_public_key"] == public_key
    assert "Copy the API token" not in serialized
    assert "approved offsite vault" not in serialized
    assert bundle["records"][0]["action_hash"] == action_hash
