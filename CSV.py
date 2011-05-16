import codecs

class CSV:
    def __init__ (self, filename):
        # self.name = name
        self.data = []

        f = codecs.open(filename, 'r', 'cp932')
        line = f.readline()
        while line:
            line = line.replace(';.*$', '')
            self.data.append(line.split(','))
            line = f.readline()

    def get (self, index):
        for d in self.data:
            if str(d[0]) == str(index):
                return d[1:]
