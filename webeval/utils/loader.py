import csv
import glob
import os.path
import re

from webeval.utils import database

FILE_PATTERN = {
	"default": ".*/?(?P<timing>(Vorher|Nachher))/.*_(?P<medium>(Video|Text))_(?P<ordering>[0-9]+)/(?P<topic>.*)-(?P<student>[^-]*)_[0-9]*\.csv"
}

def parseFilename(filename, pattern):
	res = re.match(FILE_PATTERN[pattern], filename)
	if res != None:
		topic = database.addTopic(res.group("topic"))
		student = database.addStudent(res.group("medium"), res.group("student"))
		solution = database.addSolution(student, res.group("ordering"), topic, res.group("timing"))
		return (topic,student,solution)
	return None

def loadCSV(filename):
	file = open(filename, "r", encoding="latin1")
	reader = csv.DictReader(file, delimiter=";")
	return list(reader)

class NodeMap:
	def __init__(self,topic):
		self._m = {}
		self._topic = topic
	def get(self, name):
		if name in self._m:
			return self._m[name]
		id = database.addNode(self._topic,name)
		self._m[name] = id
		return id

def loadAnswerSet(path, pattern = "default"):
	res = [[],[]]
	if os.path.isfile(path):
		files = [path]
	elif os.path.isdir(path):
		files = glob.glob(path + "/*/*/*")
	else:
		res[0].append("\"" + path + "\" is neither a file nor a folder. We assume that it is a file pattern...")
		files = glob.glob(path)

	success = []
	failed = []
	for file in files:
		res[1].append(file)
		match = parseFilename(file, pattern)
		if match == None:
			res[0].append("Could not match \"" + file + "\" against pattern \"" + FILE_PATTERN[pattern] + "\".")
			continue
		(topic,student,solution) = match
		history = loadCSV(file)
		n = 1
		nm = NodeMap(topic)
		data = {}
		for row in history:
			src = nm.get(row["Source"])
			dst = nm.get(row["Destination"])
			if row["Action"] == "Connecting":
				if (src,dst) in data:
					failed.append(file)
					continue
				database.addProgress(solution, n, "create", src, dst, "")
				data[(src,dst)] = (n, "")
			elif row["Action"] == "Renaming":
				if not (src,dst) in data:
					failed.append(file)
					continue
				database.addProgress(solution, n, "rename", src, dst, row["to"])
				data[(src,dst)] = (n, row["to"])
			elif row["Action"] == "Disconnecting":
				if not (src,dst) in data:
					failed.append(file)
					continue
				database.addProgress(solution, n, "remove", src, dst, "")
				del data[(src,dst)]
			n += 1
		for d in data:
			ordering,desc = data[d]
			database.addAnswer(solution, ordering, d[0], d[1], desc)
		success.append(file)
	return (res,success,failed)
