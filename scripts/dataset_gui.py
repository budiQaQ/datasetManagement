#!/usr/bin/env python3
"""Local browser GUI for querying and editing frame-level dataset metadata."""

from __future__ import annotations

import argparse
import csv
import errno
import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dataset_core import (
    DEFAULT_DATA_DIR,
    FRAME_FIELDNAMES,
    MAX_TAGS_PER_TYPE,
    Query,
    available_options,
    build_report,
    count_matches,
    load_csv,
    load_dataset,
    query_frames,
    split_tags,
    validate_tags,
    write_csv,
)


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>帧级数据集管理</title>
  <style>
    :root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1d2430; }
    header { background: #ffffff; border-bottom: 1px solid #dfe3ea; padding: 18px 24px; }
    h1 { margin: 0; font-size: 22px; letter-spacing: 0; }
    main { padding: 18px 24px 32px; }
    .filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 14px; }
    label { display: grid; gap: 6px; font-size: 13px; color: #4d5868; }
    select, input, textarea { min-height: 36px; border: 1px solid #c9d0db; border-radius: 6px; padding: 6px 8px; background: #fff; font-size: 14px; }
    textarea { min-height: 74px; resize: vertical; }
    .hint { color: #697586; font-size: 12px; }
    .actions { display: flex; align-items: center; gap: 10px; margin: 12px 0 16px; flex-wrap: wrap; }
    button, a.button { border: 1px solid #224a7a; background: #2f669f; color: #fff; border-radius: 6px; min-height: 36px; padding: 7px 12px; font-size: 14px; cursor: pointer; text-decoration: none; }
    button.secondary { background: #fff; color: #24415f; border-color: #b7c2d0; }
    button.danger { background: #b42318; border-color: #912018; }
    button.compact { min-height: 28px; padding: 4px 8px; font-size: 12px; }
    .status { color: #4d5868; font-size: 14px; }
    .table-wrap { overflow: auto; background: #fff; border: 1px solid #dfe3ea; border-radius: 8px; }
    .report { background: #fff; border: 1px solid #dfe3ea; border-radius: 8px; padding: 14px; margin-bottom: 16px; }
    .report h2 { margin: 0 0 12px; font-size: 18px; letter-spacing: 0; }
    .report-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 14px; }
    .report-panel { border: 1px solid #edf0f4; border-radius: 6px; padding: 10px; overflow: auto; }
    .report-panel h3 { margin: 0 0 8px; font-size: 14px; letter-spacing: 0; }
    .bar-row { display: grid; grid-template-columns: minmax(72px, 1fr) 4fr 46px; align-items: center; gap: 8px; margin: 6px 0; font-size: 13px; }
    .bar-track { height: 10px; background: #eef2f6; border-radius: 999px; overflow: hidden; }
    .bar-fill { height: 100%; background: #2f669f; }
    .stack-row { display: grid; grid-template-columns: minmax(96px, 1fr) 4fr 54px; align-items: center; gap: 10px; margin: 8px 0; font-size: 13px; }
    .stack-bar { display: flex; height: 16px; overflow: hidden; border-radius: 999px; background: #eef2f6; }
    .stack-part { min-width: 0; height: 100%; }
    .train { background: #2f669f; }
    .val { background: #2f9f6b; }
    .test { background: #d97706; }
    .legend { display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0 10px; color: #4d5868; font-size: 12px; }
    .legend span { display: inline-flex; align-items: center; gap: 5px; }
    .swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
    .report-controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin-bottom: 10px; }
    .metric-grid { display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 10px; }
    .metric { border: 1px solid #edf0f4; border-radius: 6px; padding: 12px; background: #fafbfc; }
    .metric-label { color: #697586; font-size: 12px; margin-bottom: 6px; }
    .metric-value { font-size: 26px; font-weight: 650; color: #1d2430; letter-spacing: 0; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; min-width: 1120px; }
    th, td { padding: 9px 10px; border-bottom: 1px solid #edf0f4; text-align: left; vertical-align: top; }
    th { background: #f0f3f7; color: #344054; position: sticky; top: 0; }
    td.path { max-width: 320px; overflow-wrap: anywhere; color: #536171; }
    dialog { width: min(880px, calc(100vw - 32px)); border: 1px solid #cfd6e2; border-radius: 8px; padding: 0; box-shadow: 0 18px 60px rgba(15, 23, 42, 0.2); }
    dialog::backdrop { background: rgba(15, 23, 42, 0.35); }
    .dialog-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid #e3e7ee; }
    .dialog-head h2 { margin: 0; font-size: 18px; letter-spacing: 0; }
    .dialog-body { padding: 16px 18px; }
    .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
    .wide { grid-column: 1 / -1; }
    .dialog-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 12px 18px 16px; border-top: 1px solid #e3e7ee; }
    @media (max-width: 700px) { main, header { padding-left: 12px; padding-right: 12px; } }
  </style>
</head>
<body>
  <header><h1>帧级数据集管理</h1></header>
  <main>
    <section class="filters">
      <label>数据段名<input name="segment_name" placeholder="例如 SEG_00001"></label>
      <label>帧号<input name="frame_index" type="number" min="0" step="1" placeholder="例如 183"></label>
    </section>
    <section class="filters" id="filters"></section>
    <div class="actions">
      <button id="search">筛选</button>
      <button id="new-frame">新增帧</button>
      <button class="secondary" id="reset">重置</button>
      <a class="button" id="export" href="/export">导出 CSV</a>
      <span class="status" id="status">加载中...</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>操作</th><th>帧 ID</th><th>数据段名</th><th>帧号</th><th>样机编号</th>
            <th>采集版本</th><th>天气</th><th>时段</th><th>视野方向</th><th>价值评分</th>
            <th>集合归属</th><th>模型推理情况</th><th>数据路径</th><th>目标 tag</th><th>噪声 tag</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
    <dialog id="frame-dialog">
      <form method="dialog" id="frame-form">
        <div class="dialog-head">
          <h2 id="dialog-title">新增帧</h2>
          <button class="secondary compact" type="button" id="close-dialog">关闭</button>
        </div>
        <div class="dialog-body">
          <input type="hidden" name="frame_id">
          <div class="form-grid">
            <label>数据段名<input name="segment_name" required></label>
            <label>帧号<input name="frame_index" type="number" min="0" step="1" required></label>
            <label>样机编号<input name="prototype_id" required></label>
            <label>采集版本<input name="collection_version" required></label>
            <label>天气<select name="weather" required></select></label>
            <label>时段<select name="time_of_day" required></select></label>
            <label>视野方向<select name="view_direction" required></select></label>
            <label>数据价值评分<select name="value_score" required></select></label>
            <label>集合归属<select name="dataset_split" required></select></label>
            <label class="wide">模型推理情况<textarea name="model_inference" placeholder="用户自定义描述"></textarea></label>
            <label class="wide">数据路径<input name="data_path" required></label>
            <label class="wide">目标 tag 描述
              <textarea name="target_tags" placeholder="例如：行人, 车辆, 锥桶"></textarea>
              <span class="hint">用逗号、分号或换行分隔，最多 10 个</span>
            </label>
            <label class="wide">噪声 tag 描述
              <textarea name="noise_tags" placeholder="例如：雨滴, 运动模糊"></textarea>
              <span class="hint">用逗号、分号或换行分隔，最多 10 个</span>
            </label>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="secondary" type="button" id="cancel-dialog">取消</button>
          <button id="save-frame" value="default">保存</button>
        </div>
      </form>
    </dialog>
    <section class="report">
      <h2>报表</h2>
      <div class="actions">
        <button class="secondary" id="refresh-report">刷新报表</button>
        <span class="status" id="report-status">等待加载</span>
      </div>
      <div class="report-grid">
        <div class="report-panel">
          <h3>训练/验证/测试在数据段上的分布</h3>
          <div class="legend">
            <span><i class="swatch train"></i>训练集</span>
            <span><i class="swatch val"></i>验证集</span>
            <span><i class="swatch test"></i>测试集</span>
          </div>
          <div id="segment-report"></div>
        </div>
        <div class="report-panel">
          <h3>tag 分布</h3>
          <div class="report-controls">
            <label>类别<select id="tag-report-kind"><option value="target_tags">目标 tag</option><option value="noise_tags">噪声 tag</option></select></label>
            <label>tag<select id="tag-report-select"></select></label>
          </div>
          <div class="legend">
            <span><i class="swatch train"></i>训练集</span>
            <span><i class="swatch val"></i>验证集</span>
            <span><i class="swatch test"></i>测试集</span>
          </div>
          <div id="tag-report"></div>
        </div>
        <div class="report-panel">
          <h3>数据价值评分</h3>
          <div id="score-report"></div>
        </div>
      </div>
    </section>
  </main>
  <script>
    const filterConfig = [
      ["prototype_id", "样机编号", "select"], ["collection_version", "采集版本", "select"],
      ["weather", "天气", "select"], ["time_of_day", "时段", "select"],
      ["view_direction", "视野方向", "select"], ["value_score", "价值评分", "select"],
      ["dataset_split", "集合归属", "select"], ["target_tag", "目标 tag", "input"],
      ["noise_tag", "噪声 tag", "input"]
    ];
    const filters = document.querySelector("#filters");
    const statusEl = document.querySelector("#status");
    const rowsEl = document.querySelector("#rows");
    const exportEl = document.querySelector("#export");
    const reportStatusEl = document.querySelector("#report-status");
    const segmentReportEl = document.querySelector("#segment-report");
    const tagReportKindEl = document.querySelector("#tag-report-kind");
    const tagReportSelectEl = document.querySelector("#tag-report-select");
    const tagReportEl = document.querySelector("#tag-report");
    const scoreReportEl = document.querySelector("#score-report");
    const dialog = document.querySelector("#frame-dialog");
    const form = document.querySelector("#frame-form");
    let currentRows = [];
    let optionData = {};
    let reportData = null;

    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
    }

    function splitTags(value) {
      return String(value || "").split(/[,，;；\\n]+/).map(item => item.trim()).filter(Boolean);
    }

    function params() {
      const search = new URLSearchParams();
      filterConfig.forEach(([name]) => {
        const value = document.querySelector(`[name="${name}"]`).value.trim();
        if (value) search.set(name, value);
      });
      const segmentName = document.querySelector('[name="segment_name"]').value.trim();
      const frameIndex = document.querySelector('[name="frame_index"]').value;
      if (segmentName) search.set("segment_name", segmentName);
      if (frameIndex) search.set("frame_index", frameIndex);
      search.set("limit", "100");
      return search;
    }

    function optionHtml(values) {
      return `<option value="">全部</option>${(values || []).map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join("")}`;
    }

    async function loadOptions() {
      const response = await fetch("/api/options");
      optionData = await response.json();
      filters.innerHTML = filterConfig.map(([name, label, kind]) => {
        if (kind === "input") {
          return `<label>${label}<input name="${name}" placeholder="精确匹配单个 tag"></label>`;
        }
        return `<label>${label}<select name="${name}">${optionHtml(optionData[name])}</select></label>`;
      }).join("");

      ["weather", "time_of_day", "view_direction", "value_score", "dataset_split"].forEach(name => {
        form.elements[name].innerHTML = (optionData[name] || []).map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join("");
      });
    }

    async function search() {
      const searchParams = params();
      const response = await fetch(`/api/query?${searchParams.toString()}`);
      const data = await response.json();
      currentRows = data.rows;
      statusEl.textContent = `命中 ${data.total} 帧，显示 ${data.rows.length} 帧`;
      exportEl.href = `/export?${searchParams.toString()}`;
      rowsEl.innerHTML = data.rows.map(row => `
        <tr>
          <td>
            <button class="secondary compact" data-action="edit" data-frame-id="${esc(row.frame_id)}">编辑</button>
            <button class="danger compact" data-action="delete" data-frame-id="${esc(row.frame_id)}">删除</button>
          </td>
          <td>${esc(row.frame_id)}</td><td>${esc(row.segment_name)}</td><td>${esc(row.frame_index)}</td>
          <td>${esc(row.prototype_id)}</td><td>${esc(row.collection_version)}</td><td>${esc(row.weather)}</td>
          <td>${esc(row.time_of_day)}</td><td>${esc(row.view_direction)}</td><td>${esc(row.value_score)}</td>
          <td>${esc(row.dataset_split)}</td><td>${esc(row.model_inference)}</td><td class="path">${esc(row.data_path)}</td>
          <td>${esc(row.target_tags)}</td><td>${esc(row.noise_tags)}</td>
        </tr>
      `).join("");
    }

    function defaultFrame() {
      return {
        frame_id: "", segment_name: "", frame_index: "",
        prototype_id: optionData.prototype_id?.[0] || "P001",
        collection_version: optionData.collection_version?.[0] || "v1.0",
        weather: "晴天", time_of_day: "白天", view_direction: "前",
        value_score: "5", dataset_split: "训练集", model_inference: "",
        data_path: "s3://mock-dataset/raw/SEG_NEW/000000.jpg",
        target_tags: "", noise_tags: ""
      };
    }

    function openForm(row) {
      const data = row || defaultFrame();
      document.querySelector("#dialog-title").textContent = row ? `编辑帧 ${data.frame_id}` : "新增帧";
      [
        "frame_id", "segment_name", "frame_index", "prototype_id", "collection_version",
        "weather", "time_of_day", "view_direction", "value_score", "dataset_split",
        "model_inference", "data_path", "target_tags", "noise_tags"
      ].forEach(name => form.elements[name].value = data[name] || "");
      dialog.showModal();
    }

    async function saveFrame() {
      const targetTags = splitTags(form.elements.target_tags.value);
      const noiseTags = splitTags(form.elements.noise_tags.value);
      if (targetTags.length > 10 || noiseTags.length > 10) {
        statusEl.textContent = "目标 tag 和噪声 tag 均最多允许 10 个";
        return;
      }
      const payload = {
        frame_id: form.elements.frame_id.value,
        segment_name: form.elements.segment_name.value.trim(),
        frame_index: form.elements.frame_index.value,
        prototype_id: form.elements.prototype_id.value.trim(),
        collection_version: form.elements.collection_version.value.trim(),
        weather: form.elements.weather.value,
        time_of_day: form.elements.time_of_day.value,
        view_direction: form.elements.view_direction.value,
        value_score: form.elements.value_score.value,
        dataset_split: form.elements.dataset_split.value,
        model_inference: form.elements.model_inference.value.trim(),
        data_path: form.elements.data_path.value.trim(),
        target_tags: targetTags,
        noise_tags: noiseTags
      };
      const response = await fetch("/api/frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        statusEl.textContent = data.error || "保存失败";
        return;
      }
      dialog.close();
      await loadOptions();
      await search();
      await loadReport();
      statusEl.textContent = `已保存帧 ${data.frame_id}`;
    }

    async function deleteFrame(frameId) {
      if (!confirm(`删除帧 ${frameId}？`)) return;
      const response = await fetch(`/api/frame?frame_id=${encodeURIComponent(frameId)}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) {
        statusEl.textContent = data.error || "删除失败";
        return;
      }
      await loadOptions();
      await search();
      await loadReport();
      statusEl.textContent = `已删除帧 ${frameId}`;
    }

    function renderScoreStats(stats) {
      const mean = stats.mean === null ? "暂无" : stats.mean;
      const stddev = stats.stddev === null ? "暂无" : stats.stddev;
      scoreReportEl.innerHTML = `
        <div class="metric-grid">
          <div class="metric"><div class="metric-label">均值</div><div class="metric-value">${esc(mean)}</div></div>
          <div class="metric"><div class="metric-label">标准差</div><div class="metric-value">${esc(stddev)}</div></div>
        </div>
        <div class="hint">样本数 ${esc(stats.count || 0)}</div>
      `;
    }

    function stackPart(row, key, className) {
      const total = Math.max(1, row.total || row.count || 0);
      const width = ((row[key] || 0) / total) * 100;
      return `<div class="stack-part ${className}" style="width:${width}%" title="${key}: ${esc(row[key] || 0)}"></div>`;
    }

    function renderStackRows(el, rows, labelKey) {
      el.innerHTML = rows.length ? rows.map(row => `
        <div class="stack-row">
          <div>${esc(row[labelKey])}</div>
          <div class="stack-bar">
            ${stackPart(row, "训练集", "train")}
            ${stackPart(row, "验证集", "val")}
            ${stackPart(row, "测试集", "test")}
          </div>
          <div>${esc(row.total || row.count || 0)}</div>
        </div>
      `).join("") : "<div class='hint'>暂无数据</div>";
    }

    function renderSelectedTagReport() {
      if (!reportData) return;
      const rows = reportData[tagReportKindEl.value] || [];
      const selectedTag = tagReportSelectEl.value || rows[0]?.tag || "";
      const row = rows.find(item => item.tag === selectedTag);
      tagReportSelectEl.innerHTML = rows.length ? rows.map(item => `<option value="${esc(item.tag)}">${esc(item.tag)} (${esc(item.count)})</option>`).join("") : "<option value=''>暂无 tag</option>";
      tagReportSelectEl.value = selectedTag;
      tagReportEl.innerHTML = row ? `
        <div class="stack-row">
          <div>${esc(row.tag)}</div>
          <div class="stack-bar">
            ${stackPart(row, "训练集", "train")}
            ${stackPart(row, "验证集", "val")}
            ${stackPart(row, "测试集", "test")}
          </div>
          <div>${esc(row.count)}</div>
        </div>
        <div class="hint">训练集 ${esc(row["训练集"])}，验证集 ${esc(row["验证集"])}，测试集 ${esc(row["测试集"])}</div>
      ` : "<div class='hint'>暂无数据</div>";
    }

    async function loadReport() {
      const response = await fetch("/api/report");
      reportData = await response.json();
      reportStatusEl.textContent = `总帧数 ${reportData.frame_count}`;
      renderStackRows(segmentReportEl, reportData.split_by_segment, "segment_name");
      renderSelectedTagReport();
      renderScoreStats(reportData.value_score_stats);
    }

    document.querySelector("#search").addEventListener("click", search);
    document.querySelector("#new-frame").addEventListener("click", () => openForm(null));
    document.querySelector("#refresh-report").addEventListener("click", loadReport);
    tagReportKindEl.addEventListener("change", () => {
      tagReportSelectEl.value = "";
      renderSelectedTagReport();
    });
    tagReportSelectEl.addEventListener("change", renderSelectedTagReport);
    document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
    document.querySelector("#cancel-dialog").addEventListener("click", () => dialog.close());
    rowsEl.addEventListener("click", event => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const frameId = button.dataset.frameId;
      if (button.dataset.action === "edit") {
        openForm(currentRows.find(row => row.frame_id === frameId));
      } else if (button.dataset.action === "delete") {
        deleteFrame(frameId);
      }
    });
    form.addEventListener("submit", event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      saveFrame();
    });
    document.querySelector("#reset").addEventListener("click", () => {
      document.querySelectorAll("select, input").forEach(el => el.value = "");
      search();
    });
    loadOptions().then(search).then(loadReport);
  </script>
</body>
</html>
"""


def first(values: dict[str, list[str]], name: str) -> str | None:
    value = values.get(name, [""])[0]
    return value or None


def query_from_params(values: dict[str, list[str]]) -> Query:
    frame_index = first(values, "frame_index")
    value_score = first(values, "value_score")
    return Query(
        segment_name=first(values, "segment_name"),
        frame_index=int(frame_index) if frame_index else None,
        prototype_id=first(values, "prototype_id"),
        collection_version=first(values, "collection_version"),
        weather=first(values, "weather"),
        time_of_day=first(values, "time_of_day"),
        view_direction=first(values, "view_direction"),
        value_score=int(value_score) if value_score else None,
        dataset_split=first(values, "dataset_split"),
        target_tag=first(values, "target_tag"),
        noise_tag=first(values, "noise_tag"),
    )


def load_state(data_dir: Path) -> dict[str, object]:
    frames = load_dataset(data_dir)
    return {
        "frames": frames,
        "options": available_options(frames),
    }


def reload_state(state: dict[str, object], data_dir: Path) -> None:
    state.clear()
    state.update(load_state(data_dir))


def require_text(payload: dict[str, object], name: str) -> str:
    value = str(payload.get(name, "")).strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def validate_choice(value: str, options: list[str], field_name: str) -> str:
    if value not in options:
        raise ValueError(f"{field_name} must be one of: {', '.join(options)}")
    return value


def validate_value_score(value: str) -> str:
    try:
        score = int(value)
    except ValueError as exc:
        raise ValueError("value_score must be an integer from 1 to 10") from exc
    if score < 1 or score > 10:
        raise ValueError("value_score must be an integer from 1 to 10")
    return str(score)


def save_frame_payload(data_dir: Path, state: dict[str, object], payload: dict[str, object]) -> str:
    frames = list(state["frames"])
    frame_id = str(payload.get("frame_id", "")).strip()
    is_create = not frame_id
    if is_create:
        existing_ids = [int(row["frame_id"]) for row in frames]
        frame_id = str(max(existing_ids, default=0) + 1)
    elif frame_id not in {row["frame_id"] for row in frames}:
        raise ValueError(f"frame_id {frame_id} does not exist")

    target_tags = split_tags(payload.get("target_tags", []))
    noise_tags = split_tags(payload.get("noise_tags", []))
    validate_tags(target_tags, "目标tag")
    validate_tags(noise_tags, "噪声tag")

    frame_index = int(require_text(payload, "frame_index"))
    row = {
        "frame_id": frame_id,
        "segment_name": require_text(payload, "segment_name"),
        "frame_index": str(frame_index),
        "prototype_id": require_text(payload, "prototype_id"),
        "collection_version": require_text(payload, "collection_version"),
        "weather": validate_choice(require_text(payload, "weather"), ["晴天", "阴天", "雨天"], "weather"),
        "time_of_day": validate_choice(require_text(payload, "time_of_day"), ["白天", "晚上"], "time_of_day"),
        "view_direction": validate_choice(require_text(payload, "view_direction"), ["前", "后", "左", "右"], "view_direction"),
        "value_score": validate_value_score(require_text(payload, "value_score")),
        "dataset_split": validate_choice(require_text(payload, "dataset_split"), ["训练集", "验证集", "测试集"], "dataset_split"),
        "model_inference": str(payload.get("model_inference", "")).strip(),
        "data_path": require_text(payload, "data_path"),
        "target_tags": ", ".join(target_tags),
        "noise_tags": ", ".join(noise_tags),
    }

    for existing in frames:
        same_key = (
            existing["segment_name"] == row["segment_name"]
            and existing["frame_index"] == row["frame_index"]
        )
        if same_key and existing["frame_id"] != frame_id:
            raise ValueError("segment_name + frame_index already exists")

    if is_create:
        frames.append(row)
    else:
        frames = [row if existing["frame_id"] == frame_id else existing for existing in frames]

    write_csv(data_dir / "frames.csv", frames, FRAME_FIELDNAMES)
    reload_state(state, data_dir)
    return frame_id


def delete_frame_payload(data_dir: Path, state: dict[str, object], frame_id: str) -> None:
    frame_id = frame_id.strip()
    frames = list(state["frames"])
    if frame_id not in {row["frame_id"] for row in frames}:
        raise ValueError(f"frame_id {frame_id} does not exist")

    frames = [row for row in frames if row["frame_id"] != frame_id]
    write_csv(data_dir / "frames.csv", frames, FRAME_FIELDNAMES)

    dataset_version_frames_path = data_dir / "dataset_version_frames.csv"
    if dataset_version_frames_path.exists():
        dataset_version_frames = [
            row for row in load_csv(dataset_version_frames_path) if row["frame_id"] != frame_id
        ]
        write_csv(
            dataset_version_frames_path,
            dataset_version_frames,
            ["dataset_version_id", "frame_id", "split"],
        )
    reload_state(state, data_dir)


def make_handler(data_dir: Path) -> type[BaseHTTPRequestHandler]:
    state = load_state(data_dir)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def send_json(self, payload: object, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if parsed.path == "/":
                body = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path == "/api/options":
                self.send_json(state["options"])
                return
            if parsed.path == "/api/report":
                self.send_json(build_report(state["frames"]))
                return
            if parsed.path == "/api/query":
                query = query_from_params(params)
                limit = int(first(params, "limit") or 100)
                self.send_json(
                    {
                        "total": count_matches(state["frames"], query),
                        "rows": query_frames(state["frames"], query, limit=limit),
                    }
                )
                return
            if parsed.path == "/export":
                query = query_from_params(params)
                rows = query_frames(state["frames"], query, limit=None)
                body_text = ""
                if rows:
                    from io import StringIO

                    output = StringIO()
                    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
                    body_text = output.getvalue()
                body = body_text.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="frames_export.csv"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/frame":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                frame_id = save_frame_payload(data_dir, state, payload)
            except (ValueError, json.JSONDecodeError) as exc:
                self.send_json({"error": str(exc)}, status=400)
                return
            self.send_json({"ok": True, "frame_id": frame_id})

        def do_DELETE(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/frame":
                self.send_error(404)
                return
            try:
                params = parse_qs(parsed.query)
                frame_id = require_text({"frame_id": first(params, "frame_id")}, "frame_id")
                delete_frame_payload(data_dir, state, frame_id)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, status=400)
                return
            self.send_json({"ok": True})

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--no-auto-port",
        action="store_true",
        help="Fail instead of trying the next available port when the requested port is busy.",
    )
    args = parser.parse_args()

    port = args.port
    handler = make_handler(Path(args.data_dir))
    while True:
        try:
            server = ThreadingHTTPServer((args.host, port), handler)
            break
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE or args.no_auto_port:
                raise
            port = find_available_port(args.host, port + 1)

    if port != args.port:
        print(f"Port {args.port} is busy. Using {port} instead.")
    print(f"Dataset GUI: http://{args.host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    return 0


def find_available_port(host: str, start_port: int) -> int:
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available port found from {start_port} to {start_port + 99}.")


if __name__ == "__main__":
    sys.exit(main())
