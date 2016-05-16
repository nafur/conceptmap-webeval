from flask import redirect, render_template, request, send_from_directory
from webeval import app, export

@app.route("/export/todot", methods=["GET", "POST"])
def export_todot():
	if request.method == "GET":
		return render_template("export/export_todot.html")
	return render_template("export/export_todot.html", res = export.todot("export"))
