/**
 * FJSP智能调度辅助Agent系统 - 前端应用逻辑
 */

const { createApp, ref, reactive, onMounted, onUnmounted, nextTick, watch } = Vue;

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
        const twinLoading = ref(false);
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
                console.error('API GET error:', path, e);
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
                let errMsg = '请求失败';
                try {
                    const err = await res.json();
                    errMsg = err.detail || errMsg;
                } catch (e) { /* ignore */ }
                throw new Error(errMsg);
            } catch (e) {
                console.error('API POST error:', path, e);
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
            // 销毁旧图表
            if (ganttChartInst) { ganttChartInst.dispose(); ganttChartInst = null; }
            if (convergenceChartInst) { convergenceChartInst.dispose(); convergenceChartInst = null; }

            try {
                console.log('开始调度:', scheduleConfig);
                const result = await apiPost('/schedule', {
                    instance_id: scheduleConfig.instance_id,
                    pop_size: scheduleConfig.pop_size,
                    max_gen: scheduleConfig.max_gen,
                    seed: scheduleConfig.seed,
                });
                console.log('调度结果:', result);
                scheduleResult.value = result;

                // 等待DOM渲染后再初始化图表（v-if条件渲染需要时间）
                await nextTick();
                // 额外延迟确保DOM完全就绪
                await new Promise(r => setTimeout(r, 100));

                if (ganttChart.value) {
                    renderGanttChart(result);
                } else {
                    console.error('甘特图容器未找到');
                }
                if (convergenceChart.value) {
                    renderConvergenceChart(result);
                } else {
                    console.error('收敛曲线容器未找到');
                }
            } catch (e) {
                console.error('调度失败:', e);
                alert('调度失败: ' + e.message);
            } finally {
                scheduling.value = false;
            }
        }

        // 甘特图
        function renderGanttChart(result) {
            try {
                if (!ganttChart.value) {
                    console.error('ganttChart ref is null');
                    return;
                }
                if (ganttChartInst) ganttChartInst.dispose();
                ganttChartInst = echarts.init(ganttChart.value);

                const colors = ['#1a73e8', '#e53935', '#43a047', '#fb8c00', '#8e24aa',
                               '#00acc1', '#f4511e', '#5e35b1', '#00897b', '#c0ca33',
                               '#546e7a', '#d81b60', '#3949ab', '#7cb342', '#6d4c41',
                               '#00bcd4', '#ff5722', '#673ab7', '#8bc34a', '#795548'];

                const data = [];
                const machineSchedule = result.machine_schedule || [];
                let maxEnd = 0;

                machineSchedule.forEach((tasks, mIdx) => {
                    if (!tasks) return;
                    tasks.forEach(task => {
                        data.push({
                            name: '机器' + task.machine_id,
                            value: [mIdx, task.start_time, task.end_time, task.job_id, task.operation_id],
                            itemStyle: { color: colors[(task.job_id - 1) % colors.length] }
                        });
                        if (task.end_time > maxEnd) maxEnd = task.end_time;
                    });
                });

                console.log('甘特图数据条数:', data.length, 'maxEnd:', maxEnd);

                if (data.length === 0) {
                    console.warn('甘特图数据为空');
                    return;
                }

                const yAxisData = machineSchedule.map((_, i) => '机器' + (i + 1));

                ganttChartInst.setOption({
                    title: { text: '调度甘特图', left: 'center', textStyle: { fontSize: 14 } },
                    tooltip: {
                        formatter: function(params) {
                            const v = params.value;
                            if (!v || v.length < 5) return '';
                            return '作业' + v[3] + '-工序' + v[4] + '<br/>机器' + (v[0] + 1) +
                                   '<br/>开始: ' + v[1] + '<br/>结束: ' + v[2] +
                                   '<br/>时长: ' + (v[2] - v[1]).toFixed(1);
                        }
                    },
                    grid: { left: 60, right: 30, top: 50, bottom: 40 },
                    xAxis: { type: 'value', name: '时间', min: 0, max: Math.ceil(maxEnd * 1.05) },
                    yAxis: { type: 'category', data: yAxisData, inverse: true },
                    series: [{
                        type: 'custom',
                        renderItem: function(params, api) {
                            try {
                                const categoryIndex = api.value(0);
                                const startPt = api.coord([api.value(1), categoryIndex]);
                                const endPt = api.coord([api.value(2), categoryIndex]);
                                const height = api.size([0, 1])[1] * 0.6;

                                if (!startPt || !endPt) return null;

                                const rectX = startPt[0];
                                const rectY = startPt[1] - height / 2;
                                const rectW = Math.max(endPt[0] - startPt[0], 1);
                                const rectH = height;

                                return {
                                    type: 'rect',
                                    shape: { x: rectX, y: rectY, width: rectW, height: rectH },
                                    style: api.style({
                                        stroke: '#fff',
                                        lineWidth: 1,
                                    })
                                };
                            } catch (e) {
                                console.error('renderItem error:', e);
                                return null;
                            }
                        },
                        encode: { x: [1, 2], y: 0 },
                        data: data
                    }]
                });

                console.log('甘特图渲染完成');
            } catch (e) {
                console.error('甘特图渲染失败:', e);
            }
        }

        // 收敛曲线
        function renderConvergenceChart(result) {
            try {
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
                        { name: '最优Makespan', type: 'line', data: history.map(h => h.best_makespan), smooth: true, itemStyle: { color: '#1a73e8' }, areaStyle: { opacity: 0.1 } },
                        { name: '平均Makespan', type: 'line', data: history.map(h => h.avg_makespan), smooth: true, itemStyle: { color: '#ff9800' } },
                    ]
                });
            } catch (e) {
                console.error('收敛曲线渲染失败:', e);
            }
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
            const avgLoad = stats.machine_workload.reduce((a, b) => a + b.eligible_op_count, 0) / stats.machine_workload.length;
            workloadChartInst.setOption({
                tooltip: { trigger: 'axis' },
                grid: { left: 50, right: 20, top: 20, bottom: 30 },
                xAxis: { type: 'category', name: '机器', data: stats.machine_workload.map(m => '机器' + m.machine_id) },
                yAxis: { type: 'value', name: '可选工序数' },
                series: [{
                    type: 'bar',
                    data: stats.machine_workload.map(m => ({
                        value: m.eligible_op_count,
                        itemStyle: { color: m.eligible_op_count > avgLoad * 1.2 ? '#e53935' : '#1a73e8' }
                    })),
                    label: { show: true, position: 'top' }
                }]
            });
        }

        // ==================== 数字孪生 ====================
        async function loadTwinData() {
            if (!twinInstance.value) {
                alert('请先选择实例');
                return;
            }
            twinLoading.value = true;
            // 停止之前的动画
            if (twinRunning.value) {
                twinRunning.value = false;
                if (twinTimer) { clearInterval(twinTimer); twinTimer = null; }
            }
            try {
                console.log('加载数字孪生数据:', twinInstance.value);
                const result = await apiPost('/schedule', {
                    instance_id: twinInstance.value,
                    pop_size: 50, max_gen: 100, seed: 42,
                });
                console.log('孪生调度结果:', result.makespan);
                twinScheduleData = result;
                twinMaxTime.value = result.makespan;
                twinTime.value = 0;

                // 初始化机器
                const numMachines = (result.machine_schedule || []).length;
                twinMachines.value = Array.from({ length: numMachines }, (_, i) => ({
                    id: i + 1, status: 'idle', current_job: 0, progress: 0
                }));

                // 初始化作业
                const instanceData = await apiGet('/dataset/' + twinInstance.value);
                if (instanceData && instanceData.jobs) {
                    twinJobs.value = instanceData.jobs.map(j => ({
                        id: j.job_id, status: 'waiting'
                    }));
                }

                console.log('数字孪生数据加载完成，机器数:', numMachines, '作业数:', twinJobs.value.length);
            } catch (e) {
                console.error('加载车间数据失败:', e);
                alert('加载车间数据失败: ' + e.message);
            } finally {
                twinLoading.value = false;
            }
        }

        function toggleTwinAnimation() {
            if (twinRunning.value) {
                twinRunning.value = false;
                if (twinTimer) { clearInterval(twinTimer); twinTimer = null; }
            } else {
                if (!twinScheduleData) {
                    alert('请先点击"加载车间"按钮加载数据');
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
                if (twinTimer) { clearInterval(twinTimer); twinTimer = null; }
                return;
            }

            const t = twinTime.value;
            const machineSchedule = twinScheduleData.machine_schedule || [];

            machineSchedule.forEach((tasks, mIdx) => {
                const machine = twinMachines.value[mIdx];
                if (!machine || !tasks) return;
                const currentTask = tasks.find(task => task.start_time <= t && task.end_time > t);
                if (currentTask) {
                    machine.status = 'running';
                    machine.current_job = currentTask.job_id;
                    const duration = currentTask.end_time - currentTask.start_time;
                    machine.progress = duration > 0 ? ((t - currentTask.start_time) / duration) * 100 : 100;
                } else {
                    machine.status = 'idle';
                    machine.current_job = 0;
                    machine.progress = 0;
                }
            });

            // 更新作业状态
            const jobSchedule = twinScheduleData.job_schedule || [];
            jobSchedule.forEach((tasks, jIdx) => {
                const job = twinJobs.value[jIdx];
                if (!job || !tasks) return;
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

        // ==================== 图表自适应 ====================
        function resizeAllCharts() {
            if (ganttChartInst) ganttChartInst.resize();
            if (convergenceChartInst) convergenceChartInst.resize();
            if (scaleChartInst) scaleChartInst.resize();
            if (workloadChartInst) workloadChartInst.resize();
        }

        // ==================== 页面切换 ====================
        watch(currentPage, async (page) => {
            await nextTick();
            console.log('切换到页面:', page);

            // 确保实例列表已加载
            if (instances.value.length === 0) {
                await loadInstances();
            }

            if (page === 'dashboard') {
                await checkHealth();
                await loadDatasetOverview();
            }
            if (page === 'schedule') {
                // 确保调度实例已选择
                if (!scheduleConfig.instance_id && instances.value.length > 0) {
                    scheduleConfig.instance_id = instances.value[0].instance_id;
                }
            }
            if (page === 'analysis' && instances.value.length > 0) {
                if (!analysisInstance.value) analysisInstance.value = instances.value[0].instance_id;
                await nextTick();
                await loadInstanceStats();
                renderScaleChart();
            }
            if (page === 'digitaltwin') {
                // 确保数字孪生实例已选择
                if (!twinInstance.value && instances.value.length > 0) {
                    twinInstance.value = instances.value[0].instance_id;
                }
            }
            if (page === 'history') {
                await loadHistory();
            }

            // 页面切换后延迟resize图表
            setTimeout(resizeAllCharts, 200);
        });

        // ==================== 初始化 ====================
        onMounted(async () => {
            console.log('应用已挂载');
            await checkHealth();
            await loadInstances();
            await loadDatasetOverview();
            setInterval(checkHealth, 10000);
            window.addEventListener('resize', resizeAllCharts);
        });

        onUnmounted(() => {
            window.removeEventListener('resize', resizeAllCharts);
            if (twinTimer) clearInterval(twinTimer);
            if (ganttChartInst) ganttChartInst.dispose();
            if (convergenceChartInst) convergenceChartInst.dispose();
            if (scaleChartInst) scaleChartInst.dispose();
            if (workloadChartInst) workloadChartInst.dispose();
        });

        return {
            currentPage, apiConnected, instances, scheduling, scheduleResult,
            scheduleConfig, selectedInstance, showInstanceDetail,
            instanceStats, analysisInstance, bottleneckAnalysis,
            history, datasetOverview, dbStats,
            twinInstance, twinMachines, twinJobs, twinTime, twinMaxTime, twinRunning, twinLoading,
            ganttChart, convergenceChart, scaleChart, workloadChart, twinCanvas,
            loadInstances, viewInstance, goSchedule, runSchedule,
            loadInstanceStats, loadHistory, formatTime,
            loadTwinData, toggleTwinAnimation,
        };
    }
}).mount('#app');
