#!/usr/bin/env python3
"""Simple command line interface for querying frame-level dataset metadata."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from dataset_core import DEFAULT_DATA_DIR, Query, available_options, count_matches, load_dataset, query_frames


DISPLAY_COLUMNS = [
    "frame_id",
    "segment_name",
    "frame_index",
    "prototype_id",
    "collection_version",
    "weather",
    "time_of_day",
    "view_direction",
    "value_score",
    "dataset_split",
    "model_inference",
    "data_path",
    "target_tags",
    "noise_tags",
]


def build_query(args: argparse.Namespace) -> Query:
    return Query(
        segment_name=args.segment,
        frame_index=args.frame,
        prototype_id=args.prototype,
        collection_version=args.version,
        weather=args.weather,
        time_of_day=args.time,
        view_direction=args.view,
        value_score=args.score,
        dataset_split=args.split,
        target_tag=args.target,
        noise_tag=args.noise,
        tag_match_mode=args.tag_match,
    )


def print_table(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("No frames matched.")
        return

    widths = {
        column: min(max(len(column), *(len(row.get(column, "")) for row in rows)), 34)
        for column in DISPLAY_COLUMNS
    }
    header = "  ".join(column.ljust(widths[column]) for column in DISPLAY_COLUMNS)
    print(header)
    print("  ".join("-" * widths[column] for column in DISPLAY_COLUMNS))
    for row in rows:
        cells = []
        for column in DISPLAY_COLUMNS:
            value = row.get(column, "")
            if len(value) > widths[column]:
                value = value[: widths[column] - 1] + "..."
            cells.append(value.ljust(widths[column]))
        print("  ".join(cells))


def write_export(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_query(args: argparse.Namespace) -> int:
    frames = load_dataset(Path(args.data_dir))
    query = build_query(args)
    total = count_matches(frames, query)
    limit = None if args.export else args.limit
    rows = query_frames(frames, query, limit=limit)

    if args.export:
        write_export(Path(args.export), rows)
        print(f"Matched {total} frames. Exported {len(rows)} rows to {args.export}.")
        return 0

    print(f"Matched {total} frames. Showing {len(rows)} rows.")
    print_table(rows)
    return 0


def run_options(args: argparse.Namespace) -> int:
    options = available_options(load_dataset(Path(args.data_dir)))
    for name, values in options.items():
        print(f"{name}: {', '.join(values)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))

    subparsers = parser.add_subparsers(dest="command", required=True)
    options = subparsers.add_parser("options", help="Show selectable filter values.")
    options.set_defaults(func=run_options)

    query = subparsers.add_parser("query", help="Filter frames.")
    query.add_argument("--segment")
    query.add_argument("--frame", type=int)
    query.add_argument("--prototype")
    query.add_argument("--version")
    query.add_argument("--weather", choices=["晴天", "阴天", "雨天"])
    query.add_argument("--time", choices=["白天", "晚上"])
    query.add_argument("--view", choices=["前", "后", "左", "右"])
    query.add_argument("--score", type=int, choices=range(1, 11), metavar="[1-10]")
    query.add_argument("--split", choices=["训练集", "验证集", "测试集"])
    query.add_argument("--target", help="Target tag filter.")
    query.add_argument("--noise", help="Noise tag filter.")
    query.add_argument(
        "--tag-match",
        choices=["exact", "contains"],
        default="exact",
        help="Tag matching mode: exact requires a full tag match; contains matches any tag containing the filter.",
    )
    query.add_argument("--limit", type=int, default=20)
    query.add_argument("--export", help="Export all matched rows to a CSV file.")
    query.set_defaults(func=run_query)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
