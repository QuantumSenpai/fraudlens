from fastapi import APIRouter
from schemas import TransactionInput, PredictionResponse, RuleTrigger
from services.model_service import model_service
from services.rule_service import rule_service
from services.db import get_user_history, insert_transaction

router = APIRouter()

ML_WEIGHT = 0.6
RULE_WEIGHT = 0.4


@router.post("/predict", response_model=PredictionResponse)
def predict(txn: TransactionInput):
    ml_score = model_service.predict(txn.amount, txn.time)
    history = get_user_history(txn.user_id)
    rule_score, triggers, rule_flagged = rule_service.evaluate(txn, history)

    final_score = (ML_WEIGHT * ml_score * 100) + (RULE_WEIGHT * rule_score)
    flagged = final_score >= 40 or rule_flagged

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
    )