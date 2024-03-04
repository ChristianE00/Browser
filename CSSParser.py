from DescendantSelector import DescendantSelector
from TagSelector import TagSelector
from classselector import ClassSelector
class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing error")
        return self.s[start:self.i]

    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing error")
        self.i += 1

    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        #val = self.word()
        if prop.casefold() == "font":  # handle font shorthand properties
            i = self.i
            self.ignore_until([";", "}"])
            val = self.s[i:self.i].strip()
        else:
            val = self.word()
        return prop.casefold(), val

    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
               # pairs[prop.casefold()] = val
                if prop.casefold() == 'font':
                    #i = self.i
                    split_values = val.split()
                    if(len(split_values) == 1):
                        pairs["font-family"] = split_values[0]
                    elif(len(split_values) == 2):
                        pairs["font-size"] = split_values[0]
                        pairs["font-family"] = split_values[1]
                    elif(len(split_values) == 3):
                        if(split_values[0] == "italic"):
                            pairs["font-style"] = split_values[0]
                        else:
                            pairs["font-weight"] = split_values[0]
                        pairs["font-size"] = split_values[1]
                        pairs["font-family"] = split_values[2]
                    elif(len(split_values) == 4):
                        pairs["font-style"] = split_values[0]
                        pairs["font-weight"] = split_values[1]
                        pairs["font-size"] = split_values[2]
                        pairs["font-family"] = split_values[3]
                    elif(len(split_values) > 4):
                        pairs["font-style"] = split_values[0]
                        pairs["font-weight"] = split_values[1]
                        pairs["font-size"] = split_values[2]
                        font_family = """ """.join(split_values[3:])
                        pairs["font-family"] = font_family
                else:
                    pairs[prop.casefold()] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except Exception:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
            #print('pairs: ', pairs)
        return pairs

    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None

    def selector(self):
        word = self.word()
        if word[0] == ".":
            out = ClassSelector(word[1:])
        else:
            out = TagSelector(word.casefold())
        '''
        out = TagSelector(self.word().casefold())
        '''
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            #descendant = TagSelector(tag.casefold())
            if tag[0] == ".":
                descendant = ClassSelector(tag[1:])
            else:
                descendant = TagSelector(tag.casefold())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    def parse(self):
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules


























