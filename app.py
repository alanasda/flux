from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from werkzeug.security import generate_password_hash
import random
import yagmail
import os

app = Flask(__name__)
CORS(app)

# Configuração Supabase
SUPABASE_URL = "https://szbptsuvjmaqkcgsgagx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6YnB0c3V2am1hcWtjZ3NnYWd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxNjA3MjEsImV4cCI6MjA1OTczNjcyMX0.wqjSCJ8evNog5AnP2dzk1t2nkn31EfvqDuaAkXDiqNo"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuração de e-mail
EMAIL_REMETENTE = "cyberdigitalsuporte@gmail.com"
EMAIL_SENHA_APP = "ufvz jkdc ihpu ksak"  # senha de app do Gmail
yag = yagmail.SMTP(EMAIL_REMETENTE, EMAIL_SENHA_APP)

def gerar_senha_6_digitos():
    return str(random.randint(100000, 999999))

@app.route("/webhook/<int:modulo_id>", methods=["POST"])
def webhook_envio(modulo_id):
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "message": "E-mail é obrigatório."}), 400

    # gera sempre uma nova senha (vai sobrescrever a anterior)
    senha_gerada = gerar_senha_6_digitos()
    senha_hash = generate_password_hash(senha_gerada)

    # busca usuário
    res = supabase.table("usuarios").select("*").eq("email", email).execute()
    user = res.data[0] if res.data else None

    if user:
        # atualiza senha, módulos e marca pagamento
        modulos = user.get("modulos", [])
        if modulo_id not in modulos:
            modulos.append(modulo_id)
        supabase.table("usuarios").update({
            "senha": senha_hash,
            "modulos": modulos,
            "pagamento_confirmado": True
        }).eq("email", email).execute()
    else:
        # cria novo usuário
        supabase.table("usuarios").insert({
            "nome": "Usuário",
            "email": email,
            "senha": senha_hash,
            "modulos": [modulo_id],
            "pagamento_confirmado": True
        }).execute()

    # monta o HTML completo com senha
    corpo = [f'''
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #f90;">🎉 Bem-vindo à CYBER.DIGITAL!</h2>
        <p>Olá, obrigado por acessar a <strong>CYBER.DIGITAL</strong>.</p>
        <p>Sua conta foi criada (ou atualizada) automaticamente após a compra.</p>
        <p>Use o <strong>mesmo Gmail da compra</strong> para entrar na plataforma.</p>
        <p><strong>Sua senha de acesso:</strong></p>
        <p style="font-size: 20px; font-weight: bold; color: #000;">{senha_gerada}</p>
        <p>Clique no botão abaixo para acessar:</p>
        <a href="https://cyberflux.onrender.com" style="
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(45deg, orange, gold);
            color: white;
            font-weight: bold;
            border-radius: 8px;
            text-decoration: none;
            margin-top: 10px;">
            Acessar a Plataforma
        </a>
        <p style="margin-top: 30px;">
          Qualquer dúvida, fale com a gente.<br><br>
          Obrigado,<br>
          Equipe de Suporte - <strong>CyberDigital 🚀</strong>
        </p>
      </body>
    </html>
    ''']

    # envia o e‑mail
    yag.send(
      to=email,
      subject="🎫 Acesso à plataforma CYBER.DIGITAL liberado!",
      contents=corpo
    )

    return jsonify({"success": True, "message": f"Conta criada/atualizada e módulo {modulo_id} liberado para {email}."})

if __name__ == "__main__":
    app.run(debug=True, port=10000)
