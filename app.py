import os
import sqlite3
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "kyokpa_super_secreta_123"

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

STATUS_ALUNO = [
    "ATIVO",
    "INATIVO",
    "TRANCADO"
]


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def salvar_foto(arquivo):
    if not arquivo or not arquivo.filename:
        return ""

    if not allowed_file(arquivo.filename):
        return ""

    nome_seguro = secure_filename(arquivo.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    nome_final = f"{timestamp}_{nome_seguro}"
    caminho = os.path.join(UPLOAD_FOLDER, nome_final)
    arquivo.save(caminho)
    return nome_final


def criar_banco():
    conn = conectar()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'professor'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            idade TEXT NOT NULL,
            faixa TEXT NOT NULL,
            nascimento TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            telefone TEXT NOT NULL,
            local TEXT NOT NULL,
            professor TEXT NOT NULL,
            status TEXT NOT NULL,
            matricula TEXT NOT NULL,
            observacoes TEXT,
            foto TEXT
        )
    """)

    admin = conn.execute(
        "SELECT * FROM usuarios WHERE usuario = ?",
        ("admin",)
    ).fetchone()

    if not admin:
        conn.execute(
            "INSERT INTO usuarios (usuario, senha, nome, tipo) VALUES (?, ?, ?, ?)",
            ("admin", "123", "Administrador", "admin")
        )

    conn.commit()
    conn.close()


def login_obrigatorio(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("logado"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "").strip()

        conn = conectar()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND senha = ?",
            (usuario, senha)
        ).fetchone()
        conn.close()

        if user:
            session["logado"] = True
            session["usuario_id"] = user["id"]
            session["usuario_nome"] = user["nome"]
            session["usuario_login"] = user["usuario"]
            session["usuario_tipo"] = user["tipo"]
            return redirect(url_for("dashboard"))

        flash("Usuário ou senha inválidos.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_obrigatorio
def dashboard():
    conn = conectar()

    total = conn.execute("SELECT COUNT(*) AS total FROM alunos").fetchone()["total"]
    ativos = conn.execute("SELECT COUNT(*) AS total FROM alunos WHERE status = 'ATIVO'").fetchone()["total"]
    inativos = conn.execute("SELECT COUNT(*) AS total FROM alunos WHERE status = 'INATIVO'").fetchone()["total"]
    trancados = conn.execute("SELECT COUNT(*) AS total FROM alunos WHERE status = 'TRANCADO'").fetchone()["total"]

    conn.close()

    return render_template(
        "dashboard.html",
        total=total,
        ativos=ativos,
        inativos=inativos,
        trancados=trancados
    )
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

@app.route("/alunos")
@login_obrigatorio
def alunos():
    busca = request.args.get("busca", "").strip()
    local = request.args.get("local", "").strip()
    status = request.args.get("status", "").strip()

    query = "SELECT * FROM alunos WHERE 1=1"
    params = []

    if busca:
        query += " AND nome LIKE ?"
        params.append(f"%{busca}%")

    if local:
        query += " AND local = ?"
        params.append(local)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY nome ASC"

    conn = conectar()
    lista = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "alunos.html",
        alunos=lista,
        busca=busca,
        local_filtro=local,
        status_filtro=status,
        locais=LOCAIS,
        status_opcoes=STATUS_ALUNO
    )


@app.route("/alunos/cadastrar", methods=["GET", "POST"])
@login_obrigatorio
def cadastrar_aluno():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        idade = request.form.get("idade", "").strip()
        faixa = request.form.get("faixa", "").strip()
        nascimento = request.form.get("nascimento", "").strip()
        responsavel = request.form.get("responsavel", "").strip()
        telefone = request.form.get("telefone", "").strip()
        local = request.form.get("local", "").strip()
        professor = request.form.get("professor", "").strip()
        status = request.form.get("status", "").strip()
        matricula = request.form.get("matricula", "").strip()
        observacoes = request.form.get("observacoes", "").strip()

        if not all([nome, idade, faixa, nascimento, responsavel, telefone, local, professor, status, matricula]):
            flash("Preencha todos os campos obrigatórios.")
            return redirect(url_for("cadastrar_aluno"))

        foto = request.files.get("foto")
        foto_nome = salvar_foto(foto)

        conn = conectar()
        conn.execute("""
            INSERT INTO alunos
            (nome, idade, faixa, nascimento, responsavel, telefone, local, professor, status, matricula, observacoes, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome, idade, faixa, nascimento, responsavel, telefone,
            local, professor, status, matricula, observacoes, foto_nome
        ))
        conn.commit()
        conn.close()

        flash("Aluno cadastrado com sucesso.")
        return redirect(url_for("alunos"))

    return render_template(
        "cadastrar_aluno.html",
        locais=LOCAIS,
        professores=PROFESSORES,
        status_opcoes=STATUS_ALUNO
    )


@app.route("/alunos/editar/<int:aluno_id>", methods=["GET", "POST"])
@login_obrigatorio
def editar_aluno(aluno_id):
    conn = conectar()
    aluno = conn.execute(
        "SELECT * FROM alunos WHERE id = ?",
        (aluno_id,)
    ).fetchone()

    if not aluno:
        conn.close()
        flash("Aluno não encontrado.")
        return redirect(url_for("alunos"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        idade = request.form.get("idade", "").strip()
        faixa = request.form.get("faixa", "").strip()
        nascimento = request.form.get("nascimento", "").strip()
        responsavel = request.form.get("responsavel", "").strip()
        telefone = request.form.get("telefone", "").strip()
        local = request.form.get("local", "").strip()
        professor = request.form.get("professor", "").strip()
        status = request.form.get("status", "").strip()
        matricula = request.form.get("matricula", "").strip()
        observacoes = request.form.get("observacoes", "").strip()

        foto_nome = aluno["foto"]
        nova_foto = request.files.get("foto")

        if nova_foto and nova_foto.filename:
            foto_nome = salvar_foto(nova_foto)

        conn.execute("""
            UPDATE alunos
            SET nome = ?, idade = ?, faixa = ?, nascimento = ?, responsavel = ?,
                telefone = ?, local = ?, professor = ?, status = ?, matricula = ?,
                observacoes = ?, foto = ?
            WHERE id = ?
        """, (
            nome, idade, faixa, nascimento, responsavel, telefone,
            local, professor, status, matricula, observacoes, foto_nome, aluno_id
        ))
        conn.commit()
        conn.close()

        flash("Aluno atualizado com sucesso.")
        return redirect(url_for("alunos"))

    conn.close()
    return render_template(
        "editar_aluno.html",
        aluno=aluno,
        locais=LOCAIS,
        professores=PROFESSORES,
        status_opcoes=STATUS_ALUNO
    )


@app.route("/alunos/excluir/<int:aluno_id>", methods=["POST"])
@login_obrigatorio
def excluir_aluno(aluno_id):
    conn = conectar()
    conn.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    conn.commit()
    conn.close()
    flash("Aluno excluído com sucesso.")
    return redirect(url_for("alunos"))


if __name__ == "__main__":
    criar_banco()
    app.run(debug=True)
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