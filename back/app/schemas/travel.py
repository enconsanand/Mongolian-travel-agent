"""Document schemas for the travel collections (the shape of what is stored in MongoDB).

These models are the single source of truth: the seeder checks the mock data against them,
``app.db.validators`` turns them into MongoDB ``$jsonSchema`` validators, and the API reads through them.

Conventions
- ``_id`` is a readable string id (``stay_khatgal_camp_blue_pearl``), exposed as ``id``.
- Human-readable text is bilingual: ``{"mn": ..., "en": ...}`` (``Text``). The API returns one language.
- Dates are ISO strings: ``"2026-10-03"`` for days, ``"2026-10-03T08:00:00Z"`` for timestamps.
- Money is an integer number of MNT (``*_mnt``).
- Coordinates are GeoJSON ``[lng, lat]``.
"""

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

# ----------------------------------------------------------------------------- shared types

Region = Literal["north", "west", "east", "south"]
RegionOrHub = Literal["north", "west", "east", "south", "hub"]
Lang = Literal["mn", "en"]


class Doc(BaseModel):
    """Base for stored documents: strict about unknown fields so the schema stays documented."""

    collection: ClassVar[str] = ""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(alias="_id")
    is_mock: bool = False


class Sub(BaseModel):
    """Base for embedded sub-documents."""

    model_config = ConfigDict(extra="forbid")


class Text(Sub):
    mn: str
    en: str


class Point(Sub):
    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(min_length=2, max_length=2)


class LineString(Sub):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]] = Field(min_length=2)


class Polygon(Sub):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]]


class Image(Sub):
    """A freely licensed Wikimedia Commons photo; show author + license + source link with it."""

    url: str
    original_url: str
    title: str
    license: str
    license_url: str | None = None
    author: str
    source: str
    # near_stay / location: geotagged near the stay or place; event_topic: the real event in an
    # earlier year; type: a generic photo of this kind of stay
    match: Literal["near_stay", "location", "event_topic", "type"]
    distance_m: int | None = None
    # true when the photo is not of this exact thing (the stays are fictional)
    is_illustrative: bool


# ----------------------------------------------------------------------------- geography


class AimagName(Sub):
    name: str
    name_mn: str


class RegionDoc(Doc):
    collection: ClassVar[str] = "regions"

    code: Region
    name: Text
    boundary: Polygon
    boundary_is_approximate: bool
    aimags: list[AimagName]
    highlights: list[Text]
    best_months: list[int]
    min_days: int = Field(ge=1)
    notes: Text


class CoordinateSource(Sub):
    """Provenance of a landmark point (not a verified road entrance)."""

    url: str
    source_id: str
    retrieved_on: str
    coordinate_role: Literal["landmark", "representative_point"]


class PlaceDoc(Doc):
    collection: ClassVar[str] = "places"

    name: Text
    aimag: str
    region: RegionOrHub
    kind: Literal["city", "aimag_center", "soum_center", "attraction"]
    location: Point
    aliases: list[str] = []
    coordinate_source: CoordinateSource | None = None
    fuel_available: bool
    note: Text | None = None
    images: list[Image] = []
    cover_image_url: str | None = None


# ----------------------------------------------------------------------------- routes

Surface = Literal["paved", "mixed", "gravel", "dirt"]


class RouteSegment(Sub):
    seq: int
    from_place_id: str
    to_place_id: str
    surface: Surface
    road_condition: Literal["good", "fair", "poor"]
    distance_km: int = Field(ge=0)
    drive_time_min: int = Field(ge=0)
    fuel_at_end: bool
    hazards: list[str]
    notes: Text | None = None
    geometry: LineString


class RouteDoc(Doc):
    collection: ClassVar[str] = "routes"

    name: Text
    region: Region
    area: str
    from_place_id: str
    to_place_id: str
    waypoint_place_ids: list[str]
    total_distance_km: int = Field(ge=0)
    total_drive_time_min: int = Field(ge=0)
    recommended_days: int = Field(ge=1)
    surface_km: dict[Surface, int]
    vehicle_min: Literal["sedan", "suv_4x4"]
    summary: Text
    segments: list[RouteSegment]
    geometry: LineString


# ----------------------------------------------------------------------------- events


