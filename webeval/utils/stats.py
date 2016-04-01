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

def gatherCoreData(group, medium, topic):
	return {"students": database.countStudents(group, medium, topic)}

def collectNodeUsedCounts(topic, timing = "", medium = "", ordering = "", group = "", verification_require = "", verification_exclude = ""):
	core = gatherCoreData(group, medium, topic)
	res = database.cursor().execute("""
SELECT
	nodes.name,
	COUNT(DISTINCT students.id) AS c1,
	COUNT(DISTINCT solutions.id) AS c2,
	COUNT(DISTINCT answers.id) AS c3
FROM nodes
LEFT JOIN answers ON (nodes.id = answers.src OR nodes.id = answers.dest)
LEFT JOIN solutions ON (answers.solution = solutions.id)
LEFT JOIN students ON (solutions.student = students.id)
WHERE solutions.topic=? AND (timing=? OR %d) AND (medium=? OR %d) AND (solutions.ordering=? OR %d) AND (class=? OR %d) AND (verification=? OR %d)
GROUP BY nodes.id
ORDER BY c1 desc
""" % (timing == "", medium == "", ordering == "", group == "", verification_require == ""), (topic,timing,medium,ordering,group,verification_require)).fetchall()
	listing = list(map(lambda r: [
			r["name"],
			"%s (%0.2f%%)" % (r["c1"], r["c1"]*100 / core["students"]),
			"%s (%0.2f per student)" % (r["c3"], r["c3"] / core["students"])
		], res))
	if len(res) > 0:
		foot = ["Average",
			"%0.2f ±%0.2f" % (mean(res, lambda x: x["c1"]), pstdev(res, lambda x: x["c1"])),
			"%0.2f ±%0.2f" % (mean(res, lambda x: x["c3"]), pstdev(res, lambda x: x["c3"])),
		]
	else: foot = None
	plotdata = map(lambda r: [r["name"], [r["c1"]]], res)
	plotres = plot.barplot("nodeusage-%s-%s-%s-%s-%s-%s-%s.png" % (topic,group,timing,medium,ordering,verification_require,verification_exclude), plotdata)
	return ([
		"Node",
		"Used by n students",
		"Used in n connections"
	], listing, foot, plotres)

def collectEdgeUsedCounts(topic, timing = "", medium = "", ordering = "", group = "", verification_require = "", verification_exclude = ""):
	core = gatherCoreData(group, medium, topic)
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
	return (nodes, nodes, table)

def collectEdgeCorrect(topic, timing = None, medium = None, verification = None):
	core = gatherCoreData(group, medium, topic)
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
