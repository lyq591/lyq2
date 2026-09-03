"""
FJSP 遗传算法调度模块
纯Python实现，不依赖numpy
技术方向：工艺规划与车间调度
"""
import random
import copy
import time


class FJSPSolver:
    """柔性作业车间调度问题遗传算法求解器"""

    def __init__(self, jobs_data, num_machines, num_fixtures=0,
                 pop_size=100, max_gen=200, pc=0.8, pm=0.1, seed=None):
        """
        初始化求解器
        :param jobs_data: 作业数据，格式：
            [
              {
                "job_id": 1,
                "operations": [
                  {"eligible_machines": [1,2,3], "processing_times": [10,15,20], "eligible_fixtures": [1,2]},
                  ...
                ]
              },
              ...
            ]
        :param num_machines: 机器数量
        :param num_fixtures: 工装数量
        :param pop_size: 种群大小
        :param max_gen: 最大迭代代数
        :param pc: 交叉概率
        :param pm: 变异概率
        :param seed: 随机种子
        """
        self.jobs = jobs_data
        self.num_jobs = len(jobs_data)
        self.num_machines = num_machines
        self.num_fixtures = num_fixtures
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.pc = pc
        self.pm = pm
        self.rng = random.Random(seed)

        # 预处理：每个作业的工序数
        self.ops_per_job = [len(job["operations"]) for job in jobs_data]
        self.total_ops = sum(self.ops_per_job)

        # 构建操作索引映射：(job_idx, op_idx) -> global_op_idx
        self.op_map = {}
        self.op_info = []  # 每个全局操作的信息
        idx = 0
        for j_idx, job in enumerate(jobs_data):
            for o_idx, op in enumerate(job["operations"]):
                self.op_map[(j_idx, o_idx)] = idx
                self.op_info.append({
                    "job_idx": j_idx,
                    "op_idx": o_idx,
                    "eligible_machines": op["eligible_machines"],
                    "processing_times": op["processing_times"],
                    "eligible_fixtures": op.get("eligible_fixtures", []),
                })
                idx += 1

    def _random_chromosome(self):
        """生成随机染色体：(操作序列, 机器分配)"""
        # 操作序列：每个作业号出现其工序数次
        seq = []
        for j_idx in range(self.num_jobs):
            seq.extend([j_idx] * self.ops_per_job[j_idx])
        self.rng.shuffle(seq)

        # 机器分配：每个全局操作随机选一台可选机器
        machine_assign = []
        for op in self.op_info:
            m_idx = self.rng.randint(0, len(op["eligible_machines"]) - 1)
            machine_assign.append(m_idx)

        return {"seq": seq, "machine_assign": machine_assign}

    def _init_population(self):
        """初始化种群"""
        pop = []
        for _ in range(self.pop_size):
            pop.append(self._random_chromosome())
        return pop

    def decode(self, chromosome):
        """
        解码染色体为调度方案
        返回：makespan, schedule（每台机器的任务列表）, job_schedule（每个作业的工序时间）
        """
        seq = chromosome["seq"]
        machine_assign = chromosome["machine_assign"]

        # 跟踪每个作业下一道工序的索引
        job_op_counter = [0] * self.num_jobs
        # 每台机器的可用时间
        machine_available = [0] * self.num_machines
        # 每个作业的完成时间（上一道工序结束时间）
        job_finish = [0] * self.num_jobs
        # 工装可用时间
        fixture_available = [0] * self.num_fixtures if self.num_fixtures > 0 else []

        # 调度结果
        machine_schedule = [[] for _ in range(self.num_machines)]
        job_schedule = [[] for _ in range(self.num_jobs)]

        for job_idx in seq:
            op_idx = job_op_counter[job_idx]
            job_op_counter[job_idx] += 1

            global_idx = self.op_map[(job_idx, op_idx)]
            op = self.op_info[global_idx]

            # 选择的机器
            m_local = machine_assign[global_idx]
            machine_id = op["eligible_machines"][m_local]
            m_idx = machine_id - 1  # 转为0-based
            proc_time = op["processing_times"][m_local]

            # 选择工装（如果有）
            fixture_id = None
            f_idx = -1
            if op["eligible_fixtures"] and self.num_fixtures > 0:
                # 选最早可用的工装
                best_f = None
                best_time = float('inf')
                for fid in op["eligible_fixtures"]:
                    fi = fid - 1
                    if fi < len(fixture_available) and fixture_available[fi] < best_time:
                        best_time = fixture_available[fi]
                        best_f = fid
                fixture_id = best_f
                f_idx = fixture_id - 1

            # 开始时间 = max(机器可用, 作业上道工序完成, 工装可用)
            start_time = max(machine_available[m_idx], job_finish[job_idx])
            if f_idx >= 0 and f_idx < len(fixture_available):
                start_time = max(start_time, fixture_available[f_idx])

            end_time = start_time + proc_time

            # 更新状态
            machine_available[m_idx] = end_time
            job_finish[job_idx] = end_time
            if f_idx >= 0 and f_idx < len(fixture_available):
                fixture_available[f_idx] = end_time

            # 记录调度
            task = {
                "job_id": job_idx + 1,
                "operation_id": op_idx + 1,
                "machine_id": machine_id,
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "processing_time": proc_time,
                "fixture_id": fixture_id,
            }
            machine_schedule[m_idx].append(task)
            job_schedule[job_idx].append(task)

        makespan = max(machine_available) if machine_available else 0
        return round(makespan, 2), machine_schedule, job_schedule

    def _fitness(self, chromosome):
        """适应度：makespan越小越好，返回1/makespan"""
        makespan, _, _ = self.decode(chromosome)
        return 1.0 / makespan if makespan > 0 else float('inf')

    def _tournament_select(self, pop, fitnesses, k=3):
        """锦标赛选择"""
        best = None
        best_fit = -1
        for _ in range(k):
            idx = self.rng.randint(0, len(pop) - 1)
            if fitnesses[idx] > best_fit:
                best_fit = fitnesses[idx]
                best = pop[idx]
        return copy.deepcopy(best)

    def _crossover_seq(self, p1_seq, p2_seq):
        """操作序列交叉：POX交叉"""
        # 随机划分作业集合
        job_set = list(range(self.num_jobs))
        self.rng.shuffle(job_set)
        split = self.rng.randint(1, self.num_jobs - 1)
        set1 = set(job_set[:split])

        # 子代1：保留p1中set1的位置，其余按p2顺序填充
        c1 = [None] * len(p1_seq)
        for i, j in enumerate(p1_seq):
            if j in set1:
                c1[i] = j
        p2_remaining = [j for j in p2_seq if j not in set1]
        ptr = 0
        for i in range(len(c1)):
            if c1[i] is None:
                c1[i] = p2_remaining[ptr]
                ptr += 1

        # 子代2：保留p2中set1的位置，其余按p1顺序填充
        c2 = [None] * len(p2_seq)
        for i, j in enumerate(p2_seq):
            if j in set1:
                c2[i] = j
        p1_remaining = [j for j in p1_seq if j not in set1]
        ptr = 0
        for i in range(len(c2)):
            if c2[i] is None:
                c2[i] = p1_remaining[ptr]
                ptr += 1

        return c1, c2

    def _crossover_machine(self, p1_ma, p2_ma):
        """机器分配交叉：均匀交叉"""
        c1 = []
        c2 = []
        for i in range(len(p1_ma)):
            if self.rng.random() < 0.5:
                c1.append(p1_ma[i])
                c2.append(p2_ma[i])
            else:
                c1.append(p2_ma[i])
                c2.append(p1_ma[i])
        return c1, c2

    def _mutate_seq(self, seq):
        """操作序列变异：交换两个位置"""
        if len(seq) < 2:
            return seq
        i, j = self.rng.sample(range(len(seq)), 2)
        seq[i], seq[j] = seq[j], seq[i]
        return seq

    def _mutate_machine(self, machine_assign):
        """机器分配变异：随机改变一个操作的机器选择"""
        idx = self.rng.randint(0, len(machine_assign) - 1)
        op = self.op_info[idx]
        num_m = len(op["eligible_machines"])
        if num_m > 1:
            new_m = self.rng.randint(0, num_m - 1)
            while new_m == machine_assign[idx]:
                new_m = self.rng.randint(0, num_m - 1)
            machine_assign[idx] = new_m
        return machine_assign

    def solve(self, verbose=False):
        """
        执行遗传算法求解
        返回：最优调度结果字典
        """
        start_time = time.time()

        # 初始化种群
        pop = self._init_population()
        fitnesses = [self._fitness(ind) for ind in pop]

        best_idx = fitnesses.index(max(fitnesses))
        best_ind = copy.deepcopy(pop[best_idx])
        best_makespan, best_machine_sched, best_job_sched = self.decode(best_ind)
        best_fitness = fitnesses[best_idx]

        history = []

        for gen in range(self.max_gen):
            new_pop = []

            # 精英保留：保留最优个体
            new_pop.append(copy.deepcopy(best_ind))

            while len(new_pop) < self.pop_size:
                # 选择
                p1 = self._tournament_select(pop, fitnesses)
                p2 = self._tournament_select(pop, fitnesses)

                # 交叉
                if self.rng.random() < self.pc:
                    c1_seq, c2_seq = self._crossover_seq(p1["seq"], p2["seq"])
                    c1_ma, c2_ma = self._crossover_machine(p1["machine_assign"], p2["machine_assign"])
                    c1 = {"seq": c1_seq, "machine_assign": c1_ma}
                    c2 = {"seq": c2_seq, "machine_assign": c2_ma}
                else:
                    c1 = copy.deepcopy(p1)
                    c2 = copy.deepcopy(p2)

                # 变异
                if self.rng.random() < self.pm:
                    c1["seq"] = self._mutate_seq(c1["seq"])
                if self.rng.random() < self.pm:
                    c1["machine_assign"] = self._mutate_machine(c1["machine_assign"])
                if self.rng.random() < self.pm:
                    c2["seq"] = self._mutate_seq(c2["seq"])
                if self.rng.random() < self.pm:
                    c2["machine_assign"] = self._mutate_machine(c2["machine_assign"])

                new_pop.append(c1)
                if len(new_pop) < self.pop_size:
                    new_pop.append(c2)

            pop = new_pop[:self.pop_size]
            fitnesses = [self._fitness(ind) for ind in pop]

            # 更新最优
            cur_best_idx = fitnesses.index(max(fitnesses))
            if fitnesses[cur_best_idx] > best_fitness:
                best_fitness = fitnesses[cur_best_idx]
                best_ind = copy.deepcopy(pop[cur_best_idx])
                best_makespan, best_machine_sched, best_job_sched = self.decode(best_ind)

            history.append({
                "generation": gen + 1,
                "best_makespan": best_makespan,
                "avg_makespan": round(1.0 / (sum(fitnesses) / len(fitnesses)), 2) if sum(fitnesses) > 0 else 0,
            })

            if verbose and (gen + 1) % 20 == 0:
                print(f"  Gen {gen+1}/{self.max_gen}: best_makespan={best_makespan}")

        elapsed = round(time.time() - start_time, 2)

        # 计算机器利用率
        machine_utilization = []
        for m_idx, tasks in enumerate(best_machine_sched):
            total_busy = sum(t["processing_time"] for t in tasks)
            util = round(total_busy / best_makespan * 100, 1) if best_makespan > 0 else 0
            machine_utilization.append({
                "machine_id": m_idx + 1,
                "total_busy_time": total_busy,
                "utilization_rate": util,
                "num_tasks": len(tasks),
            })

        return {
            "makespan": best_makespan,
            "machine_schedule": best_machine_sched,
            "job_schedule": best_job_sched,
            "machine_utilization": machine_utilization,
            "convergence_history": history,
            "elapsed_time": elapsed,
            "parameters": {
                "pop_size": self.pop_size,
                "max_gen": self.max_gen,
                "pc": self.pc,
                "pm": self.pm,
            },
        }


def solve_fjsp(instance_data, pop_size=100, max_gen=200, seed=42):
    """
    便捷函数：从实例数据创建求解器并求解
    :param instance_data: JSON格式的实例数据（与data/processed/*.json格式一致）
    :return: 调度结果
    """
    jobs_data = []
    for job in instance_data["jobs"]:
        ops = []
        for op in job["operations"]:
            ops.append({
                "eligible_machines": op["eligible_machines"],
                "processing_times": op["processing_times"],
                "eligible_fixtures": op.get("eligible_fixtures", []),
            })
        jobs_data.append({"job_id": job["job_id"], "operations": ops})

    solver = FJSPSolver(
        jobs_data=jobs_data,
        num_machines=instance_data["scale"]["num_machines"],
        num_fixtures=instance_data["scale"]["num_fixtures"],
        pop_size=pop_size,
        max_gen=max_gen,
        seed=seed,
    )
    return solver.solve()