class EventDoc(Doc):
    collection: ClassVar[str] = "events"

    name: Text
    description: Text
    place_id: str
    aimag: str
    region: RegionOrHub
    location: Point
    category: Literal["festival", "music_festival", "naadam", "national_holiday", "outdoor", "religious", "sport"]
    start_date: str
    end_date: str
    ticket_price_mnt: int = Field(ge=0)
    expected_attendance: int = Field(ge=0)
    stay_demand_multiplier: float = Field(ge=0)
    date_confidence: Literal["exact", "approximate"]
    images: list[Image] = []
    cover_image_url: str | None = None


# ----------------------------------------------------------------------------- stays

UnitType = Literal["dorm_bed", "double_room", "family_room", "ger", "suite", "whole_house", "wooden_cabin"]


class StayOwner(Sub):
    name: str
    phone: str
    preferred_channel: Literal["messenger", "phone", "whatsapp"]
    languages: list[str]


class StayUnit(Sub):
    unit_type: UnitType
    count: int = Field(ge=0)
    beds_per_unit: int = Field(ge=1)
    price_mnt: int = Field(ge=0)
    price_basis: Literal["per_unit", "per_person"]
    meals_included: bool


class StaySeason(Sub):
    year_round: bool
    open_from: str | None = None  # "MM-DD"
    open_to: str | None = None


class StayDoc(Doc):
    collection: ClassVar[str] = "stays"

    name: Text
    type: Literal["ger_camp", "guesthouse", "hotel", "house"]
    place_id: str
    aimag: str
    region: RegionOrHub
    location: Point
    owner: StayOwner
    units: list[StayUnit]
    total_beds: int = Field(ge=0)
    amenities: list[str]
    season: StaySeason
    cancellation_policy_id: str
    check_in: str
    check_out: str
    payment_methods: list[Literal["qpay", "cash", "card"]]
    rating: float = Field(ge=0, le=5)
    reviews_count: int = Field(ge=0)
    images: list[Image]
    cover_image_url: str


class CancellationPolicyDoc(Doc):
    collection: ClassVar[str] = "cancellation_policies"

    name: Text
    notes: Text
    free_cancel_hours_before: int = Field(ge=0)
    refund_pct_after_deadline: int = Field(ge=0, le=100)
    no_show_refund_pct: int = Field(ge=0, le=100)
    reschedule_allowed: bool
    reschedule_fee_mnt: int = Field(ge=0)
    deposit_pct: int | None = Field(default=None, ge=0, le=100)
    deposit_refundable: bool | None = None


AvailabilityStatus = Literal["open", "closed_for_season", "sold_out"]


class StayAvailabilityDoc(Doc):
    collection: ClassVar[str] = "stay_availability"

    stay_id: str
    date: str
    unit_type: UnitType
    total: int = Field(ge=0)
    available: int = Field(ge=0)
    status: AvailabilityStatus
    price_mnt: int = Field(ge=0)


# ----------------------------------------------------------------------------- drivers & vehicles


class DriverDoc(Doc):
    collection: ClassVar[str] = "drivers"

    name: Text
    phone: str
    languages: list[str]
    years_experience: int = Field(ge=0)
    rating: float = Field(ge=0, le=5)
    regions_known: list[str]
    regions_served: list[Region]
    region: RegionOrHub
    base_place_id: str
    vehicle_id: str | None = None


class VehicleRental(Sub):
    mode: Literal["with_driver", "self_drive"]
    includes_driver: bool
    price_per_day_mnt: int = Field(ge=0)
    fuel_included: bool
    # with driver
    price_per_km_mnt: int | None = None
    # self-drive
    km_included_per_day: int | None = None
    price_per_extra_km_mnt: int | None = None
    deposit_mnt: int | None = None
    insurance_per_day_mnt: int | None = None
    fuel_policy: str | None = None
    min_driver_age: int | None = None
    license_required: str | None = None
    international_license_ok: bool | None = None
    pickup_place_id: str | None = None
    one_way_drop_fee_mnt: int | None = None


class VehicleDoc(Doc):
    collection: ClassVar[str] = "vehicles"

    type: Literal["bus", "minivan", "sedan", "suv"]
    model: str
    seats: int = Field(ge=1)
    offroad_capable: bool
    fuel_type: Literal["ai92", "ai95", "diesel"]
    fuel_l_per_100km: float = Field(gt=0)
    rental: VehicleRental | None = None
    driver_id: str | None = None
    operator: str | None = None
    base_place_id: str
    region: RegionOrHub
    plate: str
    features: list[str]
    current_location: Point
    status: Literal["available", "on_trip", "scheduled", "maintenance"]


