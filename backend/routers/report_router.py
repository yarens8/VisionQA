
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from database import get_db
from database.models import TestRun
import json
import os

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{run_id}/json")
def export_run_json(run_id: int, db: Session = Depends(get_db)):
    """Test koşusunu JSON olarak dışa aktarır."""
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Test koşusu bulunamadı.")
    
    data = {
        "id": run.id,
        "platform": str(run.platform),
        "status": str(run.status),
        "started_at": str(run.started_at),
        "completed_at": str(run.completed_at),
        "target": run.target,
        "logs": json.loads(run.logs) if run.logs else None
    }
    
    return JSONResponse(content=data, headers={"Content-Disposition": f"attachment; filename=report_{run_id}.json"})

@router.post("/{run_id}/send-to-jira")
async def send_to_jira(run_id: int):
    """Bulunan hatayı Jira'ya ticket olarak açar."""
    # TODO: Jira API integration
    return {"success": true, "message": f"Issue for Run #{run_id} sent to Jira (Mock)"}

@router.post("/{run_id}/notify-slack")
async def notify_slack(run_id: int):
    """Test sonucunu Slack kanalına gönderir."""
    # TODO: Slack Webhook integration
    return {"success": true, "message": f"Notification for Run #{run_id} sent to Slack (Mock)"}


@router.get("/{run_id}/pdf-placeholder")
def export_run_pdf_placeholder(run_id: int):
    """PDF export için placeholder (Kütüphane kurulumu gerektiği için)."""
    return {"message": "PDF oluşturma özelliği için fpdf2 kütüphanesi kurulmalıdır. Şimdilik JSON export kullanabilirsiniz."}
