from kabbalah.sync_hub import Sinapse, SyncHub


def test_sync_hub_keeps_legacy_metric_aggregation():
    sync = SyncHub(hardware_hash="local")

    sync.registrar_update("node-a", {"risk": 0.2})
    sync.registrar_update("node-b", {"risk": 0.6})

    assert sync.agregar() == {"risk": 0.4}


def test_sync_hub_collects_synapse_and_reports_stats():
    sync = SyncHub(hardware_hash="local")

    sinapse = sync.coletar_sinapse("qlipot_correcao", {"score": 0.7, "delta": -0.1})
    stats = sync.get_network_stats()

    assert sinapse.tipo == "qlipot_correcao"
    assert sinapse.hash_instancia == "local"
    assert stats["hardware_hash"] == "local"
    assert stats["sinapses_coletadas"] == 1


def test_sync_hub_internalizes_after_three_distinct_instances():
    corrections = []

    class FakeQlipot:
        def aplicar_correcao(self, assinatura_acao, delta):
            corrections.append((assinatura_acao, delta))

    sync = SyncHub(qlipot=FakeQlipot(), hardware_hash="local")
    assinatura = "action-signature"

    for idx in range(3):
        accepted = sync.receber_sinapse(
            Sinapse(
                id=f"syn-{idx}",
                tipo="qlipot_correcao",
                dominio_origem="seguranca",
                hash_instancia=f"remote-{idx}",
                assinatura_acao=assinatura,
                qlipot_delta=0.15,
                metadados={"score": 0.8},
                timestamp=1.0 + idx,
                assinatura=f"sig-{idx}",
            )
        )
        assert accepted is True

    assert corrections == [(assinatura, 0.15)]
    assert assinatura not in sync.quarentena


def test_sync_hub_rejects_banned_instance():
    sync = SyncHub(hardware_hash="local")
    sync.banir_instancia("remote-bad", "invalid signal")

    accepted = sync.receber_sinapse(
        Sinapse(
            id="syn-bad",
            tipo="qlipot_correcao",
            dominio_origem="seguranca",
            hash_instancia="remote-bad",
            assinatura_acao="action",
            qlipot_delta=0.1,
            metadados={},
            timestamp=1.0,
            assinatura="sig",
        )
    )

    assert accepted is False
    assert sync.instancias["remote-bad"].status == "banido"
