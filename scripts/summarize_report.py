#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize CQF benchmark report")
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    doc = json.loads(args.report.read_text(encoding="utf-8"))

    print(f"run_id: {doc['run_id']}")
    print(f"suite: {doc['suite_id']}")
    print(f"scale: {doc['scale']}")
    print(f"duration_seconds: {doc['duration_seconds']:.2f}")

    for engine in doc.get("engines", []):
        print(f"\nEngine: {engine['name']} ({engine['base_url']}{engine['cqf_base_path']})")
        for r in engine.get("results", []):
            latency = r.get("latency_ms")
            req_s = r.get("requests_per_second")
            req_s_text = f" req/s={req_s:.2f}" if isinstance(req_s, (int, float)) else ""
            timed_ok = r.get("timed_ok_requests", r.get("pass_requests", 0))
            unsupported = r.get("unsupported_requests", 0)
            fail = r.get("fail_requests", int(r.get("total_requests", 0)) - int(timed_ok))
            correct = r.get("correct_pass_requests", timed_ok)
            if latency is None:
                print(
                    f"  {r['scenario_id']}: timed_ok={timed_ok} unsupported={unsupported} "
                    f"fail={fail} correct={correct} p95=n/a p99=n/a{req_s_text}"
                )
            else:
                p95 = latency["p95"]
                p99 = latency["p99"]
                print(
                    f"  {r['scenario_id']}: timed_ok={timed_ok} unsupported={unsupported} "
                    f"fail={fail} correct={correct} p95={p95:.1f}ms p99={p99:.1f}ms{req_s_text}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
