.PHONY: test demo run calibrate test-camera install

install:
	pip install -e .

test:
	pytest tests/ -v

test-camera:
	python scripts/test_camera.py

calibrate:
	python scripts/calibrate.py

demo:
	python -m ot2_vision.cli demo "$(INSTRUCTION)" --scene-file $(SCENE)

run:
	python -m ot2_vision.cli run "$(INSTRUCTION)"
