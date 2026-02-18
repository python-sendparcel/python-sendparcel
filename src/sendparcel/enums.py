"""Shipment processing enums."""

from enum import StrEnum


class ShipmentStatus(StrEnum):
    """Shipment lifecycle status."""

    NEW = "new"
    CREATED = "created"
    LABEL_READY = "label_ready"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"
    RETURNED = "returned"


class LabelFormat(StrEnum):
    """Shipping label format."""

    PDF = "PDF"
    ZPL = "ZPL"
    PNG = "PNG"
    EPL = "EPL"


class ConfirmationMethod(StrEnum):
    """How the provider confirms shipment status updates."""

    PUSH = "PUSH"
    PULL = "PULL"
