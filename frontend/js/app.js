/**
 * FJSP智能调度辅助Agent系统 - 前端应用逻辑
 */

const { createApp, ref, reactive, onMounted, nextTick, watch } = Vue;

const API_BASE = 'http://127.0.0.1:8000/api';

createApp({
    setup() {
        // ==================== 状态 ====================
        const currentPage = ref('dashboard');
        const apiConnected = ref(false);
        const instances = ref([]);
        const scheduling = ref(false);
        const scheduleResult = ref(null);
        const selectedInstance = ref({});
        const showInstanceDetail = ref(false);
        const instanceStats = ref(null);
        const analysisInstance = ref('');
        const bottleneckAnalysis = ref(null);
        const history = ref([]);
        const datasetOverview = ref({});
        const dbStats = ref({});

        // 调度配置
        const scheduleConfig = reactive({
            instance_id: '',
            pop_size: 100,
            max_gen: 200,
            seed: 42,
        });

        // 数字孪生
        const twinInstance = ref('');
        const twinMachines = ref([]);
        const twinJobs = ref([]);
        const twinTime = ref(0);
        const twinMaxTime = ref(0);
        const twinRunning = ref(false);
        let twinTimer = null;
        let twinScheduleData = null;

        // 图表引用
        const ganttChart = ref(null);
        const convergenceChart = ref(null);
        const scaleChart = ref(null);
        const workloadChart = ref(null);
        const twinCanvas = ref(null);

        let ganttChartInst = null;
        let convergenceChartInst = null;
        let scaleChartInst = null;
        let workloadChartInst = null;

        // ==================== API请求 ====================
        async function apiGet(path) {
            try {
                const res = await fetch(API_BASE + path);
                if (res.ok) {
                    apiConnected.value = true;
                    return await res.json();
                }
                apiConnected.value = false;
                return null;
            } catch (e) {
                apiConnected.value = false;
                return null;
            }
        }

        async function apiPost(path, data) {
            try {
                const res = await fetch(API_BASE + path, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });
                if (res.ok) return await res.json();
                const err = await res.json();
                throw new Error(err.detail || '请求失败');
            } catch (e) {
                throw e;
            }
        }

        // ==================== 健康检查 ====================
        async function checkHealth() {
            const data = await apiGet('/health');
            if (data) {
                apiConnected.value = true;
                dbStats.value = data.database_stats || {};
            }
        }

        // ==================== 数据集 ====================
        async function loadInstances() {
            const data = await apiGet('/dataset/instances');
            if (data && data.instances) {
                instances.value = data.instances;
                if (!scheduleConfig.instance_id && data.instances.length > 0) {
                    scheduleConfig.instance_id = data.instances[0].instance_id;
                }
                if (!twinInstance.value && data.instances.length > 0) {
                    twinInstance.value = data.instances[0].instance_id;
                }
            }
        }

        async function viewInstance(instanceId) {
            const data = await apiGet('/dataset/' + instanceId);
            if (data) {
                selectedInstance.value = data;
                showInstanceDetail.value = true;
            }
        }

        function goSchedule(instanceId) {
            scheduleConfig.instance_id = instanceId;
            currentPage.value = 'schedule';
        }

        async function loadDatasetOverview() {
            const data = await apiGet('/dataset/overview');
            if (data) datasetOverview.value = data;
        }

        // ==================== 调度 ====================
        async function runSchedule() {
            if (!scheduleConfig.instance_id) {
                alert('请先选择实例');
                return;
            }
            scheduling.value = true;
            scheduleResult.value = null;
            try {
                const result = await apiPost('/schedule', {
                    instance_id: scheduleConfig.instance_id,
                    pop_size: scheduleConfig.pop_size,
                    max_gen: scheduleConfig.max_gen,
                    seed: scheduleConfig.seed,
                });
                scheduleResult.value = result;
                await nextTick();
                renderGanttChart(result);
                renderConvergenceChart(result);
            } catch (e) {
                alert('调度失败: ' + e.message);
            } finally {
                scheduling.value = false;
            }
        }

        // 甘特图
        function renderGanttChart(result) {
            if (!ganttChart.value) return;
            if (ganttChartInst) ganttChartInst.dispose();
            ganttChartInst = echarts.init(ganttChart.value);

            const colors = ['#1a73e8', '#e53935', '#43a047', '#fb8c00', '#8e24aa',
                           '#00acc1', '#f4511e', '#5e35b1', '#00897b', '#c0ca33',
                           '#546e7a', '#d81b60', '#3949ab', '#7cb342', '#6d4c41',
                           '#00bcd4', '#ff5722', '#673ab7', '#8bc34a', '#795548'];

            const data = [];
            const machineSchedule = result.machine_schedule;
            let maxEnd = 0;

            machineSchedule.forEach((tasks, mIdx) => {
                tasks.forEach(task => {
                    data.push({
                        name: '机器' + task.machine_id,
                        value: [mIdx, task.start_time, task.end_time, task.job_id, task.operation_id],
                        itemStyle: { color: colors[(task.job_id - 1) % colors.length] }
                    });
                    if (task.end_time > maxEnd) maxEnd = task.end_time;
                });
            });

            const yAxisData = machineSchedule.map((_, i) => '机器' + (i + 1));

            ganttChartInst.setOption({
                title: { text: '调度甘特图', left: 'center', textStyle: { fontSize: 14 } },
                tooltip: {
                    formatter: function(params) {
                        const v = params.value;
                        return `作业${v[3]}-工序${v[4]}<br/>机器${v[0]+1}<br/>开始: ${v[1]}<br/>结束: ${v[2]}<br/>时长: ${(v[2]-v[1]).toFixed(1)}`;
                    }
                },
                grid: { left: 60, right: 30, top: 50, bottom: 40 },
                xAxis: { type: 'value', name: '时间', min: 0, max: maxEnd * 1.05 },
                yAxis: { type: 'category', data: yAxisData, inverse: true },
                series: [{
                    type: 'custom',
                    renderItem: function(params, api) {
                        const categoryIndex = api.value(0);
                        const start = api.coord([api.value(1), categoryIndex]);
                        const end = api.coord([api.value(2), categoryIndex]);
                        const height = api.size([0, 1])[1] * 0.6;
                        const rectShape = echarts.graphic.clipRectByRect({
                            x: start[0], y: start[1] - height / 2,
                            width: end[0] - start[0], height: height
                        }, {
                            x: params.coordSys.x, y: params.coordSys.y,
                            width: params.coordSys.width, height: params.coordSys.height
                        });
                        return rectShape && {
                            type: 'rect',
                            shape: rectShape,
                            style: api.style({
                                text: 'J' + api.value(3) + '-O' + api.value(4),
                                font: '10px sans-serif',
                                fill: '#fff',
                            })
                        };
                    },
                    encode: { x: [1, 2], y: 0 },
                    data: data
                }]
            });
        }

        // 收敛曲线
        function renderConvergenceChart(result) {
            if (!convergenceChart.value) return;
            if (convergenceChartInst) convergenceChartInst.dispose();
            convergenceChartInst = echarts.init(convergenceChart.value);

            const history = result.convergence_history || [];
            convergenceChartInst.setOption({
                tooltip: { trigger: 'axis' },
                legend: { data: ['最优Makespan', '平均Makespan'], top: 0 },
                grid: { left: 50, right: 20, top: 30, bottom: 30 },
                xAxis: { type: 'category', name: '迭代代数', data: history.map(h => h.generation) },
                yAxis: { type: 'value', name: 'Makespan' },
                series: [
                    { name: '最优Makespan', type: 'line', data: history.map(h => h.best_makespan), smooth: true, itemStyle: { color: '#1a73e8' } },
                    { name: '平均Makespan', type: 'line', data: history.map(h => h.avg_makespan), smooth: true, itemStyle: { color: '#ff9800' } },
                ]
            });
        }

        // ==================== 数据分析 ====================
        async function loadInstanceStats() {
            if (!analysisInstance.value) return;
            const stats = await apiGet('/dataset/' + analysisInstance.value + '/stats');
            if (stats) {
                instanceStats.value = stats;
                await nextTick();
                renderWorkloadChart(stats);
            }
            const bottlenecks = await apiGet('/dataset/' + analysisInstance.value + '/bottlenecks');
            if (bottlenecks) bottleneckAnalysis.value = bottlenecks;
        }

        function renderScaleChart() {
            if (!scaleChart.value || instances.value.length === 0) return;
            if (scaleChartInst) scaleChartInst.dispose();
            scaleChartInst = echarts.init(scaleChart.value);
            scaleChartInst.setOption({
                tooltip: { trigger: 'axis' },
                legend: { data: ['作业数', '机器数', '工装数'], top: 0 },
                grid: { left: 50, right: 20, top: 30, bottom: 40 },
                xAxis: { type: 'category', name: '实例', data: instances.value.map(i => i.instance_id.replace('FJSP-', '')) },
                yAxis: { type: 'value', name: '数量' },
                series: [
                    { name: '作业数', type: 'bar', data: instances.value.map(i => i.num_jobs), itemStyle: { color: '#1a73e8' } },
                    { name: '机器数', type: 'bar', data: instances.value.map(i => i.num_machines), itemStyle: { color: '#43a047' } },
                    { name: '工装数', type: 'bar', data: instances.value.map(i => i.num_fixtures), itemStyle: { color: '#fb8c00' } },
                ]
            });
        }

        function renderWorkloadChart(stats) {
            if (!workloadChart.value || !stats.machine_workload) return;
            if (workloadChartInst) workloadChartInst.dispose();
            workloadChartInst = echarts.init(workloadChart.value);
            workloadChartInst.setOption({
                tooltip: { trigger: 'axis' },
                grid: { left: 50, right: 20, top: 20, bottom: 30 },
                xAxis: { type: 'category', name: '机器', data: stats.machine_workload.map(m => '机器' + m.machine_id) },
                yAxis: { type: 'value', name: '可选工序数' },
                series: [{
                    type: 'bar',
                    data: stats.machine_workload.map(m => m.eligible_op_count),
                    itemStyle: {
                        color: function(params) {
                            return params.value > (stats.machine_workload.reduce((a,b)=>a+b.eligible_op_count,0)/stats.machine_workload.length)*1.2 ? '#e53935' : '#1a73e8';
                        }
                    },
                    label: { show: true, position: 'top' }
                }]
            });
        }

        // ==================== 数字孪生 ====================
        async function loadTwinData() {
            if (!twinInstance.value) return;
            try {
                const result = await apiPost('/schedule', {
                    instance_id: twinInstance.value,
                    pop_size: 50, max_gen: 100, seed: 42,
                });
                twinScheduleData = result;
                twinMaxTime.value = result.makespan;
                twinTime.value = 0;

                // 初始化机器
                const numMachines = result.machine_schedule.length;
                twinMachines.value = Array.from({ length: numMachines }, (_, i) => ({
                    id: i + 1, status: 'idle', current_job: 0, progress: 0
                }));

                // 初始化作业
                const instanceData = await apiGet('/dataset/' + twinInstance.value);
                if (instanceData) {
                    twinJobs.value = instanceData.jobs.map(j => ({
                        id: j.job_id, status: 'waiting'
                    }));
                }
            } catch (e) {
                alert('加载车间数据失败: ' + e.message);
            }
        }

        function toggleTwinAnimation() {
            if (twinRunning.value) {
                twinRunning.value = false;
                if (twinTimer) clearInterval(twinTimer);
            } else {
                if (!twinScheduleData) {
                    alert('请先加载车间数据');
                    return;
                }
                twinRunning.value = true;
                twinTimer = setInterval(updateTwin, 200);
            }
        }

        function updateTwin() {
            if (!twinScheduleData) return;
            twinTime.value += 1;
            if (twinTime.value > twinMaxTime.value) {
                twinTime.value = twinMaxTime.value;
                twinRunning.value = false;
                if (twinTimer) clearInterval(twinTimer);
                return;
            }

            const t = twinTime.value;
            const machineSchedule = twinScheduleData.machine_schedule;

            machineSchedule.forEach((tasks, mIdx) => {
                const machine = twinMachines.value[mIdx];
                const currentTask = tasks.find(task => task.start_time <= t && task.end_time > t);
                if (currentTask) {
                    machine.status = 'running';
                    machine.current_job = currentTask.job_id;
                    machine.progress = ((t - currentTask.start_time) / (currentTask.end_time - currentTask.start_time)) * 100;
                } else {
                    machine.status = 'idle';
                    machine.current_job = 0;
                    machine.progress = 0;
                }
            });

            // 更新作业状态
            const jobSchedule = twinScheduleData.job_schedule;
            jobSchedule.forEach((tasks, jIdx) => {
                const job = twinJobs.value[jIdx];
                if (!job) return;
                const allDone = tasks.every(task => task.end_time <= t);
                const isRunning = tasks.some(task => task.start_time <= t && task.end_time > t);
                if (allDone) job.status = 'done';
                else if (isRunning) job.status = 'running';
                else job.status = 'waiting';
            });
        }

        // ==================== 调度历史 ====================
        async function loadHistory() {
            const data = await apiGet('/schedule/results?limit=50');
            if (data) history.value = data.tasks || [];
        }

        function formatTime(ts) {
            if (!ts) return '-';
            const d = new Date(ts * 1000);
            return d.toLocaleString('zh-CN');
        }

        // ==================== 页面切换 ====================
        watch(currentPage, async (page) => {
            await nextTick();
            if (page === 'dashboard') {
                await checkHealth();
                await loadDatasetOverview();
            }
            if (page === 'analysis' && instances.value.length > 0) {
                if (!analysisInstance.value) analysisInstance.value = instances.value[0].instance_id;
                await loadInstanceStats();
                renderScaleChart();
            }
        });

        // ==================== 初始化 ====================
        onMounted(async () => {
            await checkHealth();
            await loadInstances();
            await loadDatasetOverview();
            setInterval(checkHealth, 10000);
        });

        return {
            currentPage, apiConnected, instances, scheduling, scheduleResult,
            scheduleConfig, selectedInstance, showInstanceDetail,
            instanceStats, analysisInstance, bottleneckAnalysis,
            history, datasetOverview, dbStats,
            twinInstance, twinMachines, twinJobs, twinTime, twinMaxTime, twinRunning,
            ganttChart, convergenceChart, scaleChart, workloadChart, twinCanvas,
            loadInstances, viewInstance, goSchedule, runSchedule,
            loadInstanceStats, loadHistory, formatTime,
            loadTwinData, toggleTwinAnimation,
        };
    }
}).mount('#app');
