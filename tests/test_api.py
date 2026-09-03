"""
API接口单元测试
技术方向：智能制造系统集成
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from flask.testing import FlaskClient
from main import app

# 配置Flask测试客户端
app.config['TESTING'] = True
client = app.test_client()


def test_health_check():
    """测试健康检查接口"""
    print("测试1: 健康检查接口...", end=" ")
    response = client.get("/api/health")
    assert response.status_code == 200, f"状态码应为200，实际{response.status_code}"
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "database_stats" in data
    print("✓ 通过")


def test_root():
    """测试根路径"""
    print("测试2: 根路径接口...", end=" ")
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert "name" in data
    assert "version" in data
    print("✓ 通过")


def test_list_instances():
    """测试获取实例列表"""
    print("测试3: 获取实例列表接口...", end=" ")
    response = client.get("/api/dataset/instances")
    assert response.status_code == 200
    data = response.get_json()
    assert "instances" in data
    assert data["total"] == 20, f"应有20个实例，实际{data['total']}"
    assert len(data["instances"]) == 20
    # 验证实例结构
    inst = data["instances"][0]
    assert "instance_id" in inst
    assert "num_jobs" in inst
    assert "num_machines" in inst
    print("✓ 通过")


def test_get_instance():
    """测试获取单个实例"""
    print("测试4: 获取单个实例接口...", end=" ")
    response = client.get("/api/dataset/FJSP-F1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["instance_id"] == "FJSP-F1"
    assert "scale" in data
    assert "jobs" in data
    assert "metadata" in data
    print("✓ 通过")


def test_get_instance_not_found():
    """测试获取不存在的实例"""
    print("测试5: 获取不存在实例(404)...", end=" ")
    response = client.get("/api/dataset/NonExistent")
    assert response.status_code == 404
    print("✓ 通过")


def test_instance_stats():
    """测试实例统计接口"""
    print("测试6: 实例统计接口...", end=" ")
    response = client.get("/api/dataset/FJSP-F1/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert "total_operations" in data
    assert "processing_time_stats" in data
    assert "machine_workload" in data
    print("✓ 通过")


def test_bottlenecks():
    """测试瓶颈识别接口"""
    print("测试7: 瓶颈识别接口...", end=" ")
    response = client.get("/api/dataset/FJSP-F1/bottlenecks")
    assert response.status_code == 200
    data = response.get_json()
    assert "machine_bottlenecks" in data
    assert "recommendation" in data
    print("✓ 通过")


def test_dataset_overview():
    """测试数据集概览接口"""
    print("测试8: 数据集概览接口...", end=" ")
    response = client.get("/api/dataset/overview")
    assert response.status_code == 200
    data = response.get_json()
    assert data["num_instances"] == 20
    assert "scale_range" in data
    print("✓ 通过")


def test_schedule_endpoint():
    """测试调度接口"""
    print("测试9: 调度接口...", end=" ")
    response = client.post("/api/schedule", json={
        "instance_id": "FJSP-F1",
        "pop_size": 30,
        "max_gen": 30,
        "seed": 42
    })
    assert response.status_code == 200, f"状态码应为200，实际{response.status_code}: {response.text}"
    data = response.get_json()
    assert "makespan" in data
    assert "machine_schedule" in data
    assert "job_schedule" in data
    assert "analysis" in data
    assert data["makespan"] > 0
    print("✓ 通过")


def test_schedule_invalid_instance():
    """测试调度不存在的实例"""
    print("测试10: 调度不存在实例(404)...", end=" ")
    response = client.post("/api/schedule", json={
        "instance_id": "NonExistent",
        "pop_size": 10,
        "max_gen": 10
    })
    assert response.status_code == 404
    print("✓ 通过")


def test_schedule_history():
    """测试调度历史接口"""
    print("测试11: 调度历史接口...", end=" ")
    response = client.get("/api/schedule/results?limit=10")
    assert response.status_code == 200
    data = response.get_json()
    assert "tasks" in data
    assert "total" in data
    print("✓ 通过")


def test_compare_instances():
    """测试实例对比接口"""
    print("测试12: 实例对比接口...", end=" ")
    response = client.get("/api/analysis/compare?instances=FJSP-F1,FJSP-F10,FJSP-F20")
    assert response.status_code == 200
    data = response.get_json()
    assert "comparison" in data
    assert len(data["comparison"]) == 3
    print("✓ 通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("API接口单元测试")
    print("=" * 60)
    test_health_check()
    test_root()
    test_list_instances()
    test_get_instance()
    test_get_instance_not_found()
    test_instance_stats()
    test_bottlenecks()
    test_dataset_overview()
    test_schedule_endpoint()
    test_schedule_invalid_instance()
    test_schedule_history()
    test_compare_instances()
    print("=" * 60)
    print("所有测试通过! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

