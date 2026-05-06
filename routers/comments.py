from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from auth import get_current_user
from config import settings
from database import get_db
from schemas import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    PaginatedCommentsResponse,
)

router = APIRouter(prefix="/api/posts/{post_id}/comments", tags=["comments"])


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    comment: CommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    """Create a new comment on a post"""
    # Check if post exists
    post = await db.get(models.Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    new_comment = models.Comment(
        content=comment.content,
        user_id=current_user.id,
        post_id=post_id,
    )
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment, attribute_names=["author"])
    
    return new_comment


@router.get("", response_model=PaginatedCommentsResponse)
async def get_comments(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
    current_user = Depends(get_current_user),
):
    """Get all comments for a post"""
    # Check if post exists
    post = await db.get(models.Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(models.Comment).where(models.Comment.post_id == post_id)
    )
    total = count_result.scalar() or 0
    
    # Get comments
    result = await db.execute(
        select(models.Comment)
        .options(selectinload(models.Comment.author))
        .where(models.Comment.post_id == post_id)
        .order_by(models.Comment.created_at.desc())
        .offset(skip)
        .limit(limit),
    )
    comments = result.scalars().all()
    
    has_more = skip + len(comments) < total
    
    return PaginatedCommentsResponse(
        comments=comments,
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    post_id: int,
    comment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    """Get a specific comment"""
    result = await db.execute(
        select(models.Comment)
        .options(selectinload(models.Comment.author))
        .where(
            models.Comment.id == comment_id,
            models.Comment.post_id == post_id,
        )
    )
    comment = result.scalars().first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    
    return comment


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    post_id: int,
    comment_id: int,
    comment_update: CommentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    """Update a comment (only author can update)"""
    result = await db.execute(
        select(models.Comment).where(
            models.Comment.id == comment_id,
            models.Comment.post_id == post_id,
        )
    )
    comment = result.scalars().first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this comment",
        )
    
    comment.content = comment_update.content
    await db.commit()
    await db.refresh(comment, attribute_names=["author"])
    
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    post_id: int,
    comment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    """Delete a comment (only author or post owner can delete)"""
    result = await db.execute(
        select(models.Comment)
        .options(selectinload(models.Comment.post))
        .where(
            models.Comment.id == comment_id,
            models.Comment.post_id == post_id,
        )
    )
    comment = result.scalars().first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    
    # Allow deletion if user is comment author OR post author
    if comment.user_id != current_user.id and comment.post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )
    
    await db.delete(comment)
    await db.commit()