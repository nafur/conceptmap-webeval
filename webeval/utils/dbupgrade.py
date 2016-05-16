from webeval.utils import database

def upgradeFrom(baseVersion):
	msgs = []
	if baseVersion == "before-versioning":
		msgs += createAnswerView()
		msgs += createConfigTable()
		setVersion("0.1")
	else:
		msgs.append("Upgrade from version %s is not implemented." % baseVersion)
	return msgs

def upgradeDB():
	msgs = []
	baseVersion = database.getVersion()
	while baseVersion != DBVERSION:
		msgs += upgradeFrom(baseVersion)
		if baseVersion == database.getVersion(): break
		baseVersion = database.getVersion()
	return msgs

def setVersion(version):
	with database.db():
		database.cursor().execute("REPLACE INTO config (name,value) VALUES (?,?)", ("version", version))

def tableExists(name, type = "table"):
	res = database.db().execute("SELECT name FROM sqlite_master WHERE type=? AND name=?", (type, name)).fetchall()
	return len(res) > 0

def columnExists(table, name):
	cols = database.db().execute("PRAGMA table_info('%s')" % table).fetchall()
	cols = filter(lambda r: r["name"] == name, cols)
	return len(cols) > 0

def createAnswerView():
	if tableExists('view_answers', 'view'):
		return ["View \"view_answers\" already exists."]
	database.db().execute('''
CREATE VIEW view_answers AS
SELECT
	answers.id,
	answers.solution,
	answers.src,
	answers.dest,
	answers.description,
	answers.verification,
	answers.delay,
	solutions.student,
	solutions.ordering,
	solutions.topic,
	solutions.timing,
	students.name,
	students.medium,
	students.class
FROM answers
INNER JOIN solutions ON (answers.solution = solutions.id)
INNER JOIN students ON (solutions.student = students.id)
''')
	return ["Created view \"view_answers\"."]

def createConfigTable():
	if tableExists('config'):
		return ["Table \"config\" already exists."]
	database.db().execute('''CREATE TABLE config (name text, value text)''')
	return ["Create table \"config\"."]
