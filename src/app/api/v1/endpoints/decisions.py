from fastapi import APIRouter, status

from app.api.v1.dependencies import ExperimentServiceDep
from app.core.schemas.decision import DecisionBody, DecisionResponse

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.post("", response_model=DecisionResponse, status_code=status.HTTP_200_OK)
async def get_decision(data: DecisionBody, experiment_service: ExperimentServiceDep) -> DecisionResponse:
    return await experiment_service.get_decisions(data)
