import functools
import os.path
import sqlite3
import sys
from flask import g

DBFILE = "db.sqlite"
VERIFICATION_FLAGS = ["fully verified", "formally correct", "content-wise correct", "structurally correct", "functionally correct"]
VERIFICATION_ICONS = [["remove","ok"],["remove","ok"],["remove","ok"],["remove","ok"],["remove","ok"]]

def createTables():
	db().execute('''CREATE TABLE topics (id integer primary key, name text)''')
	db().execute('''CREATE TABLE nodes (id integer primary key, topic int, name text)''')
	db().execute('''CREATE TABLE students (id integer primary key, name text, medium text, class text)''')
	db().execute('''CREATE TABLE solutions (id integer primary key, student int, ordering int, topic int, timing int)''')
	db().execute('''CREATE TABLE answers (id integer primary key, solution int, ordering int, src int, dest int, description text, verification int DEFAULT 0, delay int DEFAULT 0)''')
	#db().execute('''CREATE UNIQUE INDEX answers_unique ON answers(solution,src,dest)''')
	db().execute('''CREATE TABLE progress (id integer primary key, solution int, ordering int, action int, src int, dest int, description text)''')
	db().execute('''CREATE UNIQUE INDEX progress_unique ON progress(solution,ordering)''')

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

def close():
	db = getattr(g, '_database', None)
	if db is not None:
		db.close()

def cursor():
	return db().cursor()

def reset():
	if os.path.isfile(DBFILE):
		os.unlink(DBFILE)

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
def listStudentsByFilter(group, medium, topic):
	return cursor().execute("SELECT students.* FROM students LEFT JOIN solutions ON (students.id = solutions.student) WHERE class=? AND medium=? AND solutions.topic=? GROUP BY students.id ORDER BY name", (group,medium,topic)).fetchall()

def countStudents(topic = None):
	if topic == None:
		return len(listStudents())
	else:
		return len(listStudentsByTopic(topic))

def addSolution(student, ordering, topic, timing):
	c = cursor()
	c.execute("SELECT id FROM solutions WHERE student=? AND topic=?", (student,topic))
	res = c.fetchone()
	if res != None:
		return res[0]
	with db():
		c.execute("INSERT INTO solutions (student,ordering,topic,timing) VALUES (?,?,?,?)", (student,ordering,topic,timing))
	return c.lastrowid

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
	return cursor().execute("SELECT * FROM nodes WHERE topic=?", (topic,)).fetchall()

def countNodes(topic):
	return len(listNodes(topic))

def addAnswer(solution, ordering, src, dest, desc):
	with db():
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

def unverifiedAnswers(topic, limit = 10):
	return cursor().execute("""
SELECT
	answers.id AS id,
	src AS srcid,
	srcnode.name AS src,
	dest AS destid,
	destnode.name AS dest,
	description,
	answers.verification,
	answers.delay
FROM answers
INNER JOIN solutions ON (answers.solution = solutions.id)
LEFT JOIN nodes AS srcnode ON (answers.src = srcnode.id)
LEFT JOIN nodes AS destnode ON (answers.dest = destnode.id)
WHERE solutions.topic = ? AND answers.verification & 1 = 0
ORDER BY delay ASC
LIMIT ?
	""", (topic,limit)).fetchall()

def delayAnswer(id):
	with db():
		cursor().execute("UPDATE answers SET delay = delay + 1 WHERE id = ?", (id,))

def searchVerificationMatch(topic, src, dest, desc):
	with db():
		return cursor().execute("SELECT * FROM answers INNER JOIN solutions ON (answers.solution = solutions.id) WHERE verification & 1 = 1 AND topic=? AND src=? AND dest=? AND description LIKE ? GROUP BY description", (topic,src,dest,desc)).fetchall()

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

def listVerifications():
	return VERIFICATION_FLAGS[1:]

def setVerification(answer, flag):
	print("Setting to %d" % flag)
	with db():
		cursor().execute("UPDATE answers SET verification=? WHERE id=?", (flag,answer))
