import os
import requests
from PIL import Image
from datetime import datetime
import io
import json
from flask import Flask, render_template_string, request, redirect, url_for, flash
import toml

# === Load API Key from secrets.toml ===
def load_api_key():
    try:
        secrets = toml.load('secrets.toml')
        return secrets['plantnet']['api_key']
    except Exception as e:
        raise RuntimeError(f"API key not found or secrets.toml misconfigured: {e}")

API_KEY = load_api_key()
API_URL = "https://my-api.plantnet.org/v2/identify/all"

# === Flask App Setup ===
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages
UPLOAD_FOLDER = 'images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === HTML Template ===
TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tree Species Classifier</title>
    <link href="https://fonts.googleapis.com/css?family=Montserrat:700,400&display=swap" rel="stylesheet">
    <style>
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
        }
        body {
            min-height: 100vh;
            background: url("{{ url_for('static', filename='tree.jpg') }}") no-repeat center center fixed;
            background-size: cover;
            font-family: 'Montserrat', Arial, sans-serif;
        }
        .container {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .glass-card {
            background: rgba(255,255,255,0.18);
            box-shadow: 0 8px 32px 0 rgba(31,38,135,0.37);
            backdrop-filter: blur(18px) saturate(120%);
            -webkit-backdrop-filter: blur(18px) saturate(120%);
            border-radius: 24px;
            border: 1.5px solid rgba(255,255,255,0.25);
            padding: 2.5rem 2rem;
            margin: 2rem 0;
            max-width: 480px;
            width: 100%;
            color: #fff;
            animation: fadeIn 1.2s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(40px);}
            to { opacity: 1; transform: translateY(0);}
        }
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 0.5rem;
            text-shadow: 0 2px 16px #000a;
        }
        h2 {
            font-size: 1.5rem;
            margin-top: 1.5rem;
            text-shadow: 0 2px 8px #0008;
        }
        label, .info, .warning, .error {
            font-size: 1rem;
            font-weight: 500;
        }
        input[type=file], input[type=number], button {
            margin: 0.5rem 0 1rem 0;
            width: 100%;
        }
        button {
            background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%);
            color: #222;
            border: none;
            padding: 0.8rem 0;
            border-radius: 30px;
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 2px 8px #0003;
            transition: background 0.3s, color 0.3s, transform 0.2s;
        }
        button:hover {
            background: linear-gradient(90deg, #38f9d7 0%, #43e97b 100%);
            color: #111;
            transform: scale(1.04);
            box-shadow: 0 4px 16px #43e97b55;
        }
        .result-card {
            background: rgba(255,255,255,0.22);
            border-radius: 16px;
            margin: 1.2rem 0;
            padding: 1.2rem;
            box-shadow: 0 2px 12px #0002;
            color: #fff;
            border-left: 4px solid #43e97b;
            animation: fadeIn 1.2s;
        }
        .confidence-high { color: #43e97b; font-weight: bold; }
        .confidence-medium { color: #ffe066; font-weight: bold; }
        .confidence-low { color: #ff6b6b; font-weight: bold; }
        .info, .warning, .error {
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .info { background: rgba(67,233,123,0.12); border-left: 4px solid #43e97b; }
        .warning { background: rgba(255,224,102,0.12); border-left: 4px solid #ffe066; color: #ffe066;}
        .error { background: rgba(255,107,107,0.12); border-left: 4px solid #ff6b6b; color: #ff6b6b;}
        @media (max-width: 600px) {
            .glass-card { padding: 1.2rem 0.5rem; }
            h1 { font-size: 1.5rem; }
        }
        .upload-area {
            background: rgba(255,255,255,0.10);
            border: 2px dashed #43e97b;
            border-radius: 16px;
            padding: 1.2rem;
            margin-bottom: 1.2rem;
            text-align: center;
            transition: border-color 0.3s, background 0.3s;
            position: relative;
        }
        .upload-area.dragover {
            border-color: #38f9d7;
            background: rgba(67,233,123,0.12);
        }
        .upload-area input[type=file] {
            display: none;
        }
        .upload-label {
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
        }
        .upload-icon {
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
            color: #43e97b;
        }
        .upload-preview-multi {
            margin-top: 0.5rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            justify-content: center;
        }
        .upload-preview-multi .preview-img-wrapper {
            position: relative;
            display: inline-block;
            cursor: grab;
        }
        .upload-preview-multi img {
            max-width: 90px;
            max-height: 90px;
            border-radius: 10px;
            box-shadow: 0 2px 8px #0002;
            user-select: none;
        }
        .remove-btn {
            position: absolute;
            top: -8px;
            right: -8px;
            background: #ff6b6b;
            color: #fff;
            border: none;
            border-radius: 50%;
            width: 22px;
            height: 22px;
            font-size: 1.1rem;
            cursor: pointer;
            z-index: 2;
            box-shadow: 0 2px 6px #0003;
        }
        .tooltip {
            display: inline-block;
            position: relative;
            cursor: pointer;
            margin-left: 0.3rem;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 220px;
            background-color: #222;
            color: #fff;
            text-align: left;
            border-radius: 6px;
            padding: 0.5rem;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -110px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.9rem;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        .progress-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(30,30,30,0.45);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.3s;
        }
        .spinner {
            border: 6px solid #f3f3f3;
            border-top: 6px solid #43e97b;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .confetti {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            pointer-events: none;
            z-index: 2000;
        }
        .checkmark {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: #43e97b;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 2rem auto 1rem auto;
            box-shadow: 0 2px 16px #43e97b55;
            animation: popIn 0.6s;
        }
        .checkmark svg {
            width: 48px;
            height: 48px;
            stroke: #fff;
            stroke-width: 5;
            fill: none;
        }
        @keyframes popIn {
            0% { transform: scale(0.5); opacity: 0; }
            80% { transform: scale(1.1); opacity: 1; }
            100% { transform: scale(1); }
        }
        .shake {
            animation: shake 0.5s;
        }
        @keyframes shake {
            0% { transform: translateX(0); }
            20% { transform: translateX(-10px); }
            40% { transform: translateX(10px); }
            60% { transform: translateX(-10px); }
            80% { transform: translateX(10px); }
            100% { transform: translateX(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="glass-card" id="main-card">
            <h1>🌿 Tree Species Classification</h1>
            <p style="margin-bottom:1.5rem;">AI-powered tool for identifying trees and plants.<br>Upload clear images of leaves, flowers, or bark for accurate species identification.</p>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                {% for msg in messages %}
                  <div class="error">{{ msg }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}
            <form method="POST" enctype="multipart/form-data" id="upload-form">
                <label>Plant Images (Required):
                  <span class="tooltip">&#9432;
                    <span class="tooltiptext">Upload one or more clear, well-lit photos of leaves, flowers, or bark. Multiple images help improve identification accuracy.</span>
                  </span>
                </label>
                <div class="upload-area" id="upload-area-1">
                  <label class="upload-label">
                    <span class="upload-icon">📤</span>
                    <span id="upload-text-1">Drag & drop or click to select file(s)</span>
                    <input type="file" name="image1" id="file-input-1" accept="image/*" required multiple>
                    <div id="preview-multi" class="upload-preview-multi"></div>
                  </label>
                </div>
                <label>Max Results:</label>
                <input type="number" name="max_results" min="1" max="10" value="5">
                <label style="margin-left:0.5rem;">
                    <input type="checkbox" name="show_details" checked> Show Detailed Info
                </label><br>
                <button type="submit">🔍 Identify Plant Species</button>
            </form>
            <div id="progress-overlay" class="progress-overlay" style="display:none;">
                <div class="spinner"></div>
            </div>
            <canvas id="confetti-canvas" class="confetti" style="display:none;"></canvas>
            <div id="success-check" style="display:none;">
                <div class="checkmark">
                    <svg viewBox="0 0 52 52"><polyline points="14,27 22,35 38,19"></polyline></svg>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/browser-image-compression@2.0.2/dist/browser-image-compression.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
            <script>
            // --- Advanced Multi-Image Upload with Remove, Reorder, and Compression ---
            let filesArray = [];
            const area = document.getElementById('upload-area-1');
            const input = document.getElementById('file-input-1');
            const previewMulti = document.getElementById('preview-multi');
            const text = document.getElementById('upload-text-1');
            const form = document.getElementById('upload-form');
            const progressOverlay = document.getElementById('progress-overlay');
            const confettiCanvas = document.getElementById('confetti-canvas');
            const successCheck = document.getElementById('success-check');
            const mainCard = document.getElementById('main-card');

            // Helper: Render previews
            function renderPreviews() {
                previewMulti.innerHTML = '';
                filesArray.forEach((file, idx) => {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'preview-img-wrapper';
                    wrapper.draggable = true;
                    wrapper.dataset.idx = idx;
                    const img = document.createElement('img');
                    img.src = file.preview;
                    img.title = file.name;
                    // Remove button
                    const btn = document.createElement('button');
                    btn.className = 'remove-btn';
                    btn.innerHTML = '&times;';
                    btn.onclick = (e) => {
                        e.stopPropagation();
                        filesArray.splice(idx, 1);
                        renderPreviews();
                        updateInputFiles();
                    };
                    wrapper.appendChild(img);
                    wrapper.appendChild(btn);
                    // Drag events for reordering
                    wrapper.ondragstart = (e) => {
                        e.dataTransfer.setData('text/plain', idx);
                        wrapper.style.opacity = '0.5';
                    };
                    wrapper.ondragend = (e) => {
                        wrapper.style.opacity = '1';
                    };
                    wrapper.ondragover = (e) => {
                        e.preventDefault();
                        wrapper.style.border = '2px dashed #38f9d7';
                    };
                    wrapper.ondragleave = (e) => {
                        wrapper.style.border = '';
                    };
                    wrapper.ondrop = (e) => {
                        e.preventDefault();
                        wrapper.style.border = '';
                        const fromIdx = parseInt(e.dataTransfer.getData('text/plain'));
                        const toIdx = idx;
                        if (fromIdx !== toIdx) {
                            const moved = filesArray.splice(fromIdx, 1)[0];
                            filesArray.splice(toIdx, 0, moved);
                            renderPreviews();
                            updateInputFiles();
                        }
                    };
                    previewMulti.appendChild(wrapper);
                });
                text.style.display = filesArray.length ? 'none' : 'block';
            }

            // Helper: Update input.files to match filesArray
            function updateInputFiles() {
                const dataTransfer = new DataTransfer();
                filesArray.forEach(f => dataTransfer.items.add(f.file));
                input.files = dataTransfer.files;
            }

            // Handle file selection and compression
            async function handleFiles(selectedFiles) {
                for (let file of selectedFiles) {
                    // Compress image before adding
                    try {
                        const compressed = await imageCompression(file, { maxSizeMB: 0.5, maxWidthOrHeight: 1200, useWebWorker: true });
                        const preview = await imageCompression.getDataUrlFromFile(compressed);
                        filesArray.push({ file: compressed, preview, name: file.name });
                    } catch (err) {
                        alert('Image compression failed: ' + err.message);
                    }
                }
                renderPreviews();
                updateInputFiles();
            }

            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('dragover');
            });
            area.addEventListener('dragleave', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
            });
            area.addEventListener('drop', async (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    await handleFiles(e.dataTransfer.files);
                }
            });
            input.addEventListener('change', async () => {
                await handleFiles(input.files);
            });
            area.addEventListener('click', () => {
                input.click();
            });
            // Initial render
            renderPreviews();

            // --- Progress Spinner on Submit ---
            form.addEventListener('submit', function() {
                progressOverlay.style.display = 'flex';
            });

            // --- Confetti and Success/Failure Animation ---
            function showConfetti() {
                confettiCanvas.style.display = 'block';
                confetti.create(confettiCanvas, { resize: true, useWorker: true })({
                    particleCount: 180,
                    spread: 90,
                    origin: { y: 0.6 }
                });
                setTimeout(() => { confettiCanvas.style.display = 'none'; }, 2500);
            }
            function showCheckmark() {
                successCheck.style.display = 'block';
                setTimeout(() => { successCheck.style.display = 'none'; }, 1800);
            }
            function shakeCard() {
                mainCard.classList.add('shake');
                setTimeout(() => { mainCard.classList.remove('shake'); }, 600);
            }
            // --- Show/hide spinner and trigger animations based on result ---
            window.addEventListener('DOMContentLoaded', () => {
                const url = new URL(window.location.href);
                if (url.searchParams.get('success') === '1') {
                    setTimeout(() => {
                        progressOverlay.style.display = 'none';
                        showConfetti();
                        showCheckmark();
                    }, 400);
                } else if (url.searchParams.get('success') === '0') {
                    setTimeout(() => {
                        progressOverlay.style.display = 'none';
                        shakeCard();
                    }, 400);
                } else {
                    progressOverlay.style.display = 'none';
                }
            });
            </script>
            {% if results %}
                <h2>🌱 Top {{ shown_results }} Results:</h2>
                {% for r in results %}
                    <div class="result-card">
                        <h3>#{{ loop.index }} {{ r.scientific_name }}</h3>
                        <p class="{{ r.confidence_class }}">{{ r.confidence_str }}</p>
                        <div><strong>🏷️ Common Names:</strong> {{ r.common_names }}</div>
                        <p><strong>👨‍🔬 Scientific Classification:</strong></p>
                        <ul>
                            <li><strong>Family:</strong> {{ r.family_name }}</li>
                            <li><strong>Genus:</strong> {{ r.genus_name }}</li>
                            <li><strong>Species:</strong> {{ r.scientific_name }}</li>
                        </ul>
                    </div>
                {% endfor %}
                {% if show_details %}
                    <div class="info">
                        <strong>📊 Analysis Summary</strong><br>
                        Total Matches: {{ total_matches }}<br>
                        Best Match: {{ best_match }}%<br>
                        Average Confidence: {{ avg_confidence }}%<br>
                        🕐 Analysis completed at {{ timestamp }}
                    </div>
                {% endif %}
            {% elif warning %}
                <div class="warning">{{ warning }}</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

def process_image(file_storage, filename):
    try:
        image_data = file_storage.read()
        img = Image.open(io.BytesIO(image_data))
        if img.mode in ("RGBA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        max_size = 1024
        if img.size[0] > max_size or img.size[1] > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        img.save(filename, format="JPEG", quality=85, optimize=True)
        return open(filename, "rb")
    except Exception as e:
        return None

def get_confidence_class(score):
    if score >= 70:
        return "confidence-high"
    elif score >= 40:
        return "confidence-medium"
    else:
        return "confidence-low"

def format_confidence(score):
    if score >= 70:
        return f"🟢 {score:.1f}% (High Confidence)"
    elif score >= 40:
        return f"🟡 {score:.1f}% (Medium Confidence)"
    else:
        return f"🔴 {score:.1f}% (Low Confidence)"

def safe_get(dictionary, key, default="Not available"):
    try:
        value = dictionary.get(key, default)
        return value if value else default
    except:
        return default

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    warning = None
    shown_results = 0
    total_matches = 0
    best_match = 0
    avg_confidence = 0
    timestamp = None
    show_details = True
    if request.method == 'POST':
        image1 = request.files.get('image1')
        image2 = request.files.get('image2') # This will be None for the new form
        max_results = int(request.form.get('max_results', 5))
        show_details = 'show_details' in request.form
        if not image1:
            flash('Primary image is required.')
            return redirect(url_for('index'))
        try:
            # Process all files from image1
            files_to_send = []
            if image1 and image1.filename:
                for f in image1.files:
                    file_data = process_image(f, os.path.join(UPLOAD_FOLDER, f.filename))
                    if file_data:
                        files_to_send.append(('images', (f.filename, file_data, f.content_type)))
                    else:
                        flash(f'Failed to process image file: {f.filename}')
                        return redirect(url_for('index'))
            else:
                flash('No images uploaded.')
                return redirect(url_for('index'))

            params = {"api-key": API_KEY}
            response = requests.post(
                API_URL,
                files=files_to_send,
                params=params,
                timeout=45
            )
            for filename in [os.path.join(UPLOAD_FOLDER, f.filename) for f in image1.files]:
                if os.path.exists(filename):
                    os.remove(filename)
            if response.status_code == 200:
                result = response.json()
                api_results = result.get("results", [])
                if api_results:
                    shown_results = min(len(api_results), max_results)
                    for r in api_results[:max_results]:
                        species = r.get("species", {})
                        score = round(r.get("score", 0) * 100, 2)
                        scientific_name = safe_get(species, "scientificNameWithoutAuthor", "Unknown Species")
                        common_names = species.get("commonNames", [])
                        family_info = species.get("family", {})
                        genus_info = species.get("genus", {})
                        family_name = safe_get(family_info, "scientificNameWithoutAuthor", "Unknown Family")
                        genus_name = safe_get(genus_info, "scientificNameWithoutAuthor", "Unknown Genus")
                        confidence_class = get_confidence_class(score)
                        common_names_str = ', '.join(common_names[:3]) if common_names else 'Not available'
                        results.append({
                            'scientific_name': scientific_name,
                            'common_names': common_names_str,
                            'family_name': family_name,
                            'genus_name': genus_name,
                            'confidence_class': confidence_class,
                            'confidence_str': format_confidence(score)
                        })
                    total_matches = len(api_results)
                    best_match = max([r.get("score", 0) * 100 for r in api_results if r.get("score", 0) > 0], default=0)
                    valid_scores = [r.get("score", 0) * 100 for r in api_results if r.get("score", 0) > 0]
                    avg_confidence = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    return redirect(url_for('index', success=1))
                else:
                    warning = "🤔 No species matches found. This could be due to image quality issues, unusual plant species, or unclear plant parts. Try uploading clearer images or different plant parts."
                    return redirect(url_for('index', success=0))
            elif response.status_code == 401:
                flash('Invalid API key. Please check your PlantNet API key configuration.')
                return redirect(url_for('index', success=0))
            elif response.status_code == 429:
                flash('API rate limit exceeded. Please wait a moment before trying again.')
                return redirect(url_for('index', success=0))
            elif response.status_code == 413:
                flash('Image file too large. Please use smaller images (max 5MB).')
                return redirect(url_for('index', success=0))
            else:
                flash(f'API Error {response.status_code}: {response.text}')
                return redirect(url_for('index', success=0))
        except requests.exceptions.Timeout:
            flash('Request timeout. The API is taking too long to respond. Please try again.')
            return redirect(url_for('index', success=0))
        except requests.exceptions.ConnectionError:
            flash('Connection error. Please check your internet connection and try again.')
            return redirect(url_for('index', success=0))
        except Exception as e:
            flash(f'Unexpected error: {str(e)}')
            return redirect(url_for('index', success=0))
    return render_template_string(TEMPLATE, results=results, shown_results=shown_results, warning=warning, show_details=show_details, total_matches=total_matches, best_match=best_match, avg_confidence=avg_confidence, timestamp=timestamp)
if __name__ == '__main__':
    app.run(debug=True, port=5002)
    