class VehicleAvailabilityDoc(Doc):
    collection: ClassVar[str] = "vehicle_availability"

    vehicle_id: str
    date: str
    status: Literal["available", "booked", "maintenance"]
    booking_id: str | None = None
    region: RegionOrHub


# ----------------------------------------------------------------------------- public transport & shared rides

SeatClass = Literal["standard", "economy", "hard_seat", "platzkart", "kupe"]


class TrainStop(Sub):
    place_id: str
    arrive_offset_min: int = Field(ge=0)
    time: str
    day_offset: int = Field(ge=0)
    fare_from_origin_mnt: dict[str, int]


class SeatClassCapacity(Sub):
    class_: SeatClass = Field(alias="class")
    seats: int = Field(ge=0)


class TransportScheduleDoc(Doc):
    collection: ClassVar[str] = "transport_schedules"

    mode: Literal["bus", "train", "flight", "shared_van"]
    operator: str
    name: Text | None = None
    route_id: str | None = None
    from_place_id: str
    to_place_id: str
    region: Region
    departure_point: Text
    days_of_week: list[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]]
    departure_times: list[str]
    duration_min: int = Field(ge=0)
    price_mnt: int = Field(ge=0)
    seats: int = Field(ge=0)
    vehicle_id: str | None = None
    booking_channel: Text
    stops: list[TrainStop] | None = None
    seat_classes: list[SeatClassCapacity] | None = None


class TransportAvailabilityDoc(Doc):
    collection: ClassVar[str] = "transport_availability"

    schedule_id: str
    mode: Literal["bus", "train", "flight", "shared_van"]
    date: str
    departure_time: str
    seat_class: SeatClass
    seats_total: int = Field(ge=0)
    seats_left: int = Field(ge=0)
    status: AvailabilityStatus
    region: Region


class RidePoster(Sub):
    name: str
    phone: str
    note: Text | None = None


class SharedRideDoc(Doc):
    collection: ClassVar[str] = "shared_rides"

    type: Literal["driver_offer", "traveler_post"]
    from_place_id: str
    to_place_id: str
    region: Region
    date: str
    depart_time: str
    seats_total: int = Field(ge=1)
    seats_left: int = Field(ge=0)
    price_per_seat_mnt: int = Field(ge=0)
    vehicle_id: str | None = None
    driver_id: str | None = None
    posted_by: RidePoster | None = None
    luggage: Text
    notes: Text
    status: Literal["open", "full", "cancelled"]
    bookable: bool


# ----------------------------------------------------------------------------- trips, quotes, bookings, payments


class TripTraveller(Sub):
    name: str
    lang: Lang
    phone: str


class Party(Sub):
    adults: int = Field(ge=1)
    children: int = Field(ge=0)


class Budget(Sub):
    limit_mnt: int = Field(ge=0)
    spent_mnt: int = Field(ge=0)
    currency: Literal["MNT"] = "MNT"


class TripDoc(Doc):
    collection: ClassVar[str] = "trips"

    title: Text
    user_id: str | None = None
    user: TripTraveller
    party: Party
    start_date: str
    end_date: str
    region: Region
    route_id: str | None = None  # a planner-built trip can cross regions: no single stored route
    vehicle_id: str | None = None
    driver_id: str | None = None
    current_version: int = Field(ge=1)
    status: Literal["planned", "awaiting_payment", "booked", "in_progress", "completed", "cancelled"]
    budget: Budget | None = None
    created_at: str


class DayTransport(Sub):
    kind: Literal["flight", "train", "bus", "shared_ride", "self_drive"]
    schedule_id: str | None = None
    seat_class: SeatClass | None = None
    ride_id: str | None = None
    vehicle_id: str | None = None
    note: Text | None = None


class ItineraryDay(Sub):
    day: int = Field(ge=1)
    date: str
    from_place_id: str
    to_place_id: str
    route_id: str | None = None
    stay_id: str | None = None
    transport: DayTransport | None = None
    event_ids: list[str] | None = None
    note: Text | None = None


class ItineraryVersionDoc(Doc):
    """Immutable snapshot: re-planning inserts a new version instead of editing one."""

    collection: ClassVar[str] = "itinerary_versions"

    trip_id: str
    version: int = Field(ge=1)
    created_at: str
    reason: Literal["initial_plan", "delay", "user_change", "provider_cancelled"]
    change_request: str | None = None
    agent_summary: Text | None = None
    days: list[ItineraryDay]


