"""
Flask 后端服务主入口
技术方向：智能制造系统集成（RESTful API）
纯Python实现，不依赖pydantic原生库，兼容系统应用控制策略
"""
import sys
import os
import json
import time

# 确保backend目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS

from algorithms.fjsp_ga import solve_fjsp
from algorithms.analysis import DataAnalyzer
from database import get_db


# ==================== 应用初始化 ====================

app = Flask(__name__)
CORS(app)

# 数据目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

# 数据分析器和数据库
analyzer = DataAnalyzer(DATA_DIR)
db = get_db()


# ==================== 工具函数 ====================

def load_instance(instance_id):
    """加载实例数据"""
    # 先查缓存
    cached = db.get_cached_instance(instance_id)
    if cached:
        return cached["data"]

    # 从文件加载
    fpath = os.path.join(DATA_DIR, f"{instance_id}.json")
    if not os.path.exists(fpath):
        return None
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 缓存
    stats = analyzer.get_instance_stats(instance_id)
    db.cache_instance(instance_id, data, stats)
    return data


def error_response(message, status_code=404):
    """错误响应"""
    return jsonify({"detail": message}), status_code


# ==================== API路由 ====================

@app.route("/")
def root():
    """系统根路径"""
    return jsonify({
        "name": "FJSP智能调度辅助Agent系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/health",
    })


@app.route("/api/health")
def health_check():
    """健康检查"""
    stats = db.get_stats()
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "database_stats": stats,
    })


# ---------- 数据集相关 ----------

@app.route("/api/dataset/instances")
def list_instances():
    """获取所有实例列表"""
    instances = []
    if os.path.exists(DATA_DIR):
        for fname in sorted(os.listdir(DATA_DIR)):
            if fname.endswith(".json") and fname != "index.json":
                iid = fname.replace(".json", "")
                data = load_instance(iid)
                if data:
                    instances.append({
                        "instance_id": iid,
                        "num_jobs": data["scale"]["num_jobs"],
                        "num_machines": data["scale"]["num_machines"],
                        "num_fixtures": data["scale"]["num_fixtures"],
                        "operations_per_job": data["scale"]["operations_per_job"],
                        "total_processing_time": data["metadata"]["total_processing_time"],
                    })
    return jsonify({"instances": instances, "total": len(instances)})


@app.route("/api/dataset/<instance_id>")
def get_instance(instance_id):
    """获取单个实例详情"""
    data = load_instance(instance_id)
    if data is None:
        return error_response(f"实例 {instance_id} 不存在")
    return jsonify(data)


@app.route("/api/dataset/<instance_id>/stats")
def get_instance_stats(instance_id):
    """获取实例统计信息"""
    stats = analyzer.get_instance_stats(instance_id)
    if stats is None:
        return error_response(f"实例 {instance_id} 不存在")
    return jsonify(stats)


@app.route("/api/dataset/<instance_id>/bottlenecks")
def get_bottlenecks(instance_id):
    """识别实例瓶颈"""
    result = analyzer.identify_bottlenecks(instance_id)
    if result is None:
        return error_response(f"实例 {instance_id} 不存在")
    return jsonify(result)


@app.route("/api/dataset/overview")
def get_dataset_overview():
    """获取数据集概览"""
    return jsonify(analyzer.get_dataset_overview())


# ---------- 调度相关 ----------

@app.route("/api/schedule", methods=["POST"])
def create_schedule():
    """创建调度任务并执行求解"""
    body = request.get_json(force=True)
    instance_id = body.get("instance_id")
    if not instance_id:
        return error_response("缺少instance_id参数", 400)

    # 加载实例数据
    instance_data = load_instance(instance_id)
    if instance_data is None:
        return error_response(f"实例 {instance_id} 不存在")

    pop_size = body.get("pop_size", 100)
    max_gen = body.get("max_gen", 200)
    seed = body.get("seed", 42)

    # 创建任务记录
    task_id = db.create_task(
        instance_id=instance_id,
        instance_name=instance_id,
        parameters={"pop_size": pop_size, "max_gen": max_gen, "seed": seed}
    )

    try:
        # 更新状态为运行中
        db.update_task_status(task_id, "running")

        # 执行调度
        result = solve_fjsp(
            instance_data,
            pop_size=pop_size,
            max_gen=max_gen,
            seed=seed,
        )

        # 分析调度结果
        analysis = analyzer.analyze_schedule_result(result, instance_data)

        # 保存结果
        result_id = db.save_result(task_id, instance_id, result, analysis)

        # 更新任务状态
        db.update_task_status(
            task_id, "completed",
            result={"result_id": result_id},
            makespan=result["makespan"],
            elapsed_time=result["elapsed_time"],
        )

        db.add_log("info", "scheduling", f"实例 {instance_id} 调度完成，Makespan={result['makespan']}")

        return jsonify({
            "task_id": task_id,
            "result_id": result_id,
            "makespan": result["makespan"],
            "elapsed_time": result["elapsed_time"],
            "machine_schedule": result["machine_schedule"],
            "job_schedule": result["job_schedule"],
            "machine_utilization": result["machine_utilization"],
            "convergence_history": result["convergence_history"],
            "analysis": analysis,
        })

    except Exception as e:
        db.update_task_status(task_id, "failed", result={"error": str(e)})
        db.add_log("error", "scheduling", f"实例 {instance_id} 调度失败: {str(e)}")
        return error_response(f"调度失败: {str(e)}", 500)


