# Insta360 Link 2C - Linux Installation & Usage Guide

**Device**: Insta360 Link 2C (USB ID: `2e1a:4c03`)
**Driver**: `uvcvideo` (built into the Linux kernel — no third-party driver needed)

---

## Installation

### 1. Connect the Camera

Plug the camera into a USB 3.0 port. Verify it's detected:

```bash
lsusb | grep Insta360
```

Expected output:

```
Bus 001 Device 020: ID 2e1a:4c03 Insta360 Insta360 Link 2C
```

Verify video devices are created:

```bash
ls /dev/video*
```

You should see `/dev/video0` and `/dev/video1`.

### 2. Install v4l-utils (Camera Control)

```bash
sudo apt install -y v4l-utils
```

### 3. Install a Video Viewer

Any one of the following:

```bash
# ffmpeg (includes ffplay)
sudo apt install -y ffmpeg

# mpv (lightweight player)
sudo apt install -y mpv

# VLC
sudo apt install -y vlc

# cheese (GNOME webcam app)
sudo apt install -y cheese
```

---

## Verify the Camera

### Check device info

```bash
v4l2-ctl --device=/dev/video0 --info
```

### List supported formats and resolutions

```bash
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

### Supported Resolutions

| Resolution  | Format     | Frame Rates        |
|-------------|------------|--------------------|
| 3840x2160   | MJPEG, H264 | 24, 25, 30 fps   |
| 1920x1440   | MJPEG, H264 | 24, 25, 30 fps   |
| 1920x1080   | MJPEG, H264 | 24, 25, 30 fps   |
| 1280x960    | MJPEG, H264 | 24, 25, 30 fps   |
| 1280x720    | MJPEG, H264 | 24, 25, 30 fps   |

---

## Live Preview

```bash
# Quick preview (default resolution)
ffplay /dev/video0

# 4K MJPEG
ffplay -video_size 3840x2160 -input_format mjpeg /dev/video0

# 4K H.264
ffplay -video_size 3840x2160 -input_format h264 /dev/video0

# 1080p
ffplay -video_size 1920x1080 -input_format mjpeg /dev/video0

# Using mpv
mpv av://v4l2:/dev/video0

# Using VLC
vlc v4l2:///dev/video0
```

---

## Camera Controls

### List all available controls

```bash
v4l2-ctl -d /dev/video0 --list-ctrls
```

### Image Adjustments

| Control       | Range    | Default |
|---------------|----------|---------|
| brightness    | 0–100    | 50      |
| contrast      | 0–100    | 50      |
| saturation    | 0–100    | 50      |
| sharpness     | 0–100    | 50      |
| hue           | -15–15   | 0       |

```bash
v4l2-ctl -d /dev/video0 --set-ctrl=brightness=60
v4l2-ctl -d /dev/video0 --set-ctrl=contrast=55
v4l2-ctl -d /dev/video0 --set-ctrl=saturation=60
v4l2-ctl -d /dev/video0 --set-ctrl=sharpness=50
```

### White Balance

```bash
# Auto white balance (default)
v4l2-ctl -d /dev/video0 --set-ctrl=white_balance_automatic=1

# Manual white balance (2000K–10000K)
v4l2-ctl -d /dev/video0 --set-ctrl=white_balance_automatic=0
v4l2-ctl -d /dev/video0 --set-ctrl=white_balance_temperature=5500
```

### Pan, Tilt, Zoom (PTZ)

```bash
# Zoom: 100 (1x) to 400 (4x)
v4l2-ctl -d /dev/video0 --set-ctrl=zoom_absolute=200

# Pan: -522000 to 522000 (steps of 3600)
v4l2-ctl -d /dev/video0 --set-ctrl=pan_absolute=0

# Tilt: -324000 to 360000 (steps of 3600)
v4l2-ctl -d /dev/video0 --set-ctrl=tilt_absolute=0
```

### Focus

```bash
# Auto focus (default)
v4l2-ctl -d /dev/video0 --set-ctrl=focus_automatic_continuous=1

# Manual focus (0–100)
v4l2-ctl -d /dev/video0 --set-ctrl=focus_automatic_continuous=0
v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50
```

### Anti-Flicker (Power Line Frequency)

```bash
# 0=Disabled, 1=50Hz, 2=60Hz
v4l2-ctl -d /dev/video0 --set-ctrl=power_line_frequency=1
```

---

## Recording

```bash
# Record 4K MJPEG to file
ffmpeg -f v4l2 -video_size 3840x2160 -input_format mjpeg -i /dev/video0 -c:v copy output.mkv

# Record 4K H.264 to file
ffmpeg -f v4l2 -video_size 3840x2160 -input_format h264 -i /dev/video0 -c:v copy output.mp4

# Record 1080p with audio from the built-in mic
ffmpeg -f v4l2 -video_size 1920x1080 -input_format mjpeg -i /dev/video0 \
       -f alsa -i default \
       -c:v libx264 -c:a aac output.mp4
```

Press `q` to stop recording.

---

## Gesture Control

The Insta360 Link 2C has an on-board AI processor that handles gesture recognition directly on the camera hardware. Gestures work on Linux without any additional software.

**Built-in gestures:**

| Gesture        | Action                  |
|----------------|-------------------------|
| Open palm      | Zoom in / zoom out      |
| "L" shape      | Whiteboard mode         |
| Peace sign     | Center on face          |

> **Note:** Gesture settings can only be customized via the Insta360 Link Controller app on Windows/macOS. On Linux, gestures work with their default configuration.

---

## Troubleshooting

### Camera not detected

```bash
# Check USB connection
lsusb | grep Insta360

# Check kernel driver is loaded
lsmod | grep uvcvideo

# Load driver manually if needed
sudo modprobe uvcvideo
```

### Permission denied on /dev/video0

Add your user to the `video` group:

```bash
sudo usermod -aG video $USER
```

Log out and back in for it to take effect.

### No /dev/video* devices

```bash
# Check kernel messages for errors
dmesg | grep -i "insta360\|uvc\|video"
```

### Multiple cameras — identify which is which

```bash
v4l2-ctl --list-devices
```
