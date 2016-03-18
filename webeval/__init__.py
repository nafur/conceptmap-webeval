from flask import Flask, request
app = Flask(__name__)

from webeval.utils import database, learner, loader, stats

@app.teardown_appcontext
def close(exception):
	database.close()

@app.context_processor
def inject_default_values():
	return {
		"topic": request.form.get('topic', ''),
		"medium": request.form.get('medium', ''),
		"timing": request.form.get('timing', ''),
		"group": request.form.get('group', ''),
		"verification_require": database.getVerificationFromMap("require", request.form),
		"verification_exclude": database.getVerificationFromMap("exclude", request.form),
		"topics": database.listTopicDict,
		"groups": database.listGroupDict,
		"verifications": database.getVerifications,
		"core_stats": stats.gatherCoreData,
		"isSet": lambda single, value: (single & value) == single
	}


import webeval.views.core
import webeval.views.learn
import webeval.views.statistics
