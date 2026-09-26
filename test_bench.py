import json
import tempfile
import unittest
from pathlib import Path

from bench import analyze, analyze_file, parse_line


class BenchTests(unittest.TestCase):
    def test_parse_prediction(self):
        self.assertEqual(parse_line('# PREDICTION,10,STILL,6,0')['latency_us'], 6)
        self.assertIsNone(parse_line('ESP-ROM: startup'))

    def test_clean_pass(self):
        rows = [
            {'sequence': 1, 'label': 'STILL', 'latency_us': 5, 'stream_drops': 0},
            {'sequence': 2, 'label': 'STILL', 'latency_us': 6, 'stream_drops': 0},
        ]
        report = analyze(rows)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['latency_us']['median'], 5.5)

    def test_drop_fails(self):
        rows = [{'sequence': 1, 'label': 'SHAKING', 'latency_us': 5, 'stream_drops': 2}]
        self.assertEqual(analyze(rows)['status'], 'FAIL')

    def test_gap_fails(self):
        rows = [
            {'sequence': 1, 'label': 'STILL', 'latency_us': 5, 'stream_drops': 0},
            {'sequence': 3, 'label': 'STILL', 'latency_us': 5, 'stream_drops': 0},
        ]
        report = analyze(rows)
        self.assertEqual(report['sequence_gaps'], 1)
        self.assertEqual(report['status'], 'FAIL')

    def test_file_analysis(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'serial.txt'
            path.write_text('# PREDICTION,1,ROTATING,5,0\nnoise\n', encoding='utf-8')
            report = analyze_file(path)
            self.assertEqual(report['predictions'], 1)
            self.assertEqual(report['malformed_prediction_lines'], 0)


if __name__ == '__main__':
    unittest.main()
