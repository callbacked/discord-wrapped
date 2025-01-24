let cardEditorState = {
    colorPalette: 'default',
    useIndividualColors: false,
    statColors: {
        messages: '#5865F2',  // Discord Blurple
        reactions: '#57F287', // Vibrant Green
        voice: '#EB459E',     // Deep Pink
        deafen: '#FFA500',    // Warm Orange
        stream: '#3498db',    // Light Blue
        mentions: '#FEE75C',  // Golden Yellow
        replies: '#ED4245'    // Soft Red
    },
    textColor: '#FFFFFF',
    animationSpeed: 1,
    waveIntensity: 0.5,
    fontSize: 24,
    cardStyle: 'default'  
};

function getCardEditorState() {
    return {
        colorPalette: cardEditorState.colorPalette,
        useIndividualColors: cardEditorState.useIndividualColors,
        statColors: cardEditorState.statColors,
        textColor: cardEditorState.textColor,
        animationSpeed: cardEditorState.animationSpeed,
        waveIntensity: cardEditorState.waveIntensity,
        fontSize: cardEditorState.fontSize,
        cardStyle: cardEditorState.cardStyle
    };
}

const COLOR_PALETTES = {
    default: {
        messages: '#5865F2',  // Discord Blurple
        reactions: '#57F287', // Vibrant Green
        voice: '#EB459E',     // Deep Pink
        deafen: '#FFA500',    // Warm Orange
        stream: '#3498db',    // Light Blue
        mentions: '#FEE75C',  // Golden Yellow
        replies: '#ED4245'    // Soft Red
    },
    spotify: {
        messages: '#1DB954',  // Spotify Green
        reactions: '#1ED760', // Lighter Green
        voice: '#2EBD59',     // Alt Green
        deafen: '#1AA34A',    // Dark Green
        stream: '#1DB954',    // Main Green
        mentions: '#1ED760',  // Bright Green
        replies: '#1AA34A'    // Deep Green
    },
    pastel: {
        messages: '#FFB5E8',  // Pastel Pink
        reactions: '#B5DEFF', // Pastel Blue
        voice: '#E7FFAC',     // Pastel Green
        deafen: '#FFC9DE',    // Light Pink
        stream: '#A79AFF',    // Pastel Purple
        mentions: '#FFABAB',  // Pastel Red
        replies: '#85E3FF'    // Light Blue
    },
    neon: {
        messages: '#FF1B8D',  // Neon Pink
        reactions: '#00FF9F', // Neon Green
        voice: '#00F3FF',     // Neon Blue
        deafen: '#FF8400',    // Neon Orange
        stream: '#FF00FF',    // Neon Purple
        mentions: '#FFFF00',  // Neon Yellow
        replies: '#FF0000'    // Neon Red
    },
    monochrome: {
        messages: '#000000',  // Black
        reactions: '#333333', // Dark Gray
        voice: '#666666',     // Medium Gray
        deafen: '#999999',    // Light Gray
        stream: '#CCCCCC',    // Very Light Gray
        mentions: '#444444',  // Alt Dark Gray
        replies: '#888888'    // Alt Medium Gray
    }
};

let previewDebounceTimeout;
let currentPreviewRequest = null;
let currentPreviewUrl = null;
let currentPreviewImage = null;

document.addEventListener('DOMContentLoaded', () => {
    initializeColorPaletteControls();
    initializeStatColorControls();
    initializeTextColorControls();
    initializeRangeInputs();
    
    const previewContainer = document.getElementById('card-preview');
    if (previewContainer) {
        previewContainer.innerHTML = `
            <div class="text-center text-gray-500">
                <p>Generating initial preview...</p>
            </div>
        `;
        updatePreview();
    } else {
        console.error('Preview container not found');
    }
});

