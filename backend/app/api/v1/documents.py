import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_scoped_db
from app.api.v1.envelope import envelope
from app.models.user import User
from app.schemas.document import (
    CreateLinkRequest,
    DocumentOut,
    DocumentSearchResultOut,
    DocumentUploadOut,
    LinkedEntityOut,
)
from app.services.document_service import DocumentError, DocumentNotFoundError, DocumentService
from app.services.storage import LocalFileStorage

router = APIRouter(prefix="/documents", tags=["documents"])

_FILE_TYPE_BY_EXTENSION = {
    "pdf": "pdf",
    "docx": "docx",
    "pptx": "pptx",
    "xlsx": "xlsx",
}


def _infer_file_type(filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _FILE_TYPE_BY_EXTENSION.get(extension, "other")


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"error": {"code": "not_found", "message": "Document not found."}}
    )


async def _document_out(service: DocumentService, document) -> DocumentOut:
    tags = await service.get_tags(document.id)
    return DocumentOut(
        id=document.id,
        title=document.title,
        file_type=document.file_type,
        size_bytes=document.size_bytes,
        ai_summary=document.ai_summary,
        visibility=document.visibility,
        source=document.source,
        tags=tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.post("", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    visibility: str = Form(default="org"),
    force: bool = Form(default=False),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = DocumentService(session, LocalFileStorage())
    content = await file.read()
    try:
        document = await service.upload(
            organization_id=user.organization_id,
            title=title or file.filename or "Untitled",
            file_type=_infer_file_type(file.filename or ""),
            content=content,
            visibility=visibility,
            force=force,
        )
    except DocumentError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"error": {"code": exc.code, "message": exc.message}}
        ) from exc
    return envelope(DocumentUploadOut(document_id=document.id, status="processed"))


@router.get("")
async def list_documents(
    limit: int = Query(default=25, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = DocumentService(session, LocalFileStorage())
    documents = await service.list_documents(limit=limit)
    return envelope([await _document_out(service, doc) for doc in documents])


@router.get("/search")
async def search_documents(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = DocumentService(session, LocalFileStorage())
    results = await service.search(
        q, limit=limit, include_admin_only=user.role in ("owner", "admin")
    )
    return envelope(
        [
            DocumentSearchResultOut(id=doc.id, title=doc.title, file_type=doc.file_type, excerpt=excerpt)
            for doc, excerpt in results
        ]
    )


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = DocumentService(session, LocalFileStorage())
    try:
        document = await service.get(document_id)
    except DocumentNotFoundError:
        raise _not_found()
    if document.visibility == "admin_only" and user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "permission_denied", "message": "Admin/Owner only."}},
        )
    return envelope(await _document_out(service, document))


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> None:
    service = DocumentService(session, LocalFileStorage())
    try:
        await service.soft_delete(document_id)
    except DocumentNotFoundError:
        raise _not_found()


@router.post("/{document_id}/links", status_code=201)
async def create_link(
    document_id: uuid.UUID,
    body: CreateLinkRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_scoped_db),
) -> dict:
    service = DocumentService(session, LocalFileStorage())
    try:
        link = await service.create_link(
            document_id,
            target_type=body.target_type,
            target_id=body.target_id,
            relationship=body.relationship,
        )
    except DocumentNotFoundError:
        raise _not_found()
    return envelope(LinkedEntityOut.model_validate(link))
