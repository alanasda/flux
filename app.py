from flask import Flask, request, jsonify
from supabase import create_client, Client
from flask_cors import CORS
import yagmail
import os
import random
import string
import jwt
import datetime

app = Flask(__name__)
CORS(app)

# Chave secreta para codificação/decodificação do JWT
SECRET_KEY = "supersecreta"

# Supabase configuration
SUPABASE_URL = "https://szbptsuvjmaqkcgsgagx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6YnB0c3V2am1hcWtjZ3NnYWd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxNjA3MjEsImV4cCI6MjA1OTczNjcyMX0.wqjSCJ8evNog5AnP2dzk1t2nkn31EfvqDuaAkXDiqNo"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# E-mail configuration
EMAIL_REMETENTE = "cyberdigitalsuporte@gmail.com"
EMAIL_SENHA_APP = "ufvz jkdc ihpu ksak"

# Função para criar um token JWT
def create_token(email):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expira em 1 hora
    token = jwt.encode({'email': email, 'exp': expiration}, SECRET_KEY, algorithm='HS256')
    return token

# Função para verificar se o token é válido
def verify_token(token):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return decoded_token['email']
    except jwt.ExpiredSignatureError:
        return None  # Token expirado
    except jwt.InvalidTokenError:
        return None  # Token inválido

@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200

# REGISTRO
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    nome = data.get("nome")
    email = data.get("email")
    
    if not nome or not email:
        return jsonify({"success": False, "message": "Nome e e-mail são obrigatórios."}), 400

    # Verifica se o e-mail já está registrado no Supabase
    result = supabase.table("usuarios").select("*").eq("email", email).execute()
    if not result.data:
        return jsonify({"success": False, "message": "E-mail não registrado."}), 404

    # Atualiza o nome do usuário
    supabase.table("usuarios").update({"nome": nome}).eq("email", email).execute()

    return jsonify({"success": True, "message": "Registro concluído com sucesso!"}), 200

# LOGIN
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    senha = data.get("senha")
    
    if not email or not senha:
        return jsonify({"success": False, "message": "E-mail e senha são obrigatórios."}), 400

    # Verifica se o e-mail e a senha existem no Supabase
    result = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()
    user = result.data[0] if result.data else None

    if not user:
        return jsonify({"success": False, "message": "E-mail ou senha inválidos."}), 401

    # Gerar o token JWT
    token = create_token(email)

    return jsonify({
        "success": True,
        "email": user["email"],
        "nome": user.get("nome", ""),
        "modulos": user.get("modulos", []),
        "token": token  # Retorna o token no login
    })

# Webhook para liberação de módulo
@app.route("/webhook/<int:modulo_id>", methods=["POST"])
def webhook_envio(modulo_id):
    data = request.get_json()
    email = data.get("email")
    
    if not email:
        return jsonify({"success": False, "message": "E-mail é obrigatório."}), 400

    # Mapeia o ID do módulo para o que o front espera
    modulo_real = modulo_front_ids.get(modulo_id, modulo_id)

    link_login = "cyberflux.onrender.com"
    corpo = f'''
    <h2>Seu acesso ao módulo foi liberado!</h2>
    <p><strong>Módulo:</strong> {modulo_id}</p>
    <p>Clique abaixo para acessar a plataforma:</p>
    <a href="{link_login}" style="padding: 10px 20px; background: #00ffff; color: black; border-radius: 8px; text-decoration:none;">
        Entrar na Plataforma
    </a>
    '''
    try:
        yag = yagmail.SMTP(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        yag.send(to=email, subject="Acesso Liberado - CYBER.DIGITAL", contents=corpo)
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao enviar e-mail: {str(e)}"}), 500

    result = supabase.table("usuarios").select("*").eq("email", email).execute()
    user = result.data[0] if result.data else None

    if user:
        # Se o registro já existe, apenas atualiza a lista de módulos
        modulos = user.get("modulos", [])
        if modulo_real not in modulos:
            modulos.append(modulo_real)
        supabase.table("usuarios").update({"modulos": modulos}).eq("email", email).execute()
    else:
        # Se o usuário não existir, cria o registro com senha gerada de 6 dígitos
        senha_gerada = gerar_senha_6_digitos()
        supabase.table("usuarios").insert({
            "nome": "Usuário",  # Nome padrão, a ser atualizado no registro
            "email": email,
            "senha": senha_gerada,
            "modulos": [modulo_real],
            "pagamento_confirmado": True
        }).execute()
        # Envia a senha gerada por e-mail
        corpo_senha = f'''
        <h2>Bem vindo(a)!</h2>
        <p>Sua conta foi criada automaticamente após a compra.</p>
        <p>Sua senha de acesso é: <strong>{senha_gerada}</strong></p>
        <p>Utilize este e-mail e senha para acessar a plataforma e complete seu cadastro informando seu nome.</p>
        '''
        try:
            yag.send(to=email, subject="Sua senha para acesso à CYBER.DIGITAL", contents=corpo_senha)
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro ao enviar e-mail: {str(e)}"}), 500

    return jsonify({"success": True, "message": f"Acesso ao módulo {modulo_id} enviado para {email}."})

# Endpoint protegido para consulta dos dados do usuário (para o dashboard)
@app.route("/dados_usuario", methods=["GET"])
def dados_usuario():
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({"success": False, "message": "Token de autenticação é obrigatório."}), 401

    email = verify_token(token)
    
    if not email:
        return jsonify({"success": False, "message": "Token inválido ou expirado."}), 401

    result = supabase.table("usuarios").select("*").eq("email", email).execute()
    user = result.data[0] if result.data else None

    if not user:
        return jsonify({"success": False, "message": "Usuário não encontrado."}), 404

    return jsonify({
        "success": True,
        "email": user["email"],
        "nome": user.get("nome", ""),
        "modulos": user.get("modulos", [])
    })

@app.route("/", methods=["GET"])
def home():
    return "API da CYBER.DIGITAL está ativa ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
