.PHONY: install test test-physics test-detector test-cloak test-verify synth audit cloak serve-backend serve-web dev clean

PYTHON = backend/.venv/Scripts/python
PIP = backend/.venv/Scripts/pip
PYTEST = backend/.venv/Scripts/pytest

install:
	cd backend && python -m venv .venv
	$(PIP) install --timeout 300 -e backend
	cd web && npm install

test:
	$(PYTEST) backend/tests -v

test-physics:
	$(PYTEST) backend/tests/test_physics.py -v

test-detector:
	$(PYTEST) backend/tests/test_detector.py -v

test-cloak:
	$(PYTEST) backend/tests/test_cloak.py -v

test-verify:
	$(PYTEST) backend/tests/test_verify.py -v

synth:
	$(PYTHON) -m sonar.cli synth-fixture -o sample_leak.wav --planes 2

audit:
	$(PYTHON) -m sonar.cli audit sample_leak.wav

cloak:
	$(PYTHON) -m sonar.cli cloak sample_leak.wav -o sample_cloaked.wav

verify-physics:
	$(PYTHON) -m sonar.cli verify-physics sample_leak.wav

serve-backend:
	$(PYTHON) -m sonar.cli serve --port 8000 --reload

serve-web:
	cd web && npm run dev

dev:
	@echo "Starting Sonar Backend on :8000 and Web on :50242..."
	powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd c:\Projects\sonar; backend\.venv\Scripts\python -m sonar.cli serve'; cd c:\Projects\sonar\web; npm run dev"

clean:
	rm -rf sample_leak.wav sample_cloaked.wav backend/.pytest_cache web/.next

