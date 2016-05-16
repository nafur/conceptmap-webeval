import functools
import inspect
import os.path
import sqlite3
import sys
from flask import g,request

DBFILE = "db.sqlite"
VERIFICATION_FLAGS = ["fully verified", "formally correct", "content-wise correct", "structurally correct", "functionally correct"]
VERIFICATION_ICONS = [["remove","ok"],["remove","ok"],["remove","ok"],["remove","ok"],["remove","ok"]]

def db():
	db = getattr(g, '_database', None)
	if db is None:
		db = g._database = sqlite3.connect(DBFILE)
		db.row_factory = sqlite3.Row
		cursor = db.cursor()
		cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
		if cursor.fetchall() == []:
			createTables()
	return db

def openMergedDB(filename):
	db = sqlite3.connect(':memory:')
	db.row_factory = sqlite3.Row
	c = db.cursor()
	c.execute("ATTACH DATABASE '%s' AS db1" % DBFILE)
	c.execute("ATTACH DATABASE '%s' AS db2" % filename)
	return db

def close():
	db = getattr(g, '_database', None)
	if db is not None:
		db.close()

def cursor():
	return db().cursor()

def reset():
	if os.path.isfile(DBFILE):
		os.unlink(DBFILE)

def createTables():
	db().execute('''CREATE TABLE config (name text, value text)''')
	db().execute('''INSERT INTO config (name,value) VALUES (?,?)''', ("version", DBVERSION))
	# Table of different topics being tested
	db().execute('''CREATE TABLE topics (id integer primary key, name text, shortcode text)''')
	# Table of all the nodes (or terms) that must be connected. Each node is associated with a topic.
	db().execute('''CREATE TABLE nodes (id integer primary key, topic int, name text)''')
	# Table of all students that participate. Each student is part of a group (or class) and learned the topic using a specific medium.
	db().execute('''CREATE TABLE students (id integer primary key, name text, medium text, class text)''')
	# Table of all solutions that the students submitted for some topic. The students work on the topics sequentially, thus there is an ordering. Furthermore, a student submits a solution both before and after the practical course.
	db().execute('''CREATE TABLE solutions (id integer primary key, student int, topic int, ordering int, timing text)''')
	# Table of all answers (or edges in one final solution). They are ordered chronologically and consist of the source and destination node and the description of the edge. They can be verified using the flags defined in VERIFICATION_FLAGS and can be delayed within the verification process.
	db().execute('''CREATE TABLE answers (id integer primary key, solution int, ordering int, src int, dest int, description text, verification int DEFAULT 0, delay int DEFAULT 0)''')
	# Table of the progress of a solution. Compared to the answers, it not only contains the final edges but all actions performed during the solution.
	db().execute('''CREATE TABLE progress (id integer primary key, solution int, ordering int, action int, src int, dest int, description text)''')

	# View on all answers
	db().execute('''
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

def getVersion():
	try:
		return db().execute("SELECT value FROM config WHERE name='version'").fetchone()["value"]
	except:
		return "before-versioning"

def addQueryLog(caller, query, params):
	queryLog().append((caller,query, params))

def queryLog():
	ql = getattr(request, '_querylog', None)
	if ql is None:
		ql = request._querylog = []
	return ql

def executeFiltered(query, topic = "", timing = "", medium = "", ordering = "", group = "", verification_require = "", verification_exclude = "", params_before = [], params_after = []):
	f = []
	if topic != "": f.append(("(view_answers.topic=?)", [topic]))
	if timing != "": f.append(("(timing LIKE ?)", [timing]))
	if medium != "": f.append(("(medium LIKE ?)", [medium]))
	if ordering != "": f.append(("(ordering=?)", [ordering]))
	if group != "": f.append(("(class=?)", [group]))
	if verification_require != "": f.append(("(verification & ? = ?)", [verification_require,verification_require]))
	if verification_exclude != "": f.append(("(verification & ? = 0)", [verification_exclude]))
	query = query.replace("${FILTER}", " AND ".join(map(lambda x: x[0], f)))
	params = params_before + sum(map(lambda x: x[1], f), params_after)
	try:
		caller = inspect.getouterframes(inspect.currentframe(), 2)[1][3]
		addQueryLog(caller + "()", query, params)
	except:
		pass
	return cursor().execute(query, params)

def addTopic(name):
	c = cursor()
	c.execute("SELECT id FROM topics WHERE name LIKE ?", (name,))
	res = c.fetchone()
	if res != None:
		return res[0]
	with db():
		c.execute("INSERT INTO topics (name) VALUES (?)", (name,))
	return c.lastrowid

def getTopic(id):
	return cursor().execute("SELECT * FROM topics WHERE id=?", (id,)).fetchone()

def listTopics():
	return cursor().execute("SELECT * FROM topics ORDER BY name").fetchall()
def listTopicDict():
	list = cursor().execute("SELECT * FROM topics ORDER BY name").fetchall()
	return {t["id"]: t["name"] for t in list}

def listGroups():
	return cursor().execute("SELECT DISTINCT students.class FROM students").fetchall()
def listGroupDict():
	list = cursor().execute("SELECT DISTINCT students.class FROM students").fetchall()
	res = {g["class"]: g["class"] for g in list}
	res[""] = "All groups"
	return res

def listMediums():
	return cursor().execute("SELECT DISTINCT students.medium FROM students").fetchall()

def addStudent(name, medium, group):
	c = cursor()
	c.execute("SELECT id FROM students WHERE medium=? AND class=? AND name LIKE ?", (medium,group,name))
	res = c.fetchone()
	if res != None:
		return res[0]
	with db():
		c.execute("INSERT INTO students (name,medium,class) VALUES (?,?,?)", (name,medium,group))
	return c.lastrowid

def getStudent(id):
	return cursor().execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()

def listStudents():
	return cursor().execute("SELECT DISTINCT students.* FROM students ORDER BY name").fetchall()
def listStudentsByGroup(group):
	return cursor().execute("SELECT DISTINCT students.* FROM students WHERE class=? ORDER BY name", (group,)).fetchall()
def listStudentsByTopic(topic):
	return cursor().execute("SELECT students.* FROM students LEFT JOIN solutions ON (students.id = solutions.student) WHERE solutions.topic = ? GROUP BY students.id ORDER BY name", (topic,)).fetchall()
def listStudentsByFilter(topic = "", medium = "", group = "", ordering = "", timing = "", verification_require = "", verification_exclude = ""):
	query = """
SELECT student AS id, name
FROM view_answers
WHERE ${FILTER}
GROUP BY student
ORDER BY name
"""
	return executeFiltered(query, topic, timing, medium, ordering, group, verification_require, verification_exclude).fetchall()

def countStudents(**kwargs):
	return len(listStudentsByFilter(**kwargs))

def addSolution(student, ordering, topic, timing):
	c = cursor()
	c.execute("SELECT id FROM solutions WHERE student=? AND ordering=? AND topic=? AND timing=?", (student,ordering,topic,timing))
	res = c.fetchone()
	if res != None:
		return res[0]
	with db():
		c.execute("INSERT INTO solutions (student,ordering,topic,timing) VALUES (?,?,?,?)", (student,ordering,topic,timing))
	return c.lastrowid

def listSolutions():
	return cursor().execute("""
SELECT
	solutions.id,
	solutions.student,
	solutions.ordering,
	solutions.timing,
	students.name AS studentname,
	topics.name AS topicname
FROM solutions
INNER JOIN students ON (solutions.student = students.id)
INNER JOIN topics ON (solutions.topic = topics.id)
""").fetchall()

def addNode(topic, name):
	c = cursor()
	c.execute("SELECT id FROM nodes WHERE topic=? AND name LIKE ?", (topic,name))
	res = c.fetchone()
	if res != None:
		return res[0]
	with db():
		c.execute("INSERT INTO nodes (topic,name) VALUES (?,?)", (topic,name))
	return c.lastrowid

def getNode(id):
	return cursor().execute("SELECT * FROM nodes WHERE id=?", (id,)).fetchone()

def listNodes(topic):
	return cursor().execute("SELECT * FROM nodes WHERE topic=? ORDER BY name", (topic,)).fetchall()

def countNodes(topic):
	return len(listNodes(topic))

def listOrderingDict(topic):
	d = {str(c["ordering"]): str(c["ordering"]) for c in cursor().execute("SELECT DISTINCT ordering FROM solutions WHERE topic=? ORDER BY ordering", (topic,)).fetchall()}
	d[""] = "All"
	return d

def addAnswer(solution, ordering, src, dest, desc):
	with db():
		cursor().execute("INSERT OR IGNORE INTO answers (solution,ordering,src,dest,description) VALUES (?,?,?,?,?)", (solution,ordering,src,dest,desc))

def addAnswerTransactional(list):
	with db():
		for l in list:
			solution, ordering, src, dest, desc = l
			cursor().execute("INSERT OR IGNORE INTO answers (solution,ordering,src,dest,description) VALUES (?,?,?,?,?)", (solution,ordering,src,dest,desc))

def getAnswer(id):
	return cursor().execute("""
SELECT
	answers.id AS id,
	src AS srcid,
	srcnode.name AS src,
	dest AS destid,
	destnode.name AS dest,
	description,
	answers.verification
FROM answers
INNER JOIN solutions ON (answers.solution = solutions.id)
LEFT JOIN nodes AS srcnode ON (answers.src = srcnode.id)
LEFT JOIN nodes AS destnode ON (answers.dest = destnode.id)
WHERE answers.id = ?
	""", (id,)).fetchone()

def addProgress(solution, ordering, action, src, dest, desc):
	actionmap = {"create": 0, "rename": 1, "remove": 2}
	action = actionmap[action]
	with db():
		cursor().execute("INSERT OR IGNORE INTO progress (solution,ordering,action,src,dest,description) VALUES (?,?,?,?,?,?)", (solution,ordering,action,src,dest,desc))

def addProgressTransactional(list):
	actionmap = {"create": 0, "rename": 1, "remove": 2}
	with db():
		for l in list:
			solution, ordering, action, src, dest, desc = l
			action = actionmap[action]
			cursor().execute("INSERT OR IGNORE INTO progress (solution,ordering,action,src,dest,description) VALUES (?,?,?,?,?,?)", (solution,ordering,action,src,dest,desc))

def delayAnswer(id):
	with db():
		cursor().execute("UPDATE answers SET delay = delay + 1 WHERE id = ?", (id,))

def searchVerificationMatch(topic, src, dest, desc):
	with db():
		return cursor().execute("SELECT * FROM answers INNER JOIN solutions ON (answers.solution = solutions.id) WHERE verification & 1 = 1 AND topic=? AND src=? AND dest=? AND description LIKE ? GROUP BY description", (topic,src,dest,desc)).fetchall()

def autoVerify():
	query = """
REPLACE INTO answers (id, solution, ordering, src, dest, description, verification, delay)
SELECT a1.id, a1.solution, a1.ordering, a1.src, a1.dest, a1.description, a2.verification, a1.delay
FROM answers AS a1
INNER JOIN solutions AS s1 ON (a1.solution = s1.id)
INNER JOIN answers AS a2 ON (a1.src=a2.src AND a1.dest=a2.dest AND a1.description LIKE a2.description)
INNER JOIN solutions AS s2 ON (a2.solution = s2.id AND s1.topic = s2.topic)
WHERE a1.verification=0 AND a2.verification!=0
GROUP BY a1.id
"""
	with db():
		cursor().execute(query)

def unverifiedAnswers(topic, limit = 10):
	autoVerify()
	return cursor().execute("""
SELECT
	answers.id AS id,
	src AS srcid,
	srcnode.name AS src,
	dest AS destid,
	destnode.name AS dest,
	description,
	answers.verification,
	answers.delay,
	answers.solution,
	students.name AS studentname
FROM answers
INNER JOIN solutions ON (answers.solution = solutions.id)
LEFT JOIN nodes AS srcnode ON (answers.src = srcnode.id)
LEFT JOIN nodes AS destnode ON (answers.dest = destnode.id)
LEFT JOIN students ON (solutions.student = students.id)
WHERE solutions.topic = ? AND answers.verification & 1 = 0
ORDER BY delay ASC
LIMIT ?
	""", (topic,limit)).fetchall()

def packVerification(args):
	flag = 0
	n = 0
	for f in VERIFICATION_FLAGS:
		if f in args:
			flag += 2**n
		n += 1
	return flag

def unpackVerification(flag):
	res = []
	for f in VERIFICATION_FLAGS:
		if flag % 2 == 1:
			res.append(f)
		flag //= 2
	return res

def unpackVerificationIcons(flag):
	res = []
	for i in range(len(VERIFICATION_FLAGS)):
		res.append([VERIFICATION_FLAGS[i], VERIFICATION_ICONS[i][flag % 2]])
		flag //= 2
	return res

def getVerificationMap():
	return {2**i: VERIFICATION_FLAGS[i] for i in range(len(VERIFICATION_FLAGS))}

def getVerificationFromMap(prefix, map):
	return functools.reduce(
		lambda x,y: x | y,
		[2**id if map.get("verification_%s_%d" % (prefix,2**id), 0) == "on" else 0 for id in range(len(VERIFICATION_FLAGS))],
		0
	)

def getVerifications():
	return [{"id": 2**i, "name": VERIFICATION_FLAGS[i], "icon": VERIFICATION_ICONS[i]} for i in range(len(VERIFICATION_FLAGS))]

def firstVerification():
	return VERIFICATION_FLAGS[0]

def listVerifications():
	return VERIFICATION_FLAGS[1:]

def setVerification(answer, flag):
	print("Setting to %d" % flag)
	with db():
		cursor().execute("UPDATE answers SET verification=? WHERE id=?", (flag,answer))

def toggleVerification(answer, flag):
	flag = 2**VERIFICATION_FLAGS.index(flag)
	with db():
		cursor().execute("UPDATE answers SET verification=((~verification & ?) | (verification & ~?)) WHERE id=?", (flag,flag,answer))
