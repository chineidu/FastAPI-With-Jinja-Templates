"""
Crud operations for the post repository.

(Using SQLAlchemy ORM v2.x)
"""

from datetime import datetime
from typing import Any

from dateutil.parser import parse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from sqlalchemy.orm import selectinload

from src import create_logger
from src.db.models import DBPost
from src.schemas.db.models import PostSchema
from src.schemas.types import PostStatusEnum

logger = create_logger(__name__)


class PostRepository:
    """CRUD operations for the post repository."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----- Read operations -----
    async def aget_post_by_id(self, id: int) -> DBPost | None:
        """Get a post by its ID with eager loading."""
        try:
            stmt = select(DBPost).where(DBPost.id == id).options(selectinload(DBPost.user))
            return await self.db.scalar(stmt)
        except Exception as e:
            logger.error(f"Error fetching post by id '{id}': {e}")
            return None

    async def aget_post_by_user_id(self, user_id: str) -> DBPost | None:
        """Get a post by its external ID with eager loading."""
        try:
            stmt = select(DBPost).where(DBPost.user_id == user_id).options(selectinload(DBPost.user))
            return await self.db.scalar(stmt)
        except Exception as e:
            logger.error(f"Error fetching post by user_id '{user_id}': {e}")
            return None

    async def aget_post_by_slug(self, slug: str) -> DBPost | None:
        """Get a post by its slug with eager loading."""
        try:
            stmt = select(DBPost).where(DBPost.slug == slug).options(selectinload(DBPost.user))
            return await self.db.scalar(stmt)
        except Exception as e:
            logger.error(f"Error fetching post by slug '{slug}': {e}")
            return None

    async def aget_posts_cursor(
        self, user_id: int, limit: int = 20, last_seen_id: int | None = None
    ) -> tuple[list[DBPost], int | None]:
        """
        Fetch posts using cursor-based pagination (Seek Method) with eager loading.

        Parameters
        ----------
        user_id : int
            The unique identifier of the user whose posts are being fetched.
        limit : int, optional
            Number of posts to fetch, by default 20
        last_seen_id : int | None, optional
            The ID of the last seen post from the previous page, by default None

        Returns
        -------
        tuple[list[DBPost], int | None]
            A tuple containing the list of posts and the next cursor (last post's ID) or
            None if no more records.
        """
        try:
            query = (
                select(DBPost)
                .where(DBPost.user_id == user_id)
                .order_by(DBPost.id.asc())
                .limit(limit)
                .options(selectinload(DBPost.user))
            )

            # If we have a cursor, seek to the next record
            if last_seen_id is not None:
                query = query.where(DBPost.id > last_seen_id)

            result = await self.db.scalars(query)
            posts = list(result.all())

            # Calculate the next cursor
            next_cursor = posts[-1].id if posts else None

            return (posts, next_cursor)

        except Exception as e:
            logger.error(f"Error fetching posts with cursor {last_seen_id}: {e}")
            return [], None

    async def aget_posts_by_creation_time(self, created_after: str, created_before: str) -> list[DBPost]:
        """Get posts created within a specific time range. Uses database-level comparison.

        Parameters
        ----------
        created_after : str
            The start timestamp (inclusive). e.g. "2023-01-01T00:00:00"
        created_before : str
            The end timestamp (inclusive). e.g. "2023-01-31T23:59:59"

        Returns
        -------
        list[DBPost]
            List of posts created within the specified time range.
        """
        # Internal check: ensures the strings are at least valid dates
        # before hitting the DB
        try:
            start: datetime = parse(created_after)
            end: datetime = parse(created_before)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid date format passed to query: {e}")
            raise ValueError("Timestamps must be valid ISO 8601 strings.") from e

        stmt = (
            select(DBPost)
            .where(
                DBPost.published_at >= start,
                DBPost.published_at <= end,
            )
            .options(selectinload(DBPost.user))
        )
        result = await self.db.scalars(stmt)
        return list(result.all())

    # ----- Create operations -----
    async def acreate_post(self, post: PostSchema) -> int:
        """Create post in the database."""
        try:
            db_post = DBPost(**post.model_dump(exclude={"id", "published_at", "updated_at", "deleted_at"}))
        except Exception as e:
            logger.error(f"Error preparing posts for creation: {e}")
            raise e

        try:
            self.db.add(db_post)
            await self.db.commit()

            # Refresh to get the auto-generated ID
            await self.db.refresh(db_post)

            logger.info(f"Successfully created post with ID {db_post.id} in the database.")
            return db_post.id

        except IntegrityError as e:
            logger.error(f"Integrity error creating post: {e}")
            await self.db.rollback()
            raise e

        except Exception as e:
            logger.error(f"Error creating post: {e}")
            await self.db.rollback()
            raise e

    # ----- Update operations -----
    async def aupdate_post(self, post_id: int, update_data: dict[str, Any]) -> DBPost | None:
        """Update a post in the database in a single round trip.

        Note
        ----
        - Only allows updating certain fields to prevent unauthorized changes.
        - Assumes the user is already authorized to update the post
        - Allowed fields: title, post, status, allow_comments, is_pinned
        """

        # Fetch the existing post
        stmt = (
            select(DBPost)
            .where(DBPost.id == post_id)
            # Lock the row (prevents race conditions)
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        db_post: DBPost | None = result.scalar_one_or_none()

        if not db_post:
            logger.warning(f"post id {post_id} not found!")
            return None

        # Update the data
        ALLOWED_FIELDS = {"title", "post", "status", "allow_comments", "is_pinned"}
        has_changes = False

        for field, value in update_data.items():
            if field not in ALLOWED_FIELDS:
                logger.warning(f"Attempt to update disallowed field '{field}' on post {post_id}")
                continue

            # If the current field value is different, update it
            current_value = getattr(db_post, field)
            if current_value != value:
                setattr(db_post, field, value)
                has_changes = True

        if not has_changes:
            logger.info(f"No changes detected for post {post_id}. Skipping update.")
            return db_post

        try:
            await self.db.commit()
            logger.info(f"Successfully updated post {post_id}")
            return db_post

        except Exception as e:
            logger.error(f"Error updating post {post_id}: {e}")
            await self.db.rollback()
            raise

    async def aupdate_post_status(self, user_id: str, status: PostStatusEnum) -> None:
        """Update the status of a post.

        Parameters
        ----------
        user_id : str
            The unique post identifier.
        status : PostStatusEnum
            The new status to set for the post.

        Raises
        ------
        Exception
            If the update fails.
        """
        try:
            update_values: dict[str, Any] = {"status": status.value}

            stmt = update(DBPost).where(DBPost.user_id == user_id).values(**update_values)
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"Marked user_id='{user_id}' as {status.name}.")

        except Exception as e:
            logger.error(f"Error marking user_id='{user_id}' as {status.name}: {e}")
            await self.db.rollback()
            raise e

    # ----- Conversion operations -----
    def convert_DBPost_to_schema(  # noqa: N802
        self, db_post: DBPost
    ) -> PostSchema | None:
        """Convert a DBPost ORM object directly to a Pydantic response schema."""
        try:
            return PostSchema.model_validate(db_post)
        except Exception as e:
            logger.error(f"Error converting DBPost to PostSchema: {e}")
            return None
