import csv
import glob
import os.path
import re

from webeval.utils import database

FILE_PATTERN = {
	"default": ".*/(?P<timing>(Vorher|Nachher))/(?P<topicprefix>.*)_(?P<group>[^_]*)_(?P<medium>(Video|Text))_(?P<ordering>[0-9]+)/(?P<topic>.*)-(?P<student>[^-]*)_[0-9]*\.csv",
	"komisch": ".*/(?P<topicprefix>[^/]*)/(?P<group>[^_]*)/(?P<topic>.*)-(?P<student>[^-]*)_[0-9]*\.csv",
}

def patternList():
	return sorted(FILE_PATTERN.keys())
def patternDefault():
	return "default"

def canonicalizeTopic(topic):
	topic = re.sub(r'\s*[-_]\s*', ' - ', topic)
	return topic

def parseFilename(filename, pattern):
	res = re.match(FILE_PATTERN[pattern], filename.replace("\\","/"))
	if res != None:
		r = res.groupdict()
		if not "timing" in r: r["timing"] = "Vorher"
		if not "medium" in r: r["medium"] = "Text"
		if not "ordering" in r: r["ordering"] = "1"
		topic = database.addTopic(canonicalizeTopic(r["topic"]), r["topicprefix"])
		student = database.addStudent(r["student"].upper(), r["medium"], r["group"])
		solution = database.addSolution(student, r["ordering"], topic, r["timing"])
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

def error_DisconnectedTwice(cur, last):
	if cur["Action"] != "Disconnecting": return False
	if last["Action"] != "Disconnecting": return False
	if cur["Source"] != last["Source"]: return False
	if cur["Destination"] != last["Destination"]: return False
	return True
def error_RenameAfterDisconnect(cur, last):
	if cur["Action"] != "Renaming": return False
	if last["Action"] != "Disconnecting": return False
	if cur["Source"] != last["Source"]: return False
	if cur["Destination"] != last["Destination"]: return False
	return True

def fixTrivialErrors(rows):
	res = []
	for i in range(len(rows)):
		if i == 0:
			res.append(rows[0])
			continue
		if error_DisconnectedTwice(rows[i],rows[i-1]): continue
		if error_RenameAfterDisconnect(rows[i],rows[i-1]): continue
		res.append(rows[i])
	return res

def loadAnswerSet(path, pattern = "default"):
	msgs = []
	if os.path.isfile(path):
		files = [path]
	elif os.path.isdir(path):
		files = glob.glob(path + "/*/*/*.csv")
	else:
		msgs.append("\"" + path + "\" is neither a file nor a folder. We assume that it is a file pattern...")
		files = glob.glob(path)

	success = []
	failed = []
	for file in files:
		match = parseFilename(file, pattern)
		if match == None:
			msgs.append("Could not match \"" + file + "\" against pattern \"" + FILE_PATTERN[pattern] + "\".")
			continue
		(topic,student,solution) = match
		history = loadCSV(file)
		n = 1
		nm = NodeMap(topic)
		data = {}
		prglist = []
		for row in fixTrivialErrors(history):
			src = nm.get(row["Source"])
			dst = nm.get(row["Destination"])
			if row["Action"] == "Connecting":
				#database.addProgress(solution, n, "create", src, dst, "")
				prglist.append((solution, n, "create", src, dst, ""))
				if (src,dst) not in data: data[(src,dst)] = []
				data[(src,dst)].append((n, ""))
			elif row["Action"] == "Renaming":
				if not (src,dst) in data: continue
				#database.addProgress(solution, n, "rename", src, dst, row["to"])
				prglist.append((solution, n, "rename", src, dst, row["to"]))
				data[(src,dst)] = list(map(lambda s: (n,row["to"]) if s[1]==row["from"] else s, data[(src,dst)]))
			elif row["Action"] == "Disconnecting":
				if not (src,dst) in data: continue
				#database.addProgress(solution, n, "remove", src, dst, "")
				prglist.append((solution, n, "remove", src, dst, ""))
				if len(data[(src,dst)]) > 1:
					failed.append("%s (%s, %s -> %s)" % (file,"Removed duplicate connection",row["Source"],row["Destination"]))
					continue
				del data[(src,dst)]
			n += 1
		database.addProgressTransactional(prglist)
		anslist = []
		for d in data:
			for a in data[d]:
				ordering,desc = a
				#database.addAnswer(solution, ordering, d[0], d[1], desc)
				anslist.append((solution, ordering, d[0], d[1], desc))
		database.addAnswerTransactional(anslist)
		success.append(file)
	return (msgs,success,failed)
