"""
工业数据分析模块
技术方向：工业大数据采集与分析
提供数据集统计分析、瓶颈识别、特征提取等功能
"""
import json
import os
import math


class DataAnalyzer:
    """FJSP数据集分析器"""

    def __init__(self, data_dir=None):
        """
        初始化分析器
        :param data_dir: 预处理后数据目录
        """
        if data_dir is None:
            # 默认路径：项目根目录/data/processed
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base, "data", "processed")
        self.data_dir = data_dir
        self.instances = {}
        self._load_all()

    def _load_all(self):
        """加载所有实例数据"""
        if not os.path.exists(self.data_dir):
            return
        for fname in sorted(os.listdir(self.data_dir)):
            if fname.endswith(".json") and fname != "index.json":
                fpath = os.path.join(self.data_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.instances[data["instance_id"]] = data

    def get_instance_stats(self, instance_id):
        """
        获取单个实例的统计信息
        :param instance_id: 实例ID，如 "FJSP-F1"
        :return: 统计信息字典
        """
        if instance_id not in self.instances:
            return None
        data = self.instances[instance_id]
        scale = data["scale"]

        # 工序统计
        total_ops = 0
        all_processing_times = []
        machine_op_counts = [0] * scale["num_machines"]
        fixture_op_counts = [0] * scale["num_fixtures"]
        job_op_counts = []

        for job in data["jobs"]:
            job_ops = len(job["operations"])
            job_op_counts.append(job_ops)
            total_ops += job_ops
            for op in job["operations"]:
                all_processing_times.extend(op["processing_times"])
                for m in op["eligible_machines"]:
                    if 1 <= m <= scale["num_machines"]:
                        machine_op_counts[m - 1] += 1
                for f in op.get("eligible_fixtures", []):
                    if 1 <= f <= scale["num_fixtures"]:
                        fixture_op_counts[f - 1] += 1

        # 加工时间统计
        if all_processing_times:
            pt_mean = round(sum(all_processing_times) / len(all_processing_times), 2)
            pt_min = min(all_processing_times)
            pt_max = max(all_processing_times)
            pt_std = round(math.sqrt(sum((x - pt_mean) ** 2 for x in all_processing_times) / len(all_processing_times)), 2)
        else:
            pt_mean = pt_min = pt_max = pt_std = 0

        # 交货期统计
        delivery_times = [job["delivery_time"] for job in data["jobs"]]
        release_times = [job["release_time"] for job in data["jobs"]]
        priorities = [job["priority"] for job in data["jobs"]]

        return {
            "instance_id": instance_id,
            "scale": scale,
            "total_operations": total_ops,
            "avg_operations_per_job": round(total_ops / scale["num_jobs"], 2),
            "processing_time_stats": {
                "mean": pt_mean,
                "min": pt_min,
                "max": pt_max,
                "std": pt_std,
            },
            "machine_workload": [
                {"machine_id": i + 1, "eligible_op_count": machine_op_counts[i]}
                for i in range(scale["num_machines"])
            ],
            "fixture_usage": [
                {"fixture_id": i + 1, "eligible_op_count": fixture_op_counts[i]}
                for i in range(scale["num_fixtures"])
            ],
            "delivery_time_stats": {
                "mean": round(sum(delivery_times) / len(delivery_times), 2),
                "min": min(delivery_times),
                "max": max(delivery_times),
            },
            "release_time_stats": {
                "mean": round(sum(release_times) / len(release_times), 2),
                "min": min(release_times),
                "max": max(release_times),
            },
            "priority_distribution": {
                str(p): priorities.count(p) for p in set(priorities)
            },
        }

    def identify_bottlenecks(self, instance_id):
        """
        识别潜在瓶颈机器和工装
        :param instance_id: 实例ID
        :return: 瓶颈分析结果
        """
        stats = self.get_instance_stats(instance_id)
        if stats is None:
            return None

        # 机器瓶颈：可选工序数最多的机器
        machine_workloads = stats["machine_workload"]
        sorted_machines = sorted(machine_workloads, key=lambda x: x["eligible_op_count"], reverse=True)
        avg_machine_load = sum(m["eligible_op_count"] for m in machine_workloads) / len(machine_workloads) if machine_workloads else 0

        # 工装瓶颈
        fixture_usage = stats["fixture_usage"]
        sorted_fixtures = sorted(fixture_usage, key=lambda x: x["eligible_op_count"], reverse=True)

        return {
            "instance_id": instance_id,
            "machine_bottlenecks": [
                {
                    "machine_id": m["machine_id"],
                    "eligible_op_count": m["eligible_op_count"],
                    "is_bottleneck": m["eligible_op_count"] > avg_machine_load * 1.2,
                }
                for m in sorted_machines[:3]
            ],
            "avg_machine_load": round(avg_machine_load, 2),
            "fixture_bottlenecks": [
                {
                    "fixture_id": f["fixture_id"],
                    "eligible_op_count": f["eligible_op_count"],
                }
                for f in sorted_fixtures[:3]
            ],
            "recommendation": "建议优先关注高负荷机器的排程，避免任务堆积；可考虑增加瓶颈机器的可选工序分配灵活性。",
        }

    def compare_instances(self, instance_ids=None):
        """
        对比多个实例的特征
        :param instance_ids: 实例ID列表，None表示全部
        :return: 对比结果
        """
        if instance_ids is None:
            instance_ids = sorted(self.instances.keys())

        comparison = []
        for iid in instance_ids:
            stats = self.get_instance_stats(iid)
            if stats:
                comparison.append({
                    "instance_id": iid,
                    "num_jobs": stats["scale"]["num_jobs"],
                    "num_machines": stats["scale"]["num_machines"],
                    "num_fixtures": stats["scale"]["num_fixtures"],
                    "total_ops": stats["total_operations"],
                    "avg_pt": stats["processing_time_stats"]["mean"],
                    "max_pt": stats["processing_time_stats"]["max"],
                    "total_pt": stats.get("metadata", {}).get("total_processing_time", 0),
                })
        return comparison

    def get_dataset_overview(self):
        """获取整个数据集的概览"""
        if not self.instances:
            return {"error": "No instances loaded"}

        all_stats = []
        for iid in sorted(self.instances.keys()):
            stats = self.get_instance_stats(iid)
            if stats:
                all_stats.append(stats)

        total_jobs = sum(s["scale"]["num_jobs"] for s in all_stats)
        total_machines = sum(s["scale"]["num_machines"] for s in all_stats)
        total_ops = sum(s["total_operations"] for s in all_stats)
        all_pts = []
        for s in all_stats:
            # 从实例数据获取总加工时间
            iid = s["instance_id"]
            if iid in self.instances:
                all_pts.append(self.instances[iid]["metadata"]["total_processing_time"])

        return {
            "num_instances": len(all_stats),
            "total_jobs_across_instances": total_jobs,
            "total_machine_slots": total_machines,
            "total_operations": total_ops,
            "scale_range": {
                "jobs": f"{min(s['scale']['num_jobs'] for s in all_stats)} - {max(s['scale']['num_jobs'] for s in all_stats)}",
                "machines": f"{min(s['scale']['num_machines'] for s in all_stats)} - {max(s['scale']['num_machines'] for s in all_stats)}",
                "fixtures": f"{min(s['scale']['num_fixtures'] for s in all_stats)} - {max(s['scale']['num_fixtures'] for s in all_stats)}",
            },
            "avg_total_processing_time": round(sum(all_pts) / len(all_pts), 2) if all_pts else 0,
            "max_total_processing_time": max(all_pts) if all_pts else 0,
            "instances": [s["instance_id"] for s in all_stats],
        }

    def analyze_schedule_result(self, schedule_result, instance_data):
        """
        分析调度结果，提供决策解释
        技术方向：智能制造系统集成（调度决策透明化）
        :param schedule_result: GA求解返回的调度结果
        :param instance_data: 实例数据
        :return: 分析与解释
        """
        makespan = schedule_result["makespan"]
        machine_utils = schedule_result["machine_utilization"]

        # 关键路径识别：最后完成的作业
        job_finish_times = []
        for j_idx, job_sched in enumerate(schedule_result["job_schedule"]):
            if job_sched:
                finish = max(t["end_time"] for t in job_sched)
                job_finish_times.append({"job_id": j_idx + 1, "finish_time": finish})
        critical_jobs = sorted(job_finish_times, key=lambda x: x["finish_time"], reverse=True)[:3]

        # 机器负载均衡分析
        utils = [m["utilization_rate"] for m in machine_utils]
        avg_util = sum(utils) / len(utils) if utils else 0
        util_std = round(math.sqrt(sum((u - avg_util) ** 2 for u in utils) / len(utils)), 2) if utils else 0

        # 高利用率机器
        high_util_machines = [m for m in machine_utils if m["utilization_rate"] > 90]
        low_util_machines = [m for m in machine_utils if m["utilization_rate"] < 50]

        # 生成自然语言解释
        explanation = self._generate_explanation(
            makespan, critical_jobs, avg_util, util_std,
            high_util_machines, low_util_machines, instance_data
        )

        return {
            "makespan": makespan,
            "critical_path_jobs": critical_jobs,
            "machine_load_balance": {
                "avg_utilization": round(avg_util, 1),
                "utilization_std": util_std,
                "is_balanced": util_std < 15,
            },
            "high_utilization_machines": high_util_machines,
            "low_utilization_machines": low_util_machines,
            "explanation": explanation,
        }

    def _generate_explanation(self, makespan, critical_jobs, avg_util, util_std,
                               high_util, low_util, instance_data):
        """生成调度决策的自然语言解释"""
        parts = []
        parts.append(f"本次调度方案的总工期（Makespan）为 {makespan} 个时间单位。")

        if critical_jobs:
            job_ids = ", ".join(str(j["job_id"]) for j in critical_jobs)
            parts.append(f"关键路径上的作业为：作业{job_ids}，这些作业的完成时间直接影响总工期。")

        parts.append(f"机器平均利用率为 {round(avg_util, 1)}%，利用率标准差为 {util_std}，"
                     f"{'负载较为均衡' if util_std < 15 else '负载存在一定不均衡'}。")

        if high_util:
            mids = ", ".join(str(m["machine_id"]) for m in high_util)
            parts.append(f"高负荷机器（利用率>90%）：机器{mids}，建议关注这些机器的任务分配。")

        if low_util:
            mids = ", ".join(str(m["machine_id"]) for m in low_util)
            parts.append(f"低负荷机器（利用率<50%）：机器{mids}，可考虑将更多工序分配到这些机器以平衡负载。")

        # 交货期分析
        overdue_jobs = []
        for job in instance_data["jobs"]:
            jid = job["job_id"]
            delivery = job["delivery_time"]
            # 查找该作业的完成时间
            for cj in critical_jobs:
                if cj["job_id"] == jid and cj["finish_time"] > delivery:
                    overdue_jobs.append(jid)
                    break

        if overdue_jobs:
            parts.append(f"注意：作业{', '.join(map(str, overdue_jobs))}的完成时间可能超过交货期，建议优先排程。")
        else:
            parts.append("所有作业均能在交货期内完成。")

        return " ".join(parts)
