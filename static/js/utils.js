function switchTab(tab) {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    document.querySelector(`[onclick="switchTab('${tab}')"]`).classList.add('active');

    if (tab === 'overview') {
        document.getElementById('overview-tab').classList.remove('hidden');
        document.getElementById('customize-tab').classList.add('hidden');
        document.getElementById('card-editor-tab').classList.add('hidden');
        loadServerStats();
    } else if (tab === 'customize') {
        document.getElementById('overview-tab').classList.add('hidden');
        document.getElementById('customize-tab').classList.remove('hidden');
        document.getElementById('card-editor-tab').classList.add('hidden');
    } else {
        document.getElementById('overview-tab').classList.add('hidden');
        document.getElementById('customize-tab').classList.add('hidden');
        document.getElementById('card-editor-tab').classList.remove('hidden');
    }
}

async function selectServer(guildId) {
    const response = await fetch('/select_guild', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ guild_id: guildId }),
    });
    const result = await response.json();
    if (result.success) {
        const addBotButton = document.querySelector('a[href="{{ url_for("add_bot") }}"]');
        const buttonText = addBotButton.querySelector('.animated-text-fill');
        
        const wasDisabled = addBotButton.classList.contains('btn-disabled');
        const willBeDisabled = result.bot_in_server;
        
        if (wasDisabled !== willBeDisabled) {
            buttonText.classList.add('text-changing');

            await new Promise(resolve => setTimeout(resolve, 300));
            
            if (result.bot_in_server) {
                addBotButton.classList.add('btn-disabled');
                addBotButton.setAttribute('onclick', 'return false;');
                buttonText.setAttribute('data-text', 'Bot Already in Server');
                buttonText.textContent = 'Bot Already in Server';
            } else {
                addBotButton.classList.remove('btn-disabled');
                addBotButton.removeAttribute('onclick');
                buttonText.setAttribute('data-text', 'Add Bot');
                buttonText.textContent = 'Add Bot';
            }
            
            buttonText.classList.remove('text-changing');
            buttonText.classList.add('text-changed');
            
            setTimeout(() => {
                buttonText.classList.remove('text-changed');
            }, 300);
        }
        
        loadServerStats();
        loadDefaults(); 
        loadCardSettings();  
    } else {
        alert('Failed to select server.');
    }
}

async function loadDefaults() {
    try {
        const response = await fetch('/get_default_traits');
        const traits = await response.json();
        
        const traitType = document.getElementById('trait-type').value;
        const traitSelect = document.getElementById('trait-name');
        traitSelect.innerHTML = '';  
        
        const selectedTraits = traits[traitType] || {};
        
        Object.entries(selectedTraits).forEach(([name, thresholds]) => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            traitSelect.appendChild(option);
        });

        if (traitSelect.options.length > 0) {
            traitSelect.dispatchEvent(new Event('change'));
        }
    } catch (error) {
        console.error('Error loading traits:', error);
        showToast('Failed to load traits', 'error');
    }
}

document.getElementById('trait-type').addEventListener('change', loadDefaults);

document.getElementById('trait-name').addEventListener('change', function() {
    const traitType = document.getElementById('trait-type').value;
    const traitName = this.value;
    
    fetch('/get_default_traits')
        .then(response => response.json())
        .then(traits => {
            const selectedTrait = traits[traitType][traitName];
            if (selectedTrait) {
                // Use the description from the trait data if available, otherwise fall back to traitDescriptions
                const description = selectedTrait.description || traitDescriptions[traitType]?.[traitName] || "Custom trait";
                document.getElementById('trait-description').textContent = description;
                document.getElementById('trait-description-input').value = description;
                
                document.getElementById('new-name').value = traitName;  
                document.getElementById('message-ratio').value = selectedTrait.message_ratio || '';
                document.getElementById('message-threshold').value = selectedTrait.message_threshold || '';
                document.getElementById('reaction-threshold').value = selectedTrait.reaction_threshold || '';
                document.getElementById('voice-ratio').value = selectedTrait.voice_ratio || '';
                document.getElementById('voice-threshold').value = selectedTrait.voice_threshold || '';
                document.getElementById('stream-threshold').value = selectedTrait.stream_threshold || '';
                document.getElementById('deafen-ratio').value = selectedTrait.deafen_ratio || '';
                document.getElementById('deafen-threshold').value = selectedTrait.deafen_threshold || '';
            }
        })
        .catch(error => {
            console.error('Error loading trait details:', error);
            showToast('Failed to load trait details', 'error');
        });
});

