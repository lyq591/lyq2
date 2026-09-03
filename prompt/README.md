# AI工具提示词追溯目录

本目录用于记录项目开发过程中与AI工具的交流记录，确保开发过程可追溯、可复现。

## 目录结构

```
prompt/
├── README.md                                      # 本说明文件
├── phase1_topic_selection_and_design.json        # 第一阶段：vibe coding学习与选题方案设计
├── phase2_data_preparation.json                   # 第二阶段：数据准备
├── phase3_integration_and_reporting.json          # 第三阶段：集成调试与报告撰写
├── phase4_detailed_development.json               # 第四阶段：详细开发
└── phase5_debugging_and_tools.json                # 第五阶段：调试与工具完善
```

## 记录规范

- 每个阶段一个 JSON 文件，命名格式：`phase{阶段号}_{阶段名称}.json`
- JSON 文件包含：阶段名称、日期、项目名称、描述、对话记录列表、使用工具、关键决策
- 对话记录按时间顺序排列，包含 id、timestamp、role(user/assistant)、content
- 在上下文压缩前及时备份并添加新的对话记录
- 后续每个阶段同步更新本目录

## 阶段记录索引

| 阶段 | 文件 | 日期 | 对话数 | 主要内容 |
|------|------|------|--------|----------|
| 第一阶段：vibe coding学习与选题方案设计 | phase1_topic_selection_and_design.json | 2026-08-28 | 14 | Git环境配置(SSH+443端口)、vibe coding方法学习、选题确定、技术方向映射(4个方向)、方案设计、学习笔记 |
| 第二阶段：数据准备 | phase2_data_preparation.json | 2026-08-30 | 11 | FJSP-F数据集解析(纯Python .mat解析器)、预处理、JSON转换、数据补全策略、数据说明文档、prompt目录创建 |
| 第三阶段：集成调试与报告撰写 | phase3_integration_and_reporting.json | 2026-09-03 | 5 | 接口字段不一致修复(3处)、前端联调验证、端到端流程测试(8步)、需求规格说明书(11000字)、系统设计报告(22000字) |
| 第四阶段：详细开发 | phase4_detailed_development.json | 2026-09-01 | 16 | SQLite数据库(4表)、遗传算法(两段式编码/POX交叉/工装约束)、数据分析模块(统计/瓶颈/对比/解释)、Flask API(15+接口)、Vue3+ECharts前端(7页面)、自动化测试(4套件28项) |
| 第五阶段：调试与工具完善 | phase5_debugging_and_tools.json | 2026-09-03 | 17 | 前端智能调度/数字孪生修复(10处)、一键启动程序、启动脚本闪退多轮修复(Popen title/CREATE_NEW_CONSOLE/Store Python占位符)、一键关闭脚本(三重保障)、设计报告缺失章节补齐(4章) |

## 使用的AI工具

- 豆包AI助手（代码生成、数据处理、文档撰写、问题排查、方案设计、调试修复）

## AI使用策略总结

1. **提示词工程**：任务拆解、约束说明、验收标准
2. **上下文工程**：项目规则文件、先读代码再改、渐进式修改
3. **规格驱动开发**：需求文档→AI制定计划→分步实现→逐步验收
4. **自动化测试与人工审查**：核心模块均有单元测试，关键算法人工逐行审查
5. **调试与人工接管**：回滚、缩小改动范围、最小复现，必要时人工接管
