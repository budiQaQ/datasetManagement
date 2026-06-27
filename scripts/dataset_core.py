#!/usr/bin/env python3
"""Shared CSV loading and filtering helpers for the dataset tools."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATA_DIR = Path("data/seed")
WEATHER_OPTIONS = ["晴天", "阴天", "雨天"]
TIME_OF_DAY_OPTIONS = ["白天", "晚上"]
VIEW_DIRECTION_OPTIONS = ["前", "后", "左", "右"]
DATASET_SPLIT_OPTIONS = ["训练集", "验证集", "测试集"]
MAX_TAGS_PER_TYPE = 10

FRAME_FIELDNAMES = [
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


@dataclass(frozen=True)
class Query:
    segment_name: str | None = None
    frame_index: int | None = None
    prototype_id: str | None = None
    collection_version: str | None = None
    weather: str | None = None
    time_of_day: str | None = None
    view_direction: str | None = None
    value_score: int | None = None
    dataset_split: str | None = None
    target_tag: str | None = None
    noise_tag: str | None = None


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_frame(row: dict[str, str]) -> dict[str, str]:
    data_path = row.get("data_path") or row.get("image_path") or ""
    target_tags = row.get("target_tags") or row.get("target_description") or ""
    noise_tags = row.get("noise_tags") or row.get("noise_description") or ""
    return {
        "frame_id": row.get("frame_id", ""),
        "segment_name": row.get("segment_name", ""),
        "frame_index": row.get("frame_index", ""),
        "prototype_id": row.get("prototype_id", ""),
        "collection_version": row.get("collection_version", ""),
        "weather": normalize_weather(row.get("weather", "")),
        "time_of_day": normalize_time_of_day(row.get("time_of_day", "")),
        "view_direction": normalize_view_direction(row.get("view_direction", "")),
        "value_score": normalize_value_score(row.get("value_score", "")),
        "dataset_split": normalize_dataset_split(row.get("dataset_split", "")),
        "model_inference": row.get("model_inference", ""),
        "data_path": data_path,
        "target_tags": join_tags(split_tags(target_tags)),
        "noise_tags": join_tags(split_tags(noise_tags if noise_tags != "clean" else "")),
    }


def load_dataset(data_dir: Path = DEFAULT_DATA_DIR) -> list[dict[str, str]]:
    return [normalize_frame(row) for row in load_csv(data_dir / "frames.csv")]


def split_tags(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        raw_items = [str(item) for item in value]
    else:
        raw_items = re.split(r"[,，;；\n]+", str(value))

    tags: list[str] = []
    seen = set()
    for item in raw_items:
        tag = item.strip()
        if not tag or tag in seen:
            continue
        tags.append(tag)
        seen.add(tag)
    return tags


def join_tags(tags: list[str]) -> str:
    return ", ".join(tags)


def validate_tags(tags: list[str], field_name: str) -> None:
    if len(tags) > MAX_TAGS_PER_TYPE:
        raise ValueError(f"{field_name}最多允许{MAX_TAGS_PER_TYPE}个")


def normalize_weather(value: str) -> str:
    mapping = {
        "sunny": "晴天",
        "cloudy": "阴天",
        "rain": "雨天",
        "晴": "晴天",
        "阴": "阴天",
        "雨": "雨天",
    }
    return mapping.get(value, value if value in WEATHER_OPTIONS else WEATHER_OPTIONS[0])


def normalize_time_of_day(value: str) -> str:
    mapping = {
        "day": "白天",
        "dawn": "白天",
        "dusk": "晚上",
        "night": "晚上",
        "白": "白天",
        "夜": "晚上",
    }
    return mapping.get(value, value if value in TIME_OF_DAY_OPTIONS else TIME_OF_DAY_OPTIONS[0])


def normalize_view_direction(value: str) -> str:
    mapping = {
        "front": "前",
        "rear": "后",
        "left": "左",
        "right": "右",
        "front_left": "前",
        "front_right": "前",
        "rear_left": "后",
        "rear_right": "后",
    }
    return mapping.get(value, value if value in VIEW_DIRECTION_OPTIONS else VIEW_DIRECTION_OPTIONS[0])


def normalize_dataset_split(value: str) -> str:
    mapping = {
        "train": "训练集",
        "training": "训练集",
        "val": "验证集",
        "valid": "验证集",
        "validation": "验证集",
        "test": "测试集",
    }
    return mapping.get(value, value if value in DATASET_SPLIT_OPTIONS else DATASET_SPLIT_OPTIONS[0])


def normalize_value_score(value: str) -> str:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return "5"
    return str(min(max(score, 1), 10))


def frame_matches(row: dict[str, str], query: Query) -> bool:
    exact_fields = [
        "segment_name",
        "prototype_id",
        "collection_version",
        "weather",
        "time_of_day",
        "view_direction",
        "dataset_split",
    ]
    for field in exact_fields:
        expected = getattr(query, field)
        if expected is not None and row[field] != expected:
            return False

    if query.frame_index is not None and int(row["frame_index"]) != query.frame_index:
        return False
    if query.value_score is not None and int(row["value_score"]) != query.value_score:
        return False
    if query.target_tag is not None and query.target_tag not in split_tags(row["target_tags"]):
        return False
    if query.noise_tag is not None and query.noise_tag not in split_tags(row["noise_tags"]):
        return False
    return True


def query_frames(
    frames: list[dict[str, str]],
    query: Query,
    limit: int | None = 50,
) -> list[dict[str, str]]:
    results = []
    for row in frames:
        if frame_matches(row, query):
            results.append(dict(row))
            if limit is not None and len(results) >= limit:
                break
    return results


def count_matches(frames: list[dict[str, str]], query: Query) -> int:
    return sum(1 for row in frames if frame_matches(row, query))


def available_options(frames: list[dict[str, str]]) -> dict[str, list[str]]:
    return {
        "prototype_id": sorted({row["prototype_id"] for row in frames if row["prototype_id"]}),
        "collection_version": sorted(
            {row["collection_version"] for row in frames if row["collection_version"]}
        ),
        "weather": WEATHER_OPTIONS,
        "time_of_day": TIME_OF_DAY_OPTIONS,
        "view_direction": VIEW_DIRECTION_OPTIONS,
        "dataset_split": DATASET_SPLIT_OPTIONS,
        "value_score": [str(value) for value in range(1, 11)],
    }


def build_report(frames: list[dict[str, str]]) -> dict[str, object]:
    split_by_segment: dict[str, Counter[str]] = defaultdict(Counter)
    target_counter: Counter[str] = Counter()
    noise_counter: Counter[str] = Counter()
    target_split_counter: dict[str, Counter[str]] = defaultdict(Counter)
    noise_split_counter: dict[str, Counter[str]] = defaultdict(Counter)
    score_counter: Counter[str] = Counter()

    for row in frames:
        segment_name = row["segment_name"]
        split = row["dataset_split"]
        split_by_segment[segment_name][split] += 1
        score_counter[row["value_score"]] += 1
        target_tags = split_tags(row["target_tags"])
        noise_tags = split_tags(row["noise_tags"])
        target_counter.update(target_tags)
        noise_counter.update(noise_tags)
        for tag in target_tags:
            target_split_counter[tag][split] += 1
        for tag in noise_tags:
            noise_split_counter[tag][split] += 1

    segment_rows = []
    for segment_name in sorted(split_by_segment):
        counts = split_by_segment[segment_name]
        segment_rows.append(
            {
                "segment_name": segment_name,
                "训练集": counts["训练集"],
                "验证集": counts["验证集"],
                "测试集": counts["测试集"],
                "total": sum(counts.values()),
            }
        )

    return {
        "frame_count": len(frames),
        "split_by_segment": segment_rows,
        "target_tags": [
            {
                "tag": tag,
                "count": count,
                "训练集": target_split_counter[tag]["训练集"],
                "验证集": target_split_counter[tag]["验证集"],
                "测试集": target_split_counter[tag]["测试集"],
            }
            for tag, count in target_counter.most_common()
        ],
        "noise_tags": [
            {
                "tag": tag,
                "count": count,
                "训练集": noise_split_counter[tag]["训练集"],
                "验证集": noise_split_counter[tag]["验证集"],
                "测试集": noise_split_counter[tag]["测试集"],
            }
            for tag, count in noise_counter.most_common()
        ],
        "value_scores": [
            {"score": str(score), "count": score_counter[str(score)]}
            for score in range(1, 11)
        ],
    }