class QuoteLine(Sub):
    kind: Literal["stay", "vehicle", "insurance", "flight", "train", "bus", "shared_ride", "event"]
    ref_id: str
    qty: int = Field(ge=1)
    unit_price_mnt: int = Field(ge=0)
    total_mnt: int = Field(ge=0)
    label: Text


class QuoteDoc(Doc):
    """One option the agent offers for a trip; the user accepts one."""

    collection: ClassVar[str] = "quotes"

    trip_id: str
    user_id: str
    label: Text
    lines: list[QuoteLine]
    total_mnt: int = Field(ge=0)
    currency: Literal["MNT"] = "MNT"
    status: Literal["quoted", "accepted", "declined", "expired"]
    valid_until: str
    created_at: str


# held: inventory is on hold for an open checkout (booking saga step 1)
BookingStatus = Literal["pending_owner", "held", "pending_payment", "confirmed", "cancelled"]


class BookingDoc(Doc):
    """A booked item. ``kind`` decides which of the optional fields are set."""

    collection: ClassVar[str] = "bookings"

    trip_id: str
    user_id: str | None = None
    kind: Literal["stay", "vehicle", "vehicle_rental", "transport", "shared_ride", "event_ticket"]
    status: BookingStatus
    total_price_mnt: int = Field(ge=0)
    checkout_id: str | None = None
    payment_id: str | None = None
    payment_method: str | None = None
    note: Text | None = None
    # stay
    stay_id: str | None = None
    unit_type: UnitType | None = None
    check_in: str | None = None
    check_out: str | None = None
    nights: int | None = None
    guests: int | None = None
    cancellation_policy_id: str | None = None
    deposit_paid_mnt: int | None = None
    balance_due_on_arrival_mnt: int | None = None
    # vehicle / rental
    vehicle_id: str | None = None
    driver_id: str | None = None
    mode: Literal["with_driver", "self_drive"] | None = None
    start_date: str | None = None
    end_date: str | None = None
    days: int | None = None
    deposit_hold_mnt: int | None = None
    # transport / shared ride / event
    schedule_id: str | None = None
    ride_id: str | None = None
    event_id: str | None = None
    date: str | None = None
    from_place_id: str | None = None
    to_place_id: str | None = None
    seat_class: SeatClass | None = None
    seats: int | None = None
    tickets: int | None = None


# awaiting_payment: invoice created, waiting for the rail; expired / failed: it never got paid
PaymentStatus = Literal[
    "quoted",
    "approved_by_user",
    "awaiting_payment",
    "paid",
    "expired",
    "failed",
    "cancelled",
    "refunded",
]


class PaymentMethodRef(Sub):
    type: Literal["card", "qpay"]
    brand: str | None = None
    last4: str | None = None
    is_test_card: bool | None = None
    invoice_id: str | None = None


class StatusChange(Sub):
    status: PaymentStatus
    at: str
    actor: Literal["user", "agent", "owner", "system"]


class Consent(Sub):
    approved_by_user: bool
    max_amount_mnt: int | None = None
    approved_at: str | None = None


class PaymentDoc(Doc):
    """Payment for a trip.

    Lifecycle: quoted -> approved_by_user -> awaiting_payment -> paid -> (cancelled -> refunded), or
    awaiting_payment -> expired / failed. ``provider`` ``qpay`` / ``bonum`` / ``sim`` are the live rails;
    ``stripe_test`` and ``qpay_sandbox`` only appear in the older mock rows. Payments made through AP2 point at
    their checkout and Payment Mandate; ``transaction_id`` (the checkout hash) is unique among them.
    """

    collection: ClassVar[str] = "payments"

    user_id: str
    trip_id: str
    quote_id: str | None = None
    booking_ids: list[str]
    amount_mnt: int = Field(ge=0)
    currency: Literal["MNT"] = "MNT"
    method: PaymentMethodRef
    provider: Literal["qpay", "bonum", "sim", "stripe_test", "qpay_sandbox"]
    provider_ref: str
    status: PaymentStatus
    status_history: list[StatusChange]
    consent: Consent
    idempotency_key: str
    is_sandbox: bool
    checkout_id: str | None = None
    payment_mandate_id: str | None = None
    transaction_id: str | None = None
    # What the rail returned for the user to pay with (QR text, short link, deeplinks) and its payment id
    charge: dict[str, Any] | None = None