async function updateTrait() {
    const thresholds = {
        message_ratio: parseFloat(document.getElementById('message-ratio').value) || null,
        message_threshold: parseInt(document.getElementById('message-threshold').value) || null,
        reaction_threshold: parseInt(document.getElementById('reaction-threshold').value) || null,
        voice_ratio: parseFloat(document.getElementById('voice-ratio').value) || null,
        voice_threshold: parseInt(document.getElementById('voice-threshold').value) || null,
        stream_threshold: parseInt(document.getElementById('stream-threshold').value) || null,
        deafen_ratio: parseFloat(document.getElementById('deafen-ratio').value) || null,
        deafen_threshold: parseInt(document.getElementById('deafen-threshold').value) || null
    };

    try {
        const response = await fetch('/update_traits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                trait_type: document.getElementById('trait-type').value,
                trait_name: document.getElementById('trait-name').value,
                new_name: document.getElementById('new-name').value,
                description: document.getElementById('trait-description-input').value,
                thresholds: thresholds
            }),
        });

        const result = await response.json();
        if (result.success) {
            showToast('Trait updated successfully!', 'success');
            await loadDefaults();
        } else {
            showToast(result.error || 'Failed to update trait', 'error');
        }
    } catch (error) {
        console.error('Error updating trait:', error);
        showToast('Failed to update trait', 'error');
    }
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateThemeIcon(theme);
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    if (theme === 'dark') {
        icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>';
    } else {
        icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>';
    }
}

const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
    setTheme(savedTheme);
} else {
    setTheme(prefersDark.matches ? 'dark' : 'light');
}

prefersDark.addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light');
    }
});

document.getElementById('theme-toggle').addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    setTheme(currentTheme === 'dark' ? 'light' : 'dark');
});

document.getElementById('reset-traits').addEventListener('click', async () => {
    if (!confirm('Are you sure you want to reset all traits to their default values? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/reset_traits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to reset traits');
        }

        document.getElementById('new-name').value = '';
        document.getElementById('message-ratio').value = '';
        document.getElementById('message-threshold').value = '';
        document.getElementById('reaction-threshold').value = '';
        document.getElementById('voice-ratio').value = '';
        document.getElementById('voice-threshold').value = '';
        document.getElementById('stream-threshold').value = '';
        document.getElementById('deafen-ratio').value = '';
        document.getElementById('deafen-threshold').value = '';

        await loadDefaults();
        showToast('Traits have been reset to default values', 'success');
    } catch (error) {
        console.error('Error resetting traits:', error);
        showToast('Failed to reset traits', 'error');
    }
});

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastExit 0.2s ease forwards';
        setTimeout(() => {
            if (container.contains(toast)) {
                container.removeChild(toast);
            }
        }, 200);
    }, 3000);
}

function toggleCreateForm(show) {
    const form = document.getElementById('create-trait-form');
    if (show) {
        form.classList.remove('hidden');
        document.getElementById('new-trait-name').value = '';
        document.getElementById('new-message-ratio').value = '';
        document.getElementById('new-message-threshold').value = '';
        document.getElementById('new-reaction-threshold').value = '';
        document.getElementById('new-voice-ratio').value = '';
        document.getElementById('new-voice-threshold').value = '';
        document.getElementById('new-stream-threshold').value = '';
        document.getElementById('new-deafen-ratio').value = '';
        document.getElementById('new-deafen-threshold').value = '';
    } else {
        form.classList.add('hidden');
    }
}

