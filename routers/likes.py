from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Post, PostLike, User
from schemas import LikeResponse
from auth import CurrentUser

router = APIRouter()


@router.post("/{post_id}/like", response_model=LikeResponse)
async def like_post(
    post_id: int,
    current_user: User = Depends(CurrentUser),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    stmt = select(PostLike).where(
        PostLike.user_id == current_user.id,
        PostLike.post_id == post_id,
    )
    result = await db.execute(stmt)
    existing_like = result.scalar_one_or_none()
    
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already liked this post",
        )
    
    like = PostLike(user_id=current_user.id, post_id=post_id)
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
    current_user: User = Depends(CurrentUser),
    db: AsyncSession = Depends(get_db),
):
    """Unlike a post"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    stmt = select(PostLike).where(
        PostLike.user_id == current_user.id,
        PostLike.post_id == post_id,
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
    current_user: User = Depends(CurrentUser),
    db: AsyncSession = Depends(get_db),
):
    """Get like status for a post"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    stmt = select(PostLike).where(
        PostLike.user_id == current_user.id,
        PostLike.post_id == post_id,
    )
    result = await db.execute(stmt)
    liked = result.scalar_one_or_none() is not None
    
    return LikeResponse(
        post_id=post_id,
        liked=liked,
        likes_count=post.likes_count,
    )