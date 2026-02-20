"""Handler for scanning SD cards and updating file records."""
from __future__ import annotations
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.services.sd_card_service import scan_sd_card
from asphalt_turret_engine.adapters.volumes import list_removable_volumes
from asphalt_turret_engine.adapters.sd_scanner import is_thinkware_sd_card

logger = logging.getLogger(__name__)


def handle_sd_scan(session: Session, job: Job) -> None:
    """
    Scan all connected SD cards and update database with current files.
    After each card is scanned, queues a thumb_sd_batch job to pre-generate
    thumbnails in the background.
    """
    logger.info("Starting SD card scan")

    volumes = list_removable_volumes()
    if not volumes:
        job.message = "No SD cards detected"
        session.commit()
        return

    thinkware_cards = []
    for volume in volumes:
        try:
            if is_thinkware_sd_card(volume["drive_root"]):
                thinkware_cards.append(volume)
        except Exception as e:
            logger.warning(f"Error checking {volume['drive_root']}: {e}")

    if not thinkware_cards:
        job.message = "No Thinkware SD cards detected"
        session.commit()
        return

    total_new     = 0
    total_updated = 0
    total_deleted = 0
    cards_scanned = 0

    for card in thinkware_cards:
        volume_uid   = card["volume_uid"]
        volume_label = card.get("volume_label", "Unknown")

        logger.info(f"Scanning card: {volume_uid} ({volume_label})")

        try:
            result = scan_sd_card(session, volume_uid=volume_uid)
            session.commit()

            total_new     += result.new
            total_updated += result.updated
            total_deleted += result.deleted
            cards_scanned += 1

            logger.info(
                f"Card {volume_label}: {result.found} found, "
                f"{result.new} new, {result.updated} updated, "
                f"{result.deleted} removed"
            )

            # Queue thumbnail pre-generation
            # Fetch all file IDs for this card so we can thumbnail them.
            # We only thumbnail files that exist on the card right now —
            # drive_root is captured here while we know the card is mounted.
            #
            # We query ALL file IDs, not just new ones, so that thumbnails
            # for files discovered on previous scans but never viewed also
            # get generated. generate_thumbnail is idempotent — it skips
            # files that already have a cached thumbnail.
            from asphalt_turret_engine.db.models.sd_file import SDFile
            from sqlalchemy import select

            sd_file_ids: list[int] = list(
                session.execute(
                    select(SDFile.id).where(SDFile.sd_card_id == result.sd_card_id)
                ).scalars().all()
            )

            if sd_file_ids:
                thumb_job = job_crud.create_thumb_sd_batch_job(
                    session,
                    volume_uid=volume_uid,
                    drive_root=result.drive_root,
                    sd_file_ids=sd_file_ids,
                )
                session.commit()
                logger.info(
                    f"Queued thumb_sd_batch job {thumb_job.id} "
                    f"for {len(sd_file_ids)} files on {volume_label}"
                )

        except Exception as e:
            logger.error(f"Failed to scan card {volume_uid}: {e}", exc_info=True)

    # Final message
    job.message = (
        f"Scan complete: {cards_scanned} card(s), "
        f"{total_new} new, {total_updated} updated, {total_deleted} removed"
    )
    session.commit()
    logger.info(job.message)