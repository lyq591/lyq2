"""
FJSP遗传算法单元测试
技术方向：工艺规划与车间调度
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from algorithms.fjsp_ga import FJSPSolver, solve_fjsp


def get_test_instance():
    """获取测试用实例数据"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
    fpath = os.path.join(data_dir, "FJSP-F1.json")
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def test_solver_initialization():
    """测试求解器初始化"""
    print("测试1: 求解器初始化...", end=" ")
    data = get_test_instance()
    jobs_data = []
    for job in data["jobs"]:
        ops = [{"eligible_machines": op["eligible_machines"],
                "processing_times": op["processing_times"],
                "eligible_fixtures": op.get("eligible_fixtures", [])}
               for op in job["operations"]]
        jobs_data.append({"job_id": job["job_id"], "operations": ops})

    solver = FJSPSolver(
        jobs_data=jobs_data,
        num_machines=data["scale"]["num_machines"],
        num_fixtures=data["scale"]["num_fixtures"],
        pop_size=20, max_gen=10, seed=42
    )
    assert solver.num_jobs == len(jobs_data), "作业数不匹配"
    assert solver.num_machines == data["scale"]["num_machines"], "机器数不匹配"
    assert solver.total_ops > 0, "总工序数应为正数"
    assert len(solver.op_info) == solver.total_ops, "操作信息数量不匹配"
    print("✓ 通过")


def test_chromosome_generation():
    """测试染色体生成"""
    print("测试2: 染色体生成...", end=" ")
    data = get_test_instance()
    jobs_data = [{"job_id": j["job_id"],
                   "operations": [{"eligible_machines": op["eligible_machines"],
                                   "processing_times": op["processing_times"],
                                   "eligible_fixtures": op.get("eligible_fixtures", [])}
                                  for op in j["operations"]]}
                  for j in data["jobs"]]
    solver = FJSPSolver(jobs_data, data["scale"]["num_machines"], seed=42)
    chrom = solver._random_chromosome()
    assert "seq" in chrom, "染色体应包含seq"
    assert "machine_assign" in chrom, "染色体应包含machine_assign"
    assert len(chrom["seq"]) == solver.total_ops, "操作序列长度应等于总工序数"
    assert len(chrom["machine_assign"]) == solver.total_ops, "机器分配长度应等于总工序数"
    # 验证每个作业号出现次数等于其工序数
    for j_idx in range(solver.num_jobs):
        assert chrom["seq"].count(j_idx) == solver.ops_per_job[j_idx], f"作业{j_idx}出现次数不匹配"
    print("✓ 通过")


def test_decode():
    """测试解码功能"""
    print("测试3: 染色体解码...", end=" ")
    data = get_test_instance()
    jobs_data = [{"job_id": j["job_id"],
                   "operations": [{"eligible_machines": op["eligible_machines"],
                                   "processing_times": op["processing_times"],
                                   "eligible_fixtures": op.get("eligible_fixtures", [])}
                                  for op in j["operations"]]}
                  for j in data["jobs"]]
    solver = FJSPSolver(jobs_data, data["scale"]["num_machines"], seed=42)
    chrom = solver._random_chromosome()
    makespan, machine_sched, job_sched = solver.decode(chrom)
    assert makespan > 0, "Makespan应为正数"
    assert len(machine_sched) == solver.num_machines, "机器调度列表长度应等于机器数"
    assert len(job_sched) == solver.num_jobs, "作业调度列表长度应等于作业数"
    # 验证所有工序都被调度
    total_tasks = sum(len(tasks) for tasks in machine_sched)
    assert total_tasks == solver.total_ops, f"调度任务数({total_tasks})应等于总工序数({solver.total_ops})"
    print("✓ 通过")


def test_solve():
    """测试完整求解"""
    print("测试4: 完整调度求解...", end=" ")
    data = get_test_instance()
    result = solve_fjsp(data, pop_size=30, max_gen=30, seed=42)
    assert "makespan" in result, "结果应包含makespan"
    assert "machine_schedule" in result, "结果应包含machine_schedule"
    assert "job_schedule" in result, "结果应包含job_schedule"
    assert "machine_utilization" in result, "结果应包含machine_utilization"
    assert "convergence_history" in result, "结果应包含convergence_history"
    assert "elapsed_time" in result, "结果应包含elapsed_time"
    assert result["makespan"] > 0, "Makespan应为正数"
    assert len(result["convergence_history"]) == 30, "收敛历史长度应等于迭代代数"
    # 验证makespan单调不增
    history = result["convergence_history"]
    for i in range(1, len(history)):
        assert history[i]["best_makespan"] <= history[i-1]["best_makespan"], "最优makespan应单调不增"
    print("✓ 通过")


def test_machine_utilization():
    """测试机器利用率计算"""
    print("测试5: 机器利用率计算...", end=" ")
    data = get_test_instance()
    result = solve_fjsp(data, pop_size=20, max_gen=20, seed=42)
    utils = result["machine_utilization"]
    assert len(utils) == data["scale"]["num_machines"], "利用率列表长度应等于机器数"
    for u in utils:
        assert "machine_id" in u, "应包含machine_id"
        assert "utilization_rate" in u, "应包含utilization_rate"
        assert "num_tasks" in u, "应包含num_tasks"
        assert 0 <= u["utilization_rate"] <= 100, "利用率应在0-100之间"
    print("✓ 通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("FJSP遗传算法单元测试")
    print("=" * 60)
    test_solver_initialization()
    test_chromosome_generation()
    test_decode()
    test_solve()
    test_machine_utilization()
    print("=" * 60)
    print("所有测试通过! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
