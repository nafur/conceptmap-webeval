from flask import redirect, render_template, request
from webeval import app, database, stats

def getFilterSettings(form):
	topic = form.get('topic', '')
	medium = form.get('medium', '')
	timing = form.get('timing', '')
	ver_req = database.getVerificationFromMap("require", form)
	ver_exc = database.getVerificationFromMap("exclude", form)
	return topic,medium,timing,ver_req,ver_exc

@app.route("/statistics/nodeusage", methods=["GET", "POST"])
def stats_nodeusage():
	kwargs = {}
	if request.method == "POST":
		topic,medium,timing,ver_req,ver_exc = getFilterSettings(request.form)
		head,body,foot = stats.collectNodeUsedCounts(topic, timing = request.form.get('timing', ''), medium = request.form.get('medium', ''))
		plot = stats.collectNodeUsagePlot(topic, timing = request.form.get('timing', ''), medium = request.form.get('medium', ''))
		kwargs = {"head": head, "body": body, "foot": foot, "plot": plot}
	return render_template("stats/nodeusage.html", **kwargs)

@app.route("/statistics/edgeusage", methods=["GET", "POST"])
def stats_edgeusage():
	kwargs = {}
	if request.method == "POST":
		topic,medium,timing,ver_req,ver_exc = getFilterSettings(request.form)
		cols,rows,body = stats.collectEdgeUsedCounts(topic, timing = request.form.get('timing', ''), medium = request.form.get('medium', ''))
		kwargs.update({"cols": cols, "rows": rows, "body": body})
		#plot = stats.collectNodeUsagePlot(topic, core, timing = request.form.get('timing', ''), medium = request.form.get('medium', ''))
		#kwargs.update({"plot": plot})
	return render_template("stats/edgeusage.html", **kwargs)

@app.route("/statistics/groups", methods=["GET", "POST"])
def stats_groups():
	groups = {}
	for g in database.listGroups():
		cur = {}
		status = "success"
		for t in map(lambda t: t["name"], database.listTopics()):
			for m in map(lambda m: m["medium"], database.listMediums()):
				r = database.listStudentsByFilter(g["class"],m,t)
				if len(r) > 0: cur["%s / %s" % (t,m)] = r
		if len(cur) > 2: status = "error"
		groups[g["class"]] = { "all": database.listStudentsByGroup(g["class"]), "sub": cur, "status": status}

	return render_template("stats/groups.html", groups = groups)