document.getElementById('create-trait').addEventListener('click', () => {
    toggleCreateForm(true);
});

async function createTrait() {
    const thresholds = {
        message_ratio: parseFloat(document.getElementById('new-message-ratio').value) || null,
        message_threshold: parseInt(document.getElementById('new-message-threshold').value) || null,
        reaction_threshold: parseInt(document.getElementById('new-reaction-threshold').value) || null,
        voice_ratio: parseFloat(document.getElementById('new-voice-ratio').value) || null,
        voice_threshold: parseInt(document.getElementById('new-voice-threshold').value) || null,
        stream_threshold: parseInt(document.getElementById('new-stream-threshold').value) || null,
        deafen_ratio: parseFloat(document.getElementById('new-deafen-ratio').value) || null,
        deafen_threshold: parseInt(document.getElementById('new-deafen-threshold').value) || null
    };

    try {
        const response = await fetch('/create_trait', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                trait_type: document.getElementById('new-trait-type').value,
                trait_name: document.getElementById('new-trait-name').value,
                description: document.getElementById('new-trait-description').value,
                thresholds: thresholds
            }),
        });

        const result = await response.json();
        if (result.success) {
            showToast('New trait created successfully!', 'success');
            toggleCreateForm(false);
            await loadDefaults();
        } else {
            showToast(result.error || 'Failed to create trait', 'error');
        }
    } catch (error) {
        console.error('Error creating trait:', error);
        showToast('Failed to create trait', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    function updateRangeProgress(input) {
        const min = input.min || 0;
        const max = input.max || 100;
        const value = input.value;
        const percentage = ((value - min) / (max - min)) * 100;
        input.style.setProperty('--range-progress', `${percentage}%`);
    }

    const animationSpeedInput = document.getElementById('animation-speed');
    const animationSpeedValue = document.getElementById('animation-speed-value');
    updateRangeProgress(animationSpeedInput);
    animationSpeedInput.addEventListener('input', (e) => {
        animationSpeedValue.textContent = `${e.target.value}x`;
        updateRangeProgress(e.target);
    });

    const waveIntensityInput = document.getElementById('wave-intensity');
    const waveIntensityValue = document.getElementById('wave-intensity-value');
    updateRangeProgress(waveIntensityInput);
    waveIntensityInput.addEventListener('input', (e) => {
        waveIntensityValue.textContent = `${Math.round(e.target.value * 100)}%`;
        updateRangeProgress(e.target);
    });

    const fontSizeInput = document.getElementById('font-size');
    const fontSizeValue = document.getElementById('font-size-value');
    updateRangeProgress(fontSizeInput);
    fontSizeInput.addEventListener('input', (e) => {
        fontSizeValue.textContent = `${e.target.value}px`;
        updateRangeProgress(e.target);
    });

    const colorPaletteSelect = document.getElementById('color-palette');
    const useIndividualColorsCheckbox = document.getElementById('use-individual-colors');
    const statColorGroups = document.querySelectorAll('.stat-color-group');
    
    colorPaletteSelect.addEventListener('change', (e) => {
        if (e.target.value === 'custom') {
            useIndividualColorsCheckbox.checked = true;
            toggleIndividualColors(true);
        } else {
            useIndividualColorsCheckbox.checked = false;
            toggleIndividualColors(false);
            updateStatColors(COLOR_PALETTES[e.target.value]);
        }
        updatePreview();
    });
    
    useIndividualColorsCheckbox.addEventListener('change', (e) => {
        toggleIndividualColors(e.target.checked);
        if (e.target.checked) {
            colorPaletteSelect.value = 'custom';
        }
        updatePreview();
    });

    const textColorInput = document.getElementById('text-color');
    const textColorHexInput = document.getElementById('text-color-hex');
    
    textColorInput.addEventListener('input', (e) => {
        textColorHexInput.value = e.target.value.toUpperCase();
        cardEditorState.textColor = e.target.value;
        debouncedUpdatePreview();
    });
    
    textColorHexInput.addEventListener('input', (e) => {
        let value = e.target.value;
        if (value.startsWith('#')) {
            value = value.slice(1);
        }
        if (/^[0-9A-Fa-f]{6}$/.test(value)) {
            const color = '#' + value;
            textColorInput.value = color;
            cardEditorState.textColor = color;
            debouncedUpdatePreview();
        }
    });

    const colorInputs = document.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
        input.addEventListener('mouseover', () => {
            input.style.transform = 'scale(1.05)';
            input.style.transition = 'transform 0.2s ease';
        });
        input.addEventListener('mouseout', () => {
            input.style.transform = 'scale(1)';
        });
    });
});

