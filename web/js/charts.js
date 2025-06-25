// Chart Management for DEAN Evolution Dashboard

class ChartManager {
    constructor() {
        this.charts = new Map();
        this.chartConfigs = {
            fitness: {
                type: 'line',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Generation',
                                color: '#8892b0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#8892b0'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Fitness Score',
                                color: '#8892b0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#8892b0'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#8892b0'
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(30, 33, 57, 0.9)',
                            borderColor: '#64ffda',
                            borderWidth: 1
                        }
                    }
                }
            },
            diversity: {
                type: 'line',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Generation',
                                color: '#8892b0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#8892b0'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Diversity Index',
                                color: '#8892b0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#8892b0'
                            },
                            suggestedMin: 0,
                            suggestedMax: 1
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#8892b0'
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(30, 33, 57, 0.9)',
                            borderColor: '#57cbff',
                            borderWidth: 1
                        },
                        annotation: {
                            annotations: {
                                threshold: {
                                    type: 'line',
                                    yMin: 0.3,
                                    yMax: 0.3,
                                    borderColor: '#ff5757',
                                    borderWidth: 2,
                                    borderDash: [5, 5],
                                    label: {
                                        content: 'Min Threshold',
                                        enabled: true,
                                        position: 'end',
                                        color: '#ff5757',
                                        backgroundColor: 'rgba(255, 87, 87, 0.1)'
                                    }
                                }
                            }
                        }
                    }
                }
            },
            token: {
                type: 'bar',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Generation',
                                color: '#8892b0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#8892b0'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Tokens Used',
                                color: '#8892b0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#8892b0'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#8892b0'
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(30, 33, 57, 0.9)',
                            borderColor: '#ffd93d',
                            borderWidth: 1
                        }
                    }
                }
            },
            pattern: {
                type: 'scatter',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Generation',
                                color: '#8892b0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#8892b0'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Pattern Discoveries',
                                color: '#8892b0'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#8892b0'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#8892b0'
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(30, 33, 57, 0.9)',
                            borderColor: '#64ff8f',
                            borderWidth: 1
                        }
                    }
                }
            }
        };
    }

    // Initialize charts for trial details
    initializeTrialCharts() {
        this.createChart('fitness-chart', 'fitness', {
            labels: [],
            datasets: [
                {
                    label: 'Average Fitness',
                    data: [],
                    borderColor: '#64ffda',
                    backgroundColor: 'rgba(100, 255, 218, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Max Fitness',
                    data: [],
                    borderColor: '#57cbff',
                    backgroundColor: 'rgba(87, 203, 255, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Min Fitness',
                    data: [],
                    borderColor: '#ff5757',
                    backgroundColor: 'rgba(255, 87, 87, 0.1)',
                    tension: 0.4
                }
            ]
        });

        this.createChart('diversity-chart', 'diversity', {
            labels: [],
            datasets: [{
                label: 'Diversity Index',
                data: [],
                borderColor: '#57cbff',
                backgroundColor: 'rgba(87, 203, 255, 0.1)',
                tension: 0.4
            }]
        });

        this.createChart('token-chart', 'token', {
            labels: [],
            datasets: [{
                label: 'Tokens per Generation',
                data: [],
                backgroundColor: 'rgba(255, 217, 61, 0.6)',
                borderColor: '#ffd93d',
                borderWidth: 1
            }]
        });

        this.createChart('pattern-chart', 'pattern', {
            labels: [],
            datasets: [{
                label: 'Patterns Discovered',
                data: [],
                backgroundColor: '#64ff8f',
                borderColor: '#64ff8f',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        });
    }

    // Create a chart
    createChart(canvasId, configType, initialData) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas element ${canvasId} not found`);
            return;
        }

        const ctx = canvas.getContext('2d');
        const config = this.chartConfigs[configType];
        
        const chart = new Chart(ctx, {
            type: config.type,
            data: initialData,
            options: config.options
        });

        this.charts.set(canvasId, chart);
        return chart;
    }

    // Update charts with new data
    updateCharts(data) {
        if (!data.generation_metrics || data.generation_metrics.length === 0) {
            return;
        }

        const latestMetric = data.generation_metrics[data.generation_metrics.length - 1];
        const generation = latestMetric.generation;

        // Update fitness chart
        this.updateFitnessChart(generation, latestMetric);

        // Update diversity chart
        this.updateDiversityChart(generation, latestMetric.diversity_index);

        // Update token chart
        this.updateTokenChart(generation, latestMetric.total_tokens_used);

        // Update pattern chart
        if (latestMetric.patterns_discovered > 0) {
            this.updatePatternChart(generation, latestMetric.patterns_discovered);
        }
    }

    // Update fitness chart
    updateFitnessChart(generation, metrics) {
        const chart = this.charts.get('fitness-chart');
        if (!chart) return;

        // Add generation label if not exists
        if (!chart.data.labels.includes(generation)) {
            chart.data.labels.push(generation);
        }

        // Update datasets
        chart.data.datasets[0].data.push(metrics.avg_fitness);
        chart.data.datasets[1].data.push(metrics.max_fitness);
        chart.data.datasets[2].data.push(metrics.min_fitness);

        // Keep only last 50 points for performance
        if (chart.data.labels.length > 50) {
            chart.data.labels.shift();
            chart.data.datasets.forEach(dataset => dataset.data.shift());
        }

        chart.update('none'); // Update without animation for performance
    }

    // Update diversity chart
    updateDiversityChart(generation, diversityIndex) {
        const chart = this.charts.get('diversity-chart');
        if (!chart) return;

        if (!chart.data.labels.includes(generation)) {
            chart.data.labels.push(generation);
        }

        chart.data.datasets[0].data.push(diversityIndex);

        if (chart.data.labels.length > 50) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update('none');
    }

    // Update token chart
    updateTokenChart(generation, tokensUsed) {
        const chart = this.charts.get('token-chart');
        if (!chart) return;

        if (!chart.data.labels.includes(generation)) {
            chart.data.labels.push(generation);
        }

        chart.data.datasets[0].data.push(tokensUsed);

        if (chart.data.labels.length > 50) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update('none');
    }

    // Update pattern chart
    updatePatternChart(generation, patternsDiscovered) {
        const chart = this.charts.get('pattern-chart');
        if (!chart) return;

        // Add as scatter point
        chart.data.datasets[0].data.push({
            x: generation,
            y: patternsDiscovered
        });

        if (chart.data.datasets[0].data.length > 50) {
            chart.data.datasets[0].data.shift();
        }

        chart.update('none');
    }

    // Clear all charts
    clearCharts() {
        this.charts.forEach(chart => {
            chart.data.labels = [];
            chart.data.datasets.forEach(dataset => {
                dataset.data = [];
            });
            chart.update('none');
        });
    }

    // Destroy all charts
    destroyCharts() {
        this.charts.forEach(chart => {
            chart.destroy();
        });
        this.charts.clear();
    }

    // Load historical data into charts
    loadHistoricalData(generationMetrics) {
        if (!generationMetrics || generationMetrics.length === 0) {
            return;
        }

        // Clear existing data
        this.clearCharts();

        // Load all historical data
        generationMetrics.forEach(metric => {
            this.updateFitnessChart(metric.generation, metric);
            this.updateDiversityChart(metric.generation, metric.diversity_index);
            this.updateTokenChart(metric.generation, metric.total_tokens_used);
            if (metric.patterns_discovered > 0) {
                this.updatePatternChart(metric.generation, metric.patterns_discovered);
            }
        });
    }
}

// Create global chart manager instance
const chartManager = new ChartManager();