#!/usr/bin/env python3
"""Generate seed metadata for a frame-level deep learning dataset index."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from dataset_core import (
    FRAME_FIELDNAMES,
    TIME_OF_DAY_OPTIONS,
    VIEW_DIRECTION_OPTIONS,
    WEATHER_OPTIONS,
)


PROTOTYPES = [f"P{i:03d}" for i in range(1, 13)]
COLLECTION_VERSIONS = ["v1.0", "v1.1", "v1.2", "v2.0", "v2.1"]

TARGET_TAGS = [
    "行人",
    "车辆",
    "骑行者",
    "交通锥",
    "交通灯",
    "交通标志",
    "动物",
    "小目标",
    "施工围挡",
    "应急车辆",
]

NOISE_TAGS = [
    "雨滴",
    "运动模糊",
    "过曝",
    "欠曝",
    "反光",
    "遮挡",
    "传感器噪声",
    "镜头脏污",
    "压缩伪影",
    "眩光",
]


def sample_tags(rng: random.Random, candidates: list[str], min_count: int, max_count: int) -> list[str]:
    count = rng.randint(min_count, max_count)
    return sorted(rng.sample(candidates, count))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    dataset_version_frames = []
    weather_counter: Counter[str] = Counter()
    view_counter: Counter[str] = Counter()
    target_counter: Counter[str] = Counter()
    noise_counter: Counter[str] = Counter()

    frame_id = 1
    for segment_idx in range(1, args.segments + 1):
        segment_name = f"SEG_{segment_idx:05d}"
        prototype_id = rng.choice(PROTOTYPES)
        collection_version = rng.choice(COLLECTION_VERSIONS)

        for frame_index in range(args.frames_per_segment):
            weather = rng.choices(WEATHER_OPTIONS, weights=[55, 30, 15], k=1)[0]
            time_of_day = rng.choices(TIME_OF_DAY_OPTIONS, weights=[78, 22], k=1)[0]
            view_direction = rng.choice(VIEW_DIRECTION_OPTIONS)
            target_tags = sample_tags(rng, TARGET_TAGS, 1, 4)
            noise_tags = sample_tags(rng, NOISE_TAGS, 0, 3)

            frames.append(
                {
                    "frame_id": frame_id,
                    "segment_name": segment_name,
                    "frame_index": frame_index,
                    "prototype_id": prototype_id,
                    "collection_version": collection_version,
                    "weather": weather,
                    "time_of_day": time_of_day,
                    "view_direction": view_direction,
                    "data_path": f"s3://mock-dataset/raw/{segment_name}/{frame_index:06d}.jpg",
                    "target_tags": ", ".join(target_tags),
                    "noise_tags": ", ".join(noise_tags),
                }
            )

            weather_counter[weather] += 1
            view_counter[view_direction] += 1
            target_counter.update(target_tags)
            noise_counter.update(noise_tags)

            split = rng.choices(["train", "val", "test"], weights=[80, 10, 10], k=1)[0]
            dataset_version_frames.append(
                {"dataset_version_id": 1, "frame_id": frame_id, "split": split}
            )
            frame_id += 1

    dataset_versions = [
        {
            "id": 1,
            "name": "mock_seed_v1",
            "description": "Initial synthetic frame-level dataset seed.",
            "created_at": "2026-06-27T00:00:00+00:00",
        }
    ]

    write_csv(output_dir / "frames.csv", frames, FRAME_FIELDNAMES)
    write_csv(
        output_dir / "dataset_versions.csv",
        dataset_versions,
        ["id", "name", "description", "created_at"],
    )
    write_csv(
        output_dir / "dataset_version_frames.csv",
        dataset_version_frames,
        ["dataset_version_id", "frame_id", "split"],
    )

    summary = {
        "seed": args.seed,
        "segment_count": args.segments,
        "frames_per_segment": args.frames_per_segment,
        "frame_count": len(frames),
        "weather_distribution": dict(weather_counter.most_common()),
        "view_direction_distribution": dict(view_counter.most_common()),
        "top_target_tags": dict(target_counter.most_common(10)),
        "top_noise_tags": dict(noise_counter.most_common(10)),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--segments", type=int, default=80)
    parser.add_argument("--frames-per-segment", type=int, default=250)
    parser.add_argument("--seed", type=int, default=20260627)
    parser.add_argument("--output-dir", default="data/seed")
    return parser.parse_args()


if __name__ == "__main__":
    generate(parse_args())
