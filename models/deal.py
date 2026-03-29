from database.init_db import db

class Deal(db.Model):
    __tablename__ = 'deals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    stage = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    probability = db.Column(db.Integer, nullable=False, default=50)
    expected_close_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Deal {self.name} {self.stage}>'
