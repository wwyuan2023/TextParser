# coding: utf-8

from .lang import Lang

class SegText(object):
    
    _ncols = 6
    
    def __init__(self, line=None):
        self.segtext = list()
        if line is not None:
            self.parser(line)
    
    def parser(self, line:str):
        # line: "{word}/{pinyin};{gpos};{lang};{sentype};{mark}; ..."
        # e.g.: "无力感/wu2-li4-gan3;n;CN;0; 。/sil0;w;CN;0;"
        lines = line.strip().split()
        for s in lines:
            for i in range(len(s)-1, -1, -1):
                if s[i] == '/': break
            wd = s[:i]
            if wd == '': continue
            py, cx, lang, sentype, mark, _ = s[i+1:].split(';')[:SegText._ncols]
            py = py.split('-')
            if len(py) == 0 or (len(py) == 1 and py[0] == ''):
                py = None
            if cx == '': cx = None
            if lang == '': lang = None
            if mark == '': mark = None
            sentype = None if sentype == '' else int(sentype)
            self.segtext.append([wd, py, cx, lang, sentype, mark])
        # segtext: [['无力感', ['wu2', 'li4', 'gan3'], 'n', 'CN', 0], ['。', ['sil0'], 'w', 'CN', 0]]
    
    def printer(self):
        # segtext: [['无力感', ['wu2', 'li4', 'gan3'], 'n', 'CN', 0], ['。', ['sil0'], 'w', 'CN', 0]]
        line = ''
        for s in self.segtext:
            wd = s[0] if s[0] is not None else ''
            py = '-'.join(s[1]) if s[1] is not None else ''
            cx = s[2] if s[2] is not None else ''
            lang = s[3] if s[3] is not None else ''
            sentype = s[4] if s[4] is not None else ''
            mark = s[5] if s[5] is not None else ''
            line += f"{wd}/{py};{cx};{lang};{sentype};{mark}; "
        # line: "无力感/wu2-li4-gan3;n;CN;0; 。/sil0;w;CN;0;"
        return line.strip()
    
    def set_wpc(self, idx: int, wd: str, py, cx: str):
        if -len(self.segtext) <= idx < len(self.segtext):
            self.segtext[idx][0] = wd
            if type(py) is str: py = py.split('-')
            if not ((type(py) is list or type(py) is tuple) and len(py) > 0 and len(py[0]) > 0):
                py = None
            self.segtext[idx][1] = py
            self.segtext[idx][2] = cx
    
    def get_wpc(self, idx: int, wd=None, py=None, cx=None):
        if -len(self.segtext) <= idx < len(self.segtext):
            if self.segtext[idx][0] is not None:
                wd = self.segtext[idx][0]
            if (self.segtext[idx][1] is not None
                and (type(self.segtext[idx][1]) is list or type(self.segtext[idx][1]) is tuple)
                and len(self.segtext[idx][1]) > 0
                and len(self.segtext[idx][1][0]) > 0
            ):
                py = self.segtext[idx][1]
            if self.segtext[idx][2] is not None:
                cx = self.segtext[idx][2]
        return wd, py, cx

    def get_wd(self, idx: int, wd=None):
        if -len(self.segtext) <= idx < len(self.segtext):
            if self.segtext[idx][0] is not None:
                wd = self.segtext[idx][0]
        return wd
    
    def set_wd(self, idx: int, wd: str):
        if -len(self.segtext) <= idx < len(self.segtext):
            self.segtext[idx][0] = wd
    
    def get_py(self, idx: int, py=None):
        if -len(self.segtext) <= idx < len(self.segtext):
            if (self.segtext[idx][1] is not None
                and (type(self.segtext[idx][1]) is list or type(self.segtext[idx][1]) is tuple)
                and len(self.segtext[idx][1]) > 0
                and len(self.segtext[idx][1][0]) > 0
            ):
                py = self.segtext[idx][1]
        return py
    
    def set_py(self, idx: int, py):
        if -len(self.segtext) <= idx < len(self.segtext):
            if type(py) is str: py = py.split('-')
            if not ((type(py) is list or type(py) is tuple) and len(py) > 0 and len(py[0]) > 0):
                py = None
            self.segtext[idx][1] = py
    
    def get_cx(self, idx: int, cx=None):
        if -len(self.segtext) <= idx < len(self.segtext):
            if self.segtext[idx][2] is not None:
                cx = self.segtext[idx][2]
        return cx
    
    def set_cx(self, idx: int, cx: str):
        if -len(self.segtext) <= idx < len(self.segtext):
            self.segtext[idx][2] = cx
    
    def get_lang(self, idx: int, lang=Lang.UNKNOW):
        if -len(self.segtext) <= idx < len(self.segtext):
            if self.segtext[idx][3] is not None:
                lang = self.segtext[idx][3]
        return lang
    
    def set_lang(self, idx: int, lang: str = Lang.CN):
        if -len(self.segtext) <= idx < len(self.segtext):
            self.segtext[idx][3] = lang
    
    def get_sentype(self, idx: int, sentype=0):
        if -len(self.segtext) <= idx < len(self.segtext):
            if self.segtext[idx][4] is not None:
                sentype = self.segtext[idx][4]
        return sentype
    
    def set_sentype(self, idx: int, sentype: int = 0):
        if -len(self.segtext) <= idx < len(self.segtext):
            self.segtext[idx][4] = sentype
    
    def get_mark(self, idx: int, mark=None):
        if -len(self.segtext) <= idx < len(self.segtext):
            if self.segtext[idx][5] is not None:
                mark = self.segtext[idx][5]
        return mark
    
    def set_mark(self, idx: int, mark: str):
        if -len(self.segtext) <= idx < len(self.segtext):
            self.segtext[idx][5] = mark
    
    def __str__(self):
        return self.printer()
    
    def __getitem__(self, idx):
        return self.segtext[idx]
    
    def __setitem__(self, idx, val):
        self.segtext[idx] = val
    
    def __delitem__(self, idx):
        self.segtext.pop(idx)
    
    def __len__(self):
        return len(self.segtext)
        
    def __add__(self, other):
        tmp = SegText()
        tmp.segtext = self.segtext + other.segtext
        return tmp
    
    def __iadd__(self, other):
        self.segtext += other.segtext
        return self
    
    def append(self, elem=None):
        if elem is None:
            elem = [None for _ in range(SegText._ncols)]
        self.segtext.append(elem)
    
    def extend(self, other):
        self.segtext.extend(other.segtext)
    
    def pop(self, idx=-1):
        self.segtext.pop(idx)
    
    def clear(self):
        self.segtext.clear()
    
    def insert(self, idx, elem=None):
        if elem is None:
            elem = [None for _ in range(SegText._ncols)]
        self.segtext.insert(idx, elem)
    
    def copy(self, start=0, end=None):
        # deeply copy
        tmp = SegText()
        if end is None: end = len(self.segtext)
        for i in range(start, end):
            tmp.segtext.append(self.segtext[i].copy())
        return tmp


