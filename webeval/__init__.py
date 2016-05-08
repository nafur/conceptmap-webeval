import builtins
import subprocess
from flask import Flask, request
app = Flask(__name__, static_folder = None)

builtins.VERSION = 0.1
def getVersion():
	commitdate = open("webeval/.commit-date").read()
	r = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr = subprocess.PIPE).decode("utf8")
	if r == "": return "v%s @ %s" % (VERSION, commitdate)
	return "v%s @ %s / #%s" % (VERSION, commitdate, r[:8])

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
		"version": getVersion,
	}

import webeval.views.core
import webeval.views.learn
import webeval.views.statistics