@app.route("/api/schedule/custom", methods=["POST"])
def schedule_custom_task():
    """调度自定义任务"""
    body = request.get_json(force=True)
    jobs = body.get("jobs", [])
    num_machines = body.get("num_machines", 0)
    num_fixtures = body.get("num_fixtures", 0)
    pop_size = body.get("pop_size", 100)
    max_gen = body.get("max_gen", 200)
    seed = body.get("seed", 42)

    if not jobs or num_machines <= 0:
        return error_response("缺少jobs或num_machines参数", 400)

    instance_data = {
        "scale": {
            "num_jobs": len(jobs),
            "num_machines": num_machines,
            "num_fixtures": num_fixtures,
        },
        "jobs": jobs,
        "metadata": {"total_processing_time": 0},
    }

    try:
        result = solve_fjsp(instance_data, pop_size=pop_size, max_gen=max_gen, seed=seed)
        analysis = analyzer.analyze_schedule_result(result, instance_data)
        return jsonify({
            "makespan": result["makespan"],
            "elapsed_time": result["elapsed_time"],
            "machine_schedule": result["machine_schedule"],
            "job_schedule": result["job_schedule"],
            "machine_utilization": result["machine_utilization"],
            "convergence_history": result["convergence_history"],
            "analysis": analysis,
        })
    except Exception as e:
        return error_response(f"调度失败: {str(e)}", 500)


@app.route("/api/schedule/results")
def list_schedule_results():
    """获取调度结果列表"""
    limit = request.args.get("limit", 20, type=int)
    limit = min(max(limit, 1), 100)
    tasks = db.list_tasks(limit=limit)
    return jsonify({"tasks": tasks, "total": len(tasks)})


@app.route("/api/schedule/results/<int:result_id>")
def get_schedule_result(result_id):
    """获取单个调度结果详情"""
    result = db.get_result(result_id)
    if result is None:
        return error_response("调度结果不存在")
    return jsonify(result)


@app.route("/api/schedule/latest/<instance_id>")
def get_latest_result(instance_id):
    """获取某实例的最新调度结果"""
    result = db.get_latest_result(instance_id)
    if result is None:
        return error_response(f"实例 {instance_id} 暂无调度结果")
    return jsonify(result)


# ---------- 分析相关 ----------

@app.route("/api/analysis/compare")
def compare_instances():
    """对比多个实例"""
    instances_param = request.args.get("instances")
    if instances_param:
        instance_ids = [i.strip() for i in instances_param.split(",")]
    else:
        instance_ids = None
    return jsonify({"comparison": analyzer.compare_instances(instance_ids)})


@app.route("/api/analysis/schedule/<instance_id>")
def analyze_schedule(instance_id):
    """分析某实例的最新调度结果"""
    result = db.get_latest_result(instance_id)
    instance_data = load_instance(instance_id)
    if instance_data is None:
        return error_response(f"实例 {instance_id} 不存在")

    if result is None:
        # 如果没有历史结果，先执行一次调度
        schedule_result = solve_fjsp(instance_data, pop_size=50, max_gen=100, seed=42)
        analysis = analyzer.analyze_schedule_result(schedule_result, instance_data)
        return jsonify({"analysis": analysis, "schedule": schedule_result})

    analysis = analyzer.analyze_schedule_result(result, instance_data)
    return jsonify({"analysis": analysis, "result_id": result["id"]})


# ---------- 系统日志 ----------

@app.route("/api/logs")
def get_logs():
    """获取系统日志"""
    limit = request.args.get("limit", 50, type=int)
    limit = min(max(limit, 1), 200)
    level = request.args.get("level")
    logs = db.get_logs(limit=limit, level=level)
    return jsonify({"logs": logs, "total": len(logs)})


# ==================== 启动配置 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("FJSP智能调度辅助Agent系统 - 后端服务启动中...")
    print(f"数据目录: {DATA_DIR}")
    print(f"数据库: {db.db_path}")
    print("API地址: http://127.0.0.1:8000")
    print("健康检查: http://127.0.0.1:8000/api/health")
    print("=" * 60)
    app.run(host="0.0.0.0", port=8000, debug=False)
