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

def gatherCoreData(topic):
	return {"students": database.countStudents(topic)}

def collectNodeUsedCounts(topic, timing = "", medium = "", verification = ""):
	core = gatherCoreData(topic)
	res = database.cursor().execute("""
SELECT
	nodes.name,
	COUNT(DISTINCT answers.solution) AS c1,
	COUNT(*) AS c3
FROM nodes
LEFT JOIN answers ON (nodes.id = answers.src OR nodes.id = answers.dest)
LEFT JOIN solutions ON (answers.solution = solutions.id)
LEFT JOIN students ON (solutions.student = students.id)
WHERE solutions.topic=? AND (timing=? OR %d) AND (medium=? OR %d) AND (verification=? OR %d)
GROUP BY nodes.id
ORDER BY c1 desc
""" % (timing == "", medium == "", verification == ""), (topic,timing,medium,verification)).fetchall()
	listing = list(map(lambda r: [
			r[0],
			"%s (%0.2f%%)" % (r[1], r[1]*100 / core["students"]),
			"%s (%0.2f per student)" % (r[2], r[2] / core["students"])
		], res))
	if len(res) > 0:
		foot = ["Average",
			"%0.2f ±%0.2f" % (mean(res, lambda x: x[1]), pstdev(res, lambda x: x[1])),
			"%0.2f ±%0.2f" % (mean(res, lambda x: x[2]), pstdev(res, lambda x: x[2])),
		]
	else: foot = None
	return ([
		"Node",
		"Used by n students",
		"Used in n connections"
	], listing, foot)

def collectNodeUsagePlot(topic, timing = "", medium = "", verification = ""):
	core = gatherCoreData(topic)
	res = database.cursor().execute("""
SELECT
	nodes.name,
	COUNT(DISTINCT answers.solution) AS c1
FROM nodes
LEFT JOIN answers ON (nodes.id = answers.src OR nodes.id = answers.dest)
LEFT JOIN solutions ON (answers.solution = solutions.id)
LEFT JOIN students ON (solutions.student = students.id)
WHERE solutions.topic=? AND (timing=? OR %d) AND (medium=? OR %d) AND (verification = ? OR %d)
GROUP BY nodes.id
ORDER BY c1 desc
""" % (timing == "", medium == "", verification == ""), (topic,timing,medium,verification)).fetchall()
	res = list(map(lambda r: [r[0], [r[1]]], res))
	return plot.barplot("nodeusage-%s-%s-%s.png" % (timing,medium,verification), res)

def collectEdgeUsedCounts(topic, timing = None, medium = None, verification = None):
	core = gatherCoreData(topic)
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
""" % (timing == None, medium == None, verification == None), (topic,topic,timing,medium,verification)).fetchall()
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
	core = gatherCoreData(topic)
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

stats = {
	"edges": {
		"edgeCount": ("Edge Usage Count", collectEdgeUsedCounts, {}),
		"edgeCorrect": ("Edge Correct", collectEdgeCorrect, {"verification": 6}),
	},
	"nodes": {},
	"verification": {}
}
for t in [None, "Vorher", "Nachher"]:
	for m in [None, "Video", "Text"]:
		ts = "" if t == None else t
		ms = "" if m == None else m
		stats["nodes"].update({
			"nodeUsageCount%s_%s" % (ts,ms): ("Node Usage Count %s %s" % (ts,ms), collectNodeUsedCounts, {"timing": t, "medium": m}),
			"nodeUsagePlot%s_%s" % (ts,ms): ("Node Usage Plot %s %s" % (ts,ms), collectNodeUsagePlot, {"timing": t, "medium": m}),
		})
		for v in [30]:
			vs = "" if v == None else ",".join(database.unpackVerification(v))
			args = {"timing": t, "medium": m, "verification": v}
			stats["nodes"].update({
				"nodeUsageCount%s_%s_%s" % (ts,ms,str(v)): ("Node Usage Count %s %s %s" % (ts,ms,vs), collectNodeUsedCounts, args),
				"nodeUsagePlot%s_%s_%s" % (ts,ms,str(v)): ("Node Usage Plot %s %s %s" % (ts,ms,vs), collectNodeUsagePlot, args),
			})
			stats["edges"].update({
				"edgeCorrect%s_%s_%s" % (ts,ms,str(v)): ("Edge Correct %s %s %s" % (ts,ms,vs), collectEdgeCorrect, args),
			})

# Supported statistics output:
# - listing: a list of records
#	Arguments: names, records
#		names: a list of captions for the columns
#		records: a list of iterables that represent the rows
# - table: a table with arbitrary rows and columns
#	Arguments: columns, rows, cells
#		columns: a list of column labels
#		rows: a list of row labels
#		cells: a two-dimensional list that represents the cells. first dimension is row.

def generateStats(topic):
	s = {}

	print("Generating stats:")
	print("\tcore")
	core = gatherCoreData(topic)
	for group in sorted(stats):
		print("\t" + group)
		s[group] = {}
		for stat in sorted(stats[group]):
			print("\t\t" + stats[group][stat][0])
			kwargs = stats[group][stat][2]
			s[group][stat] = [stats[group][stat][0]] + stats[group][stat][1](topic, core, **kwargs)

	env = jinja2.Environment(loader=jinja2.FileSystemLoader("tpl/"))
	tpl = env.get_template("stats.tpl")
	open("out/stats_%d.html" % (topic,), "w").write(tpl.render(stats = s, core = core))
