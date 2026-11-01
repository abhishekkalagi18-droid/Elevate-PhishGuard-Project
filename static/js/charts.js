/**
 * PhishGuard Chart Controller
 * Theme-aware Chart.js integration with automatic palette updates on theme change.
 */

window.PhishGuardCharts = (function () {
    let instances = {};

    function getThemeColors() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        return {
            textColor: isDark ? '#94a3b8' : '#64748b',
            gridColor: isDark ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.06)',
            tooltipBg: isDark ? '#1e293b' : '#0f172a',
            tooltipText: isDark ? '#f8fafc' : '#ffffff',
            primary: isDark ? '#60a5fa' : '#2563eb',
            primaryFill: isDark ? 'rgba(96, 165, 250, 0.12)' : 'rgba(37, 99, 235, 0.08)',
            success: isDark ? '#34d399' : '#059669',
            successFill: isDark ? 'rgba(52, 211, 153, 0.12)' : 'rgba(5, 150, 105, 0.08)',
            danger: isDark ? '#f87171' : '#dc2626',
            dangerFill: isDark ? 'rgba(248, 113, 113, 0.12)' : 'rgba(220, 38, 38, 0.08)'
        };
    }

    function initLandingChart(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === 'undefined') return;

        const colors = getThemeColors();
        const ctx = canvas.getContext('2d');

        instances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'],
                datasets: [
                    {
                        label: 'Threat Reporting Rate (%)',
                        data: [12.0, 18.5, 29.0, 38.4, 46.2, 54.8],
                        borderColor: colors.success,
                        backgroundColor: colors.successFill,
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2.5,
                        pointBackgroundColor: colors.success,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Phish-Prone Click Rate (%)',
                        data: [32.4, 28.1, 22.5, 17.8, 14.2, 11.6],
                        borderColor: colors.danger,
                        backgroundColor: colors.dangerFill,
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2.5,
                        pointBackgroundColor: colors.danger,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: colors.textColor,
                            font: { family: 'Inter', size: 12, weight: 500 },
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: colors.tooltipBg,
                        titleColor: colors.tooltipText,
                        bodyColor: colors.tooltipText,
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        grid: { color: colors.gridColor },
                        ticks: { color: colors.textColor, font: { family: 'Inter', size: 11 } }
                    },
                    y: {
                        grid: { color: colors.gridColor },
                        ticks: {
                            color: colors.textColor,
                            font: { family: 'Inter', size: 11 },
                            callback: value => value + '%'
                        },
                        min: 0,
                        max: 60
                    }
                }
            }
        });
    }

    function initAnalyticsCharts() {
        if (typeof Chart === 'undefined') return;
        const colors = getThemeColors();

        // 1. Trend Chart
        const trendCanvas = document.getElementById('analyticsTrendChart');
        if (trendCanvas) {
            instances['analyticsTrendChart'] = new Chart(trendCanvas.getContext('2d'), {
                type: 'line',
                data: {
                    labels: ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'],
                    datasets: [
                        {
                            label: 'Threats Reported (%)',
                            data: [12.0, 18.5, 29.0, 38.4, 46.2, 54.8],
                            borderColor: colors.success,
                            backgroundColor: colors.successFill,
                            fill: true,
                            tension: 0.3
                        },
                        {
                            label: 'Phish-Prone Clicks (%)',
                            data: [32.4, 28.1, 22.5, 17.8, 14.2, 11.6],
                            borderColor: colors.danger,
                            backgroundColor: colors.dangerFill,
                            fill: true,
                            tension: 0.3
                        },
                        {
                            label: 'Training Completed (%)',
                            data: [45.0, 58.2, 70.1, 82.0, 89.5, 94.2],
                            borderColor: colors.primary,
                            borderDash: [5, 5],
                            fill: false,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: colors.textColor } }
                    },
                    scales: {
                        x: { grid: { color: colors.gridColor }, ticks: { color: colors.textColor } },
                        y: {
                            grid: { color: colors.gridColor },
                            ticks: { color: colors.textColor, callback: v => v + '%' },
                            min: 0, max: 100
                        }
                    }
                }
            });
        }

        // 2. Department Comparison Bar Chart
        const deptCanvas = document.getElementById('analyticsDeptChart');
        if (deptCanvas) {
            fetch('/api/charts/departments')
                .then(res => res.json())
                .then(data => {
                    instances['analyticsDeptChart'] = new Chart(deptCanvas.getContext('2d'), {
                        type: 'bar',
                        data: {
                            labels: data.labels,
                            datasets: [
                                {
                                    label: 'Click Rate (%)',
                                    data: data.click_rates,
                                    backgroundColor: colors.danger,
                                    borderRadius: 4
                                },
                                {
                                    label: 'Report Rate (%)',
                                    data: data.report_rates,
                                    backgroundColor: colors.success,
                                    borderRadius: 4
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { labels: { color: colors.textColor } }
                            },
                            scales: {
                                x: { grid: { color: colors.gridColor }, ticks: { color: colors.textColor } },
                                y: {
                                    grid: { color: colors.gridColor },
                                    ticks: { color: colors.textColor, callback: v => v + '%' },
                                    min: 0
                                }
                            }
                        }
                    });
                })
                .catch(err => console.error('Error loading dept chart data:', err));
        }
    }

    // Update charts whenever theme changes
    window.addEventListener('themechange', () => {
        const colors = getThemeColors();
        Object.keys(instances).forEach(id => {
            const chart = instances[id];
            if (chart && chart.options) {
                if (chart.options.scales) {
                    if (chart.options.scales.x) {
                        chart.options.scales.x.grid.color = colors.gridColor;
                        chart.options.scales.x.ticks.color = colors.textColor;
                    }
                    if (chart.options.scales.y) {
                        chart.options.scales.y.grid.color = colors.gridColor;
                        chart.options.scales.y.ticks.color = colors.textColor;
                    }
                }
                if (chart.options.plugins && chart.options.plugins.legend) {
                    chart.options.plugins.legend.labels.color = colors.textColor;
                }
                chart.update();
            }
        });
    });

    return {
        initLandingChart,
        initAnalyticsCharts
    };
})();
