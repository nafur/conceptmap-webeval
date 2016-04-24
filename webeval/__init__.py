from flask import Flask, request
app = Flask(__name__, static_folder = None)

from webeval.utils import database, dbcompare, learner, loader, stats

@app.teardown_appcontext
def close(exception):
	database.close()

@app.context_processor
def inject_default_values():
	return {
		"topic": request.form.get('topic', ''),
		"medium": request.form.get('medium', ''),
		"timing": request.form.get('timing', ''),
		"ordering": request.form.get('ordering', ''),
		"group": request.form.get('group', ''),
		"verification": database.getVerificationFromMap("", request.form),
		"verification_require": database.getVerificationFromMap("require", request.form),
		"verification_exclude": database.getVerificationFromMap("exclude", request.form),
		"topics": database.listTopicDict,
		"groups": database.listGroupDict,
		"verifications": database.getVerifications,
		"orderings": database.listOrderingDict,
		"core_stats": stats.gatherCoreData,
		"isSet": lambda single, value: (single & value) == single,
		"queryLog": database.queryLog,
	}

import webeval.views.core
import webeval.views.learn
import webeval.views.statistics
