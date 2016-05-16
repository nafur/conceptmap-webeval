import builtins
import subprocess
from flask import Flask, request
app = Flask(__name__, static_folder = None)

builtins.VERSION = "0.3.0"
builtins.DBVERSION = "0.3"

def getCommitDate():
	return open("webeval/.commit-date").read()

def getCommitHash():
	try:
		return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr = subprocess.PIPE).decode("utf8")[:8]
	except:
		return ""

def getVersionString():
	h = getCommitHash()
	if h == "": return "v%s @ %s" % (VERSION, getCommitDate())
	return "v%s @ %s / #%s" % (VERSION, getCommitDate(), h)

from webeval.utils import database, dbcompare, dbupgrade, export, learner, loader, stats

def getDBVersionState():
	dbversion = database.getVersion()
	if dbversion == DBVERSION: return ""
	return dbversion

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
		"version": VERSION,
		"version_date": getCommitDate,
		"version_hash": getCommitHash,
		"version_string": getVersionString,
		"dbversionstate": getDBVersionState,
		"dbversion": database.getVersion,
	}

import webeval.views.core
import webeval.views.export
import webeval.views.learn
import webeval.views.statistics
