"""Handler for scanning SD cards and updating file records."""
import logging
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.services.sd_card_service import scan_sd_card
from asphalt_turret_engine.adapters.volumes import list_removable_volumes
from asphalt_turret_engine.adapters.sd_scanner import is_thinkware_sd_card

logger = logging.getLogger(__name__)


def handle_sd_scan(session: Session, job: Job) -> None:
    """
    Scan all connected SD cards and update database with current files.
    
    This discovers new files and marks missing files as no longer present.
    """
    logger.info("Starting SD card scan")
    
    try:
        # 1. Discover all removable volumes
        volumes = list_removable_volumes()
        
        if not volumes:
            logger.info("No removable volumes found")
            job.message = "No SD cards detected"
            session.commit()
            return
        
        # 2. Filter to only Thinkware SD cards
        thinkware_cards = []
        for volume in volumes:
            try:
                if is_thinkware_sd_card(volume["drive_root"]):
                    thinkware_cards.append(volume)
            except Exception as e:
                logger.warning(f"Error checking {volume['drive_root']}: {e}")
        
        if not thinkware_cards:
            logger.info("No Thinkware SD cards found")
            job.message = "No Thinkware SD cards detected"
            session.commit()
            return
        
        # 3. Scan each Thinkware card
        total_new = 0
        total_updated = 0
        total_deleted = 0
        cards_scanned = 0
        
        for card in thinkware_cards:
            volume_uid = card["volume_uid"]
            volume_label = card.get("volume_label", "Unknown")
            
            logger.info(f"Scanning card: {volume_uid} ({volume_label})")
            
            try:
                # Use your existing scan_sd_card function
                result = scan_sd_card(session, volume_uid=volume_uid)
                
                total_new += result.new
                total_updated += result.updated
                total_deleted += result.deleted
                cards_scanned += 1
                
                logger.info(
                    f"Card {volume_label}: "
                    f"{result.found} found, "
                    f"{result.new} new, "
                    f"{result.updated} updated, "
                    f"{result.deleted} removed"
                )
                
            except Exception as e:
                logger.error(f"Failed to scan card {volume_uid}: {e}")
                # Continue with other cards
        
        # 4. Update job with results
        job.message = (
            f"Scanned {cards_scanned} card(s): "
            f"{total_new} new, {total_updated} updated, {total_deleted} removed"
        )
        session.commit()
        
        logger.info(f"SD scan complete: {job.message}")
        
    except Exception as e:
        logger.error(f"SD scan failed: {e}")
        job.message = f"Scan failed: {str(e)[:200]}"
        session.commit()
        raise