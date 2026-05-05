from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
import models
from auth import CurrentUser
from schemas import LikeResponse

router = APIRouter(prefix="/api/posts", tags=["likes"])


@router.post("/{post_id}/like", response_model=LikeResponse)
async def like_post(
    post_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Like a post"""
    # Check if post exists
    post = await db.get(models.Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Check if already liked
    stmt = select(models.PostLike).where(
        models.PostLike.user_id == current_user.id,
        models.PostLike.post_id == post_id,
    )
    result = await db.execute(stmt)
    existing_like = result.scalar_one_or_none()
    
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already liked this post",
        )
    
    # Create like
    like = models.PostLike(user_id=current_user.id, post_id=post_id)
    db.add(like)
    
    post.likes_count += 1
    
    await db.commit()
    
    return LikeResponse(
        post_id=post_id,
        liked=True,
        likes_count=post.likes_count,
    )


@router.delete("/{post_id}/like", response_model=LikeResponse)
async def unlike_post(
    post_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Unlike a post"""
    # Check if post exists
    post = await db.get(models.Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Check if like exists
    stmt = select(models.PostLike).where(
        models.PostLike.user_id == current_user.id,
        models.PostLike.post_id == post_id,
    )
    result = await db.execute(stmt)
    like = result.scalar_one_or_none()
    
    if not like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You haven't liked this post",
        )
    
    await db.delete(like)
    
    post.likes_count -= 1
    
    await db.commit()
    
    return LikeResponse(
        post_id=post_id,
        liked=False,
        likes_count=post.likes_count,
    )


@router.get("/{post_id}/likes", response_model=LikeResponse)
async def get_post_like_status(
    post_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get like status for a post"""
    # Check if post exists
    post = await db.get(models.Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Check if user liked the post
    stmt = select(models.PostLike).where(
        models.PostLike.user_id == current_user.id,
        models.PostLike.post_id == post_id,
    )
    result = await db.execute(stmt)
    liked = result.scalar_one_or_none() is not None
    
    return LikeResponse(
        post_id=post_id,
        liked=liked,
        likes_count=post.likes_count,
    )