function initializeColorPaletteControls() {
    const colorPaletteSelect = document.getElementById('color-palette');
    const useIndividualColorsCheckbox = document.getElementById('use-individual-colors');
    const statColorGroups = document.querySelectorAll('.stat-color-group');
    
    colorPaletteSelect.addEventListener('change', (e) => {
        cardEditorState.colorPalette = e.target.value;
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
}

function initializeStatColorControls() {
    const statColorInputs = document.querySelectorAll('.stat-color');
    
    statColorInputs.forEach(input => {
        const statType = input.dataset.stat;
        input.value = cardEditorState.statColors[statType];
        
        input.addEventListener('input', (e) => {
            cardEditorState.statColors[statType] = e.target.value;
            debouncedUpdatePreview();
        });
        
        input.addEventListener('change', updatePreview);
    });
}

function toggleIndividualColors(enabled) {
    cardEditorState.useIndividualColors = enabled;
    const statColorGroups = document.querySelectorAll('.stat-color-group');
    const statColorInputs = document.querySelectorAll('.stat-color');
    
    statColorGroups.forEach(group => {
        group.style.opacity = enabled ? '1' : '0.5';
    });
    
    statColorInputs.forEach(input => {
        input.disabled = !enabled;
    });
}

function updateStatColors(palette) {
    const statColorInputs = document.querySelectorAll('.stat-color');
    
    statColorInputs.forEach(input => {
        const statType = input.dataset.stat;
        input.value = palette[statType];
        cardEditorState.statColors[statType] = palette[statType];
    });

    cardEditorState.textColor = '#FFFFFF';
    const textColorInput = document.getElementById('text-color');
    const textColorHexInput = document.getElementById('text-color-hex');
    if (textColorInput && textColorHexInput) {
        textColorInput.value = '#FFFFFF';
        textColorHexInput.value = '#FFFFFF';
    }
}

function initializeRangeInputs() {
    const animationSpeedInput = document.getElementById('animation-speed');
    const waveIntensityInput = document.getElementById('wave-intensity');
    const fontSizeInput = document.getElementById('font-size');
    const fontSizeValue = document.getElementById('font-size-value');

    animationSpeedInput.addEventListener('input', (e) => {
        cardEditorState.animationSpeed = parseFloat(e.target.value);
        debouncedUpdatePreview();
    });

    waveIntensityInput.addEventListener('input', (e) => {
        cardEditorState.waveIntensity = parseFloat(e.target.value);
        debouncedUpdatePreview();
    });

    fontSizeInput.addEventListener('input', (e) => {
        cardEditorState.fontSize = parseInt(e.target.value);
        fontSizeValue.textContent = `${e.target.value}px`;
        debouncedUpdatePreview();
    });

    animationSpeedInput.addEventListener('change', updatePreview);
    waveIntensityInput.addEventListener('change', updatePreview);
    fontSizeInput.addEventListener('change', updatePreview);
}

function initializeTextColorControls() {
    const textColorInput = document.getElementById('text-color');
    const textColorHexInput = document.getElementById('text-color-hex');
    
    if (textColorInput && textColorHexInput) {
        textColorInput.value = cardEditorState.textColor;
        textColorHexInput.value = cardEditorState.textColor;
        
        textColorInput.addEventListener('input', (e) => {
            const newColor = e.target.value;
            cardEditorState.textColor = newColor;
            textColorHexInput.value = newColor;
            debouncedUpdatePreview();
        });
        
        textColorHexInput.addEventListener('input', (e) => {
            let newColor = e.target.value;
            if (newColor.startsWith('#')) {
                if (isValidHexColor(newColor)) {
                    cardEditorState.textColor = newColor;
                    textColorInput.value = newColor;
                    debouncedUpdatePreview();
                }
            } else {
                newColor = '#' + newColor;
                if (isValidHexColor(newColor)) {
                    cardEditorState.textColor = newColor;
                    textColorInput.value = newColor;
                    debouncedUpdatePreview();
                }
            }
        });
        
        textColorInput.addEventListener('change', updatePreview);
        textColorHexInput.addEventListener('change', (e) => {
            let newColor = e.target.value;
            if (!newColor.startsWith('#')) {
                newColor = '#' + newColor;
            }
            if (isValidHexColor(newColor)) {
                cardEditorState.textColor = newColor;
                textColorInput.value = newColor;
                textColorHexInput.value = newColor;
                updatePreview();
            } else {
                textColorHexInput.value = cardEditorState.textColor;
            }
        });
    }
}

function isValidHexColor(hex) {
    return /^#[0-9A-F]{6}$/i.test(hex);
}

function debouncedUpdatePreview() {
    clearTimeout(previewDebounceTimeout);
    
    if (currentPreviewRequest && currentPreviewRequest.abortController) {
        currentPreviewRequest.abortController.abort();
        currentPreviewRequest = null;
    }
    
    const previewContainer = document.getElementById('card-preview');
    if (previewContainer && currentPreviewImage) {
        updatePreviewPlaceholder();
    }
    
    previewDebounceTimeout = setTimeout(() => {
        updatePreview();
    }, 300);
}

function updatePreviewPlaceholder(message = 'Updating preview...') {
    const previewContainer = document.getElementById('card-preview');
    
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center';
    loadingOverlay.innerHTML = `
        <div class="text-center text-white">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
            <p>${message}</p>
        </div>
    `;
    
    const existingOverlay = previewContainer.querySelector('.loading-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }
    
    previewContainer.appendChild(loadingOverlay);
}

async function updatePreview() {
    try {
        const previewContainer = document.getElementById('card-preview');
        if (!previewContainer) {
            console.error('Preview container not found');
            return;
        }

        previewContainer.innerHTML = '<div class="loading">Generating preview...</div>';

        const settings = getCardEditorState();

        const response = await fetch('/api/preview-card', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to generate preview');
        }

        const img = new Image();
        img.onload = () => {
            previewContainer.innerHTML = '';
            previewContainer.appendChild(img);
        };
        img.onerror = () => {
            previewContainer.innerHTML = '<div class="error">Failed to load preview image</div>';
        };
        img.src = data.preview_url;
    } catch (error) {
        console.error('Error generating preview:', error);
        const previewContainer = document.getElementById('card-preview');
        if (previewContainer) {
            previewContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        }
    }
}

function cleanupPreview() {
    if (currentPreviewImage) {
        currentPreviewImage.src = '';
        currentPreviewImage.remove();
        currentPreviewImage = null;
    }
    
    if (currentPreviewUrl) {
        URL.revokeObjectURL(currentPreviewUrl);
        currentPreviewUrl = null;
    }
}

function resetDefaults() {
    cardEditorState = {
        colorPalette: 'default',
        useIndividualColors: false,
        statColors: COLOR_PALETTES.default,
        textColor: '#FFFFFF',
        animationSpeed: 1,
        waveIntensity: 0.5,
        fontSize: 24,
        cardStyle: 'default'
    };
    
    updateUIFromState();
    updatePreview();
}

function updateUIFromState() {
    const colorPaletteSelect = document.getElementById('color-palette');
    colorPaletteSelect.value = cardEditorState.colorPalette;
    
    const useIndividualColorsCheckbox = document.getElementById('use-individual-colors');
    useIndividualColorsCheckbox.checked = cardEditorState.useIndividualColors;
    toggleIndividualColors(cardEditorState.useIndividualColors);
    
    Object.entries(cardEditorState.statColors).forEach(([stat, color]) => {
        const input = document.querySelector(`.stat-color[data-stat="${stat}"]`);
        if (input) input.value = color;
    });
    
    const textColorInput = document.getElementById('text-color');
    const textColorHexInput = document.getElementById('text-color-hex');
    if (textColorInput && textColorHexInput) {
        textColorInput.value = cardEditorState.textColor;
        textColorHexInput.value = cardEditorState.textColor;
    }
    
    const animationSpeedInput = document.getElementById('animation-speed');
    const waveIntensityInput = document.getElementById('wave-intensity');
    const fontSizeInput = document.getElementById('font-size');
    const fontSizeValue = document.getElementById('font-size-value');
    
    if (animationSpeedInput) animationSpeedInput.value = cardEditorState.animationSpeed;
    if (waveIntensityInput) waveIntensityInput.value = cardEditorState.waveIntensity;
    if (fontSizeInput) {
        fontSizeInput.value = cardEditorState.fontSize;
        if (fontSizeValue) fontSizeValue.textContent = `${cardEditorState.fontSize}px`;
    }
}

function applyChanges() {
    const applyButton = document.querySelector('button[onclick="applyChanges()"]');
    const originalText = applyButton.textContent;
    applyButton.textContent = 'Saving...';
    applyButton.disabled = true;

    fetch('/api/apply-card-settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(cardEditorState)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Failed to save settings: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showToast('Settings saved successfully', 'success');
        } else {
            showToast(data.error || 'Error saving settings', 'error');
        }
    })
    .catch(error => {
        console.error('Error applying changes:', error);
        showToast(error.message || 'Error saving settings', 'error');
    })
    .finally(() => {
        applyButton.textContent = originalText;
        applyButton.disabled = false;
    });
}

const style = document.createElement('style');
style.textContent = `
    .loading-overlay {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 20;
    }
    
    #card-preview {
        position: relative;
        min-height: 300px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0, 0, 0, 0.05);
        border-radius: 0.5rem;
        overflow: hidden;
    }
    
    #card-preview img {
        max-width: 100%;
        height: auto;
        display: block;
    }
`;
document.head.appendChild(style);

window.addEventListener('beforeunload', cleanupPreview);

document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        cleanupPreview();
    }
});

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    const container = document.getElementById('toast-container');
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease-out forwards';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
} 