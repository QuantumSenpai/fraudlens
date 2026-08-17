from pydantic import BaseModel
from typing import Optional


class TransactionInput(BaseModel):
    user_id: str
    device_id: str
    amount: float
    time: float
    lat: float
    lon: float
    timestamp: str


class RuleTrigger(BaseModel):
    rule: str
    detail: str
    weight: int


class PredictionResponse(BaseModel):
    ml_score: float
    rule_score: int
    final_score: float
    flagged: bool
    triggered_rules: list[RuleTrigger]