class RefundDoc(Doc):
    collection: ClassVar[str] = "refunds"

    payment_id: str
    user_id: str
    trip_id: str
    booking_id: str
    amount_mnt: int = Field(ge=0)
    reason: Literal["provider_cancelled", "user_cancelled", "policy_refund", "duplicate"]
    reason_text: Text
    policy_applied: str
    status: Literal["pending", "succeeded", "failed"]
    provider_ref: str
    requested_at: str
    completed_at: str | None = None


# ----------------------------------------------------------------------------- agent memory & audit


class AuditLogDoc(Doc):
    """Append-only record of every agent action, approval and payment step."""

    collection: ClassVar[str] = "audit_log"

    ts: str
    actor: Literal["user", "agent", "owner", "system"]
    user_id: str | None = None
    trip_id: str | None = None
    action: str
    entity: str
    entity_id: str
    amount_mnt: int | None = None
    details: dict[str, Any] = {}


class ToolCall(Sub):
    name: str
    args: dict[str, Any] = {}


class ChatMessage(Sub):
    role: Literal["user", "agent", "system", "tool"]
    ts: str
    text: str
    tool_calls: list[ToolCall] | None = None


class ConversationDoc(Doc):
    collection: ClassVar[str] = "conversations"

    user_id: str
    trip_id: str | None = None
    lang: Lang
    started_at: str
    updated_at: str
    messages: list[ChatMessage]


class PendingApproval(Sub):
    payment_id: str
    amount_mnt: int = Field(ge=0)


class AgentStateDoc(Doc):
    """Where the agent is in planning a trip, so it can resume after a restart."""

    collection: ClassVar[str] = "agent_state"

    trip_id: str
    user_id: str
    step: Literal["collecting_slots", "planning", "quoting", "awaiting_payment", "booked", "replanning"]
    slots: dict[str, Any]
    missing_slots: list[str]
    pending_approval: PendingApproval | None = None
    updated_at: str


class UserMemoryDoc(Doc):
    """Long-term things the agent learned about a user (preferences, constraints)."""

    collection: ClassVar[str] = "user_memory"

    user_id: str
    kind: Literal["preference", "constraint", "fact"]
    text: str
    source_conversation_id: str | None = None
    created_at: str


class AppConfigDoc(Doc):
    collection: ClassVar[str] = "app_config"

    currency: Literal["MNT"] = "MNT"
    price_per_liter_mnt: dict[str, int]
    remote_area_markup_pct: int = Field(ge=0)
    updated_at: str


# ----------------------------------------------------------------------------- mock travellers (users collection)


class SavedCard(Sub):
    """A saved card: only the provider token and last4, never the number or CVC."""

    type: Literal["card"]
    brand: str
    last4: str = Field(min_length=4, max_length=4)
    exp_month: int = Field(ge=1, le=12)
    exp_year: int
    holder_name: str
    provider: Literal["stripe_test"]
    provider_payment_method: str
    is_default: bool
    is_test_card: bool


class SavedQPay(Sub):
    type: Literal["qpay"]
    is_default: bool


class UserProfileAuth(Sub):
    provider: Literal["backend"]
    password_from_env: str


class MockUserDoc(Doc):
    """Traveller profile fields stored on ``users`` next to the login fields of ``app.models.User``."""

    collection: ClassVar[str] = "users"

    email: str
    first_name: str
    last_name: str
    display_name: Text
    phone: str
    is_active: bool
    lang: Lang
    role: Literal["traveler", "admin"]
    auth: UserProfileAuth
    payment_methods: list[SavedCard | SavedQPay]
    created_at: str


# Every collection loaded from data/mock, keyed by collection name
DOC_MODELS: dict[str, type[Doc]] = {
    m.collection: m
    for m in (
        RegionDoc,
        PlaceDoc,
        RouteDoc,
        EventDoc,
        StayDoc,
        CancellationPolicyDoc,
        StayAvailabilityDoc,
        DriverDoc,
        VehicleDoc,
        VehicleAvailabilityDoc,
        TransportScheduleDoc,
        TransportAvailabilityDoc,
        SharedRideDoc,
        TripDoc,
        ItineraryVersionDoc,
        QuoteDoc,
        BookingDoc,
        PaymentDoc,
        RefundDoc,
        AuditLogDoc,
        ConversationDoc,
        AgentStateDoc,
        UserMemoryDoc,
        AppConfigDoc,
        MockUserDoc,
    )
}
