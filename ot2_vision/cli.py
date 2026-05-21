"""CLI entry point for OT-2 Vision-Language-to-Protocol system."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .config import get_config
from .protocol.validator import ProtocolValidator

console = Console()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool) -> None:
    """OT-2 Vision-Language-to-Protocol System"""
    setup_logging(verbose)


@main.command(name="test-camera")
def test_camera() -> None:
    """Test RealSense camera capture with live RGB+Depth display."""
    import cv2

    from .camera.realsense import RealSenseCamera

    console.print("[bold]Starting RealSense camera test...[/bold]")
    cam = RealSenseCamera(width=1280, height=720)
    cam.start()
    console.print("[green]Camera started. Press 'q' to quit.[/green]")

    try:
        while True:
            frame = cam.capture()
            # Normalize depth for visualization
            depth_vis = cv2.applyColorMap(cv2.convertScaleAbs(frame.depth, alpha=0.03), cv2.COLORMAP_JET)
            combined = cv2.addWeighted(frame.rgb, 0.6, depth_vis, 0.4, 0)

            cy, cx = frame.rgb.shape[0] // 2, frame.rgb.shape[1] // 2
            center_depth = frame.depth_at_pixel(cx, cy)
            cv2.putText(combined, f"Center: {center_depth:.3f}m", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("RealSense Test", combined)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cam.stop()
        cv2.destroyAllWindows()


@main.command()
@click.option("--save", type=click.Path(), default=None, help="Save calibration to this path")
def calibrate(save: str | None) -> None:
    """Run camera-to-deck calibration using ArUco markers."""
    import cv2

    from .camera.realsense import RealSenseCamera
    from .grounding.calibration import CameraDeckCalibrator

    config = get_config()
    save_path = save or config.calibration_path

    console.print("[bold]Starting calibration...[/bold]")
    console.print("Place 4 ArUco markers (DICT_4X4_50, IDs 0-3) at the deck calibration points.")
    console.print("Press SPACE to capture and calibrate, 'q' to quit.")

    cam = RealSenseCamera(width=1280, height=720)
    cam.start()
    calibrator = CameraDeckCalibrator()

    try:
        while True:
            frame = cam.capture()
            display = frame.rgb.copy()

            # Show detected markers
            markers = calibrator.detect_markers(frame)
            for mid, pos in markers.items():
                cv2.putText(display, f"M{mid}: ({pos[0]:.0f},{pos[1]:.0f},{pos[2]:.0f})mm", (10, 30 + mid * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.putText(display, f"Markers found: {len(markers)}/4", (10, display.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.imshow("Calibration", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):
                try:
                    T = calibrator.calibrate(frame)
                    error = calibrator.reprojection_error(frame)
                    console.print(f"[green]Calibration successful! Reprojection error: {error:.2f} mm[/green]")
                    calibrator.save(save_path)
                    console.print(f"Saved to {save_path}")
                    break
                except ValueError as e:
                    console.print(f"[red]Calibration failed: {e}[/red]")
            elif key == ord("q"):
                break
    finally:
        cam.stop()
        cv2.destroyAllWindows()


@main.command()
@click.argument("instruction")
@click.option("--execute/--no-execute", default=False, help="Execute on OT-2 (default: no)")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save protocol to this path")
def run(instruction: str, execute: bool, output: str | None) -> None:
    """Run the full pipeline: capture → detect → ground → generate → [execute]."""
    from .pipeline import VisionProtocolPipeline

    pipeline = VisionProtocolPipeline()
    pipeline.initialize(skip_ot2=not execute)

    try:
        console.print(f"[bold]Instruction:[/bold] {instruction}")
        result = pipeline.run(instruction, execute=execute, save_path=output)

        # Show detections
        console.print(f"\n[bold]Detections:[/bold] {len(result['detections'])} objects found")
        for obj in result.get("grounded_objects", []):
            console.print(f"  - {obj.detection.class_name} in Slot {obj.slot_id} ({obj.labware_name})")

        # Show validation
        v = result["validation"]
        if v["valid"]:
            console.print(f"\n[green]Validation: {v['message']}[/green]")
        else:
            console.print(f"\n[red]Validation: {v['message']}[/red]")

        # Show protocol
        console.print(Panel(Syntax(result["protocol_code"], "python", theme="monokai"), title="Generated Protocol"))
        console.print(f"\nSaved to: {result['saved_to']}")

        # Show execution status
        if result["execution"]["status"] != "skipped":
            console.print(f"Execution: {result['execution']}")
    finally:
        pipeline.cleanup()


@main.command()
@click.argument("instruction")
@click.option("--scene-file", type=click.Path(exists=True), help="JSON file with mock scene")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save protocol to this path")
@click.option("--simulate/--no-simulate", default=False, help="Run opentrons_simulate after generation")
def demo(instruction: str, scene_file: str | None, output: str | None, simulate: bool) -> None:
    """Demo mode: generate protocol from mock scene (no camera/OT-2 needed)."""
    from .protocol.generator import ProtocolGenerator
    from .protocol.scene_description import build_mock_scene

    config = get_config()

    # Build scene description
    if scene_file:
        with open(scene_file) as f:
            scene_data = json.load(f)
        # scene_data: {"slots": {"1": ["96-well plate", "corning_96_wellplate_360ul_flat"], ...}}
        slot_labware = {k: tuple(v) for k, v in scene_data["slots"].items()}
    else:
        # Default demo scene: two plates and a tip rack
        slot_labware = {
            "1": ("96-well plate", "corning_96_wellplate_360ul_flat"),
            "3": ("96-well plate", "corning_96_wellplate_360ul_flat"),
            "10": ("300ul tip rack", "opentrons_96_tiprack_300ul"),
        }

    scene_desc = build_mock_scene(slot_labware)

    console.print("[bold]Demo Mode[/bold] (no camera/OT-2 required)")
    console.print(f"[bold]Instruction:[/bold] {instruction}")
    console.print(Panel(scene_desc, title="Scene Description"))

    # Generate protocol
    console.print("\nGenerating protocol with Claude API...")
    generator = ProtocolGenerator(api_key=config.anthropic_api_key)
    code = generator.generate_from_scene_text(instruction, scene_desc)

    # Validate
    is_valid, msg = ProtocolValidator.validate(code)
    if is_valid:
        console.print(f"[green]Validation: {msg}[/green]")
    else:
        console.print(f"[red]Validation: {msg}[/red]")

    # Show protocol
    console.print(Panel(Syntax(code, "python", theme="monokai"), title="Generated Protocol"))

    # Save
    if output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = str(Path(config.protocols_dir) / f"demo_protocol_{ts}.py")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(code)
    console.print(f"\nSaved to: {output}")

    # Simulate
    if simulate:
        console.print("\nRunning opentrons_simulate...")
        sim_ok, sim_output = ProtocolValidator.simulate(code)
        if sim_ok:
            console.print(f"[green]Simulation passed[/green]")
        else:
            console.print(f"[red]Simulation failed:[/red]\n{sim_output}")


@main.command()
@click.argument("protocol_file", type=click.Path(exists=True))
def validate(protocol_file: str) -> None:
    """Validate a generated protocol."""
    code = Path(protocol_file).read_text()

    is_valid, msg = ProtocolValidator.validate(code)
    if is_valid:
        console.print(f"[green]{msg}[/green]")
    else:
        console.print(f"[red]{msg}[/red]")
        sys.exit(1)

    # Also try simulation
    console.print("Running opentrons_simulate...")
    sim_ok, sim_output = ProtocolValidator.simulate(code)
    if sim_ok:
        console.print(f"[green]Simulation passed[/green]")
    else:
        console.print(f"[yellow]Simulation output:[/yellow]\n{sim_output}")


@main.command(name="wave-goodbye")
@click.option("--host", envvar="OT2_IP", required=True, help="OT-2 IP address")
@click.option("--port", envvar="OT2_PORT", default=31950, help="OT-2 port")
def wave_goodbye(host: str, port: int) -> None:
    """Wave goodbye! The robot waves its arm and flashes lights."""
    import signal

    from .executor.ot2_client import OT2Client
    from .executor.primitives import WAVE_GOODBYE

    client = OT2Client(host=host, port=port)
    run_id = None

    def emergency_stop(signum, frame):
        console.print("\n[red bold]EMERGENCY STOP[/red bold]")
        if run_id:
            try:
                client.stop_run(run_id)
            except Exception:
                pass
        sys.exit(1)

    signal.signal(signal.SIGINT, emergency_stop)

    try:
        health = client.health_check()
        console.print(f"[green]Connected to {health['name']}[/green]")
    except Exception as e:
        console.print(f"[red]Connection failed: {e}[/red]")
        sys.exit(1)

    protocol_id = client.upload_protocol(WAVE_GOODBYE)
    run_id = client.create_run(protocol_id, poll_analysis=True)
    console.print("[bold]Waving goodbye...[/bold] (Ctrl+C to stop)")
    client.start_run(run_id)
    status = client.wait_for_run(run_id, timeout=120, poll_interval=2)
    console.print(f"[green]{status}[/green]")


@main.command()
@click.argument("protocol_file", type=click.Path(exists=True))
@click.option("--host", envvar="OT2_IP", required=True, help="OT-2 IP address")
@click.option("--port", envvar="OT2_PORT", default=31950, help="OT-2 port")
def execute(protocol_file: str, host: str, port: int) -> None:
    """Upload and execute a protocol on the OT-2."""
    from .executor.ot2_client import OT2Client
    from .executor.protocol_runner import ProtocolRunner

    code = Path(protocol_file).read_text()

    console.print(f"Connecting to OT-2 at {host}:{port}...")
    client = OT2Client(host=host, port=port)

    try:
        health = client.health_check()
        console.print(f"[green]Connected. Firmware: {health.get('fw_version', 'unknown')}[/green]")
    except Exception as e:
        console.print(f"[red]Connection failed: {e}[/red]")
        sys.exit(1)

    runner = ProtocolRunner(client)
    console.print("Uploading and executing protocol...")
    result = runner.run_protocol(code)
    console.print(f"[green]Run completed: {result['status']}[/green]")
    console.print(f"Protocol ID: {result['protocol_id']}")
    console.print(f"Run ID: {result['run_id']}")


@main.command(name="test-webcam")
@click.option("--device", "-d", type=int, default=None, help="Video device index (e.g., 3 for /dev/video3)")
@click.option("--width", type=int, default=1920, help="Capture width")
@click.option("--height", type=int, default=1080, help="Capture height")
@click.option("--save", type=click.Path(), default=None, help="Save a frame to this path and exit")
def test_webcam(device: int | None, width: int, height: int, save: str | None) -> None:
    """Test webcam capture (for Insta360 Link 2C or any USB camera)."""
    import cv2

    from .camera.webcam import WebcamCamera

    config = get_config()
    dev = device if device is not None else config.camera_device

    console.print(f"[bold]Opening webcam at /dev/video{dev} ({width}x{height})...[/bold]")
    cam = WebcamCamera(device_index=dev, width=width, height=height)
    cam.start()

    if save:
        frame = cam.capture()
        cv2.imwrite(save, frame)
        console.print(f"[green]Saved frame to {save}[/green]")
        cam.stop()
        return

    console.print("[green]Camera started. Press 'q' to quit, 's' to save a frame.[/green]")
    try:
        while True:
            frame = cam.capture()
            cv2.imshow("Webcam Test", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s"):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = f"capture_{ts}.jpg"
                cv2.imwrite(path, frame)
                console.print(f"Saved: {path}")
    finally:
        cam.stop()
        cv2.destroyAllWindows()


@main.command()
@click.option("--image", "-i", type=click.Path(exists=True), default=None, help="Image file to analyze (or capture live)")
@click.option("--device", "-d", type=int, default=None, help="Camera device index")
def analyze(image: str | None, device: int | None) -> None:
    """Analyze the OT-2 deck using Claude Vision (identify labware and slots)."""
    from .camera.webcam import WebcamCamera
    from .vision.scene_analyzer import SceneAnalyzer

    config = get_config()

    if image:
        console.print(f"[bold]Analyzing image: {image}[/bold]")
        analyzer = SceneAnalyzer(api_key=config.anthropic_api_key)
        analysis = analyzer.analyze_image_file(image)
    else:
        dev = device if device is not None else config.camera_device
        console.print(f"[bold]Capturing from /dev/video{dev}...[/bold]")
        cam = WebcamCamera(device_index=dev)
        cam.start()
        jpeg_bytes = cam.capture_jpeg()
        cam.stop()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_path = f"capture_{ts}.jpg"
        Path(img_path).write_bytes(jpeg_bytes)
        console.print(f"Saved capture to {img_path}")

        analyzer = SceneAnalyzer(api_key=config.anthropic_api_key)
        analysis = analyzer.analyze_image(jpeg_bytes)

    console.print(Panel(json.dumps(analysis, indent=2), title="Scene Analysis (JSON)"))

    scene_text = analyzer.build_scene_text(analysis)
    console.print(Panel(scene_text, title="Scene Description"))


@main.command(name="vision-run")
@click.argument("instruction")
@click.option("--execute/--no-execute", default=False, help="Execute on OT-2 (default: no)")
@click.option("--image", "-i", type=click.Path(exists=True), default=None, help="Image file instead of live capture")
@click.option("--device", "-d", type=int, default=None, help="Camera device index")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save protocol to this path")
@click.option("--simulate/--no-simulate", default=False, help="Run opentrons_simulate after generation")
def vision_run(instruction: str, execute: bool, image: str | None, device: int | None, output: str | None, simulate: bool) -> None:
    """Full vision-language pipeline: capture → analyze → generate → [execute]."""
    from .vision_pipeline import VisionLanguagePipeline

    config = get_config()
    dev = device if device is not None else config.camera_device

    pipeline = VisionLanguagePipeline(camera_device=dev)
    pipeline.initialize(skip_camera=image is not None, skip_ot2=not execute)

    try:
        console.print(f"[bold]Instruction:[/bold] {instruction}")
        result = pipeline.run(instruction, execute=execute, save_path=output, image_path=image)

        # Show analysis
        analysis = result["analysis"]
        console.print(f"\n[bold]Scene Analysis:[/bold] {len(analysis.get('labware', []))} labware items identified")
        for item in analysis.get("labware", []):
            console.print(f"  - Slot {item['slot']}: {item['type']} ({item['load_name']}) [{item.get('confidence', '?')}]")
        if analysis.get("notes"):
            console.print(f"  Notes: {analysis['notes']}")

        console.print(Panel(result["scene_text"], title="Scene Description"))

        # Show validation
        v = result["validation"]
        if v["valid"]:
            console.print(f"\n[green]Validation: {v['message']}[/green]")
        else:
            console.print(f"\n[red]Validation: {v['message']}[/red]")

        # Show protocol
        console.print(Panel(Syntax(result["protocol_code"], "python", theme="monokai"), title="Generated Protocol"))
        console.print(f"\nSaved to: {result['saved_to']}")
        console.print(f"Captured image: {result.get('captured_image', 'N/A')}")

        # Simulate
        if simulate:
            console.print("\nRunning opentrons_simulate...")
            sim_ok, sim_output = ProtocolValidator.simulate(result["protocol_code"])
            if sim_ok:
                console.print(f"[green]Simulation passed[/green]")
            else:
                console.print(f"[red]Simulation failed:[/red]\n{sim_output}")

        # Show execution status
        if result["execution"]["status"] != "skipped":
            exec_status = result["execution"]
            if exec_status["status"] == "succeeded":
                console.print(f"\n[green bold]Execution succeeded![/green bold]")
            elif exec_status["status"] == "error":
                console.print(f"\n[red]Execution error: {exec_status['message']}[/red]")
            else:
                console.print(f"\nExecution: {exec_status}")
    finally:
        pipeline.cleanup()


if __name__ == "__main__":
    main()
