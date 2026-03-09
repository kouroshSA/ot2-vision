"""High-level protocol execution: upload → run → monitor."""

import logging

from .ot2_client import OT2Client

logger = logging.getLogger(__name__)


class ProtocolRunner:
    """Upload, execute, and monitor an OT-2 protocol."""

    def __init__(self, client: OT2Client):
        self.client = client

    def run_protocol(
        self,
        protocol_code: str,
        labware_paths: list[str] | None = None,
        wait: bool = True,
        timeout: int = 600,
    ) -> dict:
        """
        Full execution flow: upload → create run → wait for analysis → play → monitor.

        Returns dict with protocol_id, run_id, and final status.
        """
        logger.info("Uploading protocol...")
        protocol_id = self.client.upload_protocol(protocol_code, labware_paths)
        logger.info(f"Protocol uploaded: {protocol_id}")

        logger.info("Creating run...")
        run_id = self.client.create_run(protocol_id, poll_analysis=True)
        logger.info(f"Run created: {run_id}")

        logger.info("Starting run...")
        self.client.start_run(run_id)

        status = "started"
        if wait:
            logger.info("Waiting for run to complete...")
            status = self.client.wait_for_run(run_id, timeout=timeout)
            logger.info(f"Run completed with status: {status}")

        return {
            "protocol_id": protocol_id,
            "run_id": run_id,
            "status": status,
        }
