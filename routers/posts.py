from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from auth import get_current_user, get_current_user_optional
from config import settings
from database import get_db
from schemas import (
    LikeResponse,
    PaginatedPostsResponse,
    PostCreate,
    PostResponse,
    PostUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedPostsResponse)
async def get_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
    current_user = Depends(get_current_user),
):
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0

    # Get posts with author
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit),
    )
    posts = result.scalars().all()

    has_more = skip + len(posts) < total

    # Get like status and comments count for current user
    posts_data = []
    for post in posts:
        # Create post dict
        post_dict = {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "date_posted": post.date_posted,
            "likes_count": post.likes_count,
            "user_id": post.user_id,
            "author": {
                "id": post.author.id,
                "username": post.author.username,
                "email": post.author.email,
                "image_file": post.author.image_file,
                "image_path": post.author.image_path,
            },
        }
        
        # Get comments count
        comments_count_result = await db.execute(
            select(func.count()).select_from(models.Comment).where(models.Comment.post_id == post.id)
        )
        post_dict["comments_count"] = comments_count_result.scalar() or 0
        
        # Check if current user liked this post
        like_result = await db.execute(
            select(models.PostLike).where(
                models.PostLike.user_id == current_user.id,
                models.PostLike.post_id == post.id,
            )
        )
        is_liked = like_result.scalar_one_or_none() is not None
        post_dict["is_liked_by_current_user"] = is_liked
        
        posts_data.append(post_dict)

    return PaginatedPostsResponse(
        posts=posts_data,
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    post: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id,
        likes_count=0,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    
    # Create response dict
    post_dict = {
        "id": new_post.id,
        "title": new_post.title,
        "content": new_post.content,
        "date_posted": new_post.date_posted,
        "likes_count": new_post.likes_count,
        "user_id": new_post.user_id,
        "is_liked_by_current_user": False,
        "comments_count": 0,
        "author": {
            "id": new_post.author.id,
            "username": new_post.author.username,
            "email": new_post.author.email,
            "image_file": new_post.author.image_file,
            "image_path": new_post.author.image_path,
        },
    }
    
    return post_dict


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user_optional),
):
    # Get the post with author
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # Load comments separately with their authors
    comments_result = await db.execute(
        select(models.Comment)
        .options(selectinload(models.Comment.author))
        .where(models.Comment.post_id == post_id)
        .order_by(models.Comment.created_at.desc()),
    )
    comments = comments_result.scalars().all()
    
    # Check if current user liked this post (only if user is authenticated)
    is_liked = False
    if current_user:
        like_result = await db.execute(
            select(models.PostLike).where(
                models.PostLike.user_id == current_user.id,
                models.PostLike.post_id == post_id,
            )
        )
        is_liked = like_result.scalar_one_or_none() is not None
    
    # Create a dictionary for the response
    post_dict = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "date_posted": post.date_posted,
        "likes_count": post.likes_count,
        "user_id": post.user_id,
        "is_liked_by_current_user": is_liked,
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "email": post.author.email,
            "image_file": post.author.image_file,
            "image_path": post.author.image_path,
        },
        "comments_count": len(comments),
        "comments": [
            {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
                "user_id": comment.user_id,
                "post_id": comment.post_id,
                "author": {
                    "id": comment.author.id,
                    "username": comment.author.username,
                    "image_path": comment.author.image_path,
                },
            }
            for comment in comments
        ],
    }
    
    return post_dict


@router.post("/{post_id}/like", response_model=LikeResponse)
async def like_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    """Like a post"""
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
    
    like = models.PostLike(user_id=current_user.id, post_id=post_id)
    db.add(like)
    post.likes_count += 1
    
    await db.commit()
    await db.refresh(post)
    
    return LikeResponse(
        post_id=post_id,
        liked=True,
        likes_count=post.likes_count,
    )


@router.delete("/{post_id}/like", response_model=LikeResponse)
async def unlike_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    """Unlike a post"""
    post = await db.get(models.Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
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
    await db.refresh(post)
    
    return LikeResponse(
        post_id=post_id,
        liked=False,
        likes_count=post.likes_count,
    )


@router.get("/{post_id}/likes", response_model=LikeResponse)
async def get_post_like_status(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    """Get like status for a post"""
    post = await db.get(models.Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
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


@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full(
    post_id: int,
    post_data: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    post.title = post_data.title
    post.content = post_data.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    
    # Create response dict
    post_dict = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "date_posted": post.date_posted,
        "likes_count": post.likes_count,
        "user_id": post.user_id,
        "is_liked_by_current_user": False,
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "email": post.author.email,
            "image_file": post.author.image_file,
            "image_path": post.author.image_path,
        },
    }
    
    return post_dict


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    
    # Create response dict
    post_dict = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "date_posted": post.date_posted,
        "likes_count": post.likes_count,
        "user_id": post.user_id,
        "is_liked_by_current_user": False,
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "email": post.author.email,
            "image_file": post.author.image_file,
            "image_path": post.author.image_path,
        },
    }
    
    return post_dict


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )

    # Delete associated likes and comments first
    await db.execute(
        models.PostLike.__table__.delete().where(models.PostLike.post_id == post_id)
    )
    await db.execute(
        models.Comment.__table__.delete().where(models.Comment.post_id == post_id)
    )
    await db.delete(post)
    await db.commit()