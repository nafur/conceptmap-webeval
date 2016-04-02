from flask import redirect, render_template, request, send_from_directory
from webeval import app, database, learner

import os.path

@app.route("/learn/<int:topic>")
def learn(topic):
	def extractVerification(c):
		c = dict(c)
		c["verification"] = database.unpackVerificationIcons(c["verification"])
		return c
	candidates = database.unverifiedAnswers(topic)
	candidates = map(extractVerification, candidates)
	return render_template("learn/learn.html", topic = database.getTopic(topic), candidates = candidates)

@app.route("/learn/<int:topic>/<int:answer>", methods=["GET", "POST"])
def learn_answer(topic, answer):
	if request.method == "GET":
		return render_template("learn/learn_answer.html", topic = database.getTopic(topic), answer = database.getAnswer(answer))
	database.setVerification(answer, database.getVerificationFromMap("", request.form))
	return redirect("/learn/%d" % topic)

@app.route("/learn/verify/<int:topic>/<int:answer>", methods=["POST"])
def verify_answer(topic, answer):
	database.toggleVerification(answer, database.firstVerification())
	return redirect("/learn/%d" % topic)

@app.route("/learn/delay/<int:topic>/<int:answer>")
def delay_answer(topic, answer):
	database.delayAnswer(answer)
	return redirect("/learn/%d" % topic)

@app.route("/learn/toggle/<int:topic>/<int:answer>/<string:flag>")
def toggle_flag(topic, answer, flag):
	database.toggleVerification(answer, flag)
	return redirect("/learn/%d" % topic)
