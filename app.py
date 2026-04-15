import os
import json
import datetime
from flask import Flask, render_template, request, send_from_directory, jsonify, session
from werkzeug.utils import secure_filename
from functools import wraps
import whisper

try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
except ImportError:
    from moviepy.editor import VideoFileClip

app = Flask(__name__)
app.secret_key = "fribal_secret_key"
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024 

print("Carregando modelo de legenda (Whisper)...")
model = whisper.load_model("base") 

DB_FILE = 'database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Inicializa o banco
videos_db = load_db()

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'auth' not in session:
            return jsonify({"error": "Não autorizado"}), 401
        return f(*args, **kwargs)
    return decorated_function

def format_vtt_timestamp(seconds):
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

def generate_subtitles(video_path, filename):
    try:
        print(f"Gerando legendas para: {filename}...")
        vtt_filename = filename.rsplit('.', 1)[0] + ".vtt"
        vtt_path = os.path.join(app.config['UPLOAD_FOLDER'], vtt_filename)
        
        result = model.transcribe(video_path, verbose=False, language='pt')
        
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for segment in result['segments']:
                start = format_vtt_timestamp(segment['start'])
                end = format_vtt_timestamp(segment['end'])
                f.write(f"{start} --> {end}\n")
                f.write(f"{segment['text'].strip()}\n\n")
        
        return f"/video/stream/{vtt_filename}"
    except Exception as e:
        print(f"Erro ao gerar legenda: {e}")
        return None
    
def sync_database():
    global videos_db
    if not os.path.exists(UPLOAD_FOLDER): return
    
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith('.mp4')]
    db_filenames = {v['filename']: v for v in videos_db}
    new_db = []

    for f in files:
        if f in db_filenames:
            new_db.append(db_filenames[f])
        else:
            # Caso caia um arquivo novo na pasta, assume GERAL/GERAL
            video_entry = {
                "id": int(datetime.datetime.now().timestamp()),
                "title": f.replace('_', ' ').replace('.mp4', ''),
                "filename": f,
                "category": "GERAL",
                "subcategory": "GERAL",
                "tags": ["interno"],
                "url": f"/video/stream/{f}",
                "vtt": f"/video/stream/{f.rsplit('.', 1)[0] + '.vtt'}" if os.path.exists(os.path.join(UPLOAD_FOLDER, f.rsplit('.', 1)[0] + '.vtt')) else None
            }
            new_db.append(video_entry)
    
    videos_db = new_db
    save_db(videos_db) 

sync_database()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    # Senha fr1b4l atualizada conforme seu código
    if data.get('user') == 'admin' and data.get('pass') == 'fr1b4l':
        session['auth'] = True
        return jsonify({"status": "logado"})
    return jsonify({"error": "Dados inválidos"}), 401

@app.route('/upload', methods=['POST'])
@login_required
def upload_video():
    file = request.files['video']
    title = request.form.get('title')
    tags = request.form.get('tags', '')
    category = request.form.get('category', 'GERAL')
    subcategory = request.form.get('subcategory', 'GERAL')
    generate_cap = request.form.get('generate_caption') == 'true'
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    vtt_url = generate_subtitles(filepath, filename) if generate_cap else None
    
    video_entry = {
        "id": int(datetime.datetime.now().timestamp()),
        "title": title or filename,
        "filename": filename,
        "category": category,
        "subcategory": subcategory,
        "tags": [t.strip().lower() for t in tags.split(',') if t.strip()],
        "url": f"/video/stream/{filename}",
        "vtt": vtt_url
    }
    
    videos_db.append(video_entry)
    save_db(videos_db)
    return jsonify(video_entry)

@app.route('/view/<int:video_id>')
def view_video(video_id):
    # Carrega do DB para garantir que o ID exista após reboot
    current_db = load_db()
    video = next((v for v in current_db if v['id'] == video_id), None)
    if video:
        return render_template('player.html', video=video)
    return "Vídeo não encontrado", 404

@app.route('/video/stream/<filename>')
def stream(filename):
    response = send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/subtitles/save', methods=['POST'])
@login_required
def save_subtitles():
    data = request.json
    filename_url = data.get('filename')
    content = data.get('content')

    if not filename_url or not content:
        return jsonify({"error": "Dados insuficientes"}), 400
    
    clean_vtt_name = filename_url.split('/')[-1]
    vtt_path = os.path.join(app.config['UPLOAD_FOLDER'], clean_vtt_name)
    
    try:
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        corresponding_mp4 = clean_vtt_name.replace('.vtt', '.mp4')
        
        global videos_db
        updated = False
        for video in videos_db:
            if video['filename'] == corresponding_mp4:
                video['vtt'] = f"/video/stream/{clean_vtt_name}"
                updated = True
                break
        if updated:
            save_db(videos_db)
        return jsonify({"status": "Legenda atualizada e salva no banco!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/videos')
def list_videos():
    query = request.args.get('q', '').lower().strip()
    cat_filter = request.args.get('cat', '').upper().strip()
    sub_filter = request.args.get('sub', '').upper().strip()
    
    filtered = videos_db
    
    if cat_filter:
        filtered = [v for v in filtered if v.get('category', '').upper() == cat_filter]
    if sub_filter:
        filtered = [v for v in filtered if v.get('subcategory', '').upper() == sub_filter]
    if query:
        filtered = [
            v for v in filtered 
            if query in v.get('title', '').lower() or 
            any(query in str(tag).lower().strip() for tag in v.get('tags', []))
        ]
        
    return jsonify(filtered)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=False)