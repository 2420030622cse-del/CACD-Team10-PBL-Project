// Charts configuration using Chart.js

let lengthGrowthChart = null;
let progressTraceChart = null;
let profileRadarChart = null;
let methodComparisonChart = null;

// Helper to determine base alphabet size
function getBaseForType(ptype) {
    if (ptype === 'PIN') return 10;
    return 94;
}

// 1. RENDER SEARCH SPACE GROWTH (LINE CHART, LOGARITHMIC)
function renderLengthGrowthChart(canvasId, ptype) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return;
    
    if (lengthGrowthChart) {
        lengthGrowthChart.destroy();
    }

    const base = getBaseForType(ptype);
    const labels = [];
    const data = [];

    // PIN is special: we only show PIN size or length growth for digits
    const maxLen = ptype === 'PIN' ? 10 : 12;
    const minLen = 4;

    for (let l = minLen; l <= maxLen; l++) {
        labels.push(`L=${l}`);
        data.push(Math.pow(base, l));
    }

    lengthGrowthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `Search Space Size (${ptype})`,
                data: data,
                borderColor: '#00f0ff',
                backgroundColor: 'rgba(0, 240, 255, 0.05)',
                borderWidth: 2,
                pointBackgroundColor: '#00f0ff',
                pointHoverRadius: 6,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'logarithmic',
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value) {
                            return value.toExponential(0);
                        }
                    },
                    title: {
                        display: true,
                        text: 'Total Combinations (Log Scale)',
                        color: '#94a3b8',
                        font: { size: 10 }
                    }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let val = context.raw;
                            return `Combinations: ${val.toLocaleString()}`;
                        }
                    }
                }
            }
        }
    });
}

// 2. RENDER REAL-TIME PROGRESS TRACE CHART
function initProgressTraceChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return null;
    
    if (progressTraceChart) {
        progressTraceChart.destroy();
    }

    progressTraceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [0],
            datasets: [{
                label: 'Attempts Checked',
                data: [0],
                borderColor: '#ab20fd',
                backgroundColor: 'rgba(171, 32, 253, 0.05)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 200 },
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' },
                    title: { display: true, text: 'Total Attempts', color: '#94a3b8', font: { size: 10 } }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' },
                    title: { display: true, text: 'Elapsed Time (Seconds)', color: '#94a3b8', font: { size: 10 } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
    
    return progressTraceChart;
}

function updateProgressTraceChart(elapsedSec, attemptsCount) {
    if (!progressTraceChart) return;
    
    progressTraceChart.data.labels.push(elapsedSec.toFixed(1));
    progressTraceChart.data.datasets[0].data.push(attemptsCount);
    
    // Keep standard visible history of data points to avoid crowding
    if (progressTraceChart.data.labels.length > 30) {
        progressTraceChart.data.labels.shift();
        progressTraceChart.data.datasets[0].data.shift();
    }
    
    progressTraceChart.update('none'); // Update without full re-render animations for speed
}

// 3. RENDER AI SECURITY PROFILE RADAR CHART
function renderRadarProfileChart(ratings) {
    const ctx = document.getElementById('profileRadarChart');
    if (!ctx || typeof Chart === 'undefined') return;
    
    if (profileRadarChart) {
        profileRadarChart.destroy();
    }

    profileRadarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Strength', 'Memorability', 'Randomness', 'Pattern Safety', 'Usability'],
            datasets: [{
                label: 'Password Dimension Score',
                data: [
                    ratings.security_strength,
                    ratings.memorability,
                    ratings.randomness,
                    ratings.pattern_safety,
                    ratings.typing_usability
                ],
                borderColor: '#ab20fd',
                backgroundColor: 'rgba(171, 32, 253, 0.25)',
                borderWidth: 2,
                pointBackgroundColor: '#ab20fd',
                pointBorderColor: '#fff',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    pointLabels: { color: '#94a3b8', font: { size: 11, weight: '500' } },
                    ticks: {
                        color: '#94a3b8',
                        backdropColor: 'transparent',
                        font: { size: 8 }
                    },
                    suggestedMin: 0,
                    suggestedMax: 10
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// 4. RENDER METHOD COMPARISON BAR CHART (BAR, LOG SCALE)
function renderMethodComparisonChart(comparisonData) {
    const ctx = document.getElementById('methodComparisonChart');
    if (!ctx || typeof Chart === 'undefined') return;
    
    if (methodComparisonChart) {
        methodComparisonChart.destroy();
    }

    methodComparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: comparisonData.methods,
            datasets: [
                {
                    label: 'Attempts Until Match or Exhaustion',
                    data: comparisonData.attempts_needed,
                    backgroundColor: [
                        'rgba(255, 0, 60, 0.75)',    // BF (Red)
                        'rgba(0, 240, 255, 0.75)',   // Dict (Cyan)
                        'rgba(255, 183, 0, 0.75)',   // Rule (Yellow)
                        'rgba(182, 70, 255, 0.75)'   // Hybrid (Purple)
                    ],
                    borderColor: [
                        '#ff003c', '#00f0ff', '#ffb700', '#b646ff'
                    ],
                    borderWidth: 1.5,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', // Horizontal bars
            scales: {
                x: {
                    type: 'logarithmic',
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value) {
                            return value.toExponential(0);
                        }
                    },
                    title: { display: true, text: 'Total Attempts Required (Log scale)', color: '#94a3b8', font: { size: 10 } }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { weight: 'bold' } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        afterBody: function(items) {
                            const index = items[0].dataIndex;
                            const found = comparisonData.found[index];
                            return found ? "✓ Cracks Password" : "✗ Candidate list exhausted";
                        },
                        label: function(context) {
                            return `Attempts: ${context.raw.toLocaleString()}`;
                        }
                    }
                }
            }
        }
    });
}
