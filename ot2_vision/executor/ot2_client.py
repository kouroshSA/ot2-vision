"""Lightweight OT-2 REST API client."""

import json
import logging
import tempfile
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class OT2Client:
    """Lightweight OT-2 REST API client for protocol upload and execution."""

    def __init__(self, host: str, port: int = 31950):
        self.base_url = f"http://{host}:{port}"
        self.headers = {"Opentrons-Version": "3"}
        self.json_headers = {
            "Opentrons-Version": "3",
            "Content-Type": "application/json",
        }

    def health_check(self) -> dict:
        """Check robot connectivity. Returns health JSON."""
        resp = requests.get(f"{self.base_url}/health", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def upload_protocol(self, protocol_code: str, labware_paths: list[str] | None = None) -> str:
        """Upload a protocol string + optional labware JSONs. Returns protocol_id."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, prefix="ot2_vision_") as f:
            f.write(protocol_code)
            protocol_path = f.name

        file_handles = []
        try:
            proto_fh = open(protocol_path, "rb")
            file_handles.append(proto_fh)
            files = [("files", ("protocol.py", proto_fh))]

            if labware_paths:
                for lw_path in labware_paths:
                    p = Path(lw_path)
                    fh = open(lw_path, "rb")
                    file_handles.append(fh)
                    files.append(("files", (p.name, fh)))

            resp = requests.post(
                f"{self.base_url}/protocols",
                headers={"Opentrons-Version": "3"},
                files=files,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]["id"]
        finally:
            for fh in file_handles:
                fh.close()
            Path(protocol_path).unlink(missing_ok=True)

    def create_run(self, protocol_id: str, poll_analysis: bool = True, timeout: int = 120) -> str:
        """Create a run from protocol. Optionally wait for analysis. Returns run_id."""
        payload = json.dumps({"data": {"protocolId": protocol_id}})
        resp = requests.post(f"{self.base_url}/runs", headers=self.json_headers, data=payload, timeout=30)
        resp.raise_for_status()
        run_id = resp.json()["data"]["id"]

        if poll_analysis:
            self._wait_for_analysis(protocol_id, timeout)

        return run_id

    def _wait_for_analysis(self, protocol_id: str, timeout: int = 120) -> None:
        """Poll until protocol analysis is complete."""
        url = f"{self.base_url}/protocols/{protocol_id}/analyses"
        start = time.time()
        while time.time() - start < timeout:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data and data[-1].get("status") == "completed":
                    return
                if data and data[-1].get("status") == "failed":
                    raise RuntimeError(f"Protocol analysis failed: {data[-1]}")
            time.sleep(3)
        raise TimeoutError("Protocol analysis did not complete in time")

    def start_run(self, run_id: str) -> None:
        """Start (play) a run."""
        payload = json.dumps({"data": {"actionType": "play"}})
        resp = requests.post(f"{self.base_url}/runs/{run_id}/actions", headers=self.json_headers, data=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"Started run {run_id}")

    def get_run_status(self, run_id: str) -> str:
        """Get current run status."""
        resp = requests.get(f"{self.base_url}/runs/{run_id}", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()["data"]["status"]

    def wait_for_run(self, run_id: str, timeout: int = 600, poll_interval: int = 5) -> str:
        """Poll until run completes. Returns final status."""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_run_status(run_id)
            if status == "succeeded":
                return status
            if status in ("failed", "stopped"):
                raise RuntimeError(f"Run {run_id} ended with status: {status}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Run {run_id} did not complete within {timeout}s")

    def stop_run(self, run_id: str) -> None:
        """Stop a running run."""
        payload = json.dumps({"data": {"actionType": "stop"}})
        resp = requests.post(f"{self.base_url}/runs/{run_id}/actions", headers=self.json_headers, data=payload, timeout=10)
        resp.raise_for_status()

    def cancel_current_run(self) -> str | None:
        """Stop whatever run is currently active. Returns run_id if stopped, None if nothing active."""
        runs = self.list_runs()
        for run in runs:
            if run.get("current") and run.get("status") in ("running", "paused"):
                run_id = run["id"]
                self.stop_run(run_id)
                logger.info(f"Cancelled active run {run_id}")
                return run_id
        return None

    def home(self) -> None:
        """Home the robot via the POST /robot/home endpoint."""
        payload = json.dumps({"target": "robot"})
        resp = requests.post(f"{self.base_url}/robot/home", headers=self.json_headers, data=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Robot homed")

    def set_lights(self, on: bool) -> None:
        """Turn the deck lights on or off."""
        payload = json.dumps({"on": on})
        resp = requests.post(f"{self.base_url}/robot/lights", headers=self.json_headers, data=payload, timeout=10)
        resp.raise_for_status()

    def get_run_errors(self, run_id: str) -> list:
        """Get error details from a run."""
        resp = requests.get(f"{self.base_url}/runs/{run_id}", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("errors", [])

    def list_runs(self) -> list:
        """List all runs."""
        resp = requests.get(f"{self.base_url}/runs", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
