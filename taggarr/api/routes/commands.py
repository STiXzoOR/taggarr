"""Command routes for taggarr API."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import Command, User

router = APIRouter(prefix="/api/v1", tags=["commands"])


class CommandResponse(BaseModel):
    """Command response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    body: str | None
    status: str
    queued_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    duration: str | None
    exception: str | None
    trigger: str


class CreateCommandRequest(BaseModel):
    """Request model for creating a command."""

    name: str
    body: dict | None = None


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


@router.get("/command", response_model=list[CommandResponse])
async def list_commands(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CommandResponse]:
    """List recent commands.

    Returns the last 50 commands ordered by queued_at descending.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        List of recent commands.
    """
    commands = (
        db.query(Command)
        .order_by(Command.queued_at.desc())
        .limit(50)
        .all()
    )

    return [
        CommandResponse(
            id=cmd.id,
            name=cmd.name,
            body=cmd.body,
            status=cmd.status,
            queued_at=cmd.queued_at,
            started_at=cmd.started_at,
            ended_at=cmd.ended_at,
            duration=cmd.duration,
            exception=cmd.exception,
            trigger=cmd.trigger,
        )
        for cmd in commands
    ]


@router.get("/command/{command_id}", response_model=CommandResponse)
async def get_command(
    command_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommandResponse:
    """Get command by ID.

    Args:
        command_id: ID of the command to retrieve.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Command details.

    Raises:
        HTTPException: If command not found.
    """
    command = db.query(Command).filter(Command.id == command_id).first()

    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found",
        )

    return CommandResponse(
        id=command.id,
        name=command.name,
        body=command.body,
        status=command.status,
        queued_at=command.queued_at,
        started_at=command.started_at,
        ended_at=command.ended_at,
        duration=command.duration,
        exception=command.exception,
        trigger=command.trigger,
    )


@router.post("/command", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
async def create_command(
    request: CreateCommandRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommandResponse:
    """Queue a new command.

    Args:
        request: Command creation request.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Created command details.
    """
    command = Command(
        name=request.name,
        body=json.dumps(request.body) if request.body else None,
        status="Queued",
        queued_at=datetime.now(),
        trigger="manual",
    )

    db.add(command)
    db.commit()
    db.refresh(command)

    return CommandResponse(
        id=command.id,
        name=command.name,
        body=command.body,
        status=command.status,
        queued_at=command.queued_at,
        started_at=command.started_at,
        ended_at=command.ended_at,
        duration=command.duration,
        exception=command.exception,
        trigger=command.trigger,
    )


@router.delete("/command/{command_id}", response_model=MessageResponse)
async def cancel_command(
    command_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Cancel a queued command.

    Only commands with status "Queued" can be cancelled.

    Args:
        command_id: ID of the command to cancel.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Success message.

    Raises:
        HTTPException: If command not found or cannot be cancelled.
    """
    command = db.query(Command).filter(Command.id == command_id).first()

    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found",
        )

    if command.status != "Queued":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel command that is not queued",
        )

    db.delete(command)
    db.commit()

    return MessageResponse(message="Command cancelled")
