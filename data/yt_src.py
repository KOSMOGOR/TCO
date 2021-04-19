import sqlalchemy
from flask_login import UserMixin
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class Yt(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'yt_src'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    yt_id = sqlalchemy.Column(sqlalchemy.String, nullable=True)