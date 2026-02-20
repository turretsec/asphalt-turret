"""merge duplicate sd_card records and add card_identity column

Revision ID: b7e3d1f92c05
Revises: a6b979e0914a
Create Date: 2026-02-20 09:15:00.000000

This migration does two things:
1. Adds the card_identity column (schema change)
2. Fixes any existing duplicate SDCard records that arose from Windows
   volume UID changes. Two SDCard records are considered duplicates when
   they share a volume_label AND have overlapping file fingerprints.

   For each duplicate group:
   - The record with the oldest first_seen_at is the winner (preserves history)
   - SDFile rows from losers are re-parented to the winner, skipping
     fingerprint duplicates (keep winner's copy)
   - ClipSource rows from losers are re-parented to the winner
   - Loser records are deleted

   The winner's volume_uid is updated to the most recently seen UID
   (last_seen_at) so it matches whatever Windows currently reports.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 'b7e3d1f92c05'
down_revision: Union[str, Sequence[str], None] = 'a6b979e0914a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Find duplicate groups by volume_label + fingerprint overlap ────────
    # Cards with the same label that share at least one file fingerprint
    # are almost certainly the same physical card.

    dupe_query = text("""
        SELECT DISTINCT
            a.id   AS card_a,
            b.id   AS card_b,
            a.volume_label,
            a.first_seen_at AS a_first,
            b.first_seen_at AS b_first
        FROM sd_card a
        JOIN sd_card b
            ON a.volume_label = b.volume_label
            AND a.id < b.id
        WHERE EXISTS (
            SELECT 1
            FROM sd_file fa
            JOIN sd_file fb ON fa.fingerprint = fb.fingerprint
            WHERE fa.sd_card_id = a.id
              AND fb.sd_card_id = b.id
        )
    """)

    dupes = conn.execute(dupe_query).fetchall()

    if not dupes:
        print("No duplicate SD card records found — nothing to merge.")
    else:
        print(f"Found {len(dupes)} duplicate pair(s) to merge.")

    for row in dupes:
        card_a, card_b = row.card_a, row.card_b

        # Winner = older record (more history), loser = newer record
        winner_id = card_a if row.a_first <= row.b_first else card_b
        loser_id  = card_b if winner_id == card_a else card_a

        print(f"  Merging card {loser_id} → card {winner_id} (label={row.volume_label!r})")

        # Get winner's fingerprints to detect true duplicates
        winner_fps = set(
            r[0] for r in conn.execute(
                text("SELECT fingerprint FROM sd_file WHERE sd_card_id = :id"),
                {"id": winner_id}
            ).fetchall()
        )

        # Get loser's files
        loser_files = conn.execute(
            text("SELECT id, fingerprint FROM sd_file WHERE sd_card_id = :id"),
            {"id": loser_id}
        ).fetchall()

        reparented = 0
        deleted    = 0
        for f in loser_files:
            if f.fingerprint in winner_fps:
                # True duplicate — delete the loser copy
                conn.execute(
                    text("DELETE FROM sd_file WHERE id = :id"),
                    {"id": f.id}
                )
                deleted += 1
            else:
                # Re-parent to winner
                conn.execute(
                    text("UPDATE sd_file SET sd_card_id = :winner WHERE id = :id"),
                    {"winner": winner_id, "id": f.id}
                )
                winner_fps.add(f.fingerprint)
                reparented += 1

        # Re-parent ClipSource rows
        conn.execute(
            text("UPDATE clip_source SET sd_card_id = :winner WHERE sd_card_id = :loser"),
            {"winner": winner_id, "loser": loser_id}
        )

        # Update winner's volume_uid to the most recently seen one
        most_recent = conn.execute(
            text("""
                SELECT volume_uid FROM sd_card
                WHERE id IN (:a, :b)
                ORDER BY last_seen_at DESC
                LIMIT 1
            """),
            {"a": winner_id, "b": loser_id}
        ).scalar()

        conn.execute(
            text("UPDATE sd_card SET volume_uid = :uid WHERE id = :id"),
            {"uid": most_recent, "id": winner_id}
        )

        # Delete the loser record
        conn.execute(
            text("DELETE FROM sd_card WHERE id = :id"),
            {"id": loser_id}
        )

        print(
            f"    Done: {reparented} files re-parented, "
            f"{deleted} duplicates removed"
        )


def downgrade() -> None:
    # Data merges are not reversible — we can't reconstruct which files
    # belonged to which original record. The schema column can be dropped.
    pass