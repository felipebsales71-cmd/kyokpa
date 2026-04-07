import os
import sqlite3
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "kyokpa_super_secreta"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "alunos.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

LOCAIS = [
    "MARIA NILCE BRANDÃO",
    "CLARETIANO",
    "SEDE DA ACADEMIA",
    "JACEGUAI",
    "GIRASSOL",
    "MUCAJAÍ",
    "PRAÇA DO CARANÃ"
]

PROFESSORES = [
    "WELLINGTON SALES",
    "FELIPE SALES",
    "LOHANA SALES",
    "KAYO NAVECA",
    "JENNIFER MELO",
    "THIAGO BENJUMEA",
    "GLEIDJANISON LIMA"
]

STATUS_ALUNO = ["ATIVO", "INATIVO", "TRANCADO"]


# ================= BANCO =================

def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def criar_banco():
    conn = conectar()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            senha TEXT,
            nome TEXT,
            tipo TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            idade TEXT,
            faixa TEXT,
            nascimento TEXT,
            responsavel TEXT,
            telefone TEXT,
            local TEXT,
            professor TEXT,
            status TEXT,
            matricula TEXT,
            observacoes TEXT,
            foto TEXT
        )
    """)

    admin = conn.execute(
        "SELECT * FROM usuarios WHERE usuario = ?",
        ("admin",)
    ).fetchone()

    if not admin:
        conn.execute("""
            INSERT INTO usuarios (usuario, senha, nome, tipo)
            VALUES (?, ?, ?, ?)
        """, ("admin", "123", "Administrador", "admin"))

    conn.commit()
    conn.close()


# ================= LOGIN =================

def login_obrigatorio(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conn = conectar()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND senha = ?",
            (usuario, senha)
        ).fetchone()
        conn.close()

        if user:
            session["logado"] = True
            session["usuario_nome"] = user["nome"]
            return redirect(url_for("dashboard"))
        else:
            flash("Login inválido")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= DASHBOARD =================

@app.route("/dashboard")
@login_obrigatorio
def dashboard():
    conn = conectar()

    total = conn.execute("SELECT COUNT(*) as t FROM alunos").fetchone()["t"]

    conn.close()

    return render_template("dashboard.html", total=total)


# ================= LISTA =================

@app.route("/alunos")
@login_obrigatorio
def alunos():
    conn = conectar()
    lista = conn.execute("SELECT * FROM alunos ORDER BY nome").fetchall()
    conn.close()

    return render_template("alunos.html", alunos=lista)


# ================= CADASTRO =================

@app.route("/alunos/cadastrar", methods=["GET", "POST"])
@login_obrigatorio
def cadastrar_aluno():
    if request.method == "POST":
        nome = request.form["nome"]
        idade = request.form["idade"]
        faixa = request.form["faixa"]
        nascimento = request.form["nascimento"]
        responsavel = request.form["responsavel"]
        telefone = request.form["telefone"]
        local = request.form["local"]
        professor = request.form["professor"]
        status = request.form["status"]
        matricula = request.form["matricula"]
        observacoes = request.form["observacoes"]

        foto = request.files.get("foto")
        nome_foto = ""

        if foto and "." in foto.filename:
            nome_foto = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + secure_filename(foto.filename)
            foto.save(os.path.join(UPLOAD_FOLDER, nome_foto))

        conn = conectar()
        conn.execute("""
            INSERT INTO alunos
            (nome, idade, faixa, nascimento, responsavel, telefone, local, professor, status, matricula, observacoes, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome, idade, faixa, nascimento, responsavel,
            telefone, local, professor, status,
            matricula, observacoes, nome_foto
        ))
        conn.commit()
        conn.close()

        return redirect(url_for("alunos"))

    return render_template(
        "cadastrar_aluno.html",
        locais=LOCAIS,
        professores=PROFESSORES,
        status_opcoes=STATUS_ALUNO
    )


# ================= EDITAR =================

@app.route("/alunos/editar/<int:id>", methods=["GET", "POST"])
@login_obrigatorio
def editar_aluno(id):
    conn = conectar()
    aluno = conn.execute("SELECT * FROM alunos WHERE id = ?", (id,)).fetchone()

    if request.method == "POST":
        conn.execute("""
            UPDATE alunos SET nome=?, idade=?, faixa=?, nascimento=?, responsavel=?, telefone=?,
            local=?, professor=?, status=?, matricula=?, observacoes=?
            WHERE id=?
        """, (
            request.form["nome"],
            request.form["idade"],
            request.form["faixa"],
            request.form["nascimento"],
            request.form["responsavel"],
            request.form["telefone"],
            request.form["local"],
            request.form["professor"],
            request.form["status"],
            request.form["matricula"],
            request.form["observacoes"],
            id
        ))
        conn.commit()
        conn.close()
        return redirect(url_for("alunos"))

    conn.close()
    return render_template(
        "editar_aluno.html",
        aluno=aluno,
        locais=LOCAIS,
        professores=PROFESSORES,
        status_opcoes=STATUS_ALUNO
    )


# ================= EXCLUIR =================

@app.route("/alunos/excluir/<int:id>")
@login_obrigatorio
def excluir_aluno(id):
    conn = conectar()
    conn.execute("DELETE FROM alunos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("alunos"))


# ================= RELATÓRIOS =================

@app.route("/relatorios")
@login_obrigatorio
def relatorios():
    conn = conectar()

    dados = conn.execute("""
        SELECT local, COUNT(*) as total
        FROM alunos
        GROUP BY local
        ORDER BY total DESC
    """).fetchall()

    conn.close()

    return render_template("relatorios.html", dados=dados)


# ================= START =================

if __name__ == "__main__":
    criar_banco()
    app.run()