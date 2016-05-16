import os
import re
import subprocess

from webeval.utils import database

def hasCategories():
    res = database.db().execute("SELECT medium, timing FROM view_answers GROUP BY medium,timing").fetchall()
    return len(res) > 1

def getFilename(prefix, solution, suffix, cats):
    if cats:
        timing = solution["timing"]
        topicname = solution["topicname"]
        topicshort = solution["topicshort"]
        group = solution["class"]
        name = solution["studentname"]
        medium = solution["medium"]
        ordering = solution["ordering"]
        foldername = "%s/%s/%s_%s_%s_%s" % (prefix, timing, topicshort, group, medium, ordering)
        os.makedirs(foldername, exist_ok = True)
        filename = "%s/%s-%s.%s" % (foldername, topicname, name, suffix)
        return filename

def todot(prefix):
    cats = hasCategories()

    res = []
    for s in database.listSolutions():
        filename = getFilename(prefix, s, "dot", cats)
        res.append("Exporting solution %s" % filename)

        f = open(filename, "w")
        f.write("digraph g {\n")
        for r in database.listAnswers(s["id"]):
            f.write("\t\"%s\" -> \"%s\" [label=\"%s\"];\n" % (r["src"], r["dest"], r["description"].replace('"','')))
        f.write("\tlabelloc = \"t\";\n")
        f.write("\tlabel = \"%s-%s\";\n" % (s["id"], s["studentname"]))
        f.write("}\n")
        f.close()

        subprocess.check_output(["dot", "-O", "-Tpdf", filename])

    return res
