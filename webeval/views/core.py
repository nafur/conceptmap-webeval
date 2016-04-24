from flask import redirect, render_template, request, safe_join, send_file
from webeval import app, database, dbcompare, loader

import os.path

@app.route("/")
def main():
	return render_template("index.html")

@app.route("/static/<path:file>")
def serve_static(file):
	res = send_file(safe_join('static', file))
	res.headers["Cache-Control"] = "no-store,no-cache,must-revalidate,max-age=0"
	res.headers["Expires"] = "-1"
	res.headers['Pragma'] = 'no-cache'
	return res

@app.route("/admin/reset", methods = ["GET","POST"])
def admin_reset():
	if request.method == "POST":
		database.reset()
		return redirect("/")
	else:
		return render_template("admin/reset.html")

@app.route('/admin/browse/', defaults={'path': ''})
@app.route('/admin/browse/<path:path>')
def browseFiles(path):
	abs_path = os.path.join(os.path.expanduser("~"), path)
	parent = os.path.relpath(os.path.join(abs_path, os.pardir), os.path.expanduser("~")) if path != "" else None
	if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
		return render_template("admin/import_failed.html", reason  = "The given path is not a directory.")
	children = os.listdir(abs_path)
	files = ", ".join([f for f in children if os.path.isfile(os.path.join(abs_path, f))])
	dirs = {f: os.path.join(path, f) for f in children if os.path.isdir(os.path.join(abs_path, f))}
	breadcrumbs = []
	p = path
	while p != "":
		breadcrumbs.append((os.path.basename(p), p))
		p = os.path.dirname(p)
	breadcrumbs.append(("~",""))
	breadcrumbs.reverse()

	return render_template("admin/import_selection.html", pattern = loader.patternList(), patternDefault = loader.patternDefault(), parent = parent, curpath = path, files = files, dirs = dirs, breadcrumbs = breadcrumbs)

@app.route("/admin/import/<path:path>", methods = ["POST"])
def importFiles(path):
	abs_path = os.path.join(os.path.expanduser("~"), path)
	msgs,success,failed = loader.loadAnswerSet(abs_path, request.form["pattern"])
	return render_template("admin/import_done.html", messages = msgs, success = success, failed = failed, path = path)

@app.route("/admin/compare", methods = ["GET", "POST"])
def admin_compare():
	if request.method == "POST":
		filename = request.form.get('file', '')
		return render_template("admin/compare.html", res = dbcompare.compareWith(filename), filename = filename)
	else:
		return render_template("admin/compare.html")
