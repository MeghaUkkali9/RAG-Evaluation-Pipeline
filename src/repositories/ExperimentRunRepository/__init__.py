from sqlalchemy.orm import Session

from src.models.experiment_run import ExperimentRun
from src.services.EvaluationService.schemas import ExperimentResult


class ExperimentRunRepository:
    def __init__(self, session: Session):
        self._session = session

    def save_result(self, result: ExperimentResult) -> ExperimentRun:
        per_query = []
        for pq in result.per_query:
            per_query.append(pq.model_dump())

        run = ExperimentRun(
            name=result.config.name,
            config=result.config.model_dump(mode="json"),
            metrics={
                "retrieval": result.retrieval.model_dump(),
                "ops": result.ops.model_dump(),
                "per_query": per_query,
            },
        )

        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run

    def list_all(self) -> list[ExperimentRun]:
        return self._session.query(ExperimentRun).order_by(ExperimentRun.created_at).all()
