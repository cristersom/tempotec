from sqlalchemy import func

from tempotec import database, login_manager
from datetime import datetime
from flask_login import UserMixin


@login_manager.user_loader
def load_usuario(id_usuario):
    return Usuario.query.get(int(id_usuario))


class Usuario(database.Model, UserMixin):
    id = database.Column(database.Integer, primary_key=True)
    username = database.Column(database.String, nullable=False)
    email = database.Column(database.String, nullable=False, unique=True)
    senha = database.Column(database.String, nullable=False)
    foto_perfil = database.Column(database.String, default='default.jpg')
    posts = database.relationship('Post', backref='autor', lazy=True)
    cursos = database.Column(database.String, nullable=False, default='Não Informado')

    def media_avaliacao(self):
        avg = database.session.query(func.avg(Avaliacao.nota)) \
            .filter(Avaliacao.id_usuario == self.id).scalar()
        return round(avg or 0, 1)

    def foi_avaliado_por(self, avaliador_id, post_id):
        return Avaliacao.query.filter_by(
            id_usuario=self.id,
            id_avaliador=avaliador_id,
            id_post=post_id
        ).first() is not None


class Post(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    titulo = database.Column(database.String, nullable=False)
    corpo = database.Column(database.Text, nullable=False)
    data_criacao = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)
    id_usuario = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)
    candidaturas = database.relationship('Candidatura', backref='post', lazy=True, foreign_keys='Candidatura.id_post')


class Candidatura(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    data_criacao = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)
    id_usuario = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)
    id_post = database.Column(database.Integer, database.ForeignKey('post.id'), nullable=False)
    status = database.Column(database.Integer, database.ForeignKey('post.id'), nullable=False, default=0)
    usuario = database.relationship('Usuario', backref='candidaturas', foreign_keys=[id_usuario])


class Avaliacao(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    data_criacao = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)
    id_post = database.Column(database.Integer, database.ForeignKey('post.id'), nullable=False)
    id_usuario = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)
    id_avaliador = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)
    nota = database.Column(database.Integer, primary_key=False, default=0, nullable=False)