from flask import redirect, render_template, request
from webeval import app, database, stats

def getFilterSettings(form):
	r = {}
	r["topic"] = form.get('topic', '')
	r["medium"] = form.get('medium', '')
	r["timing"] = form.get('timing', '')
	r["ordering"] = form.get('ordering', '')
	r["group"] = form.get('group', '')
	r["verification_require"] = database.getVerificationFromMap("require", form)
	r["verification_exclude"] = database.getVerificationFromMap("exclude", form)
	return r

@app.route("/statistics/nodeusage", methods=["GET", "POST"])
def stats_nodeusage():
	kwargs = {}
	if request.method == "POST":
		kwargs = getFilterSettings(request.form)
		head,body,foot,plot = stats.collectNodeUsedCounts(**kwargs)
		kwargs.update({"head": head, "body": body, "foot": foot, "plot": plot})
	return render_template("stats/nodeusage.html", **kwargs)

@app.route("/statistics/edgeusage", methods=["GET", "POST"])
def stats_edgeusage():
	kwargs = {}
	if request.method == "POST":
		kwargs = getFilterSettings(request.form)
		cols,rows,body = stats.collectEdgeUsedCounts(**kwargs)
		kwargs.update({"cols": cols, "rows": rows, "body": body})
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
