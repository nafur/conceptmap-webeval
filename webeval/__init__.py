from flask import Flask
#from flask.ext.babel import Babel
app = Flask(__name__)
#babel = Babel(app)

from webeval.utils import database, loader, stats

@app.teardown_appcontext
def close(exception):
	database.close()

import webeval.views.core
import webeval.views.statistics
