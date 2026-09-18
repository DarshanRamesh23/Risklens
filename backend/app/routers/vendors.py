from fastapi import APIRouter, HTTPException

from app.db.postgres import Finding, Vendor, get_session
from app.schemas import FindingOut, VendorCreate, VendorOut

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


@router.post("", response_model=VendorOut)
def create_vendor(payload: VendorCreate):
    session = get_session()
    try:
        vendor = Vendor(**payload.model_dump())
        session.add(vendor)
        session.commit()
        session.refresh(vendor)
        return vendor
    finally:
        session.close()


@router.get("", response_model=list[VendorOut])
def list_vendors():
    session = get_session()
    try:
        return session.query(Vendor).order_by(Vendor.created_at.desc()).all()
    finally:
        session.close()


@router.get("/{vendor_id}", response_model=VendorOut)
def get_vendor(vendor_id: int):
    session = get_session()
    try:
        vendor = session.get(Vendor, vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return vendor
    finally:
        session.close()


@router.get("/{vendor_id}/findings", response_model=list[FindingOut])
def get_vendor_findings(vendor_id: int):
    session = get_session()
    try:
        return (
            session.query(Finding)
            .filter(Finding.vendor_id == vendor_id)
            .order_by(Finding.created_at.desc())
            .all()
        )
    finally:
        session.close()
