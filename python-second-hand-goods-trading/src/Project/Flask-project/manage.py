from flask_migrate import Migrate,MigrateCommand
from flask_script import Manager
from main import app
from extensions import db
from models import User,Item,Comment,Interest

manager = Manager(app)

migrate = Migrate(app,db)

manager.add_command('db',MigrateCommand)

if __name__ == '__main__':
    manager.run()