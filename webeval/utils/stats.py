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
	def get(self, row):
		return self.body[row]
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
	res = database.executeFiltered(query, topic, timing, medium, ordering, group, verification_require, verification_exclude).fetchall()

	lstdata = [[
			r["name"],
			"%s" % r["c1"],
			"%0.2f%%" % (r["c1"]*100 / core["students"]),
			"%s (%0.2f per student)" % (r["c3"], r["c3"] / core["students"])
		] for r in res]
	lst = Listing("Node usage", lstdata)
	lst.setHead([
		"Node",
		("Used by n students", "colspan=\"2\""),
		"Used in n connections"
	])
	if len(res) > 0:
		lst.setFoot(["Average",
			("%0.2f ±%0.2f" % (mean(res, lambda x: x["c1"]), pstdev(res, lambda x: x["c1"])), "colspan=\"2\""),
			"%0.2f ±%0.2f" % (mean(res, lambda x: x["c3"]), pstdev(res, lambda x: x["c3"])),
		])
	plt = Plot("Node usage", map(lambda r: [r["name"], [r["c1"]]], res))
	plt.setLabels(None, "# usages")
	plt.plot("barplot", "nodeusage-%s-%s-%s-%s-%s-%s-%s.png" % (topic,group,timing,medium,ordering,verification_require,verification_exclude))
	return [lst, plt]

def nodesPerStudent(topic, timing = "", medium = "", ordering = "", group = "", verification_require = "", verification_exclude = ""):
	core = gatherCoreData(topic, medium, group, ordering, timing, verification_require, verification_exclude)
	query = """
SELECT
	ncnt,
	COUNT(DISTINCT student) AS scnt
FROM (
	SELECT
		student,
		COUNT(DISTINCT nodes.id) AS ncnt
	FROM view_answers
	INNER JOIN nodes ON (nodes.id = src OR nodes.id = dest)
	WHERE ${FILTER}
	GROUP BY student
)
GROUP BY ncnt
"""
	res = database.executeFiltered(query, topic, timing, medium, ordering, group, verification_require, verification_exclude).fetchall()
	lstdata = [[
		r["ncnt"],
		"%s" % r["scnt"],
		"%0.2f%%" % (r["scnt"]*100 / core["students"])
	] for r in res]
	lst = Listing("Students using n nodes", lstdata)
	lst.setHead(["# nodes", ("# students", "colspan=\"2\"")])

	data = plot.injectMissing([ [r["ncnt"], [r["scnt"]]] for r in res])
	plt = Plot("Students with number of nodes", data)
	plt.setLabels("# nodes", "# students")
	plt.plot("barplot", "nodesperstudent-%s-%s-%s-%s-%s-%s-%s.png" % (topic,group,timing,medium,ordering,verification_require,verification_exclude))
	plt.description = """This plot shows the number of students that have used a specific number of nodes."""

	query = """
SELECT
	COUNT(DISTINCT nodes.id) AS cnt
FROM view_answers
INNER JOIN nodes ON (nodes.id = src OR nodes.id = dest)
WHERE ${FILTER}
GROUP BY student
"""
	res = database.executeFiltered(query, topic, timing, medium, ordering, group, verification_require, verification_exclude).fetchall()

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

	query = """
SELECT
	nsrc.id AS src,
	ndst.id AS dst,
	COUNT(DISTINCT view_answers.id) AS cnt
FROM view_answers
INNER JOIN nodes AS nsrc ON (nsrc.id = src)
INNER JOIN nodes AS ndst ON (ndst.id = dest)
WHERE ${FILTER}
GROUP BY nsrc.id,ndst.id
"""
	res = database.executeFiltered(query, topic, timing, medium, ordering, group, verification_require, verification_exclude).fetchall()

	table = [([0] * len(nodes)) for n in nodes]
	for row in res:
		table[nm[row["src"]]][nm[row["dst"]]] = row["cnt"]

	nodes.append("Average")
	for row in table:
		row.append("%0.2f" % (sum(row) / core["students"]))
	newRow = []
	for col in range(len(table[0])-1):
		newRow.append(sum(map(lambda x: x[col], table)) / core["students"])
	newRow.append(sum(newRow))
	table.append(map(lambda x: "%0.2f" % x, newRow))
	tbl = Table("Edge usage", nodes, nodes, table)
	return [tbl]

def collectEdgesPerStudent(topic, timing = "", medium = "", ordering = "", group = "", verification_require = "", verification_exclude = ""):
	core = gatherCoreData(topic, medium, group, ordering, timing, verification_require, verification_exclude)
	query = """
SELECT
	ecnt,
	COUNT(DISTINCT student) AS scnt
FROM (
	SELECT
		student,
		COUNT(DISTINCT id) AS ecnt
	FROM view_answers
	WHERE ${FILTER}
	GROUP BY student
)
GROUP BY ecnt
"""
	res = database.executeFiltered(query, topic, timing, medium, ordering, group, verification_require, verification_exclude).fetchall()

	lstdata = [[
		r["ecnt"],
		"%s" % r["scnt"],
		"%0.2f%%" % (r["scnt"]*100 / core["students"])
	] for r in res]
	lst = Listing("Students created n edges", lstdata)
	lst.setHead(["# edges", ("# students", "colspan=\"2\"")])

	plt = Plot("Students with number of edges", map(lambda r: [r["ecnt"], [r["scnt"]]], res))
	plt.setLabels("# nodes", "# students")
	plt.plot("barplot", "edgesperstudent-%s-%s-%s-%s-%s-%s-%s.png" % (topic,group,timing,medium,ordering,verification_require,verification_exclude))
	plt.description = """This plot shows the number of students that have created a specific number of edges."""

	query = """
SELECT
	COUNT(DISTINCT view_answers.id) AS cnt
FROM view_answers
WHERE ${FILTER}
GROUP BY student
"""
	res = database.executeFiltered(query, topic, timing, medium, ordering, group, verification_require, verification_exclude).fetchall()
	ind = Individual("Stuff")
	if len(res) > 0:
		avg,dev = mean(res, lambda x: x["cnt"]), pstdev(res, lambda x: x["cnt"])
		ind.add("Edges created by students", "%0.2f ±%0.2f" % (avg,dev), "The average student created %0.2f edges." % avg)
	return [lst,plt,ind]

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
