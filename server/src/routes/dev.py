import logging

from fastapi import APIRouter, HTTPException
from kink import di
from src.repositories.sqlite_dev_repository import SqliteDevRepository
from src.services.retrieval_engine.ports.outbound.VectorStoreContract import VectorStoreContract

router = APIRouter(prefix="/dev", tags=["dev"])
logger = logging.getLogger(__name__)

@router.get("/facts")
def get_facts():
    """
    Developer endpoint to fetch deterministic chunks.
    """
    facts = di[SqliteDevRepository].get_facts()
        
    return {
        "status": "success",
        "total_chunks": len(facts),
        "data": facts
    }

@router.get("/seai")
def get_seai():
    """
    Developer endpoint to inspect SEAI raw inputs, episodes, and atoms.
    """
    seai = di[SqliteDevRepository].get_seai()

    return {
        "status": "success",
        **seai,
    }

@router.get("/raw_inputs/{input_id}")
def get_raw_input(input_id: str):
    """
    Developer endpoint to fetch the original raw conversational text.
    """
    raw_input = di[SqliteDevRepository].get_raw_input(input_id)
    if not raw_input:
        raise HTTPException(status_code=404, detail="Raw input not found")
        
    return {
        "status": "success",
        "data": raw_input,
    }

@router.delete("/facts")
def delete_all_facts():
    """
    Developer endpoint to completely wipe the SQLite database tables and the Chroma vector store.
    """
    di[SqliteDevRepository].wipe_all()
    try:
        vector_store = di[VectorStoreContract]
        vector_store.reset()
    except Exception as e:
        logger.warning("dev_vector_reset_failed error=%s", e)
    
    return {
        "status": "success",
        "message": "All databases cleared successfully"
    }
