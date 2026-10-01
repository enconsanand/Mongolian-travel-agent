"""The planner's request, the model's reading of it, and the structured plan built from both."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.i18n import Lang

Style = Literal["value", "comfort", "culture"]
PlanWarning = Literal["unresolved_place", "no_availability", "over_budget", "too_many_places"]

MAX_TRIP_DAYS = 30


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(default="", max_length=2000)
    guests: int = Field(ge=1, le=60)
    start_date: date
    end_date: date
    budget_mnt: int | None = Field(default=None, ge=0)  # None: no limit
    style: Style
    lang: Lang = "mn"

    @model_validator(mode="after")
    def _dates(self) -> "PlanRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        if (self.end_date - self.start_date).days + 1 > MAX_TRIP_DAYS:
            raise ValueError(f"a trip is at most {MAX_TRIP_DAYS} days")
        return self

    @property
    def nights(self) -> int:
        return (self.end_date - self.start_date).days


class PlaceNights(BaseModel):
    place: str = Field(description="The place as the traveller wrote it")
    nights: int = Field(ge=1, le=MAX_TRIP_DAYS)


class TripIntent(BaseModel):
    """What the planner model read from the request. Names only: ids come from the resolver.

    Every list is bounded and there is no free-form map: decoding against an open-ended schema, Workers AI's
    llama kept inventing keys until it ran out of tokens.
    """

    must_places: list[str] = Field(
        default=[], max_length=12, description="Every place the traveller wants to visit, as written"
    )
    avoid_places: list[str] = Field(default=[], max_length=12, description="Places the traveller does not want")
    interests: list[str] = Field(
        default=[], max_length=8, description="Activities, e.g. horse riding, stargazing, festival"
    )
    landscape: Literal["water", "mountain", "desert", ""] = Field(
        default="",
        description="When they named no place: water (lake, river), mountain (rock, peak), or desert (sand, gobi)",
    )
    nights: list[PlaceNights] = Field(
        default=[], max_length=12, description="Only where the traveller asked for a number of nights"
    )

    @property
    def nights_hint(self) -> dict[str, int]:
        return {n.place: n.nights for n in self.nights}


class ResolvedPlace(BaseModel):
    query: str
    place_id: str | None
    status: Literal["included", "unresolved"]


class StayPick(BaseModel):
    stay_id: str
    unit_type: str
    units: int = Field(ge=1)
    nights: int = Field(ge=1)
    total_mnt: int = Field(ge=0)


class PlanDay(BaseModel):
    """One day; field-for-field an ``ItineraryDay`` plus distance, drive time and the stay pick."""

    day: int = Field(ge=1)
    date: str
    from_place_id: str
    to_place_id: str
    via_place_ids: list[str] = []  # visited on the way when there are more places than nights
    route_id: str | None = None
    distance_km: int = 0
    drive_time_min: int = 0
    stay: StayPick | None = None  # set on the first night of each stay block
    stay_id: str | None = None  # the stay slept in that night (every night of a block)
    event_ids: list[str] = []
    note: str | None = None


class Totals(BaseModel):
    stays_mnt: int = 0
    events_mnt: int = 0
    total_mnt: int = 0
    budget_mnt: int | None = None
    within_budget: bool = True


class TripFit(BaseModel):
    """Whether the dates leave time to arrive, sleep, and return. Decided from drive time, not by the model."""

    feasible: bool = True
    min_nights: int = 0
    drive_min: int = 0
    place_id: str | None = None


class Assembly(BaseModel):
    days: list[PlanDay]
    totals: Totals
    warnings: list[PlanWarning]
    fit: TripFit = Field(default_factory=TripFit)
