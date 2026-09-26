# M5 Edge-AI Test Bench

A small USB test bench for the M5 TinyML motion classifier. It checks the device output without reflashing, resetting, or changing firmware.

## What it checks

- Valid prediction labels
- Inference latency
- Prediction sequence gaps
- Stream drops reported by the firmware
- Existing Serial Monitor logs

## Run it

```powershell
cd D:\m5-edge-ai-test-bench
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bench.py --port COM11 --seconds 30
```

Close Arduino Serial Monitor first. The test bench listens at 115200 baud and writes a timestamped JSON report to `reports/`. A nonzero exit code means at least one check failed.

To analyze the saved log from the classifier:

```powershell
.\.venv\Scripts\python.exe bench.py --input "D:\# PREDICTION,161,STILL,5,0.txt"
```

## Expected first result

The current classifier has measured 5–6 µs inference and 0 stream drops in a stable run. This tool verifies those values again as a repeatable test rather than relying on a manual inspection of Serial Monitor output.

## Test strategy

This is milestone one. Future checks will add long-run memory sampling, controlled reset/recovery checks, replayed serial fixtures, and a command-line summary suitable for CI. A test-bench PASS only means the observed protocol and health checks passed; it is not proof of model accuracy.
