from datetime import datetime

from fastapi import APIRouter, Depends, Request
from schemas import TransactionInput, PredictionResponse, RuleTrigger
from services.auth import require_merchant
from services.client_ip import resolve_client_ip
from services.db import get_user_history, insert_transaction
from services.model_service import model_service
from services.live_features import build_live_features
from services.rate_limit import rate_limiter
from services.rule_service import rule_service
from services.rules_config import RULES_CONFIG

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
def predict(txn: TransactionInput, request: Request, merchant: dict = Depends(require_merchant)):
    rate_limiter.enforce(
        "checks",
        str(merchant["id"]),
        resolve_client_ip(request),
        limit=60,
        window_seconds=60,
    )
    history = get_user_history(txn.user_id)
    try:
        current_time = datetime.fromisoformat(txn.timestamp.replace("Z", "+00:00"))
    except ValueError:
        current_time = datetime.now().astimezone()
    live_features = build_live_features(
        txn.amount,
        current_time,
        None,
        history,
        0,
        1,
        txn.lat,
        txn.lon,
    )
    ml_score, ml_factors = model_service.predict_with_factors(txn.amount, txn.time, live_features)
    rule_score, triggers, rule_flagged = rule_service.evaluate(txn, history)

    scoring = RULES_CONFIG["scoring"]
    final_score = (scoring["ml_weight"] * ml_score * 100) + (scoring["rule_weight"] * rule_score)
    flagged = final_score >= RULES_CONFIG["scoring"]["legacy_flag_from"] or rule_flagged

    insert_transaction(txn, rule_score, round(ml_score * 100, 2), round(final_score, 2), flagged)

    return PredictionResponse(
        ml_score=round(ml_score * 100, 2),
        rule_score=rule_score,
        final_score=round(final_score, 2),
        flagged=flagged,
        triggered_rules=[
            RuleTrigger(rule=name, detail=detail, weight=weight)
            for name, detail, weight in triggers
        ],
        model_version=model_service.version,
        ml_factors=ml_factors,
    )
