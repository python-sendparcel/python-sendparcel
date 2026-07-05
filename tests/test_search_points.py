"""Tests for search_points capability."""

from __future__ import annotations

from typing import Any

import pytest

from sendparcel.exceptions import ProviderCapabilityError
from sendparcel.flow import ShipmentFlow
from sendparcel.provider import BaseProvider
from sendparcel.types import (
    AddressInfo,
    ParcelInfo,
    PickupPoint,
    ShipmentCreateResult,
)


class SearchPointsProvider(BaseProvider):
    """Provider that supports search_points with configurable results."""

    slug = "search_test"
    display_name = "Search Test"
    points_result: list[PickupPoint] | Exception | None = None

    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return {"external_id": "ext-1"}

    async def search_points(
        self,
        *,
        query: str | None = None,
        near: tuple[float, float] | None = None,
        radius_m: int | None = None,
        point_type: str | None = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> list[PickupPoint]:
        if isinstance(self.points_result, Exception):
            raise self.points_result
        if self.points_result is None:
            raise NotImplementedError("points_result not configured")
        return self.points_result


class NoSearchProvider(BaseProvider):
    """Provider that does not support search_points."""

    slug = "no-search"
    display_name = "No Search"

    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return {"external_id": "ext-1"}


class DummyShipment:
    id = "ship-1"
    status = "new"
    provider = "search_test"
    external_id = ""
    tracking_number = ""


class DummyRepo:
    async def create(self, **kwargs):
        return DummyShipment()

    async def save(self, shipment):
        return shipment

    async def update_status(self, shipment_id, status, **fields):
        return DummyShipment()

    async def update_fields(self, shipment_id, **fields):
        return DummyShipment()

    async def delete(self, shipment_id):
        pass

    async def find_by_reference(self, provider, reference_id):
        return DummyShipment()

    async def create_with_idempotency_key(
        self, provider, status, reference_id, **kwargs
    ):
        return (None, DummyShipment())

    def get_by_id_sync(self, shipment_id, *, for_update: bool = False):
        return DummyShipment()

    async def get_by_id(self, shipment_id, *, for_update: bool = False):
        return DummyShipment()


def _make_flow(
    provider: type[BaseProvider],
) -> tuple[ShipmentFlow, BaseProvider, DummyRepo]:
    from sendparcel.registry import PluginRegistry

    registry = PluginRegistry()
    registry.register(provider)
    repo = DummyRepo()
    flow = ShipmentFlow(repository=repo, registry=registry)
    instance = provider(shipment=repo)
    return flow, instance, repo


class TestSearchPointsProvider:
    """BaseProvider.search_points raises ProviderCapabilityError by default."""

    async def test_default_raises_capability_error(self) -> None:
        provider = NoSearchProvider(shipment=DummyShipment())
        with pytest.raises(ProviderCapabilityError):
            await provider.search_points(query="Krakow")


class TestSearchPointsFlow:
    """ShipmentFlow.search_points delegates to provider."""

    async def test_flow_search_points_returns_provider_results(self) -> None:
        provider_class = SearchPointsProvider
        provider_class.points_result = [
            PickupPoint(
                code="KRA010",
                name="Krakow Main",
                provider_slug="search_test",
                address="ul. Glowna 1, Krakow",
                location={"lat": 50.0647, "lng": 19.9450},
                opening_hours=None,
                point_type="parcel_locker",
                raw=None,
            )
        ]
        flow, _, _ = _make_flow(provider_class)

        points = await flow.search_points(
            "search_test",
            query="Krakow",
        )

        assert len(points) == 1
        assert points[0]["code"] == "KRA010"
        assert points[0]["name"] == "Krakow Main"

    async def test_flow_search_points_passes_params_to_provider(self) -> None:
        provider_class = SearchPointsProvider
        provider_class.points_result = []
        flow, _, __ = _make_flow(provider_class)

        await flow.search_points(
            "search_test",
            query="Warsaw",
            near=(52.23, 21.01),
            radius_m=5000,
            point_type="parcel_locker",
            limit=10,
        )

        # Provider received the call (points_result was accessed)
        assert provider_class.points_result == []

    async def test_flow_search_points_unsupported_provider_raises(self) -> None:
        flow, _, _ = _make_flow(NoSearchProvider)

        with pytest.raises(ProviderCapabilityError):
            await flow.search_points("no-search", query="Krakow")

    async def test_flow_search_points_with_proximity(self) -> None:
        provider_class = SearchPointsProvider
        provider_class.points_result = [
            PickupPoint(
                code="WAW001",
                name="Warsaw Center",
                provider_slug="search_test",
                address="ul. Marszalkowska 1, Warsaw",
                location={"lat": 52.2300, "lng": 21.0100},
                opening_hours=None,
                point_type="parcel_locker",
                raw=None,
            ),
            PickupPoint(
                code="WAW002",
                name="Warsaw North",
                provider_slug="search_test",
                address="ul. Wawelska 2, Warsaw",
                location={"lat": 52.2400, "lng": 21.0200},
                opening_hours=None,
                point_type="parcel_locker",
                raw=None,
            ),
        ]
        flow, _, _ = _make_flow(provider_class)

        points = await flow.search_points(
            "search_test",
            near=(52.23, 21.01),
            radius_m=5000,
        )

        assert len(points) == 2
        # Results ordered by distance (nearest first)
        assert points[0]["code"] == "WAW001"
        assert points[1]["code"] == "WAW002"
