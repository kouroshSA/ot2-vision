"""Quick protocol executor for interactive use."""

import signal
import sys

from .ot2_client import OT2Client

# Default connection from .env
_client = None


def get_client(host: str = "169.254.142.150", port: int = 31950) -> OT2Client:
    global _client
    if _client is None:
        _client = OT2Client(host, port)
    return _client


def run(protocol_code: str, host: str = "169.254.142.150", port: int = 31950) -> str:
    """Upload and execute a protocol string. Returns final status."""
    client = get_client(host, port)
    run_id = None

    def emergency_stop(signum, frame):
        print("\n*** EMERGENCY STOP ***")
        if run_id:
            try:
                client.stop_run(run_id)
            except Exception:
                pass
        sys.exit(1)

    signal.signal(signal.SIGINT, emergency_stop)

    protocol_id = client.upload_protocol(protocol_code)
    run_id = client.create_run(protocol_id, poll_analysis=True)
    client.start_run(run_id)
    status = client.wait_for_run(run_id, timeout=300, poll_interval=2)

    if status != "succeeded":
        errors = client.get_run_errors(run_id)
        for e in errors:
            print(f"Error: {e.get('detail', e)}")

    return status
