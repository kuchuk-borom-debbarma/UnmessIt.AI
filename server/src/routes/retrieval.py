from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from kink import di
from src.services.retrieval_engine.ports.inbound.RetrievalServiceContract import RetrievalServiceContract

router = APIRouter(prefix="/api/retrieval", tags=["Retrieval"])

class QueryRequest(BaseModel):
    query: str

@router.post("/query")
async def query_endpoint(request: QueryRequest):
    """
    Retrieves facts based on the query and generates an answer using the Retrieval Engine pipeline.
    """
    try:
        retrieval_service = di[RetrievalServiceContract]
        answer = retrieval_service.query(text=request.query)
        return answer
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