function toggleIndividualColors(enabled) {
    cardEditorState.useIndividualColors = enabled;
    const statColorGroups = document.querySelectorAll('.stat-color-group');
    const statColorInputs = document.querySelectorAll('.stat-color');
    
    statColorGroups.forEach(group => {
        group.style.opacity = enabled ? '1' : '0.5';
        group.style.transition = 'opacity 0.3s ease';
    });
    
    statColorInputs.forEach(input => {
        input.disabled = !enabled;
        input.style.cursor = enabled ? 'pointer' : 'not-allowed';
    });
}

function updateStatColors(palette) {
    const statColorInputs = document.querySelectorAll('.stat-color');
    
    statColorInputs.forEach(input => {
        const statType = input.dataset.stat;
        input.value = palette[statType];
        cardEditorState.statColors[statType] = palette[statType];
        
        input.style.transition = 'background-color 0.3s ease';
    });
}

async function loadCardSettings() {
    try {
        const response = await fetch('/api/get-card-settings');
        const settings = await response.json();
        
        document.getElementById('color-palette').value = settings.colorPalette;
        document.getElementById('use-individual-colors').checked = settings.useIndividualColors;
        document.getElementById('text-color').value = settings.textColor;
        document.getElementById('text-color-hex').value = settings.textColor;
        document.getElementById('animation-speed').value = settings.animationSpeed;
        document.getElementById('wave-intensity').value = settings.waveIntensity;
        document.getElementById('font-size').value = settings.fontSize;
        
        if (settings.useIndividualColors && settings.statColors) {
            Object.entries(settings.statColors).forEach(([stat, color]) => {
                const input = document.querySelector(`.stat-color[data-stat="${stat}"]`);
                if (input) {
                    input.value = color;
                }
            });
        }

        toggleIndividualColors(settings.useIndividualColors);
        
        document.getElementById('animation-speed-value').textContent = `${settings.animationSpeed}x`;
        document.getElementById('wave-intensity-value').textContent = `${Math.round(settings.waveIntensity * 100)}%`;
        document.getElementById('font-size-value').textContent = `${settings.fontSize}px`;
        
        updateRangeProgress(document.getElementById('animation-speed'));
        updateRangeProgress(document.getElementById('wave-intensity'));
        updateRangeProgress(document.getElementById('font-size'));
        
        cardEditorState = {
            ...cardEditorState,
            colorPalette: settings.colorPalette,
            useIndividualColors: settings.useIndividualColors,
            statColors: settings.statColors || {},
            textColor: settings.textColor,
            animationSpeed: settings.animationSpeed,
            waveIntensity: settings.waveIntensity,
            fontSize: settings.fontSize
        };
        
        await updatePreview();
    } catch (error) {
        console.error('Error loading card settings:', error);
        showToast('Failed to load card settings', 'error');
    }
}

function updateRangeProgress(input) {
    const min = input.min || 0;
    const max = input.max || 100;
    const value = input.value;
    const percentage = ((value - min) / (max - min)) * 100;
    input.style.setProperty('--range-progress', `${percentage}%`);
}

window.onload = () => {
    loadServerStats();
    loadDefaults();
    loadCardSettings();  
};