import os
import os.path
import subprocess

from webeval.utils import database

def hasCategories():
    res = database.db().execute("SELECT medium, timing FROM view_answers GROUP BY medium,timing").fetchall()
    return len(res) > 1

def getFilename(base, filename, newExt):
    baseFilename,ext = os.path.splitext(filename)
    return "%s/%s.%s" % (base, baseFilename, newExt)

def todot(prefix):
    cats = hasCategories()

    res = []
    for s in database.listSolutions():
        filename = getFilename(prefix, s["filename"], "dot")
        os.makedirs(os.path.dirname(filename), exist_ok = True)
        res.append("Exporting solution %s" % filename)

        f = open(filename, "w")
        f.write("digraph g {\n")
        for r in database.listAnswers(s["id"]):
            f.write("\t\"%s\" -> \"%s\" [label=\"%s\"];\n" % (r["src"], r["dest"], r["description"].replace('"','')))
        f.write("\tlabelloc = \"t\";\n")
        f.write("\tlabel = \"ID: %s / Name: %s\";\n" % (s["id"], s["studentname"]))
        f.write("}\n")
        f.close()

        subprocess.check_output(["dot", "-O", "-Tpdf", filename])

    return res
