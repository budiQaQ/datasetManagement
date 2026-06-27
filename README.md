# Dataset Management

帧级数据集管理工具，支持本地 GUI 和简单命令行筛选。项目只依赖 Python 标准库，不需要安装第三方包。

## 功能

- 按帧管理数据，`segment_name + frame_index` 唯一定位一帧。
- 支持新增、编辑、删除、筛选和导出 CSV。
- 支持固定枚举字段：
  - 天气：`晴天`、`阴天`、`雨天`
  - 时段：`白天`、`晚上`
  - 视野方向：`前`、`后`、`左`、`右`
- 支持自定义目标 tag 和噪声 tag，每类最多 10 个。
- 支持数据价值评分、训练/验证/测试归属、模型推理情况描述。
- 支持本地报表：数据段上的集合堆叠分布、可选 tag 分布、价值评分分布。

## 数据字段

`data/seed/frames.csv` 是主数据文件，字段如下：

| 字段 | 说明 |
| --- | --- |
| `frame_id` | 内部唯一 ID |
| `segment_name` | 数据段名 |
| `frame_index` | 帧号 |
| `prototype_id` | 样机编号 |
| `collection_version` | 采集版本 |
| `weather` | 天气 |
| `time_of_day` | 时段 |
| `view_direction` | 视野方向 |
| `value_score` | 数据价值评分，1 到 10 的整数 |
| `dataset_split` | 集合归属：训练集、验证集、测试集 |
| `model_inference` | 模型推理情况，自定义描述 |
| `data_path` | 数据路径 |
| `target_tags` | 目标 tag 描述 |
| `noise_tags` | 噪声 tag 描述 |

## Windows 运行

要求 Python 3.10 或更高版本。

```powershell
py -3 --version
py -3 scripts\dataset_gui.py
```

启动后打开终端输出的地址，通常是：

```text
http://127.0.0.1:8765
```

如果当前 PowerShell 显示中文异常，可以先执行：

```powershell
chcp 65001
```

## macOS / Linux 运行

```bash
python3 scripts/dataset_gui.py
```

## 命令行筛选

查看可选值：

```bash
python3 scripts/dataset_cli.py options
```

筛选示例：

```bash
python3 scripts/dataset_cli.py query --weather 雨天 --view 前 --target 行人 --limit 20
```

Windows PowerShell 对应命令：

```powershell
py -3 scripts\dataset_cli.py query --weather 雨天 --view 前 --target 行人 --limit 20
```

## 生成虚构数据

当前仓库默认保留空数据表。需要生成测试数据时运行：

```bash
python3 scripts/generate_mock_dataset.py --segments 80 --frames-per-segment 250 --output-dir data/seed
```

Windows PowerShell：

```powershell
py -3 scripts\generate_mock_dataset.py --segments 80 --frames-per-segment 250 --output-dir data\seed
```

## PostgreSQL

如需导入数据库，可先执行：

```bash
psql -f docs/schema.sql
```

再参考 [docs/seed_data.md](docs/seed_data.md) 中的导入示例。
