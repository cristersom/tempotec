from flask import render_template, redirect, url_for, flash, request
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from tempotec import app, database, bcrypt
from tempotec.enums import Status
from tempotec.forms import FormLogin, FormCriarConta, FormEditarPerfil
from tempotec.models import Usuario, Post, Candidatura, Avaliacao
from flask_login import login_user, logout_user, current_user, login_required
import secrets
import os
from PIL import Image


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/contato')
def contato():
    return render_template('contato.html')


@app.route('/usuarios')
@login_required
def usuarios():
    lista_usuarios = Usuario.query.all()
    return render_template('usuarios.html', lista_usuarios=lista_usuarios)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form_login = FormLogin()
    if form_login.validate_on_submit() and 'botao_submit_login' in request.form:
        usuario = Usuario.query.filter_by(email=form_login.email.data).first()
        if usuario and bcrypt.check_password_hash(usuario.senha, form_login.senha.data):
            login_user(usuario, remember=form_login.lembrar_dados.data)
            flash(f'Login feito com sucesso no e-mail: {form_login.email.data}', 'success')
            par_next = request.args.get('next')
            if par_next:
                return redirect(par_next)
            else:
                return redirect(url_for('home'))
        else:
            flash(f'Falha no Login. E-mail ou Senha Incorretos', 'danger')
    return render_template('login.html', form_login=form_login)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form_criarconta = FormCriarConta()
    if form_criarconta.validate_on_submit() and 'botao_submit_criarconta' in request.form:
        senha_cript = bcrypt.generate_password_hash(form_criarconta.senha.data)
        usuario = Usuario(username=form_criarconta.username.data, email=form_criarconta.email.data, senha=senha_cript)
        database.session.add(usuario)
        database.session.commit()
        flash(f'Conta criada para o e-mail: {form_criarconta.email.data}', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', form_criarconta=form_criarconta)


@app.route('/sair')
@login_required
def sair():
    logout_user()
    flash(f'Logout feito com sucesso', 'success')
    return redirect(url_for('home'))


@app.route('/perfil')
@login_required
def perfil():
    foto_perfil = url_for('static', filename='fotos_perfil/{}'.format(current_user.foto_perfil))

    candidaturas_usuario = Candidatura.query \
        .join(Post, Candidatura.id_post == Post.id) \
        .filter(Candidatura.id_usuario == current_user.id) \
        .order_by(Candidatura.data_criacao.desc()) \
        .all()


    return render_template('perfil.html',
                           foto_perfil=foto_perfil,
                           candidaturas_usuario=candidaturas_usuario)


@app.route('/post/criar', methods=['GET', 'POST'])
@login_required
def criar_post():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        corpo = request.form.get('corpo')

        if not titulo or not corpo:
            flash('Título e corpo são obrigatórios.', 'danger')
            return redirect(url_for('criar_post'))

        novo_post = Post(
            titulo=titulo,
            corpo=corpo,
            id_usuario=current_user.id,
         )
        database.session.add(novo_post)
        database.session.commit()
        flash('Post criado com sucesso!', 'success')
        return redirect(url_for('home'))
    return render_template('criarpost.html')


@app.route('/posts')
def listar_posts():
    subquery = select(Candidatura.id_post).where(Candidatura.id_usuario == current_user.id)

    posts = Post.query.options(joinedload(Post.autor)) \
        .filter(Post.id_usuario != current_user.id) \
        .filter(Post.id.not_in(subquery)) \
        .order_by(Post.data_criacao.desc()) \
        .all()
    return render_template('listarposts.html', posts=posts)


@app.route('/posts/candidatar', methods=['POST'])
def candidatar_post():
    candidatura = Candidatura(
        id_usuario=current_user.id,
        id_post=request.form.get('post_id'),
    )
    database.session.add(candidatura)
    database.session.commit()
    flash('Candidatura realizada com sucesso!', 'success')
    return redirect(url_for('listar_posts'))


@app.route('/aceitar_candidato', methods=['POST'])
@login_required
def aceitar_candidato():
    candidatura_id = request.form.get('candidatura_id')
    candidatura = Candidatura.query.get_or_404(candidatura_id)

    candidatura.status = Status.APROVADO

    Candidatura.query.filter(
        Candidatura.id_post == candidatura.id_post,
        Candidatura.id != candidatura.id
    ).update({Candidatura.status: Status.REJEITADO}, synchronize_session='fetch')

    database.session.commit()

    flash(f'Candidato {candidatura.usuario.username} aceito com sucesso!', 'success')
    return redirect(url_for('perfil'))


def salvar_imagem(imagem):
    codigo = secrets.token_hex(8)
    nome, extensao = os.path.splitext(imagem.filename)
    nome_arquivo = nome + codigo + extensao
    caminho_completo = os.path.join(app.root_path, 'static/fotos_perfil', nome_arquivo)
    tamanho = (400, 400)
    imagem_reduzida = Image.open(imagem)
    imagem_reduzida.thumbnail(tamanho)
    imagem_reduzida.save(caminho_completo)
    return nome_arquivo


def atualizar_cursos(form):
    lista_cursos = []
    for campo in form:
        if 'curso_' in campo.name:
            if campo.data:
                lista_cursos.append(campo.label.text)
    return ';'.join(lista_cursos)


@app.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    form = FormEditarPerfil()
    if form.validate_on_submit():
        current_user.email = form.email.data
        current_user.username = form.username.data
        if form.foto_perfil.data:
            nome_imagem = salvar_imagem(form.foto_perfil.data)
            current_user.foto_perfil = nome_imagem
        current_user.cursos = atualizar_cursos(form)
        database.session.commit()
        flash('Perfil atualizado com sucesso', 'success')
        return redirect(url_for('perfil'))
    elif request.method == "GET":
        form.email.data = current_user.email
        form.username.data = current_user.username
    foto_perfil = url_for('static', filename='fotos_perfil/{}'.format(current_user.foto_perfil))
    return render_template('editarperfil.html', foto_perfil=foto_perfil, form=form)


@app.route('/avaliar_usuario', methods=['POST'])
@login_required
def avaliar_usuario():
    id_usuario = request.form.get('avaliado_id')
    id_post = request.form.get('post_id')
    nota = int(request.form.get('nota'))

    existing = Avaliacao.query.filter_by(
        id_usuario=id_usuario,
        id_post=id_post,
        id_avaliador=current_user.id
    ).first()

    if existing:
        flash('Você já avaliou este usuário.', 'info')
        return redirect(request.referrer)

    avaliacao = Avaliacao(
        id_post=id_post,
        id_usuario=id_usuario,
        id_avaliador=current_user.id,
        nota=nota
    )

    candidatura = Candidatura.query.filter_by(
        id_usuario=id_usuario,
        id_post=id_post
    ).first()

    if candidatura:
        candidatura.status = Status.APROVADO

    database.session.add(avaliacao)
    database.session.add(candidatura)
    database.session.commit()

    flash('Avaliação registrada com sucesso!', 'success')
    return redirect(request.referrer)


