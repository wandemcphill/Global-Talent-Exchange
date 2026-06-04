from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.core.module import DomainModule, register_domain_modules
from app.trader.router import router as trader_router
from app.trader.schemas import (
    TraderBalanceView,
    TraderDashboardView,
    TraderDepositResultView,
    TraderDisputeView,
    TraderOrderBookView,
    TraderOrderView,
    TraderOverviewView,
    TraderProfileView,
    TraderQuoteView,
    TraderSettlementView,
    TraderWithdrawalResultView,
)


def test_trader_overview_mounts_production_path_and_v2_alias() -> None:
    app = FastAPI()

    register_domain_modules(app, (DomainModule("trader", router=trader_router),))

    routes = {
        (route.path, tuple(sorted(route.methods or ()))): route for route in app.routes if isinstance(route, APIRoute)
    }
    production_route = routes[("/api/trader/overview", ("GET",))]
    versioned_route = routes[("/api/v2/trader/overview", ("GET",))]

    assert production_route.endpoint is versioned_route.endpoint
    assert production_route.response_model is TraderOverviewView
    assert versioned_route.response_model is TraderOverviewView

    openapi_paths = app.openapi()["paths"]
    assert "/api/trader/overview" in openapi_paths
    assert "/api/v2/trader/overview" in openapi_paths
    assert "/api/api/trader/overview" not in openapi_paths


def test_trader_standalone_contracts_mount_production_path_and_v2_alias() -> None:
    app = FastAPI()

    register_domain_modules(app, (DomainModule("trader", router=trader_router),))

    routes = {
        (route.path, tuple(sorted(route.methods or ()))): route for route in app.routes if isinstance(route, APIRoute)
    }

    expected = {
        ("/api/trader/profile", ("GET",)): TraderProfileView,
        ("/api/v2/trader/profile", ("GET",)): TraderProfileView,
        ("/api/trader/dashboard", ("GET",)): TraderDashboardView,
        ("/api/v2/trader/dashboard", ("GET",)): TraderDashboardView,
        ("/api/trader/balance", ("GET",)): TraderBalanceView,
        ("/api/v2/trader/balance", ("GET",)): TraderBalanceView,
        ("/api/trader/order-book/{market_id}", ("GET",)): TraderOrderBookView,
        ("/api/v2/trader/order-book/{market_id}", ("GET",)): TraderOrderBookView,
        ("/api/trader/orders", ("GET",)): list[TraderOrderView],
        ("/api/v2/trader/orders", ("GET",)): list[TraderOrderView],
        ("/api/trader/orders/{order_id}", ("GET",)): TraderOrderView,
        ("/api/v2/trader/orders/{order_id}", ("GET",)): TraderOrderView,
        ("/api/trader/orders/{order_id}/cancel", ("POST",)): TraderOrderView,
        ("/api/v2/trader/orders/{order_id}/cancel", ("POST",)): TraderOrderView,
        ("/api/trader/quote", ("POST",)): TraderQuoteView,
        ("/api/v2/trader/quote", ("POST",)): TraderQuoteView,
        ("/api/trader/disputes", ("GET",)): list[TraderDisputeView],
        ("/api/v2/trader/disputes", ("GET",)): list[TraderDisputeView],
        ("/api/trader/disputes", ("POST",)): TraderDisputeView,
        ("/api/v2/trader/disputes", ("POST",)): TraderDisputeView,
        ("/api/trader/disputes/{dispute_id}", ("GET",)): TraderDisputeView,
        ("/api/v2/trader/disputes/{dispute_id}", ("GET",)): TraderDisputeView,
        ("/api/trader/settlements", ("GET",)): list[TraderSettlementView],
        ("/api/v2/trader/settlements", ("GET",)): list[TraderSettlementView],
        ("/api/trader/settlements/{settlement_id}", ("GET",)): TraderSettlementView,
        ("/api/v2/trader/settlements/{settlement_id}", ("GET",)): TraderSettlementView,
        ("/api/trader/deposit", ("POST",)): TraderDepositResultView,
        ("/api/v2/trader/deposit", ("POST",)): TraderDepositResultView,
        ("/api/trader/withdraw", ("POST",)): TraderWithdrawalResultView,
        ("/api/v2/trader/withdraw", ("POST",)): TraderWithdrawalResultView,
    }

    for key, response_model in expected.items():
        assert key in routes
        assert routes[key].response_model == response_model

    openapi_paths = app.openapi()["paths"]
    assert "/api/trader/profile" in openapi_paths
    assert "/api/v2/trader/profile" in openapi_paths
    assert "/api/trader/quote" in openapi_paths
    assert "/api/v2/trader/withdraw" in openapi_paths
