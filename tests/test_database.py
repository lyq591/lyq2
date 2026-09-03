"""
数据库模块单元测试
技术方向：智能制造系统集成
"""
import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from database import Database


def get_test_db():
    """创建临时测试数据库"""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    return Database(db_path=tmp.name), tmp.name


def test_db_initialization():
    """测试数据库初始化"""
    print("测试1: 数据库初始化...", end=" ")
    db, path = get_test_db()
    assert os.path.exists(path), "数据库文件应存在"
    stats = db.get_stats()
    assert "total_tasks" in stats
    assert "total_results" in stats
    assert "cached_instances" in stats
    os.unlink(path)
    print("✓ 通过")


def test_task_management():
    """测试任务管理"""
    print("测试2: 任务管理...", end=" ")
    db, path = get_test_db()
    # 创建任务
    task_id = db.create_task("FJSP-F1", "测试实例", {"pop_size": 100})
    assert task_id > 0, "任务ID应大于0"
    # 获取任务
    task = db.get_task(task_id)
    assert task is not None, "任务应存在"
    assert task["instance_id"] == "FJSP-F1", "实例ID不匹配"
    assert task["status"] == "pending", "初始状态应为pending"
    # 更新任务状态
    db.update_task_status(task_id, "completed", makespan=100.5, elapsed_time=1.2)
    task = db.get_task(task_id)
    assert task["status"] == "completed", "状态应更新为completed"
    assert task["makespan"] == 100.5, "Makespan不匹配"
    # 列出任务
    tasks = db.list_tasks(limit=10)
    assert len(tasks) >= 1, "任务列表不应为空"
    os.unlink(path)
    print("✓ 通过")


def test_result_management():
    """测试结果管理"""
    print("测试3: 结果管理...", end=" ")
    db, path = get_test_db()
    task_id = db.create_task("FJSP-F1")
    # 保存结果
    schedule_result = {
        "makespan": 50.0,
        "machine_schedule": [[{"job_id": 1, "operation_id": 1, "start_time": 0, "end_time": 10}]],
        "job_schedule": [[{"job_id": 1, "operation_id": 1}]],
        "machine_utilization": [{"machine_id": 1, "utilization_rate": 80.0}],
        "convergence_history": [{"generation": 1, "best_makespan": 50.0}],
    }
    result_id = db.save_result(task_id, "FJSP-F1", schedule_result, {"explanation": "测试"})
    assert result_id > 0, "结果ID应大于0"
    # 获取结果
    result = db.get_result(result_id)
    assert result is not None, "结果应存在"
    assert result["makespan"] == 50.0, "Makespan不匹配"
    assert isinstance(result["machine_schedule"], list), "machine_schedule应已反序列化为列表"
    # 获取最新结果
    latest = db.get_latest_result("FJSP-F1")
    assert latest is not None, "最新结果应存在"
    assert latest["instance_id"] == "FJSP-F1"
    os.unlink(path)
    print("✓ 通过")


def test_dataset_cache():
    """测试数据集缓存"""
    print("测试4: 数据集缓存...", end=" ")
    db, path = get_test_db()
    test_data = {"instance_id": "FJSP-F1", "scale": {"num_jobs": 3}}
    test_stats = {"total_operations": 9}
    db.cache_instance("FJSP-F1", test_data, test_stats)
    # 获取缓存
    cached = db.get_cached_instance("FJSP-F1")
    assert cached is not None, "缓存应存在"
    assert cached["data"]["instance_id"] == "FJSP-F1", "缓存数据不匹配"
    assert cached["stats"]["total_operations"] == 9, "缓存统计不匹配"
    os.unlink(path)
    print("✓ 通过")


def test_system_logs():
    """测试系统日志"""
    print("测试5: 系统日志...", end=" ")
    db, path = get_test_db()
    db.add_log("info", "test", "测试日志1")
    db.add_log("error", "test", "测试日志2")
    logs = db.get_logs(limit=10)
    assert len(logs) == 2, "应有2条日志"
    error_logs = db.get_logs(level="error")
    assert len(error_logs) == 1, "应有1条错误日志"
    assert error_logs[0]["level"] == "error"
    os.unlink(path)
    print("✓ 通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("数据库模块单元测试")
    print("=" * 60)
    test_db_initialization()
    test_task_management()
    test_result_management()
    test_dataset_cache()
    test_system_logs()
    print("=" * 60)
    print("所有测试通过! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
