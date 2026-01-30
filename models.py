# models.py   (replace or add to your existing file)

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

class CellData(db.Model):
    __tablename__ = "cell_data"

    id = db.Column(db.Integer, primary_key=True)
    page_name   = db.Column(db.String(100), nullable=False, index=True)
    row_index   = db.Column(db.Integer, nullable=False)
    col_index   = db.Column(db.Integer, nullable=False)
    cell_value  = db.Column(db.Text, nullable=True)          # allow NULL or empty

    __table_args__ = (
        UniqueConstraint('page_name', 'row_index', 'col_index', name='unique_cell'),
    )

    def __repr__(self):
        return f"<Cell {self.page_name} [{self.row_index},{self.col_index}] = {self.cell_value}>"