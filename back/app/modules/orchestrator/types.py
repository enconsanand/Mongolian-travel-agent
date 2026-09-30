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


class TripIntent(BaseModel):
    """What the planner model read from the request. Names only: ids come from the resolver."""

    must_places: list[str] = Field(default=[], description="Every place the traveller wants to visit, as written")
    avoid_places: list[str] = Field(default=[], description="Places the traveller does not want")
    interests: list[str] = Field(default=[], description="Activities, e.g. horse riding, stargazing, festival")
    nights_hint: dict[str, int] = Field(default={}, description="Place name as written -> nights wanted there")


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


class Assembly(BaseModel):
    days: list[PlanDay]
    totals: Totals
    warnings: list[PlanWarning]
