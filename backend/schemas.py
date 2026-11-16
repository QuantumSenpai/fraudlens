from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, IPvAnyAddress, model_validator


class TransactionInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=160)
    device_id: str = Field(min_length=1, max_length=160)
    amount: FiniteFloat = Field(gt=0, lt=10_000_000)
    time: FiniteFloat = Field(ge=0)
    lat: FiniteFloat = Field(ge=-90, le=90)
    lon: FiniteFloat = Field(ge=-180, le=180)
    timestamp: str = Field(min_length=1, max_length=40)


class RuleTrigger(BaseModel):
    rule: str
    detail: str
    weight: int


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ml_score: float
    rule_score: int
    final_score: float
    flagged: bool
    triggered_rules: list[RuleTrigger]
    model_version: str
    ml_factors: list[dict[str, float | str]]


class ScreenSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(ge=1, le=16384)
    height: int = Field(ge=1, le=16384)
    pixel_ratio: FiniteFloat | None = Field(default=None, gt=0, le=10)


class DeviceSignalsInput(BaseModel):
    device_id: str = Field(min_length=1, max_length=160)
    user_id: str = Field(min_length=1, max_length=160)
    platform: Literal["web", "mobile", "extension"]
    user_agent: str = Field(min_length=1, max_length=512)
    screen: ScreenSignals
    timezone: str = Field(min_length=1, max_length=64)
    language: str = Field(min_length=1, max_length=35)
    lat: FiniteFloat | None = Field(default=None, ge=-90, le=90)
    lon: FiniteFloat | None = Field(default=None, ge=-180, le=180)
    ip_override: IPvAnyAddress | None = None

    @model_validator(mode="after")
    def coordinates_are_paired(self):
        if (self.lat is None) != (self.lon is None):
            raise ValueError("lat and lon must be provided together")
        return self


class DeviceSignalsResponse(BaseModel):
    device_id: str
    first_seen: str
    last_seen: str
    trust_score: int = Field(ge=0, le=100)


class CheckInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=160)
    device_id: str = Field(min_length=1, max_length=160)
    amount: FiniteFloat = Field(gt=0, lt=10_000_000)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    payment_method: Literal["upi", "card", "netbanking", "wallet"]
    lat: FiniteFloat | None = Field(default=None, ge=-90, le=90)
    lon: FiniteFloat | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates_are_paired(self):
        if (self.lat is None) != (self.lon is None):
            raise ValueError("lat and lon must be provided together")
        return self


class CheckReason(BaseModel):
    rule: str
    detail: str
    weight: int


class CheckResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    check_id: str
    decision: Literal["ALLOW", "REVIEW", "BLOCK"]
    final_score: float = Field(ge=0, le=100)
    ml_score: float = Field(ge=0, le=100)
    rule_score: int = Field(ge=0, le=100)
    reasons: list[CheckReason]
    model_version: str
    ml_factors: list[dict[str, float | str]]
    latency_ms: int = Field(ge=0)


class PaymentOrderInput(BaseModel):
    check_id: UUID


class PaymentOrderResponse(BaseModel):
    order_id: str
    amount: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    key_id: str


class PaymentVerificationInput(BaseModel):
    razorpay_order_id: str = Field(min_length=1, max_length=80)
    razorpay_payment_id: str = Field(min_length=1, max_length=80)
    razorpay_signature: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


class PaymentVerificationResponse(BaseModel):
    order_id: str
    payment_id: str
    status: Literal["created", "authorized", "captured", "failed"]


class ReviewInput(BaseModel):
    outcome: Literal["approve", "reject"]
    reviewer: str = Field(default="admin", min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=2000)
