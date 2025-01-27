let activityChart, usersChart, mentionsChart;

function getChartColors() {
    const style = getComputedStyle(document.documentElement);
    return {
        primary: `hsl(${style.getPropertyValue('--primary')})`,
        muted: `hsl(${style.getPropertyValue('--muted')})`,
        mutedForeground: `hsl(${style.getPropertyValue('--muted-foreground')})`,
        border: `hsl(${style.getPropertyValue('--border')})`,
        background: `hsl(${style.getPropertyValue('--background')})`,
        foreground: `hsl(${style.getPropertyValue('--foreground')})`,
    };
}

const commonChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'bottom',
            labels: {
                padding: 20,
                usePointStyle: true,
                pointStyle: 'circle',
                font: {
                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
                    size: 12,
                },
                color: '#5d5e5d',
            }
        },
        tooltip: {
            backgroundColor: getChartColors().background,
            titleColor: '#5d5e5d',
            bodyColor: '#5d5e5d',
            borderColor: getChartColors().border,
            borderWidth: 1,
            padding: 12,
            cornerRadius: 8,
            titleFont: {
                size: 14,
                weight: 'medium'
            },
            bodyFont: {
                size: 13
            },
            displayColors: false
        }
    }
};

function createGradient(ctx, color) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, color);
    gradient.addColorStop(1, color + '20'); 
    return gradient;
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
}

async function loadServerStats() {
    const response = await fetch('/get_server_stats');
    const data = await response.json();
    const colors = getChartColors();

    document.getElementById('total-messages').textContent = data.overview.total_messages.toLocaleString();
    document.getElementById('total-reactions').textContent = data.overview.total_reactions.toLocaleString();
    document.getElementById('total-voice-time').textContent = formatDuration(data.overview.total_voice_time);
    document.getElementById('active-users').textContent = data.overview.active_users.toLocaleString();

    if (activityChart) activityChart.destroy();
    const activityCtx = document.getElementById('activity-chart').getContext('2d');
    activityChart = new Chart(activityCtx, {
        type: 'doughnut',
        data: {
            labels: ['Messages', 'Reactions', 'Voice (hours)', 'Stream (hours)', 'Deafen (hours)'],
            datasets: [{
                data: [
                    data.overview.total_messages,
                    data.overview.total_reactions,
                    Math.round(data.overview.total_voice_time / 3600 * 10) / 10,
                    Math.round(data.overview.total_stream_time / 3600 * 10) / 10,
                    Math.round(data.overview.total_deafen_time / 3600 * 10) / 10
                ],
                backgroundColor: [
                    'hsl(221, 83%, 53%)',
                    'hsl(142, 71%, 45%)',
                    'hsl(262, 83%, 58%)',
                    'hsl(31, 97%, 44%)',
                    'hsl(346, 87%, 43%)'
                ],
                borderWidth: 2,
                borderColor: colors.background
            }]
        },
        options: {
            ...commonChartOptions,
            cutout: '75%',
            plugins: {
                ...commonChartOptions.plugins,
                legend: {
                    ...commonChartOptions.plugins.legend,
                    position: 'bottom'
                },
                tooltip: {
                    ...commonChartOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const label = context.label.split(' ')[0];
                            if (label === 'Messages' || label === 'Reactions') {
                                return `${label}: ${value.toLocaleString()}`;
                            } else {
                                return `${label}: ${value.toLocaleString()} hours`;
                            }
                        }
                    }
                }
            }
        }
    });

    // Update top users chart
    if (usersChart) usersChart.destroy();
    const usersCtx = document.getElementById('users-chart').getContext('2d');
    
    const userData = data.top_users.map(user => ({
        username: user.username || `User ${user.user_id}`,
        score: Math.round(user.activity_score),
        details: {
            messages: user.messages_sent,
            reactions: user.reactions_added,
            voiceHours: Math.round(user.voice_time / 3600 * 10) / 10,
            streamHours: Math.round(user.stream_time / 3600 * 10) / 10
        }
    }));
    
    usersChart = new Chart(usersCtx, {
        type: 'bar',
        data: {
            labels: userData.map(user => user.username),
            datasets: [{
                label: 'Activity Score',
                data: userData.map(user => user.score),
                backgroundColor: 'hsl(221, 83%, 53%)',
                borderRadius: 6,
                borderSkipped: false,
                barThickness: 20,
                maxBarThickness: 30
            }]
        },
        options: {
            ...commonChartOptions,
            plugins: {
                ...commonChartOptions.plugins,
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const user = userData[context.dataIndex];
                            return [
                                `Activity Score: ${user.score}`,
                                `Messages: ${user.details.messages.toLocaleString()}`,
                                `Reactions: ${user.details.reactions.toLocaleString()}`,
                                `Voice Time: ${user.details.voiceHours}h`,
                                `Stream Time: ${user.details.streamHours}h`
                            ];
                        }
                    }
                }
            }
        }
    });

    // Update mentions chart
    if (mentionsChart) mentionsChart.destroy();
    const mentionsCtx = document.getElementById('mentions-chart').getContext('2d');
    mentionsChart = new Chart(mentionsCtx, {
        type: 'bar',
        data: {
            labels: data.mentions.map(mention => mention.display_name),
            datasets: [{
                label: 'Mentions',
                data: data.mentions.map(mention => mention.total_mentions),
                backgroundColor: 'hsl(262, 83%, 58%)',
                borderRadius: 6,
                borderSkipped: false,
                barThickness: 20,
                maxBarThickness: 30
            }]
        },
        options: {
            ...commonChartOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    border: {
                        display: false
                    },
                    grid: {
                        color: colors.border,
                        drawBorder: false,
                        lineWidth: 0.5
                    },
                    ticks: {
                        color: '#5d5e5d',
                        padding: 10,
                        font: {
                            size: 12
                        },
                        stepSize: 1,
                        callback: function(value) {
                            if (Math.floor(value) === value) {
                                return value;
                            }
                        }
                    }
                },
                x: {
                    border: {
                        display: false
                    },
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#5d5e5d',
                        padding: 10,
                        font: {
                            size: 12
                        },
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            },
            plugins: {
                ...commonChartOptions.plugins,
                legend: {
                    display: false
                },
                tooltip: {
                    ...commonChartOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y} mentions`;
                        }
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
}