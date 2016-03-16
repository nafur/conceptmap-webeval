from webeval.utils import database

def learnAnswer(topic, answer):
	(id,solution,ordering,src,dest,desc,verification) = answer
	srcnode = database.getNode(src)
	dstnode = database.getNode(dest)
	matches = database.searchVerificationMatch(topic, src, dest, desc)

	if len(matches) == 1:
		match = matches[0]
		print("\t%s --- %s --> %s  was automatically verified." % (srcnode[2],desc,dstnode[2]))
		database.setVerification(id, match["verification"])
		return
	elif len(matches) > 1:
		print("\t%s --- %s --> %s" % (srcnode[2],desc,dstnode[2]))
		print("\tThe following candidates may be used for semiautomatic verification:")
		print("\t\t0: None of them")
		answers = []
		n = 1
		for match in matches:
			answers.append(match["verification"])
			print("\t\t%d: %s --- %s --> %s (%s)" % (n,srcnode[2],match["description"],dstnode[2],", ".join(database.unpackVerification(match["verification"]))))
			n += 1
		while True:
			res = input("> ")
			if res.isdigit():
				res = int(res)
				if res == 0:
					break
				elif res > 0 and res < n:
					database.setVerification(id, answers[res-1])
					return

	flags = []
	for flag in database.listVerifications():
		while True:
			print("Is this answer %s correct? (Y/N)" % flag)
			print("\t%s --- %s --> %s" % (srcnode[2],desc,dstnode[2]))
			res = input("> ")
			if res in ["y", "Y"]:
				flags.append(flag)
				break
			elif res in ["n", "N"]:
				break
			else:
				print("Your input was invalid. Try again.")
	database.setVerification(id, database.packVerification(flags))
