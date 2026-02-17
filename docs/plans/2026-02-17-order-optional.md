# Make Order Optional — Implementation Plan

**Goal:** Decouple `Order` from the `Shipment` protocol and flow, making it an optional convenience.

**Architecture:** Remove `order: Order` from `Shipment` protocol. `ShipmentFlow.create_shipment()` takes explicit address/parcel params. Add `create_shipment_from_order()` convenience. `BaseProvider.create_shipment()` receives address/parcel data as explicit params.

**Tech Stack:** Python 3.12+, asyncio, runtime_checkable protocols, TypedDict

## Tasks

1. Core protocols — Remove order from Shipment
2. Core flow — New create_shipment + create_shipment_from_order
3. Core provider — Explicit params on BaseProvider.create_shipment
4. Core tests — Update all fixtures and flow tests
5. DPD provider — Read from params not self.shipment.order
6. InPost provider — Read from params not self.shipment.order
7. CLI package — Remove order from CLIShipment
8. Django wrapper — Update adapter, keep OrderModelMixin
9. FastAPI wrapper — Support both order-based and direct creation
10. Litestar wrapper — Same as FastAPI changes
11. Documentation updates
