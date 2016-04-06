import jinja2
import math
import numbers
import statistics

from webeval.utils import database, plot

def mean(data, key = lambda x: float(x)):
	return statistics.mean(map(key, data))

def pstdev(data, key = lambda x: float(x)):
	return statistics.pstdev(map(key, data))

isNumber = lambda x: isinstance(x,numbers.Real)
formatPercent = lambda x: "%0.2f%%" % (x*100,)
formatFloat = lambda x: "%0.2f" % x

def reformat(data, formatter, condition = isNumber):
	if type(data) is list:
		return [reformat(d, formatter, condition) for d in data]
	else:
		return formatter(data) if condition(data) else data

def printUsages(data, desc, key, str):
	data.sort(key = key)
	data = map(str, data)
	print("\n".join([desc] + list(data) + [""]))

def gatherCoreData(topic, medium, group, ordering, timing, verification_require, verification_exclude):
	return {"students": database.countStudents(topic=topic, medium=medium, group=group, ordering=ordering, timing=timing, verification_require=verification_require, verification_exclude=verification_exclude)}

class Listing:
	type = "listing"
	def __init__(self, name, body):
		self.name = name
		self.body = body
		self.description = None
	def setHead(self, head):
		self.head = head
	def setFoot(self, foot):
		self.foot = foot

class Table:
	type = "table"
	def __init__(self, name, cols, rows, body):
		self.name = name
		self.cols = cols
		self.rows = rows
		self.body = body
		self.description = None

class Plot:
	type = "plot"
	def __init__(self, name, data):
		self.name = name
		self.data = data
		self.description = None
	def setLabels(self, xlabel, ylabel):
		self.xlabel = xlabel
		self.ylabel = ylabel
	def plot(self, type, filename):
		if type == "barplot":
			self.filename = plot.barplot(filename, self.data, self.xlabel, self.ylabel)
		else:
			self.error = "Error: Unknown plot type \"%s\"." % type

class Individual:
	type = "individual"
	def __init__(self, name):
		self.name = name
		self.data = []
	def add(self, title, value, description = None):
		self.data.append({"title":title, "value":value, "description":description})
	def notEmpty(self):
		return len(self.data) > 0

def collectNodeUsedCounts(topic, timing = "", medium = "", ordering = "", group = "", verification_require = "", verification_exclude = ""):
	core = gatherCoreData(topic, medium, group, ordering, timing, verification_require, verification_exclude)
	query = """
SELECT
	nodes.name AS name,
	COUNT(DISTINCT student) AS c1,
	COUNT(DISTINCT solution) AS c2,
	COUNT(DISTINCT view_answers.id) AS c3
FROM view_answers
LEFT JOIN nodes ON (nodes.id = src OR nodes.id = dest)
WHERE ${FILTER}
GROUP BY nodes.id
ORDER BY c1 desc
"""
	res = database.executeFiltered(query, topic, medium, group, ordering, timing, verification_require, verification_exclude).fetchall()

	lstdata = map(lambda r: [
			r["name"],
			"%s (%0.2f%%)" % (r["c1"], r["c1"]*100 / core["students"]),
			"%s (%0.2f per student)" % (r["c3"], r["c3"] / core["students"])
		], res)
	lst = Listing("Node usage", lstdata)
	lst.setHead([
		"Node",
		"Used by n students",
		"Used in n connections"
	])
	if len(res) > 0:
		lst.setFoot(["Average",
			"%0.2f ±%0.2f" % (mean(res, lambda x: x["c1"]), pstdev(res, lambda x: x["c1"])),
			"%0.2f ±%0.2f" % (mean(res, lambda x: x["c3"]), pstdev(res, lambda x: x["c3"])),
		])
	plt = Plot("Node usage", map(lambda r: [r["name"], [r["c1"]]], res))
	plt.setLabels(None, "# usages")
	plt.plot("barplot", "nodeusage-%s-%s-%s-%s-%s-%s-%s.png" % (topic,group,timing,medium,ordering,verification_require,verification_exclude))
	return [lst, plt]

