from fastapi import APIRouter, File, HTTPException, UploadFile

from app.db.postgres import get_session, Vendor
from app.schemas import IngestResponse
from app.services.ingestion import ingest_policy_document, ingest_vendor_document

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


@router.post("/policy", response_model=IngestResponse)
async def ingest_policy(policy_name: str, file: UploadFile = File(...)):
    raw_bytes = await file.read()
    result = ingest_policy_document(policy_name, file.filename, raw_bytes)
    return {"detail": result}


@router.post("/vendor/{vendor_id}", response_model=IngestResponse)
async def ingest_vendor(vendor_id: int, file: UploadFile = File(...)):
    session = get_session()
    try:
        if not session.get(Vendor, vendor_id):
            raise HTTPException(status_code=404, detail="Vendor not found")
    finally:
        session.close()

    raw_bytes = await file.read()
    result = ingest_vendor_document(vendor_id, file.filename, raw_bytes)
    return {"detail": result}
