import os
import sys
import uuid
import threading
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import gdown

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(WEB_DIR, ".."))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

sys.path.append(BASE_DIR)
from core.rekynt_engine import RekyntAIStudioEngine
from core.auth import BrokerAuthManager

app = Flask(__name__, static_folder=WEB_DIR)
CORS(app)

engine = RekyntAIStudioEngine(output_dir=os.path.join(ASSETS_DIR, "output"))
auth_manager = BrokerAuthManager()
jobs = {}

@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")

@app.route("/style.css")
def style_css():
    return send_from_directory(WEB_DIR, "style.css")

@app.route("/app.js")
def app_js():
    return send_from_directory(WEB_DIR, "app.js")

@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(ASSETS_DIR, filename)

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}
    email = data.get("email", "").strip()
    
    if auth_manager.is_authorized(email):
        return jsonify({
            "success": True,
            "email": email,
            "message": f"Bem-vindo ao Rekynt AI Studio, {email}!"
        })
    else:
        return jsonify({
            "success": False,
            "error": f"O e-mail '{email}' não possui cadastro ativo na Rekynt Imóveis. Entre em contato com a gerência."
        }), 403

@app.route("/api/auth/brokers", methods=["GET"])
def get_brokers():
    return jsonify({
        "authorized_brokers": auth_manager.get_authorized_brokers()
    })

@app.route("/api/auth/add-broker", methods=["POST"])
def add_broker():
    data = request.json or {}
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "E-mail obrigatório"}), 400
    
    added = auth_manager.add_broker(email)
    if added:
        return jsonify({"success": True, "message": f"Corretor '{email}' cadastrado com sucesso!"})
    return jsonify({"success": True, "message": f"Corretor '{email}' já estava cadastrado."})

@app.route("/api/media", methods=["GET"])
def get_media():
    def list_files(subdir):
        d = os.path.join(ASSETS_DIR, subdir)
        if not os.path.exists(d):
            return []
        return [f for f in os.listdir(d) if not f.startswith(".")]

    return jsonify({
        "videos": list_files("drive_uploads"),
        "outputs": list_files("output"),
        "tracks": list_files("audio")
    })

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nome de arquivo inválido"}), 400

    filename = secure_filename(file.filename)
    save_dir = os.path.join(ASSETS_DIR, "drive_uploads")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)

    file.save(save_path)
    print(f"[Upload Server] Novo vídeo enviado pelo corretor: {save_path}")

    return jsonify({
        "success": True,
        "filename": filename,
        "rel_path": f"drive_uploads/{filename}",
        "message": f"Vídeo '{filename}' pronto para edição!"
    })

@app.route("/api/upload-drive-url", methods=["POST"])
def upload_drive_url():
    data = request.json or {}
    drive_url = data.get("drive_url", "").strip()
    if not drive_url:
        return jsonify({"error": "URL do Google Drive é obrigatória"}), 400

    out_dir = os.path.join(ASSETS_DIR, "drive_uploads")
    os.makedirs(out_dir, exist_ok=True)

    try:
        print(f"[Google Drive Import] Baixando do link: {drive_url}...")
        if "folders/" in drive_url or "folder" in drive_url:
            gdown.download_folder(drive_url, output=out_dir, quiet=False, remaining_ok=True)
        else:
            gdown.download(drive_url, output=out_dir, quiet=False, fuzzy=True)
    except Exception as e:
        print(f"[Google Drive Import] Aviso no download: {e}")

    # Coletar TODOS os clipes válidos baixados do imóvel
    all_videos = []
    for root, _, files in os.walk(out_dir):
        for f in files:
            if f.upper().endswith(('.MOV', '.MP4')) and not f.startswith(('Rekynt_', 'test_', 'imovel_drive_')):
                fp = os.path.join(root, f)
                if os.path.getsize(fp) > 100000:
                    all_videos.append((fp, os.path.getmtime(fp)))

    all_videos.sort(key=lambda x: x[1], reverse=True)

    if not all_videos:
        return jsonify({"error": "Nenhum vídeo válido (.MOV ou .MP4) encontrado no link do Drive"}), 400

    video_list = [
        {
            "filename": f"🎬 TOUR COMPLETO UNIFICADO DO IMÓVEL ({len(all_videos)} Clipes da Pasta)",
            "rel_path": "drive_uploads/TOUR_COMPLETO_UNIFICADO.mp4"
        }
    ]

    for fp, _ in all_videos:
        fn = os.path.basename(fp)
        video_list.append({"filename": f"📹 Clipe Individual: {fn}", "rel_path": f"drive_uploads/{fn}"})

    default_rel_path = "drive_uploads/TOUR_COMPLETO_UNIFICADO.mp4"
    default_filename = f"🎬 TOUR COMPLETO UNIFICADO DO IMÓVEL ({len(all_videos)} Clipes da Pasta)"

    print(f"[Google Drive Import] Importados {len(all_videos)} clipes do imóvel!")

    return jsonify({
        "success": True,
        "filename": default_filename,
        "rel_path": default_rel_path,
        "videos": video_list,
        "message": f"✅ {len(all_videos)} clipes do imóvel importados com sucesso!"
    })

def run_render_job(job_id, video_path, user_email, estilo_musica, com_legendas):
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["message"] = "Unificando os ambientes do imóvel em um Reels Comercial High-Performance..."
    try:
        output_filename = f"Rekynt_Reels_{job_id}.mp4"
        output_file = engine.processar_video_imovel(
            caminho_video=video_path,
            user_email=user_email,
            estilo_musica=estilo_musica,
            com_legendas=com_legendas,
            output_filename=output_filename
        )
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["output_file"] = os.path.basename(output_file)
        jobs[job_id]["message"] = "Tour Completo do Imóvel gerado com sucesso!"
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Erro no processamento: {str(e)}"

@app.route("/api/process", methods=["POST"])
def process_video():
    data = request.json or {}
    video_rel = data.get("video", "drive_uploads/TOUR_COMPLETO_UNIFICADO.mp4")
    user_email = data.get("user_email", "corretor.rekynt@gmail.com")
    estilo_musica = data.get("estilo_musica", "luxo")
    com_legendas = bool(data.get("com_legendas", True))

    video_path = os.path.join(ASSETS_DIR, video_rel) if not os.path.isabs(video_rel) else video_rel

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "message": "Iniciando unificação dos ambientes do imóvel...",
        "output_file": None,
        "error": None
    }

    thread = threading.Thread(target=run_render_job, args=(job_id, video_path, user_email, estilo_musica, com_legendas))
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "job_id": job_id, "message": "Renderização iniciada."})

@app.route("/api/status/<job_id>", methods=["GET"])
def get_job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job não encontrado"}), 404
    return jsonify(job)

def start_server():
    port = int(os.environ.get("PORT", 5000))
    print(f"Servidor Rekynt Reels AI Studio rodando na porta {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    start_server()
