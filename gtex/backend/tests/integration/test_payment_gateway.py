from __future__ import annotations


def test_payment_gateway_methods(client):
    response = client.get("/integrations/payments/methods")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, list)
    assert body
    assert "provider_key" in body[0]


def test_payment_gateway_quote_and_order(client, demo_auth_headers):
    quote = client.post(
        "/integrations/payments/quote",
        json={"amount": "25.0000", "input_unit": "fiat"},
    )
    assert quote.status_code == 200, quote.text
    payload = quote.json()
    assert payload["gross_amount"]

    order = client.post(
        "/integrations/payments/orders",
        headers=demo_auth_headers,
        json={"amount": "25.0000", "input_unit": "fiat"},
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert body["reference"]
