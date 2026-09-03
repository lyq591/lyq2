"""
数据分析模块单元测试
技术方向：工业大数据采集与分析
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from algorithms.analysis import DataAnalyzer


def get_analyzer():
    """获取分析器实例"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
    return DataAnalyzer(data_dir)


def test_analyzer_initialization():
    """测试分析器初始化"""
    print("测试1: 分析器初始化...", end=" ")
    analyzer = get_analyzer()
    assert len(analyzer.instances) > 0, "应加载至少一个实例"
    assert "FJSP-F1" in analyzer.instances, "应包含FJSP-F1"
    print("✓ 通过")


def test_instance_stats():
    """测试实例统计"""
    print("测试2: 实例统计分析...", end=" ")
    analyzer = get_analyzer()
    stats = analyzer.get_instance_stats("FJSP-F1")
    assert stats is not None, "统计结果不应为None"
    assert stats["instance_id"] == "FJSP-F1"
    assert "total_operations" in stats
    assert "processing_time_stats" in stats
    assert "machine_workload" in stats
    assert stats["total_operations"] > 0, "总工序数应大于0"
    assert stats["processing_time_stats"]["mean"] > 0, "平均加工时间应大于0"
    print("✓ 通过")


def test_bottleneck_identification():
    """测试瓶颈识别"""
    print("测试3: 瓶颈识别...", end=" ")
    analyzer = get_analyzer()
    result = analyzer.identify_bottlenecks("FJSP-F1")
    assert result is not None, "瓶颈分析结果不应为None"
    assert "machine_bottlenecks" in result
    assert "fixture_bottlenecks" in result
    assert "recommendation" in result
    assert len(result["machine_bottlenecks"]) > 0, "应识别出至少一个机器瓶颈"
    print("✓ 通过")


def test_dataset_overview():
    """测试数据集概览"""
    print("测试4: 数据集概览...", end=" ")
    analyzer = get_analyzer()
    overview = analyzer.get_dataset_overview()
    assert overview["num_instances"] == 20, "应有20个实例"
    assert "scale_range" in overview
    assert "instances" in overview
    assert len(overview["instances"]) == 20
    print("✓ 通过")


def test_compare_instances():
    """测试实例对比"""
    print("测试5: 实例对比...", end=" ")
    analyzer = get_analyzer()
    comparison = analyzer.compare_instances(["FJSP-F1", "FJSP-F10", "FJSP-F20"])
    assert len(comparison) == 3, "应对比3个实例"
    assert comparison[0]["instance_id"] == "FJSP-F1"
    assert comparison[2]["instance_id"] == "FJSP-F20"
    # F20应比F1规模大
    assert comparison[2]["num_jobs"] > comparison[0]["num_jobs"], "F20作业数应大于F1"
    print("✓ 通过")


def test_schedule_analysis():
    """测试调度结果分析"""
    print("测试6: 调度结果分析...", end=" ")
    analyzer = get_analyzer()
    from algorithms.fjsp_ga import solve_fjsp
    data = analyzer.instances["FJSP-F1"]
    schedule = solve_fjsp(data, pop_size=20, max_gen=20, seed=42)
    analysis = analyzer.analyze_schedule_result(schedule, data)
    assert "makespan" in analysis
    assert "critical_path_jobs" in analysis
    assert "machine_load_balance" in analysis
    assert "explanation" in analysis
    assert len(analysis["explanation"]) > 50, "解释文本应足够长"
    assert "关键路径" in analysis["explanation"] or "工期" in analysis["explanation"], "解释应包含关键信息"
    print("✓ 通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("数据分析模块单元测试")
    print("=" * 60)
    test_analyzer_initialization()
    test_instance_stats()
    test_bottleneck_identification()
    test_dataset_overview()
    test_compare_instances()
    test_schedule_analysis()
    print("=" * 60)
    print("所有测试通过! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
