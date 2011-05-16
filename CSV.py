import codecs

class CSV:
    def __init__ (self, filename):
        # self.name = name
        self.data = []

        f = codecs.open(filename, 'r', 'cp932')
        line = f.readline()
        while line:
            line = line.rstrip().replace(';.*$', '')
            self.data.append(line.split(','))
            line = f.readline()

    def get (self, index):
        for d in self.data:
            if unicode(d[0]) == unicode(index):
                return d[1:]
