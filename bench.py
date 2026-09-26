"""Measure an M5 TinyML classifier over USB without changing its firmware."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import statistics
import time

PATTERN = re.compile(r'^# PREDICTION,(\d+),(STILL|SHAKING|ROTATING),(\d+),(\d+)\s*$')


def parse_line(line):
    match = PATTERN.match(line.strip())
    if not match:
        return None
    return {
        'sequence': int(match.group(1)),
        'label': match.group(2),
        'latency_us': int(match.group(3)),
        'stream_drops': int(match.group(4)),
    }


def analyze(rows, requested_seconds=None):
    if not rows:
        return {'status': 'FAIL', 'reason': 'No valid prediction lines found', 'predictions': 0}
    sequences = [row['sequence'] for row in rows]
    gaps = sum(max(0, b - a - 1) for a, b in zip(sequences, sequences[1:]))
    latencies = [row['latency_us'] for row in rows]
    drops = max(row['stream_drops'] for row in rows)
    report = {
        'status': 'PASS',
        'predictions': len(rows),
        'first_sequence': sequences[0],
        'last_sequence': sequences[-1],
        'sequence_gaps': gaps,
        'labels_seen': sorted(set(row['label'] for row in rows)),
        'latency_us': {
            'min': min(latencies), 'median': statistics.median(latencies), 'max': max(latencies)
        },
        'max_stream_drops': drops,
        'requested_seconds': requested_seconds,
        'checks': {
            'valid_labels': all(row['label'] in {'STILL', 'SHAKING', 'ROTATING'} for row in rows),
            'nonnegative_latency': all(row['latency_us'] >= 0 for row in rows),
            'no_sequence_gaps': gaps == 0,
            'no_stream_drops': drops == 0,
        },
    }
    report['status'] = 'PASS' if all(report['checks'].values()) else 'FAIL'
    return report


def analyze_file(path):
    rows = []
    malformed = 0
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('# PREDICTION'):
            row = parse_line(line)
            if row is None:
                malformed += 1
            else:
                rows.append(row)
    report = analyze(rows)
    report['source'] = str(path)
    report['malformed_prediction_lines'] = malformed
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port')
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--input', type=Path, help='Analyze an existing Serial Monitor log instead of opening a port')
    parser.add_argument('--out', type=Path, default=Path(__file__).parent / 'reports')
    args = parser.parse_args()
    if args.input:
        report = analyze_file(args.input)
    else:
        if not args.port:
            parser.error('--port is required unless --input is used')
        try:
            import serial
        except ImportError:
            parser.exit(1, 'Install dependencies with: python -m pip install -r requirements.txt\n')
        rows = []
        deadline = time.monotonic() + args.seconds
        with serial.Serial(args.port, 115200, timeout=0.2) as port:
            print(f'Listening on {args.port} for {args.seconds} seconds...', flush=True)
            while time.monotonic() < deadline:
                row = parse_line(port.readline().decode('ascii', errors='replace'))
                if row:
                    rows.append(row)
                    print(f"{row['sequence']}: {row['label']} ({row['latency_us']} us, drops={row['stream_drops']})")
        report = analyze(rows, args.seconds)
    report['created_at_utc'] = datetime.now(timezone.utc).isoformat()
    args.out.mkdir(exist_ok=True)
    output = args.out / f"bench_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print(f'Report: {output}')
    raise SystemExit(0 if report['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
