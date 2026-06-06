from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.admin_godmode.runtime_paths import admin_godmode_state_path
from app.models.treasury import PaymentMode
from app.services.payment_gateway_service import PaymentGatewayError, PaymentGatewayService


class _FakeTreasuryService:
    def ensure_settings(self, session):
        del session
        return SimpleNamespace(
            deposit_mode=PaymentMode.HYBRID,
            withdrawal_mode=PaymentMode.MANUAL,
            currency_code="NGN",
        )


def _service(tmp_path):
    return PaymentGatewayService(
        session=object(),
        settings=SimpleNamespace(config_root=tmp_path),
    )


def test_payment_gateway_methods_are_korapay_and_manual_only(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "app.services.payment_gateway_service.TreasuryService",
        _FakeTreasuryService,
    )

    methods = _service(tmp_path).list_methods()

    assert [method.method_key for method in methods] == [
        "bank_transfer_manual",
        "korapay",
    ]
    assert [method.display_name for method in methods] == [
        "Manual bank transfer",
        "KoraPay",
    ]
    assert {method.method_group for method in methods} == {
        "manual_bank_transfer",
        "automatic_gateway",
    }


def test_payment_gateway_methods_ignore_paystack_from_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "app.services.payment_gateway_service.TreasuryService",
        _FakeTreasuryService,
    )
    state_path = admin_godmode_state_path(tmp_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "payment_rails": [
                    {
                        "provider": "paystack",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                    },
                    {
                        "provider": "crypto_fiat",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                    },
                    {
                        "provider": "bank_transfer_manual",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                    },
                    {
                        "provider": "korapay",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    methods = _service(tmp_path).list_methods()

    assert [method.method_key for method in methods] == ["bank_transfer_manual", "korapay"]
    assert {method.provider_key for method in methods}.isdisjoint({"paystack", "crypto_fiat"})


def test_noncanonical_payment_method_is_rejected(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "app.services.payment_gateway_service.TreasuryService",
        _FakeTreasuryService,
    )

    with pytest.raises(PaymentGatewayError, match="Unknown payment provider"):
        _service(tmp_path).quote_deposit(
            amount="1000",
            input_unit="fiat",
            method_key="apple_pay",
        )


@pytest.mark.parametrize("operation", ["quote", "create"])
def test_manual_bank_transfer_is_not_an_automatic_purchase_order(
    monkeypatch,
    tmp_path,
    operation: str,
) -> None:
    monkeypatch.setattr(
        "app.services.payment_gateway_service.TreasuryService",
        _FakeTreasuryService,
    )
    service = _service(tmp_path)

    with pytest.raises(PaymentGatewayError, match="treasury deposit request flow"):
        if operation == "quote":
            service.quote_deposit(
                amount="1000",
                input_unit="fiat",
                method_key="bank_transfer_manual",
            )
        else:
            service.create_purchase_order(
                user=object(),
                amount="1000",
                input_unit="fiat",
                method_key="bank_transfer_manual",
            )
