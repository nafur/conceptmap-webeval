import matplotlib.pyplot as plt
import numpy

colors = ["b", "r", "g"]

def injectMissing(data, columns = 1):
    minlabel = min(data, key = lambda x: x[0])[0]
    maxlabel = max(data, key = lambda x: x[0])[0]
    labels = range(minlabel, maxlabel + 1)
    ddata = {x[0]: x[1] for x in data}
    for l in labels:
        if l not in ddata:
            ddata[l] = [0] * columns
    return [ [l, ddata[l]] for l in labels]

def barplot(filename, data, xlabel, ylabel):
    data = list(data)
    if data == []:
        return ""
    n = len(data)
    cols = len(data[0][1])
    ind = numpy.arange(n)
    fig,ax = plt.subplots()
    width = 1.0 / (cols+1)

    for i in range(cols):
        d = list(map(lambda r: r[1][i], data))
        r = ax.bar(ind + i*width + 0.25, d, width, color=colors[i])

    labels = list(map(lambda r: r[0], data))
    if ylabel != None: ax.set_ylabel(ylabel)
    if xlabel != None: ax.set_xlabel(xlabel)
    ax.xaxis.set_ticks(numpy.arange(0, len(labels), 1) + 0.5)
    #todo: use wrap=False
    ax.set_xticklabels(labels, rotation=25, ha="right", size="small")

    plt.subplots_adjust(left=0.125, right=0.9, top=0.9, bottom=0.2)
    plt.savefig("webeval/static/plots/" + filename)

    return "/static/plots/" + filename
