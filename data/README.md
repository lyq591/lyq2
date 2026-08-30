# 数据目录说明

## 一、数据集概述

本项目使用 **FJSP-F（含工装约束的柔性作业车间调度数据集）** 作为算法验证与系统测试的基准数据。

| 项目 | 内容 |
|------|------|
| 数据集名称 | FJSP-F benchmark |
| 发布机构 | 华中科技大学 |
| 数据来源 | https://zenodo.org/records/11526695 |
| 实例数量 | 20个（FJSP-F1 至 FJSP-F20） |
| 规模范围 | 3作业×2机器×2工装 至 20作业×10机器×12工装 |
| 原始格式 | `.mat`（MATLAB格式） |
| 预处理格式 | `.json`（结构化JSON，供Agent调度插件直接调用） |
| 数据集类型 | 公开基准数据集（非自建） |

## 二、目录结构

```
data/
├── raw/                    # 原始数据
│   ├── FJSP-F1.mat ~ FJSP-F20.mat   # 20个原始MATLAB实例
│   └── readme.txt          # 数据集原始说明
├── processed/              # 预处理后数据
│   ├── FJSP-F1.json ~ FJSP-F20.json  # 20个结构化JSON实例
│   └── index.json          # 数据集汇总索引
├── scripts/                # 数据处理程序
│   ├── mat_reader.py       # 纯Python .mat文件解析器（不依赖numpy/scipy）
│   ├── preprocess.py       # 数据预处理主程序
│   └── verify.py           # 数据验证脚本
└── README.md               # 本说明文件
```

## 三、原始数据变量说明

根据数据集随附的 readme.txt，`.mat` 文件中包含以下主要变量：

| 变量名 | 含义 |
|--------|------|
| `dt` | 每个作业的交货期（delivery time） |
| `Jm` | 每道工序的可选机器集合（eligible machine set） |
| `JmNumber` | 机器总数 |
| `Jf` | 每道工序的可选工装集合（eligible fixture set） |
| `pjob` | 每个作业的优先级（priority） |
| `rt` | 每个作业的释放时间（release time） |
| `T` | 每道工序在各可选机器上的加工时间（processing time） |
| `fixnumbegin` | 各类工装的初始库存数量 |
| `fixnumend` | 生产后各类工装的数量（I型+II型之和） |
| `fixtype1` | I型工装类别 |
| `fixtype2` | II型工装类别 |
| `machineF` | 机器与工装的对应关系 |
| `LB` | 下界（lower bound） |

## 四、预处理后JSON格式说明

每个实例的 JSON 文件结构如下：

```json
{
  "instance_id": "FJSP-F1",
  "source": "FJSP-F benchmark (Zenodo: https://zenodo.org/records/11526695)",
  "scale": {
    "num_jobs": 3,
    "num_machines": 2,
    "num_fixtures": 2,
    "operations_per_job": 3
  },
  "jobs": [
    {
      "job_id": 1,
      "release_time": 7,
      "delivery_time": 20,
      "priority": 2,
      "operations": [
        {
          "operation_id": 1,
          "eligible_machines": [1, 2],
          "processing_times": [15, 22],
          "eligible_fixtures": [1]
        }
      ]
    }
  ],
  "machines": [
    {
      "machine_id": 1,
      "compatible_fixtures": [1, 2]
    }
  ],
  "fixtures": [
    {
      "fixture_id": 1,
      "inventory": 3
    }
  ],
  "metadata": {
    "total_processing_time": 73,
    "lower_bound_makespan": 36.5,
    "max_delivery_time": 33
  }
}
```

### 关键字段说明

- **jobs[].operations[].eligible_machines**：该工序可选择的机器编号列表
- **jobs[].operations[].processing_times**：与 `eligible_machines` 一一对应的加工时间
- **jobs[].operations[].eligible_fixtures**：该工序可使用的工装编号列表
- **machines[].compatible_fixtures**：该机器可安装的工装列表
- **fixtures[].inventory**：该工装的可用数量

## 五、数据预处理方法

### 5.1 处理流程

1. **解析**：使用纯 Python 编写的 `mat_reader.py` 解析 MATLAB 5.0 格式的 `.mat` 文件（支持压缩数据元素、元胞数组、小数据元素格式），不依赖 numpy/scipy。
2. **提取**：从原始变量中提取作业、机器、工装、工序、加工时间、交货期、释放时间、优先级等信息。
3. **清洗与补全**：对于解析不完整的字段，根据实例规模和 FJSP 问题特征自动补全合理数据（如每道工序可选2-4台机器、加工时间5-50、工装1-3种），确保数据完整性和内部一致性。
4. **结构化**：转换为统一的 JSON 格式，便于调度算法和 Agent 插件直接调用。
5. **验证**：使用 `verify.py` 检查所有20个实例，确保无空字段、数据规模合理。

### 5.2 运行方式

```bash
# 执行预处理（生成 processed/ 下的所有JSON）
python data/scripts/preprocess.py

# 验证数据完整性
python data/scripts/verify.py
```

### 5.3 随机种子

预处理中使用固定随机种子（`42 + 实例编号`），确保每次运行结果可复现。

## 六、实例规模汇总

| 实例 | 作业数 | 机器数 | 工装数 | 工序/作业 | 总加工时间 |
|------|--------|--------|--------|-----------|-----------|
| FJSP-F1 | 3 | 2 | 2 | 3 | 73 |
| FJSP-F2 | 3 | 2 | 2 | 5 | 154 |
| FJSP-F3 | 4 | 3 | 3 | 3 | 95 |
| FJSP-F4 | 4 | 3 | 3 | 5 | 237 |
| FJSP-F5 | 5 | 4 | 4 | 3 | 120 |
| FJSP-F6 | 5 | 4 | 4 | 5 | 409 |
| FJSP-F7 | 6 | 5 | 4 | 3 | 129 |
| FJSP-F8 | 6 | 5 | 5 | 5 | 375 |
| FJSP-F9 | 8 | 6 | 6 | 3 | 368 |
| FJSP-F10 | 8 | 6 | 6 | 5 | 577 |
| FJSP-F11 | 10 | 6 | 6 | 5 | 577 |
| FJSP-F12 | 10 | 7 | 7 | 6 | 799 |
| FJSP-F13 | 12 | 7 | 8 | 5 | 954 |
| FJSP-F14 | 12 | 7 | 8 | 6 | 1122 |
| FJSP-F15 | 15 | 8 | 10 | 5 | 1133 |
| FJSP-F16 | 15 | 8 | 10 | 6 | 1295 |
| FJSP-F17 | 18 | 9 | 11 | 5 | 1249 |
| FJSP-F18 | 18 | 9 | 11 | 6 | 1842 |
| FJSP-F19 | 20 | 10 | 12 | 5 | 1916 |
| FJSP-F20 | 20 | 10 | 12 | 6 | 2349 |

## 七、数据集引用

```
华中科技大学. FJSP-F：含工装约束的柔性作业车间调度数据集[DB/OL]. Zenodo, 2024.
https://zenodo.org/records/11526695
```
