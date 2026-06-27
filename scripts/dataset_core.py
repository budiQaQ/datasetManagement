#!/usr/bin/env python3
"""Shared CSV loading and filtering helpers for the dataset tools."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATA_DIR = Path("data/seed")
WEATHER_OPTIONS = ["晴天", "阴天", "雨天"]
TIME_OF_DAY_OPTIONS = ["白天", "晚上"]
VIEW_DIRECTION_OPTIONS = ["前", "后", "左", "右"]
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


def frame_matches(row: dict[str, str], query: Query) -> bool:
    exact_fields = [
        "segment_name",
        "prototype_id",
        "collection_version",
        "weather",
        "time_of_day",
        "view_direction",
    ]
    for field in exact_fields:
        expected = getattr(query, field)
        if expected is not None and row[field] != expected:
            return False

    if query.frame_index is not None and int(row["frame_index"]) != query.frame_index:
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
    }
