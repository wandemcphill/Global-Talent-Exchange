from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.models.attachment import Attachment
from backend.app.models.user import User

from .schemas import AttachmentView

router = APIRouter(prefix="/api/attachments", tags=["attachments"])


@router.post("", response_model=AttachmentView, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AttachmentView:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachment is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Attachment too large.")
    attachment = Attachment(
        filename=file.filename or "attachment",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        data=content,
        created_by_user_id=current_user.id,
        metadata_json={},
    )
    session.add(attachment)
    session.commit()
    session.refresh(attachment)
    return AttachmentView.model_validate(attachment)


@router.get("/{attachment_id}")
def download_attachment(
    attachment_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    attachment = session.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found.")
    if attachment.created_by_user_id not in {None, current_user.id} and current_user.role.value not in {"admin", "super_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this attachment.")
    return Response(
        content=attachment.data,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'attachment; filename=\"{attachment.filename}\"'},
    )
