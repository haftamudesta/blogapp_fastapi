from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from auth import get_current_user
from config import settings
from database import get_db
from schemas import PaginatedPostsResponse, PostCreate, PostResponse, PostUpdate

router = APIRouter()


@router.get("", response_model=PaginatedPostsResponse)
async def get_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
    current_user = Depends(get_current_user),
):
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit),
    )
    posts = result.scalars().all()

    has_more = skip + len(posts) < total

    # Get like status for current user
    posts_data = []
    for post in posts:
        post_dict = PostResponse.model_validate(post)
        
        # Check if current user liked this post
        like_result = await db.execute(
            select(models.PostLike).where(
                models.PostLike.user_id == current_user.id,
                models.PostLike.post_id == post.id,
            )
        )
        is_liked = like_result.scalar_one_or_none() is not None
        post_dict.is_liked_by_current_user = is_liked
        
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
    
    # Set is_liked_by_current_user to False for new post
    post_response = PostResponse.model_validate(new_post)
    post_response.is_liked_by_current_user = False
    return post_response


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # Check if current user liked this post
    post_response = PostResponse.model_validate(post)
    like_result = await db.execute(
        select(models.PostLike).where(
            models.PostLike.user_id == current_user.id,
            models.PostLike.post_id == post_id,
        )
    )
    is_liked = like_result.scalar_one_or_none() is not None
    post_response.is_liked_by_current_user = is_liked
    
    return post_response


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
    
    post_response = PostResponse.model_validate(post)
    post_response.is_liked_by_current_user = False
    return post_response


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
    
    post_response = PostResponse.model_validate(post)
    post_response.is_liked_by_current_user = False
    return post_response


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

    # Delete associated likes
    await db.execute(
        select(models.PostLike).where(models.PostLike.post_id == post_id)
    )
    await db.delete(post)
    await db.commit()