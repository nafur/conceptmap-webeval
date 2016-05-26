from webeval.utils import database

def getID(v1, v2, flag):
	s1 = "1" if v1 & flag > 0 else "0"
	s2 = "1" if v2 & flag > 0 else "0"
	return s1 + s2

def compareWith(filename):
	db = database.openMergedDB(filename)
	res = db.execute("""
SELECT
	ns1.name AS src,
	nd1.name AS dst,
	va1.student,
	va1.description,
	va2.description,
	va1.verification AS v1,
	va2.verification AS v2
FROM db1.view_answers AS va1
INNER JOIN db1.nodes AS ns1 ON (ns1.id = va1.src)
INNER JOIN db1.nodes AS nd1 ON (nd1.id = va1.dest)
INNER JOIN db2.nodes AS ns2 ON (ns2.name = ns1.name)
INNER JOIN db2.nodes AS nd2 ON (nd2.name = nd1.name)
INNER JOIN db2.view_answers AS va2 ON (
	va2.src = ns2.id AND va2.dest = nd2.id AND
	va1.student = va2.student AND va1.timing = va2.timing AND
	va1.description = va2.description
)
ORDER BY va1.src,va1.dest
""").fetchall()

	res = list(map(lambda x: dict(x), res))
	stats = {}
	flags = range(len(database.VERIFICATION_FLAGS))
	for f in flags:
		if f == 0: continue
		agreement = {"00": 0, "01": 0, "10": 0, "11": 0}
		for r in res:
			agreement[getID(r["v1"], r["v2"], 2**f)] += 1
		allSum = sum(agreement.values())
		aYes = (agreement["10"] + agreement["11"]) / allSum
		bYes = (agreement["01"] + agreement["11"]) / allSum
		agree = (agreement["00"] + agreement["11"]) / allSum
		rndAgree = (aYes*bYes + (1-aYes)*(1-bYes))

		if rndAgree == 1:
			kappa = 1
		else:
			kappa = (agree - rndAgree) / (1 - rndAgree)
		stats[database.VERIFICATION_FLAGS[f]] = {
			"ayes": aYes,
			"byes": bYes,
			"randomAgree": rndAgree,
			"agree": agree,
			"kappa": kappa
		}

	return stats