def nodesPerStudent(topic, timing = "", medium = "", ordering = "", group = "", verification_require = "", verification_exclude = ""):
	core = gatherCoreData(topic, medium, group, ordering, timing, verification_require, verification_exclude)
	res = database.cursor().execute("""
SELECT
	ncnt,
	COUNT(DISTINCT student) AS scnt
FROM (
	SELECT
		student,
		COUNT(DISTINCT nodes.id) AS ncnt
	FROM view_answers
	INNER JOIN nodes ON (nodes.id = src OR nodes.id = dest)
	WHERE (view_answers.topic=?) AND (timing=? OR %d) AND (medium=? OR %d) AND (ordering=? OR %d) AND (class=? OR %d) AND (verification=? OR %d)
	GROUP BY student
)
GROUP BY ncnt
""" % (timing == "", medium == "", ordering == "", group == "", verification_require == ""), (topic,timing,medium,ordering,group,verification_require)).fetchall()
	lstdata = map(lambda r: [
		r["ncnt"],
		"%s (%0.2f%%)" % (r["scnt"], r["scnt"]*100 / core["students"])
	], res)
	lst = Listing("Students using n nodes", lstdata)
	lst.setHead(["# nodes", "# students"])

	plt = Plot("Students with number of nodes", map(lambda r: [r["ncnt"], [r["scnt"]]], res))
	plt.setLabels("# nodes", "# students")
	plt.plot("barplot", "nodesperstudent-%s-%s-%s-%s-%s-%s-%s.png" % (topic,group,timing,medium,ordering,verification_require,verification_exclude))
	plt.description = """This plot shows the number of students that have used a specific number of nodes."""

	res = database.cursor().execute("""
SELECT
	COUNT(DISTINCT nodes.id) AS cnt
FROM answers
INNER JOIN solutions ON (answers.solution = solutions.id)
INNER JOIN nodes ON (answers.src = nodes.id OR answers.dest = nodes.id)
INNER JOIN students ON (solutions.student = students.id)
WHERE (solutions.topic=?) AND (timing=? OR %d) AND (medium=? OR %d) AND (solutions.ordering=? OR %d) AND (class=? OR %d) AND (verification=? OR %d)
GROUP BY solutions.student
""" % (timing == "", medium == "", ordering == "", group == "", verification_require == ""), (topic,timing,medium,ordering,group,verification_require)).fetchall()

	ind = Individual("Stuff")
	if len(res) > 0:
		avg,dev = mean(res, lambda x: x["cnt"]), pstdev(res, lambda x: x["cnt"])
		ind.add("Nodes used by students", "%0.2f ±%0.2f" % (avg,dev), "The average student used %0.2f nodes." % avg)
	return [lst, plt, ind]

def collectEdgeUsedCounts(topic, timing = "", medium = "", ordering = "", group = "", verification_require = "", verification_exclude = ""):
	core = gatherCoreData(topic, medium, group, ordering, timing, verification_require, verification_exclude)
	nodes = database.listNodes(topic)
	nm = {}
	for n in nodes: nm[n["id"]] = len(nm)
	nodes = list(map(lambda n: n["name"], nodes))
	res = database.cursor().execute("""
SELECT n1.id,n2.id,answers.*
FROM nodes AS n1, nodes AS n2
INNER JOIN answers ON (n1.id = answers.src AND n2.id = answers.dest)
LEFT JOIN solutions ON (answers.solution = solutions.id)
LEFT JOIN students ON (solutions.student = students.id)
WHERE n1.topic = ? AND n2.topic = ? AND (timing=? OR %d) AND (medium=? OR %d) AND (verification = ? OR %d)
""" % (timing == "", medium == "", verification_require == ""), (topic,topic,timing,medium,verification_require)).fetchall()
	table = [([0] * len(nodes)) for n in nodes]
	for row in res:
		table[nm[row[0]]][nm[row[1]]] += 1
	nodes.append("Average")
	for row in table:
		row.append("%0.2f ±%0.2f" % (mean(row), pstdev(row)))
	newRow = []
	for col in range(len(table[0])-1):
		newRow.append("%0.2f ±%0.2f" % (mean(table, lambda x: x[col]), pstdev(table, lambda x: x[col])))
	table.append(newRow + [""])
	tbl = Table("Edge usage", nodes, nodes, table)
	return [tbl]

def collectEdgeCorrect(topic, timing = None, medium = None, verification = None):
	core = gatherCoreData(topic, medium, group, ordering, timing, verification_require, verification_exclude)
	nodes = database.listNodes(topic)
	nm = {}
	for n in nodes: nm[n["id"]] = len(nm)
	nodes = list(map(lambda n: n["name"], nodes))
	res = database.cursor().execute("""
SELECT n1.id,n2.id,answers.*
FROM nodes AS n1, nodes AS n2
INNER JOIN answers ON (n1.id = answers.src AND n2.id = answers.dest)
LEFT JOIN solutions ON (answers.solution = solutions.id)
LEFT JOIN students ON (solutions.student = students.id)
WHERE n1.topic = ? AND n2.topic = ? AND (timing=? OR %d) AND (medium=? OR %d)
""" % (timing == None, medium == None), (topic,topic,timing,medium)).fetchall()
	table = [[[0,0] for n in nodes] for n in nodes]
	for row in res:
		if int(row["verification"]) & verification == verification:
			table[nm[row[0]]][nm[row[1]]][0] += 1
		table[nm[row[0]]][nm[row[1]]][1] += 1
	table = list(map(lambda r: list(map(lambda x: x[0]/x[1] if x[1] != 0 else 0, r)), table))
	nodes.append("Average")
	for row in table:
		row.append("%0.2f ±%0.2f" % (mean(row), pstdev(row)))
	newRow = []
	for col in range(len(table[0])-1):
		newRow.append("%0.2f ±%0.2f" % (mean(table, lambda x: float(x[col])), pstdev(table, lambda x: float(x[col]))))
	table.append(newRow + [""])
	table = reformat(table, formatPercent, isNumber)
	return ["table", nodes, nodes, table]
