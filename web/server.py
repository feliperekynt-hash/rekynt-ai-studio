import os
import sys
import re
import uuid
import threading
import urllib.request
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

def _download_google_drive_folder_custom(drive_url, out_dir):
    """
    Extrator de alta precisão para qualquer pasta do Google Drive na Nuvem.
    Bypassa bloqueios de scraping extraindo IDs de arquivos diretamente do HTML público.
    """
    folder_match = re.search(r'(?:folders/|id=)([a-zA-Z0-9_-]+)', drive_url)
    if not folder_match:
        return False

    folder_id = folder_match.group(1)
    req_url = f"https://drive.google.com/drive/folders/{folder_id}"

    try:
        req = urllib.request.Request(req_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        file_ids = list(set(re.findall(r'file[/\\]+d[/\\]+([a-zA-Z0-9_-]{25,45})', html)))
        print(f"[Google Drive Scraper] IDs de vídeos extraídos com sucesso ({len(file_ids)} clipes): {file_ids[:5]}")

        if not file_ids:
            return False

        # Baixar os primeiros 10 clipes para formar o Reels commercial perfeito
        for idx, fid in enumerate(file_ids[:10]):
            out_file = os.path.join(out_dir, f"imovel_clip_{idx+1}.MOV")
            if not os.path.exists(out_file) or os.path.getsize(out_file) < 100000:
                print(f"[Google Drive Scraper] Baixando clipe {idx+1}/{len(file_ids[:10])} (ID: {fid})...")
                try:
                    gdown.download(id=fid, output=out_file, quiet=True, fuzzy=True, use_cookies=False)
                except Exception as ex:
                    print(f"[Google Drive Scraper] Aviso ao baixar ID {fid}: {ex}")

        return True
    except Exception as err:
        print(f"[Google Drive Scraper] Erro ao raspar pasta do Drive: {err}")
        return False

@app.route("/api/upload-drive-url", methods=["POST"])
def upload_drive_url():
    data = request.json or {}
    drive_url = data.get("drive_url", "").strip()
    if not drive_url:
        return jsonify({"error": "URL do Google Drive é obrigatória"}), 400

    out_dir = os.path.join(ASSETS_DIR, "drive_uploads")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Tentar Extrator Direto Personalizado de Alta Precisao
    success_custom = _download_google_drive_folder_custom(drive_url, out_dir)

    # 2. Fallback gdown
    if not success_custom:
        try:
            folder_match = re.search(r'(?:folders/|id=)([a-zA-Z0-9_-]+)', drive_url)
            clean_url = f"https://drive.google.com/drive/folders/{folder_match.group(1)}" if folder_match else drive_url
            gdown.download_folder(clean_url, output=out_dir, quiet=True, remaining_ok=True, use_cookies=False)
        except Exception as e:
            print(f"[Google Drive Import] Aviso no fallback gdown: {e}")

    # Coletar TODOS os clipes válidos no diretório
    all_videos = []
    for root, _, files in os.walk(out_dir):
        for f in files:
            if f.upper().endswith(('.MOV', '.MP4')) and not f.startswith(('Rekynt_', 'test_')):
                fp = os.path.join(root, f)
                if os.path.getsize(fp) > 100000:
                    all_videos.append((fp, os.path.getmtime(fp)))

    all_videos.sort(key=lambda x: x[1], reverse=True)

    if not all_videos:
        return jsonify({
            "error": "Não foi possível acessar a pasta do Google Drive. Verifique se o link está como 'Qualquer pessoa com o link pode ver' ou use o botão 'Escolher Arquivo do Celular' para subir os vídeos direto da galeria!"
        }), 400

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

    print(f"[Google Drive Import] Importados {len(all_videos)} clipes do imóvel com sucesso!")

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
