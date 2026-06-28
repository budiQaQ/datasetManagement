# 初始化虚构数据

当前种子数据位于 `data/seed/`，由 `scripts/generate_mock_dataset.py` 生成。

## 文件

- `frames.csv`: 帧级主表，`segment_name + frame_index` 可唯一定位一帧。
- `dataset_versions.csv`: 示例数据集版本。
- `dataset_version_frames.csv`: 示例版本中的 train / val / test 划分。
- `summary.json`: 本次生成数据的统计摘要。

## 帧字段

- `frame_id`: 内部唯一 ID。
- `segment_name`: 数据段名。
- `frame_index`: 帧号。
- `prototype_id`: 样机编号。
- `collection_version`: 采集版本。
- `weather`: 天气，可选 `晴天`、`阴天`、`雨天`。
- `time_of_day`: 时段，可选 `白天`、`晚上`。
- `view_direction`: 视野方向，可选 `前`、`后`、`左`、`右`。
- `value_score`: 数据价值评分，1 到 10 的整数。
- `dataset_split`: 数据属于 `训练集`、`验证集` 或 `测试集`。
- `model_inference`: 模型推理情况，用户自定义描述。
- `data_path`: 数据路径。
- `target_tags`: 自定义目标 tag 描述，逗号分隔，最多 10 个。
- `noise_tags`: 自定义噪声 tag 描述，逗号分隔，最多 10 个。

## 默认规模

- 数据段数：80
- 每段帧数：250
- 总帧数：20,000

## 重新生成

```bash
python3 scripts/generate_mock_dataset.py \
  --segments 80 \
  --frames-per-segment 250 \
  --seed 20260627 \
  --output-dir data/seed
```

如果要模拟几十万帧，可以调整参数：

```bash
python3 scripts/generate_mock_dataset.py \
  --segments 1000 \
  --frames-per-segment 300 \
  --seed 20260627 \
  --output-dir data/seed_300k
```

## 简单命令行接口

查看可选筛选值：

```bash
python3 scripts/dataset_cli.py options
```

筛选雨天、前视、有行人 tag 的帧：

```bash
python3 scripts/dataset_cli.py query \
  --weather 雨天 \
  --view 前 \
  --target 行人 \
  --limit 20
```

导出筛选结果：

```bash
python3 scripts/dataset_cli.py query \
  --weather 雨天 \
  --view 前 \
  --target 行人 \
  --export data/seed/rain_front_pedestrian.csv
```

## 本地 GUI

启动本地浏览器管理页面：

```bash
python3 scripts/dataset_gui.py
```

然后打开：

```text
http://127.0.0.1:8765
```

如果 `8765` 已经被占用，程序会自动切换到下一个可用端口，并在终端输出实际地址，例如：

```text
Port 8765 is busy. Using 8766 instead.
Dataset GUI: http://127.0.0.1:8766
```

页面支持筛选、导出、新增、编辑、删除和报表。新增或编辑时，目标 tag 和噪声 tag 都是自定义文本，使用逗号、分号或换行分隔，每类最多 10 个。

报表包含：

- 训练集/验证集/测试集在各个数据段上的堆叠条分布。
- 选择某个目标 tag 后查看该 tag 在训练集/验证集/测试集中的分布。
- 选择某个噪声 tag 后查看该 tag 在训练集/验证集/测试集中的分布。
- 数据价值评分均值和标准差。

这些操作会直接修改 `data/seed/frames.csv`。正式数据建议先用 Git 提交或复制备份后再批量编辑。

## PostgreSQL 导入示例

先执行 `docs/schema.sql` 建表，然后按顺序导入：

```sql
\copy frames FROM 'data/seed/frames.csv' CSV HEADER;
\copy dataset_versions FROM 'data/seed/dataset_versions.csv' CSV HEADER;
\copy dataset_version_frames FROM 'data/seed/dataset_version_frames.csv' CSV HEADER;
```

## 组合筛选示例

```sql
SELECT *
FROM frames
WHERE weather = '雨天'
  AND view_direction = '前'
  AND target_tags LIKE '%行人%';
```
