# coding: utf-8

import os, sys
import re
import json

import textparser
from textparser import Config
from textparser.utils import DBC2SBC, Syllable, Lang
from textparser.version import __version__


class T2S(object):
    def __init__(self, res_file):
        with open(res_file, 'r', encoding="utf-8") as f:
            self.map = json.load(f)
    
    def __call__(self, text):
        return "".join([self.map.get(x, x) for x in text])


class Num2WrdCN(object):
    def __init__(self):
        self.DIG = ('零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十')
        self.YAO = ('零', '幺', '二', '三', '四', '五', '六', '七', '八', '九', '十')
        self.LIA = ('零', '一', '两', '三', '四', '五', '六', '七', '八', '九', '十')
        self.ORD = ('', '十', '百', '千')
        self.MAG = ('', '万', '亿', '兆', '京', '垓', '秭', '穰', '沟', '涧', '正', '载', '极', '恒河沙', '阿僧祗', '那由他', '不可思议', '无量大数')
        self.DOT = '点'
        self.NEG = '负'
        self.LIATEN = '两十'
        self.TWOTEN = '二十'
        self.ZERO = '零'

    def __call__(self, nums, cnf="m"):
        nums = DBC2SBC(nums).strip()
        
        if nums == '':
            return ''
        
        if cnf == 'm':
            return self._num2word_m(nums)
        elif cnf == 'i':
            return self._num2word_i(nums)
        elif cnf == 's':
            return self._num2word_s(nums)
        elif cnf == 'l':
            return self._num2word_l(nums)
        elif cnf == 'o':
            return self._num2word_o(nums)
        return self._num2word_s(nums)
    
    def _number_to_zh(self, istr):

        outs = ''
        if istr == '': return outs
        
        # judge negtive
        if istr[0] == '-':
            outs += self.NEG
            istr = istr[1:]
        
        # istr -> integer.decimal
        arr = istr.split('.')
        integer, decimal = arr[0], ''
        if len(arr) > 1: decimal = arr[1]

        # delete head zeros
        integer = integer.lstrip('0')
        if integer == '': integer = '0'

        if integer == '0': outs += self.ZERO

        # split by group
        L = len(integer)
        N, D = L // 4, L % 4
        M = N + int(D > 0)
        chunks = [None for _ in range(M)]
        mag = M - 1
        if D > 0:
            chunks[0] = integer[:D]
        for i in range(N):
            chunks[i+int(D>0)] = integer[D+i*4:D+i*4+4]

        # replace integer
        for num in chunks:
            num = int(num)
            tmp = ''
            for i in (3,2,1,0):
                n = int(num / (10 ** i)) % 10
                if not(tmp != '' or n != 0): continue
                if not((self.ZERO in tmp and n == 0) or (i ==  n == 1 and tmp == '')):
                    tmp += self.LIA[n]
                if n:
                    tmp += self.ORD[i]
            if tmp != self.ZERO and tmp != '' and tmp[-1] == self.ZERO: tmp = tmp[:-1]
            if tmp != '': tmp += self.MAG[mag]
            if (num < 1000) and (mag != M - 1) and (self.ZERO not in outs):
                tmp = self.ZERO + tmp
            outs += tmp
            mag -= 1
        
        # if int(integer) != 0 and outs != '' and outs[-1] == sel.ZERO
        if outs != self.ZERO and outs != '' and outs[-1] == self.ZERO:
            outs = outs[:-1]
        
        # 两 -> 二
        outs = outs.replace('两十', '二十')
        if outs != '' and outs[-1] == '两': outs = outs[:-1] + '二'
        
        # replace decimal
        if decimal != '':
            outs += self.DOT
            for s in decimal:
                outs += self.DIG[int(s)]
        
        if outs == '': outs = self.ZERO

        return outs
    
    def _num2word_m(self, nums):
        zh = self._number_to_zh(nums)
        return zh
    
    def _num2word_i(self, nums):
        zh = ''.join([self.YAO[int(i)] for i in nums])
        return zh
    
    def _num2word_s(self, nums):
        zh = ''.join([self.DIG[int(i)] for i in nums])
        return zh
    
    def _num2word_l(self, nums):
        if nums == '2': return '两'
        return self._num2word_m(nums)
    
    def _num2word_o(self, nums):
        if int(nums) == 0: return self.ZERO
        ling = self.ZERO if nums[0] == '0' else ''
        return ling + self._num2word_m(nums)


class TextNormalizerCN(object):
    def __init__(self, res_root_dir=None, loglv=0):
        self.loglv = loglv
        self.dtable = dict()
        
        # default resource paths
        if res_root_dir is None: res_root_dir = textparser.__path__[0]
        self.res_paths = [
            os.path.join(res_root_dir, path)
            for path in Config.cn_special_symbols_paths
        ]

        self.files_mtime = dict()
        
        rulelist = list()
        for res_path in self.res_paths:
            rulelist += self._load(res_path)
            self.files_mtime[res_path] = int(os.stat(res_path).st_mtime)
        
        # sort by weight
        self.rulelist = tuple(sorted(rulelist, key=lambda x:x[0], reverse=True))
        
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: rule count={len(self.rulelist)}\n")
        
        # compile regex
        self.regex = {
            '^([\u4e00-\u9fa5]+)': re.compile(r'^([\u4e00-\u9fa5]+)'),
            '^([a-zA-Z\']+)': re.compile(r'^([a-zA-Z\']+)'),
            '^(\d+)': re.compile(r'^(\d+)'),
            '^(\s+)': re.compile(r'^(\s+)'),
            '^([a-z]{1})<([^>]*)>$': re.compile(r'^([a-z]{1})<([^>]*)>$'),
            '^([a-z]{1})<([^>]+)>': re.compile(r'^([a-z]{1})<([^>]+)>'),
            '<([^>]+)>$': re.compile(r'<([^>]+)>$'),
            '^(\d+)': re.compile(r'^(\d+)'),
            '^([dtyfismlo]{1})': re.compile(r'^([dtyfismlo]{1})'),
            '^<(.+?)>': re.compile(r'^<(.+?)>'),
            '^(\d+)(.+)$': re.compile(r'^(\d+)(.+)$'),
        }
        
        self.N2W = Num2WrdCN()
        self.T2S = T2S(os.path.join(res_root_dir, Config.cn_t2s_path))

    def _load(self, filename):
        func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: load from {filename}\n")
        
        with open(filename, 'rt') as f:
            lines = f.readlines()
        
        hvar = dict()
        rulelist = list()
        for line in lines:
            line = line.strip()
            if line == '': continue
            mr = re.match(r'^#!DT!#(.+)$', line)
            if mr:
                k, v = mr.group(1).strip().split()
                self.dtable[k] = v
                continue
            if line[0] == '#': continue
            mr = re.match(r'^(\$\{.+?\})\s*=(.+)$', line)
            if mr:
                k, v = mr.group(1), mr.group(2)
                hvar[k] = v.strip()
                continue
            if self.loglv >= 3:
                sys.stderr.write(f"{func_name}: parse one line: {line}\n")
            mr = re.match(r'^(\d+)\?(.+):([a-z]{1}<.+)$', line)
            if mr:
                weight, tkn, result = mr.group(1), mr.group(2), mr.group(3)
                # weight
                weight = int(weight)
                # token list
                tknlist = [None for _ in range(10)]
                while tkn != "":
                    mr = re.match(r'^([1-9]{1})([SMFYH]{1})\s*', tkn)
                    if mr:
                        i, j = mr.group(1), mr.group(2)
                        tknlist[int(i)] = j
                        tkn = tkn[mr.end(2):].strip()
                    else:
                        break
                while tknlist[-1] is None:
                    tknlist.pop(-1)
                # token property
                tknprop = dict()
                while tkn != "":
                    mr = re.match(r'^(\d{1})([bd]{1})([\{\}!#]{1})(\"[^\"]+?\")\s*', tkn)
                    if mr:
                        idx_, opr1_, opr2_ = mr.group(1), mr.group(2), mr.group(3)
                        key_ = idx_ + opr1_ + opr2_
                        val_ = mr.group(4)
                        tkn = tkn[mr.end(4):].strip() # new tkn
                        # expand vars
                        while True:
                            mr = re.match(r'.*?(\$\{.+?\})', val_)
                            if mr:
                                vn = mr.group(1)
                                assert vn in hvar, f"{func_name}: find {vn} is not in hvar when parse line={line}\n"
                                vv = hvar[vn]
                                val_ = val_.replace(vn, vv)
                                if self.loglv >= 3:
                                    sys.stderr.write(f"{func_name}: {vn} -> {vv}, val_={val_}\n")
                            else:
                                break
                        tknprop[key_] = val_
                        # check invalid
                        assert 0 < int(idx_) < len(tknlist), f"{func_name}: invalid property {key_} {val_} in {line}"
                        if opr1_ == 'd':
                            assert tknlist[int(idx_)] == 'Y', f"{func_name}: invalid property {key_} {val_} in {line}\n"
                        continue
                    mr = re.match(r'^(\d{1})([ht]{1})([\{\}!#]{1})(\d+\"[^\"]+?\")\s*', tkn)
                    if mr:
                        idx_, opr1_, opr2_ = mr.group(1), mr.group(2), mr.group(3)
                        key_ = idx_ + opr1_ + opr2_
                        val_ = mr.group(4)
                        tkn = tkn[mr.end(4):].strip() # new tkn
                        # expand vars
                        while True:
                            mr = re.match(r'.*?(\$\{.+?\})', val_)
                            if mr:
                                vn = mr.group(1)
                                assert vn in hvar, f"{func_name}: find {vn} is not in hvar when parse line={line}\n"
                                vv = hvar[vn]
                                val_ = val_.replace(vn, vv)
                                if self.loglv >= 3:
                                    sys.stderr.write(f"{func_name}: {vn} -> {vv}, val_={val_}\n")
                            else:
                                break
                        tknprop[key_] = val_
                        # check invalid
                        assert 0 < int(idx_) < len(tknlist), f"{func_name}: invalid property {key_} {val_} in {line}"
                        continue
                    mr = re.match(r'(\d{1})([zc]{1})([<>=]{1})(\S+)\s*', tkn)
                    if mr:
                        idx_, opr1_, opr2_ = mr.group(1), mr.group(2), mr.group(3)
                        key_ = idx_ + opr1_ + opr2_
                        val_ = mr.group(4)
                        tkn = tkn[mr.end(4):].strip() # new tkn
                        tknprop[key_] = val_
                        flag = 1
                        # check invalid
                        if opr1_ == 'z':
                            assert 0 < int(idx_) < len(tknlist) and (tknlist[int(idx_)] in 'SM'), f"{func_name}: invalid property {key_} {val_} in {line}"
                        continue
                    assert 0, f"{func_name}: unkown property {tkn} in {line}"
                # result
                check = result
                while True:
                    mr = re.match(r'^([dtyfismlo]{1}(<.+?>){1,};)', check)
                    if not mr: break
                    check = check[mr.end(1):]
                    #ret = mr.group(2)
                    # todo check result
                    # ....
                assert check == '', f"{func_name}: unkown result {check} in {line}"
                result = result.strip(';') # delete last ';'
                # output
                rulelist.append((weight, tknlist, tknprop, result))
                # trace
                if self.loglv >= 3:
                    sys.stderr.write(f"line={line}\n")
                    sys.stderr.write(self._rule_printer(rulelist[-1]))
            else:
                assert 0, f"{func_name}: parse rule error, rule={line}"

        # trace
        if self.loglv >= 3:
            for rule in rulelist:
                self._rule_printer(rule)
        
        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: load from {filename}, rule count={len(rulelist)}\n")
        
        return rulelist

    def _rule_printer(self, rule: list):
        weight, tknlist, tknprop, result = rule
        _str = "-----------------------------\n"
        _str += f"weight: {weight}\n"
        _str += f"tknlist: "
        for i in range(1, len(tknlist)):
            _str += f"{i}{tknlist[i]} "
        _str += f"\ntknproperty:"
        for k in tknprop:
            v = tknprop[k]
            _str += f"{k}{v} "
        _str += f"\nresult: {result}\n"
        _str += "-----------------------------\n"
        return _str
    
    def _token_printer(self, token: list):
        _str = "-----------------------------\n"
        for tk in token:
            _str += f"tokenize: {tk[0]} `{tk[1]}`"
            if len(tk) > 2:
                _str += f" `{tk[2]}`"
            _str += "\n"
        _str += "-----------------------------\n"
        return _str

    def tokenize(self, istr: str):
        istr = DBC2SBC(istr).strip()

        tokenlist = []
        while istr != '':
            # H token
            mr = self.regex['^([\u4e00-\u9fa5]+)'].match(istr)
            if mr:
                istr = istr[mr.end(1):]
                tokenlist.append(['H', mr.group(1)])
                continue
            # Y token
            mr = self.regex['^([a-zA-Z\']+)'].match(istr)
            if mr:
                istr = istr[mr.end(1):]
                tokenlist.append(['Y', mr.group(1)])
                continue
            # S token
            mr = self.regex['^(\d+)'].match(istr)
            if mr:
                istr = istr[mr.end(1):]
                tokenlist.append(['S', mr.group(1)])
                continue
            # F token, specail blanks
            mr = self.regex['^(\s+)'].match(istr)
            if mr:
                istr = istr[mr.end(1):]
                tokenlist.append(['F', ' '])
                continue
            # F token
            ch = istr[0]
            istr = istr[1:]
            if len(tokenlist) > 0 and tokenlist[-1][1] == ch and ch in "——……": # 合并特例
                tokenlist[-1][1] += ch
            else:
                tokenlist.append(['F', ch])
        
        # post process
        outputs = []
        i, N = 0, len(tokenlist)
        while i < N:
            # combine S.S => M
            if i + 2 < N and (tokenlist[i][0] == 'S' and tokenlist[i+1][1] == '.' and tokenlist[i+2][0] == 'S'):
                if (i > 0 and tokenlist[i-1][1] == '.') or (i + 3 < N and tokenlist[i+3][1] == '.'):
                    # maybe ip address or version, etc.
                    pass
                else:
                    outputs.append(['M', tokenlist[i][1]+tokenlist[i+1][1]+tokenlist[i+2][1]])
                    i += 3
                    continue
            # delete blank between these cases: S+F/F+S/Y+S/S+Y/F+Y/Y+F
            if ((tokenlist[i][1] == ' ' and (0 < i < N-1)) \
                and (tokenlist[i-1][0] in 'SFY' and tokenlist[i+1][0] in 'SFY') \
                and (tokenlist[i-1][0] != tokenlist[i+1][0]) \
            ):
                i += 1
                continue
            # identify pinyin mark, such as `(chong2)`
            if (((i + 4 < N) and tokenlist[i][0] == 'H')
                and (tokenlist[i+1][0] == tokenlist[i+4][0] == 'F')
                and (  (tokenlist[i+1][1] == '(' and tokenlist[i+4][1] == ')')
                    or (tokenlist[i+1][1] == '（' and tokenlist[i+4][1] == '）')
                    or (tokenlist[i+1][1] == '[' and tokenlist[i+4][1] == ']')
                    or (tokenlist[i+1][1] == '【' and tokenlist[i+4][1] == '】')
                    or (tokenlist[i+1][1] == '<' and tokenlist[i+4][1] == '>')
                )
                and (tokenlist[i+2][0] == 'Y' and tokenlist[i+3][0] == 'S')
                and (Syllable.is_py(tokenlist[i+2][1]) and 0 <= int(tokenlist[i+3][1]) <= 5)
            ):
                if len(outputs) > 0 and outputs[-1][0] == 'H':
                    outputs[-1][1] += tokenlist[i][1]
                else:
                    outputs.append(tokenlist[i])
                position = len(outputs[-1][1])
                pinyin = '(' + tokenlist[i+2][1] + tokenlist[i+3][1] + ')'
                if len(outputs[-1]) > 2:
                    outputs[-1][2] += f" {position}{pinyin}"
                else:
                    outputs[-1].append(f"{position}{pinyin}")
                i += 5
                continue
            # combine H token
            if len(outputs) > 0 and outputs[-1][0] == tokenlist[i][0] == 'H':
                outputs[-1][1] += tokenlist[i][1]
                i += 1
                continue
            # others
            outputs.append(tokenlist[i])
            i += 1
            continue
        
        # trace token
        if self.loglv > 0:
            sys.stderr.write(self._token_printer(outputs))
        
        return outputs

    def process(self, tokens):
        changed = []
        preToken = None     # 上条规则匹配的最后一个token，用于规则的连接
        preTokenId = None   # 上条规则匹配的最后一个token，用于规则的连接的判断
        preResult = None    # 上条规则匹配的最后一个result，用于规则的连接的判断
        link_rule = 0       # 是否连接上条规则匹配的最后一个token一起匹配，值为0/1
        while len(tokens) > 0:
            rule_matched = None     # 返回匹配的规则
            ret = None              # 返回匹配的token数目
            for rule in self.rulelist:
                # match rule
                if link_rule:
                    ret = self.match([preToken, *tokens], rule) # 和前一个token连接后一起去匹配
                else:
                    ret = self.match(tokens, rule)
                if ret <= 0:
                    if self.loglv > 2:
                        sys.stderr.write(f"Match Rule:\n")
                        sys.stderr.write(self._rule_printer(rule))
                        sys.stderr.write(f"Failed, ret = {ret}\n")
                    continue
                # match success
                rule_matched = rule
                break

            weight, tknlist, tknprop, result = rule_matched
            if self.loglv > 0:
                sys.stderr.write(f"Tokens={tokens}\nMatch success:\n")
                sys.stderr.write(self._rule_printer(rule_matched))
            # 连接规则的一些情况判断
            if link_rule:
                if ret == 1: # 只匹配到上一个token，所以匹配失败
                    if self.loglv > 1:
                        sys.stderr.write(f"Only Match preToken, drop it 0!\n")
                    link_rule = 0
                    continue
                # 上条规则匹配的最后一个token的result和本条规则的第一个token的result是否一致
                curResult = result.split(';').pop(0)
                mr = self.regex['^([a-z]{1})<([^>]*)>$'].match(curResult)
                if not mr:
                    if self.loglv > 1:
                        sys.stderr.write(f"The curResult{curResult} not unique, drop it!\n")
                    link_rule = 0
                    continue
                a, c = mr.group(1), mr.group(2)
                mr = self.regex['^([a-z]{1})<([^>]+)>'].match(preResult)
                b, d = mr.group(1), mr.group(2)
                mr = self.regex['<([^>]+)>$'].match(preResult)
                if mr: d = mr.group(1)
                if a != b:
                    if self.loglv > 1:
                        sys.stderr.write(f"The preResult[{b},{d}] is not equal to curResult[{a},{c}], drop it 1!\n")
                    link_rule = 0
                    continue
                if c.isdigit() and d.isdigit():
                    if int(c) != 1 or int(d) != preTokenId:
                        if self.loglv > 1:
                            sys.stderr.write(f"The preResult[{b},{d}] is not equal to curResult[{a},{c}], drop it 2!\n")
                        link_rule = 0
                        continue
                elif c != d:
                    if self.loglv > 1:
                        sys.stderr.write(f"The preResult[{b},{d}] is not equal to curResult[{a},{c}], drop it 3!\n")
                    link_rule = 0
                    continue
            # replace
            replaced = self.replace(tokens, result, link_rule)
            changed += replaced
            if self.loglv > 1:
                sys.stderr.write(f"Replaced = " + " ".join(replaced) + "\n")
            # shift tokens
            preToken0 = None
            for i in range(1, len(tknlist) - link_rule):
                preToken0 = tokens.pop(0)
            # trace token
            if self.loglv > 1 and len(tokens) > 0:
                if link_rule:
                    sys.stderr.write(self._token_printer([preToken, *tokens]))
                else:
                    sys.stderr.write(self._token_printer(tokens))
            # link rule
            preToken = preToken0
            preTokenId = len(tknlist) - 1
            preResult = result.split(';').pop(-1)
            if preTokenId > 1: link_rule = 1

        touched = "".join(changed)
        return touched
    
    def match(self, tokens, rule):
        weight, tknlist, tknprop, result = rule
        # match token number
        if len(tokens) < len(tknlist) - 1:
            return -1
        # match token type
        for i in range(1, len(tknlist)):
            if tknlist[i] != tokens[i-1][0]:
                if tknlist[i] == 'M' and tokens[i-1][0] == 'S':
                    continue
                return -2
        # define match functions
        def match_c(val:str, opr:str, content:str):
            val, content = int(val), len(content)
            if opr == '=': return content == val
            elif opr == '<': return content < val
            elif opr == '>': return content > val
            elif opr == '!': return content != val
            return True
        def match_z(val:str, opr:str, content:str):
            val, content = float(val), float(content)
            if opr == '=': return content == val
            elif opr == '<': return content < val
            elif opr == '>': return content > val
            elif opr == '!': return content != val
            return True
        def match_b(val:str, opr:str, content:str):
            val = val.strip('"').strip('^')
            items = val.split('^')
            if opr == '#':
                if content in items: return True
            elif opr == '}':
                for item in items:
                    if content.find(item) != -1: return True
            elif opr == '{':
                for item in items:
                    if item.find(content) != -1: return True
            elif opr == '!':
                return all([content != item for item in items])
            return False
        def match_d(val:str, opr:str, content:str):
            return match_b(val, opr, content.upper())
        def match_t(val:str, opr:str, content:str):
            mr = self.regex['^(\d+)'].match(val)
            n = mr.group(1)
            val = val[mr.end(1):]
            content = content[-int(n):]
            return match_b(val, opr, content)
        def match_h(val:str, opr:str, content:str):
            mr = self.regex['^(\d+)'].match(val)
            n = mr.group(1)
            val = val[mr.end(1):]
            content = content[:int(n)]
            return match_b(val, opr, content)
        
        # match token property
        orres, isorres = -1, -1
        for tknp in tknprop:
            val = tknprop[tknp]
            ii, condition, opr = int(tknp[0]) - 1, tknp[1], tknp[2]

            isor = -1
            if len(tknp) > 3:
                isor, isorres = 1, 1
            if isor == 1 and orres == 1:
                continue

            res = 0
            content = tokens[ii][1]
            if condition == 'c':
                if not match_c(val, opr, content): res = -3
            elif condition == 'z':
                if not match_z(val, opr, content): res = -4
            elif condition == 'b':
                if not match_b(val, opr, content): res = -5
            elif condition == 'd':
                if not match_d(val, opr, content): res = -6
            elif condition == 'h':
                if not match_h(val, opr, content): res = -7
            elif condition == 't':
                if not match_t(val, opr, content): res = -8
            
            if isor == -1 and res < 0: return res
            elif isor == 1 and res == 0: orres = 1

        if isorres == 1 and orres != 1: return -9

        return len(tknlist) - 1 # 返回匹配的token数量
    
    def replace(self, tokens, result, link_rule):
        def _dtable2word(fh: str, flag: int):
            val = self.dtable.get(fh.upper(), '') if flag else self.dtable.get(fh, fh)
            return val
        
        results = result.split(';')
        if link_rule: results.pop(0)

        outputs = []
        for rp in results:
            mr = self.regex['^([dtyfismlo]{1})'].match(rp)
            opr = mr.group(1)
            rp = rp[mr.end(1):]
            str_con = ''
            while rp != '':
                while rp[0] != '<': rp = rp[1:]
                mr = self.regex['^<(.+?)>'].match(rp)
                if not mr: break
                ic = mr.group(1)
                rp = rp[mr.end(1)+1:]
                if ic.isdigit():
                    i = int(ic) - 1 - link_rule
                    cont = tokens[i][1]
                    if len(tokens[i]) > 2: # 判断是否有特殊标记
                        cont = list(cont)
                        for pp in reversed(tokens[i][2].strip().split()):
                            mr = self.regex['^(\d+)(.+)$'].match(pp)
                            assert mr
                            position, pinyin = int(mr.group(1)), mr.group(2)
                            cont.insert(position, pinyin)
                        cont = "".join(cont)
                    str_con += cont
                else:
                    cont = ic
                    str_con += cont
            if opr == 't' or opr == 'y':
                outputs.append(str_con)
            elif opr == 'f' or opr == 'd':
                outputs.append(_dtable2word(str_con, 0 if opr == 'f' else 1))
            else: #  opr in 'msilo':
                outputs.append(self.N2W(str_con, opr))

        return outputs
    
    def update(self):
        is_change = False
        for res_path in self.res_paths:
            if self.files_mtime[res_path] != int(os.stat(res_path).st_mtime):
                is_change = True
        if is_change:
            rulelist = list()
            for res_path in self.res_paths:
                rulelist += self._load(res_path)
                self.files_mtime[res_path] = int(os.stat(res_path).st_mtime)
            self.rulelist = tuple(sorted(rulelist, key=lambda x:x[0], reverse=True))

    def __call__(self, utt_id, utt_text):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: input> utt_id={utt_id}, utt_text=`{utt_text}`\n")
            
        utt_text = self.T2S(utt_text)
        utt_text = self.process(self.tokenize(utt_text))

        # 标点统一替换成全角
        utt_text = utt_text.replace(',', '，')
        utt_text = utt_text.replace('!', '！')
        utt_text = utt_text.replace('?', '？')
        utt_text = utt_text.replace(':', '：')
        utt_text = utt_text.replace(';', '；')

        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: output> utt_id={utt_id}, utt_text=`{utt_text}`\n")

        return utt_id, utt_text


class Num2WrdEN(object):
    def __init__(self):
        self.D = dict(
            [("0", "zero"), ("1", "one"), ("2", "two"), ("3", "three"), ("4", "four"), ("5", "five"), ("6", "six"), ("7", "seven"), ("8", "eight"), ("9", "nine"), 
             ("00", "zero"), ("01", "one"), ("02", "two"), ("03", "three"), ("04", "four"), ("05", "five"), ("06", "six"), ("07", "seven"), ("08", "eight"), ("09", "nine"), 
            ("10", "ten"), ("11", "eleven"), ("12", "twelve"), ("13", "thirteen"), ("14", "fourteen"), ("15", "fifteen"), ("16", "sixteen"), ("17", "seventeen"), ("18", "eighteen"), ("19", "nineteen"), 
            ("20", "twenty"), ("30", "thirty"), ("40", "forty"), ("50", "fifty"), ("60", "sixty"), ("70", "seventy"), ("80", "eighty"), ("90", "ninety")]
        )
        self.DD = dict(
            [("0", "oh"), ("1", "one"), ("2", "two"), ("3", "three"), ("4", "four"), ("5", "five"), ("6", "six"), ("7", "seven"), ("8", "eight"), ("9", "nine"), 
             ("00", "oh"), ("01", "one"), ("02", "two"), ("03", "three"), ("04", "four"), ("05", "five"), ("06", "six"), ("07", "seven"), ("08", "eight"), ("09", "nine")]
        )
        self.OhDD = dict(
            [("0", "oh"), ("1", "one"), ("2", "two"), ("3", "three"), ("4", "four"), ("5", "five"), ("6", "six"), ("7", "seven"), ("8", "eight"), ("9", "nine"), 
             ("00", "oh oh"), ("01", "oh one"), ("02", "oh two"), ("03", "oh three"), ("04", "oh four"), ("05", "oh five"), ("06", "oh six"), ("07", "oh seven"), ("08", "oh eight"), ("09", "oh nine")]
        )
        for i in range(10, 100):
            x = str(i)
            self.DD[x] = self.OhDD[x] = self._num2en(x)
        self.Card2Ord = dict(
            [("one", "first"), ("two", "secord"), ("three", "third"), ("five", "fifth"), ("eight", "eighth"), ("nine", "ninth"), ("twelve", "twelfth")]
        )
        self.Mult = ["", "thousand", "million", "billion", "trillion", "quadrillion", "quintillion", "sextillion", "septillion", "octillion", "nonillion"]
        self.Month = dict(
             [("1", "January"), ("2", "February"), ("3", "March"), ("4", "April"), ("5", "May"), ("6", "June"),
             ("7", "July"), ("8", "August"), ("9", "September"), ("10", "October"), ("11", "November"), ("12", "December")]
        )
    
    def _del_front_zero(self, x: str):
        while len(x) > 2:
            if x[0] == '0' and x[1].isdigit(): x = x[1:]
            else: break
        return x
    
    def _fraction2words(self, x: str):
        # format: 2/3
        xs = x.split("/")
        assert len(xs) == 2, f"x={x}"
        numberator, denominator = xs
        if denominator == "2":
            if numberator == "1":
                return "one half"
            else:
                return self._num2en(numberator) + " halves"
        elif denominator == "4":
            if numberator == "1":
                return "one quarter"
            else:
                return self._num2en(numberator) + " quarters"
        elif int(denominator) < 20:
            if numberator == "1":
                return "one " + self._num2en_ordinal(denominator)
            else:
                return self._num2en(numberator) + " " + self._num2en_ordinal(denominator) + "s"
        else:
            return self._num2en(numberator) + " over " + self._num2en(denominator)

    def _num2en_ordinal(self, x: str):
        #  Cardinals are [one two three...]
        #  Ordinals  are [first second third...]
        x = self._num2en(x)
        xs = x.split()
        if not xs[-1].isalpha():
            return x + "th"
        last = xs[-1]
        if last in self.Card2Ord:
            last = self.Card2Ord[last]
        elif last[-1] == "y":
            last = last[:-1] + "ieth"
        elif last[-2:] != "th":
            last += "th"
        xs[-1] = last
        return " ".join(xs)
    
    def _num2en(self, x: str):
        def _groupify(basic: str, multnum: int):
            # turn [seventeen, 3] to seventeen billion
            if multnum == 0: return basic # the first group is unitless
            if multnum < len(self.Mult): return basic + " " + self.Mult[multnum]
            # Otherwise it must be huuuuuge, so fake it with scientific notation
            return basic + " times ten to the " + self._num2en_ordinal(multnum * 3)
        def _chunks2en(chunks: list):
            out = []
            for chunk in chunks:
                if len(chunk[0]) == 0 or int(chunk[0]) == 0: continue # bugfix : 400,000
                out.append(_groupify(_int2en(chunk[0]), chunk[1]))
            return out
        def _int2en(x: str):
            if x in self.D: return self.D[x]
            if len(x) == 2:
                # like forty two
                # note that neither bit can be zero at this point
                return self.D[x[0]+"0"] + " " + self.D[x[1]]
            elif len(x) == 3:
                h, rest = self.D[x[0]] + " hundred", x[1:]
                if x[0] == "0":
                    h = ""
                    if rest == "00": return h
                    return _int2en(rest)
                if rest == "00":
                    return h
                return h + " and " + _int2en(rest)
            else:
                return _bigint2en(x)
        def _bigint2en(x: str):
            chunks, groupnum = [], 0
            # pull at most three digits from the end
            while len(x) > 0:
                num = x[-3:]
                x = x[:-3]
                if len(num) > 0: chunks.insert(0, [num, groupnum])
                groupnum += 1
            if len(chunks) == 0: return self.D['0'] # rare but possible
            
            # The special 'and' that shows up in like "one thousand and eight"
            # and "two billion and fifteen", but not "one thousand [*and] five hundred"
            # or "one million, [*and] nine"
            and_ = "and" if int(chunks[-1][1]) == 0 and int(chunks[-1][0]) < 100 else ""
            chunks = _chunks2en(chunks)
            
            # bugfix: neilb: deals with case where we have at least millions, thousands,
            # but 00N for the last chunk.
            # $chunks[-2] .= " and" if $and and @chunks > 1;
            if and_ != "" and len(chunks) > 1:
                chunks[-2] += " and " + chunks[-1]
                chunks.pop()
            
            # Avoid having a comma if just two units
            if len(chunks) == 2 and and_ == "":
                return chunks[0] + " " + chunks[1]
            
            return ", ".join(chunks)
        
        x = x.lower()
        if x == "nan": return "not-a-number"
        if x == "+inf" or x == "+infinity": return "positive infinity"
        if x == "-inf" or x == "-infinity": return "negative infinity"
        if x == "inf": return "infinity"
        
        x_ = x
        x = self._del_front_zero(x)
        sign = ""
        if x[0] == "-" or x[0] == "+":
            sign = x[0]
            x = x[1:]
        
        # x: [0-9]*.[0-9]*
        int_, fract = None, None
        xs = x.split('.')
        if len(xs) == 1:
            int_ = x
        elif len(xs) == 2:
            if xs[0] == "": int_, fract = None, xs[1]
            elif xs[1] == "": int_, fract = xs[0], None
            else: int_, fract = xs
        else:
            # x is not number
            return "unkown number"
        
        # sign
        out = ""
        if sign == "+": out += "positive "
        elif sign == "-": out += "negative "
        
        # interger
        if int_ is not None:
            out += _int2en(int_) + " "
        
        # float
        if fract is not None:
            while len(fract) > 1:
                if fract[-1] == "0": fract = fract[:-1]
                else: break
            if len(fract) > 0:
                out += "point " + self._num2word_s(fract) + " "
        
        return out.rstrip()
    
    def _num2word_m(self, x: str):
        x = self._del_front_zero(x)
        return self._num2en(x)
    
    def _num2word_s(self, x: str):
        x = [self.D[i] for i in x]
        return " ".join(x)
    
    def _num2word_o(self, x: str):
        x = [self.DD[i] for i in x]
        return " ".join(x)

    def _num2word_x(self, x: str):
        x = self._del_front_zero(x)
        return self._num2en_ordinal(x)
    
    def _num2time(self, x: str, is_us=True):
        # format: hh:mm[:ss]
        xs = x.split(":")
        h, m = xs[:2]
        s = xs[2] if len(xs) == 3 else None
        out = ""
        if int(m) == 0:
            out += self._num2en(h)
        elif int(m) == 15:
            out += "a quarter"
            out += " after" if is_us else " past"
            out += " " + self._num2en(h)
        elif int(m) == 45:
            out += "a quarter"
            out += " of" if is_us else " to"
            out += " " + self._num2en(str(int(h)+1))
        else:
            out += self._num2en(h) + " " + self._num2en(m)
        
        if s is not None:
            out += " " + self._num2en(s)
            if 0 < int(s) <= 1:
                out += " second"
            else:
                out += " seconds"
        
        return out
    
    def _num2year(self, y: str):
        if self._del_front_zero(y) == "0": return "zero"
        if y in self.DD: return self.DD[y]
        
        if len(y) == 5:
            if y[2:] == "000":
                return self.DD[y[:2]] + " thousand"
            if y[1] == "0":
                # A family of troublesome cases: things like "60123".
                # We can't say "sixty one twenty-three" because that sounds
                # just like sixty-one twenty-three.  So we special-case this
                # whole group.
                if y[2:] == "000": return self.DD[y[:2]] + " thousand"
                if y[2:4] == "00": return self.DD[y[:2]] + " thousand " + self.D[y[-1]]
                if y[2] == "0": return self.DD[y[:2]] + " thousand " + self.DD[y[3:]]
                if y[-2:] == "00": return self.DD[y[:2]] + " thousand " + self.D[y[2]] + " hundred"
                return self.DD[y[:2]] + " thousand " + self.D[y[2]] + " " + self.OhDD[y[3:]]
            if y[2:4] == "00": return self.DD[y[:2]] + " oh oh " + self.DD[y[-1]]
            if y[2] == "0": return self.DD[y[:2]] + " oh " + self.DD[y[3:]]
            return self.OhDD[y[:2]] + " " + self.D[y[2]] + " " + self.OhDD[y[3:]]
        elif len(y) == 4:
            if y[1:] == "000": return self.DD[y[0]] + " thousand"
            if y[2:] == "00": return self.DD[y[:2]] + " hundred"
            if y[1:3] == "00": return self.DD[y[0]] + " thousan and " + self.DD[y[-1]]
            return self.OhDD[y[:2]] + " " + self.OhDD[y[2:]]
        elif len(y) == 3:
            if y[1:] == "00": return self.DD[y[0]] + " hundred"
            return self.OhDD[y[0]] + " " + self.OhDD[y[1:]]
        
        return self._num2en(y)
        
    def _num2month(self, m: str):
        m = self._del_front_zero(m)
        return self.Month.get(m, "")
        
    def __call__(self, nums, cnf="m"):
        nums = DBC2SBC(nums).strip()
        
        if nums == '':
            return ''
        
        if cnf == 'o':
            return self._num2word_o(nums)
        elif cnf == 's':
            return self._num2word_s(nums)
        elif cnf == 'm':
            return self._num2word_m(nums)
        elif cnf == 'e':
            return self._fraction2words(nums)
        elif cnf == 'x':
            return self._num2word_x(nums)
        elif cnf == 'n':
            ends = nums[-1].lower() == "s"
            ye = self._num2year(nums[:-2] if nums[-2] == "'" else nums[:-1]) if ends else self._num2year(nums)
            if ends:
                ye = ye[:-1] + "ies" if ye[-1] == "y" else ye + "s"
            return ye
        elif cnf == 'u':
            return self._num2month(nums)
        elif cnf == 'j':
            return self._num2time(nums)
        return self._num2word_s(nums)


class TextNormalizerEN(object):
    def __init__(self, res_root_dir=None, loglv=0):
        self.loglv = loglv
        self.dtable = dict()
        
        # default resource paths
        if res_root_dir is None: res_root_dir = textparser.__path__[0]
        self.res_paths = [
            os.path.join(res_root_dir, path)
            for path in Config.en_special_symbols_paths
        ]

        self.files_mtime = dict()
        
        rulelist = list()
        for res_path in self.res_paths:
            rulelist += self._load(res_path)
            self.files_mtime[res_path] = int(os.stat(res_path).st_mtime)
        
        # sort by weight
        self.rulelist = tuple(sorted(rulelist, key=lambda x:x[0], reverse=True))
        
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: rule count={len(self.rulelist)}\n")
        
        # compile regex
        self.regex = {
            '^([\u4e00-\u9fa5]+)': re.compile(r'^([\u4e00-\u9fa5]+)'),
            '^([a-zA-Z\']+)': re.compile(r'^([a-zA-Z\']+)'),
            '^(\d+)': re.compile(r'^(\d+)'),
            '^(\s+)': re.compile(r'^(\s+)'),
            '^([a-z]{1})<([^>]*)>$': re.compile(r'^([a-z]{1})<([^>]*)>$'),
            '^([a-z]{1})<([^>]+)>': re.compile(r'^([a-z]{1})<([^>]+)>'),
            '<([^>]+)>$': re.compile(r'<([^>]+)>$'),
            '^(\d+)': re.compile(r'^(\d+)'),
            '^([dtyfismnuxeoj]{1})': re.compile(r'^([dtyfismnuxeoj]{1})'),
            '^<(.+?)>': re.compile(r'^<(.+?)>'),
            '^(\d+)(.+)$': re.compile(r'^(\d+)(.+)$'),
        }
        
        self.N2W = Num2WrdEN()

    def _load(self, filename):
        func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: load from {filename}\n")
        
        with open(filename, 'rt') as f:
            lines = f.readlines()
        
        hvar = dict()
        rulelist = list()
        for line in lines:
            line = line.strip()
            if line == '': continue
            mr = re.match(r'^#!DT!#\s+(\S+)\s+(.+)$', line)
            if mr:
                k, v = mr.group(1), mr.group(2).strip()
                self.dtable[k] = [" " + x + " " for x in v.split("|")] # 首尾加上一个空格
                continue
            if line[0] == '#': continue
            mr = re.match(r'^(\$\{.+?\})\s*=(.+)$', line)
            if mr:
                k, v = mr.group(1), mr.group(2)
                hvar[k] = v.strip()
                continue
            if self.loglv >= 3:
                sys.stderr.write(f"{func_name}: parse one line: {line}\n")
            mr = re.match(r'^(\d+)\?(.+):([a-z]{1}<.+)$', line)
            if mr:
                weight, tkn, result = mr.group(1), mr.group(2), mr.group(3)
                # weight
                weight = int(weight)
                # token list
                tknlist = [None for _ in range(10)]
                while tkn != "":
                    mr = re.match(r'^([1-9]{1})([SMFYH]{1})\s*', tkn)
                    if mr:
                        i, j = mr.group(1), mr.group(2)
                        tknlist[int(i)] = j
                        tkn = tkn[mr.end(2):].strip()
                    else:
                        break
                while tknlist[-1] is None:
                    tknlist.pop(-1)
                # token property
                tknprop = dict()
                while tkn != "":
                    mr = re.match(r'^(\d{1})([bd]{1})([\{\}!#]{1})(\"[^\"]+?\")\s*', tkn)
                    if mr:
                        idx_, opr1_, opr2_ = mr.group(1), mr.group(2), mr.group(3)
                        key_ = idx_ + opr1_ + opr2_
                        val_ = mr.group(4)
                        tkn = tkn[mr.end(4):].strip() # new tkn
                        # expand vars
                        while True:
                            mr = re.match(r'.*?(\$\{.+?\})', val_)
                            if mr:
                                vn = mr.group(1)
                                assert vn in hvar, f"{func_name}: find {vn} is not in hvar when parse line={line}\n"
                                vv = hvar[vn]
                                val_ = val_.replace(vn, vv)
                                if self.loglv >= 3:
                                    sys.stderr.write(f"{func_name}: {vn} -> {vv}, val_={val_}\n")
                            else:
                                break
                        tknprop[key_] = val_
                        # check invalid
                        assert 0 < int(idx_) < len(tknlist), f"{func_name}: invalid property {key_} {val_} in {line}"
                        if opr1_ == 'd':
                            assert tknlist[int(idx_)] == 'Y', f"{func_name}: invalid property {key_} {val_} in {line}\n"
                        continue
                    mr = re.match(r'^(\d{1})([ht]{1})([\{\}!#]{1})(\d+\"[^\"]+?\")\s*', tkn)
                    if mr:
                        idx_, opr1_, opr2_ = mr.group(1), mr.group(2), mr.group(3)
                        key_ = idx_ + opr1_ + opr2_
                        val_ = mr.group(4)
                        tkn = tkn[mr.end(4):].strip() # new tkn
                        # expand vars
                        while True:
                            mr = re.match(r'.*?(\$\{.+?\})', val_)
                            if mr:
                                vn = mr.group(1)
                                assert vn in hvar, f"{func_name}: find {vn} is not in hvar when parse line={line}\n"
                                vv = hvar[vn]
                                val_ = val_.replace(vn, vv)
                                if self.loglv >= 3:
                                    sys.stderr.write(f"{func_name}: {vn} -> {vv}, val_={val_}\n")
                            else:
                                break
                        tknprop[key_] = val_
                        # check invalid
                        assert 0 < int(idx_) < len(tknlist), f"{func_name}: invalid property {key_} {val_} in {line}"
                        continue
                    mr = re.match(r'(\d{1})([zc]{1})([<>=]{1})(\S+)\s*', tkn)
                    if mr:
                        idx_, opr1_, opr2_ = mr.group(1), mr.group(2), mr.group(3)
                        key_ = idx_ + opr1_ + opr2_
                        val_ = mr.group(4)
                        tkn = tkn[mr.end(4):].strip() # new tkn
                        tknprop[key_] = val_
                        flag = 1
                        # check invalid
                        if opr1_ == 'z':
                            assert 0 < int(idx_) < len(tknlist) and (tknlist[int(idx_)] in 'SM'), f"{func_name}: invalid property {key_} {val_} in {line}"
                        continue
                    assert 0, f"{func_name}: unkown property {tkn} in {line}"
                # result
                check = result
                while True:
                    mr = re.match(r'^([dtyfismnuxeoj]{1}(<.+?>){1,};)', check)
                    if not mr: break
                    check = check[mr.end(1):]
                    #ret = mr.group(2)
                    # todo check result
                    # ....
                assert check == '', f"{func_name}: unkown result {check} in {line}"
                result = result.strip(';') # delete last ';'
                # output
                rulelist.append((weight, tknlist, tknprop, result))
                # trace
                if self.loglv >= 3:
                    sys.stderr.write(f"line={line}\n")
                    sys.stderr.write(self._rule_printer(rulelist[-1]))
            else:
                assert 0, f"{func_name}: parse rule error, rule={line}"

        # trace
        if self.loglv >= 3:
            for rule in rulelist:
                self._rule_printer(rule)
        
        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: load from {filename}, rule count={len(rulelist)}\n")
        
        return rulelist

    def _rule_printer(self, rule: list):
        weight, tknlist, tknprop, result = rule
        _str = "-----------------------------\n"
        _str += f"weight: {weight}\n"
        _str += f"tknlist: "
        for i in range(1, len(tknlist)):
            _str += f"{i}{tknlist[i]} "
        _str += f"\ntknproperty:"
        for k in tknprop:
            v = tknprop[k]
            _str += f"{k}{v} "
        _str += f"\nresult: {result}\n"
        _str += "-----------------------------\n"
        return _str
    
    def _token_printer(self, token: list):
        _str = "-----------------------------\n"
        for tk in token:
            _str += f"tokenize: {tk[0]} `{tk[1]}`"
            if len(tk) > 2:
                _str += f" `{tk[2]}`"
            _str += "\n"
        _str += "-----------------------------\n"
        return _str

    def tokenize(self, istr: str):
        istr = DBC2SBC(istr).strip()

        tokenlist = []
        while istr != '':
            # H token
            mr = self.regex['^([\u4e00-\u9fa5]+)'].match(istr)
            if mr:
                istr = istr[mr.end(1):]
                tokenlist.append(['H', mr.group(1)])
                continue
            # Y token
            mr = self.regex['^([a-zA-Z\']+)'].match(istr)
            if mr:
                istr = istr[mr.end(1):]
                tokenlist.append(['Y', mr.group(1)])
                continue
            # S token
            mr = self.regex['^(\d+)'].match(istr)
            if mr:
                istr = istr[mr.end(1):]
                tokenlist.append(['S', mr.group(1)])
                continue
            # specail blanks
            mr = self.regex['^(\s+)'].match(istr)
            if mr:
                istr = istr[mr.end(1):]
                # H/Y/F token can contain blank tail
                if len(tokenlist) > 0 and tokenlist[-1][0] in "HYF":
                    tokenlist[-1][1] += mr.group(1)
                continue
            # F token
            ch = istr[0]
            istr = istr[1:]
            if len(tokenlist) > 0 and tokenlist[-1][1] == ch and ch in "——……": # 合并特例
                tokenlist[-1][1] += ch
            else:
                tokenlist.append(['F', ch])
        
        # post process
        outputs = []
        i, N = 0, len(tokenlist)
        while i < N:
            # combine S.S => M
            if i + 2 < N and (tokenlist[i][0] == 'S' and tokenlist[i+1][1] == '.' and tokenlist[i+2][0] == 'S'):
                if (i > 0 and tokenlist[i-1][1] == '.') or (i + 3 < N and tokenlist[i+3][1] == '.'):
                    # maybe ip address or version, etc.
                    pass
                else:
                    outputs.append(['M', tokenlist[i][1]+tokenlist[i+1][1]+tokenlist[i+2][1]])
                    i += 3
                    continue
            # identify pinyin mark, such as `(chong2)`
            if (((i + 4 < N) and tokenlist[i][0] == 'H')
                and (tokenlist[i+1][0] == tokenlist[i+4][0] == 'F')
                and (  (tokenlist[i+1][1] == '(' and tokenlist[i+4][1] == ')')
                    or (tokenlist[i+1][1] == '（' and tokenlist[i+4][1] == '）')
                    or (tokenlist[i+1][1] == '[' and tokenlist[i+4][1] == ']')
                    or (tokenlist[i+1][1] == '【' and tokenlist[i+4][1] == '】')
                    or (tokenlist[i+1][1] == '<' and tokenlist[i+4][1] == '>')
                )
                and (tokenlist[i+2][0] == 'Y' and tokenlist[i+3][0] == 'S')
                and (Syllable.is_py(tokenlist[i+2][1]) and 0 <= int(tokenlist[i+3][1]) <= 5)
            ):
                if len(outputs) > 0 and outputs[-1][0] == 'H':
                    outputs[-1][1] += tokenlist[i][1]
                else:
                    outputs.append(tokenlist[i])
                position = len(outputs[-1][1])
                pinyin = '(' + tokenlist[i+2][1] + tokenlist[i+3][1] + ')'
                if len(outputs[-1]) > 2:
                    outputs[-1][2] += f" {position}{pinyin}"
                else:
                    outputs[-1].append(f"{position}{pinyin}")
                i += 5
                continue
            # combine H token
            if len(outputs) > 0 and outputs[-1][0] == tokenlist[i][0] == 'H':
                outputs[-1][1] += tokenlist[i][1]
                i += 1
                continue
            # others
            outputs.append(tokenlist[i])
            i += 1
            continue
        
        # trace token
        if self.loglv > 0:
            sys.stderr.write(self._token_printer(outputs))
        
        return outputs

    def process(self, tokens):
        changed = []
        preToken = None     # 上条规则匹配的最后一个token，用于规则的连接
        preTokenId = None   # 上条规则匹配的最后一个token，用于规则的连接的判断
        preResult = None    # 上条规则匹配的最后一个result，用于规则的连接的判断
        link_rule = 0       # 是否连接上条规则匹配的最后一个token一起匹配，值为0/1
        while len(tokens) > 0:
            rule_matched = None     # 返回匹配的规则
            ret = None              # 返回匹配的token数目
            for rule in self.rulelist:
                # match rule
                if link_rule:
                    ret = self.match([preToken, *tokens], rule) # 和前一个token连接后一起去匹配
                else:
                    ret = self.match(tokens, rule)
                if ret <= 0:
                    if self.loglv > 2:
                        sys.stderr.write(f"Match Rule:\n")
                        sys.stderr.write(self._rule_printer(rule))
                        sys.stderr.write(f"Failed, ret = {ret}\n")
                    continue
                # match success
                rule_matched = rule
                break

            weight, tknlist, tknprop, result = rule_matched
            if self.loglv > 0:
                sys.stderr.write(f"Tokens={tokens}\nMatch success:\n")
                sys.stderr.write(self._rule_printer(rule_matched))
            # 连接规则的一些情况判断
            if link_rule:
                if ret == 1: # 只匹配到上一个token，所以匹配失败
                    if self.loglv > 1:
                        sys.stderr.write(f"Only Match preToken, drop it 0!\n")
                    link_rule = 0
                    continue
                # 上条规则匹配的最后一个token的result和本条规则的第一个token的result是否一致
                curResult = result.split(';').pop(0)
                mr = self.regex['^([a-z]{1})<([^>]*)>$'].match(curResult)
                if not mr:
                    if self.loglv > 1:
                        sys.stderr.write(f"The curResult{curResult} not unique, drop it!\n")
                    link_rule = 0
                    continue
                a, c = mr.group(1), mr.group(2)
                mr = self.regex['^([a-z]{1})<([^>]+)>'].match(preResult)
                b, d = mr.group(1), mr.group(2)
                mr = self.regex['<([^>]+)>$'].match(preResult)
                if mr: d = mr.group(1)
                if a != b:
                    if self.loglv > 1:
                        sys.stderr.write(f"The preResult[{b},{d}] is not equal to curResult[{a},{c}], drop it 1!\n")
                    link_rule = 0
                    continue
                if c.isdigit() and d.isdigit():
                    if int(c) != 1 or int(d) != preTokenId:
                        if self.loglv > 1:
                            sys.stderr.write(f"The preResult[{b},{d}] is not equal to curResult[{a},{c}], drop it 2!\n")
                        link_rule = 0
                        continue
                elif c != d:
                    if self.loglv > 1:
                        sys.stderr.write(f"The preResult[{b},{d}] is not equal to curResult[{a},{c}], drop it 3!\n")
                    link_rule = 0
                    continue
            # replace
            replaced = self.replace(tokens, result, link_rule)
            changed += replaced
            if self.loglv > 1:
                sys.stderr.write(f"Replaced = " + " ".join(replaced) + "\n")
            # shift tokens
            preToken0 = None
            for i in range(1, len(tknlist) - link_rule):
                preToken0 = tokens.pop(0)
            # trace token
            if self.loglv > 1 and len(tokens) > 0:
                if link_rule:
                    sys.stderr.write(self._token_printer([preToken, *tokens]))
                else:
                    sys.stderr.write(self._token_printer(tokens))
            # link rule
            preToken = preToken0
            preTokenId = len(tknlist) - 1
            preResult = result.split(';').pop(-1)
            if preTokenId > 1: link_rule = 1

        touched = "".join(changed)
        return touched
    
    def match(self, tokens, rule):
        weight, tknlist, tknprop, result = rule
        # match token number
        if len(tokens) < len(tknlist) - 1:
            return -1
        # match token type
        for i in range(1, len(tknlist)):
            if tknlist[i] != tokens[i-1][0]:
                if tknlist[i] == 'M' and tokens[i-1][0] == 'S':
                    continue
                return -2
        # define match functions
        def match_c(val:str, opr:str, content:str):
            val, content = int(val), len(content)
            if opr == '=': return content == val
            elif opr == '<': return content < val
            elif opr == '>': return content > val
            elif opr == '!': return content != val
            return True
        def match_z(val:str, opr:str, content:str):
            val, content = float(val), float(content)
            if opr == '=': return content == val
            elif opr == '<': return content < val
            elif opr == '>': return content > val
            elif opr == '!': return content != val
            return True
        def match_b(val:str, opr:str, content:str):
            val = val.strip('"').strip('^')
            items = val.split('^')
            if opr == '#':
                if content in items: return True
            elif opr == '}':
                for item in items:
                    if content.find(item) != -1: return True
            elif opr == '{':
                for item in items:
                    if item.find(content) != -1: return True
            elif opr == '!':
                return all([content != item for item in items])
            return False
        def match_d(val:str, opr:str, content:str):
            return match_b(val, opr, content.upper())
        def match_t(val:str, opr:str, content:str):
            mr = self.regex['^(\d+)'].match(val)
            n = mr.group(1)
            val = val[mr.end(1):]
            content = content[-int(n):].upper()
            return match_b(val, opr, content)
        def match_h(val:str, opr:str, content:str):
            mr = self.regex['^(\d+)'].match(val)
            n = mr.group(1)
            val = val[mr.end(1):]
            content = content[:int(n)].upper()
            return match_b(val, opr, content)
        
        # match token property
        orres, isorres = -1, -1
        for tknp in tknprop:
            val = tknprop[tknp]
            ii, condition, opr = int(tknp[0]) - 1, tknp[1], tknp[2]

            isor = -1
            if len(tknp) > 3:
                isor, isorres = 1, 1
            if isor == 1 and orres == 1:
                continue

            res = 0
            content = tokens[ii][1].strip()
            if condition == 'c':
                if not match_c(val, opr, content): res = -3
            elif condition == 'z':
                if not match_z(val, opr, content): res = -4
            elif condition == 'b':
                if not match_b(val, opr, content): res = -5
            elif condition == 'd':
                if not match_d(val, opr, content): res = -6
            elif condition == 'h':
                if not match_h(val, opr, content): res = -7
            elif condition == 't':
                if not match_t(val, opr, content): res = -8
            
            if isor == -1 and res < 0: return res
            elif isor == 1 and res == 0: orres = 1

        if isorres == 1 and orres != 1: return -9

        return len(tknlist) - 1 # 返回匹配的token数量
    
    def replace(self, tokens, result, link_rule):
        def _dtable2word(fh: str, flag: int):
            # flag: 0=f; 1=d(signular); 2=d(plural)
            if flag > 0:
                fh = fh.upper()
                if flag > 1 and len(self.dtable.get(fh, [])) > 1:
                    val = self.dtable[fh][1]
                else:
                    val = self.dtable.get(fh, [''])[0]
            else:
                val = self.dtable.get(fh, [fh])[0]
            return val
        def _isolated(x: str):
            return " ".join([i for i in x])
        
        results = result.split(';')
        if link_rule: results.pop(0)
        
        last_val = -1
        outputs = []
        for rp in results:
            mr = self.regex['^([dtyfismnuxeoj]{1})'].match(rp)
            opr = mr.group(1)
            rp = rp[mr.end(1):]
            str_con = ''
            while rp != '':
                while rp[0] != '<': rp = rp[1:]
                mr = self.regex['^<(.+?)>'].match(rp)
                if not mr: break
                ic = mr.group(1)
                rp = rp[mr.end(1)+1:]
                if ic.isdigit():
                    i = int(ic) - 1 - link_rule
                    cont = tokens[i][1]
                    if len(tokens[i]) > 2: # 判断是否有特殊标记
                        cont = list(cont)
                        for pp in reversed(tokens[i][2].strip().split()):
                            mr = self.regex['^(\d+)(.+)$'].match(pp)
                            assert mr
                            position, pinyin = int(mr.group(1)), mr.group(2)
                            cont.insert(position, pinyin)
                        cont = "".join(cont)
                    str_con += cont
                else:
                    cont = ic
                    str_con += " " + cont + " " if opr == 'y' else cont
            if opr == 't' or opr == 'y':
                outputs.append(str_con)
            elif opr == 'f':
                str_con = str_con.replace(" ", "")
                if len(outputs) > 0 and outputs[-1] == " ": outputs.pop()
                outputs.append(_dtable2word(str_con, 0))
            elif opr == 'd':
                str_con = str_con.replace(" ", "")
                if last_val > 1 or last_val == 0:
                    outputs.append(_dtable2word(str_con, 2)) # 单位复数
                else:
                    outputs.append(_dtable2word(str_con, 1)) # 单位单数
            elif opr == 'i':
                outputs.append(_isolated(str_con))
            else: #  opr in 'smnuxeoj':
                outputs.append(" ")
                outputs.append(self.N2W(str_con, opr))
                outputs.append(" ")
            
            last_val = -1
            if opr in 'ms':
                try:
                    last_val = float(str_con)
                except:
                    last_val = -1

        return outputs
    
    def update(self):
        is_change = False
        for res_path in self.res_paths:
            if self.files_mtime[res_path] != int(os.stat(res_path).st_mtime):
                is_change = True
        if is_change:
            rulelist = list()
            for res_path in self.res_paths:
                rulelist += self._load(res_path)
                self.files_mtime[res_path] = int(os.stat(res_path).st_mtime)
            self.rulelist = tuple(sorted(rulelist, key=lambda x:x[0], reverse=True))

    def __call__(self, utt_id, utt_text):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: input> utt_id={utt_id}, utt_text=`{utt_text}`\n")
            
        utt_text = self.process(self.tokenize(utt_text))

        # 标点统一替换成全角
        utt_text = utt_text.replace(',', '，')
        utt_text = utt_text.replace('!', '！')
        utt_text = utt_text.replace('?', '？')
        utt_text = utt_text.replace(':', '：')
        utt_text = utt_text.replace(';', '；')
        
        # 删除多余空白
        utt_text = utt_text.replace('  ', ' ')

        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: output> utt_id={utt_id}, utt_text=`{utt_text}`\n")

        return utt_id, utt_text

 
class TextNormalizer(object):
    def __init__(self, res_root_dir=None, loglv=0):
        self.loglv = loglv        
        self.textnorm_cn = TextNormalizerCN(res_root_dir, loglv=loglv)
        self.textnorm_en = TextNormalizerEN(res_root_dir, loglv=loglv)
        
        # compile regex
        self.regex = {
            'Chinese': re.compile(r'^([\u4e00-\u9fa5]+)'),
            'English': re.compile(r'^([a-zA-Z\']+)'),
            'PinyinMark': re.compile(r'^([<\(\[（【]([a-zA-Z]+)(\d)[>\)\]）】])'),
            'Blank': re.compile(r'^(\s+)'),
        }
        
    def _split_text(self, utt_text):
        # 中英文拆分，注意拼音标记
        sub_text, sub_lang = [], []
        pre_lang = Lang.UNKNOW
        while utt_text != '':
            # Chinese
            mr = self.regex['Chinese'].match(utt_text)
            if mr:
                r1 = mr.group(1)
                utt_text = utt_text[mr.end(1):]
                if pre_lang != Lang.CN:
                    sub_text.append(r1)
                    sub_lang.append(Lang.CN)
                else:
                    sub_text[-1] += r1
                pre_lang = Lang.CN
                continue
            # Enligsh
            mr = self.regex['English'].match(utt_text)
            if mr:
                r1 = mr.group(1)
                utt_text = utt_text[mr.end(1):]
                if pre_lang != Lang.EN:
                    sub_text.append(r1)
                    sub_lang.append(Lang.EN)
                else:
                    sub_text[-1] += r1
                pre_lang = Lang.EN
                continue
            # Pinyin mark
            mr = self.regex['PinyinMark'].match(utt_text)
            if mr:
                r1 = mr.group(1)
                utt_text = utt_text[mr.end(1):]
                py, tone = mr.group(2), mr.group(3)
                if Syllable.is_py(py) and int(tone) <= 5:
                    if pre_lang == Lang.CN:
                        sub_text[-1] += r1
                    else:
                        sub_text.append("囧" + r1)
                        sub_lang.append(Lang.CN)
                else:
                    sub_text.append(r1)
                    sub_lang.append(Lang.EN)
                continue
            # Symbol: blank
            mr = self.regex['Blank'].match(utt_text)
            if mr:
                r1 = mr.group(1)
                utt_text = utt_text[mr.end(1):]
                if len(sub_text) > 0:
                    sub_text[-1] += r1
                continue
            # Symbol: others
            r1 = utt_text[0]
            utt_text = utt_text[1:]
            if len(sub_text) > 0:
                sub_text[-1] += r1
            else:
                sub_text.append(r1)
                sub_lang.append(Lang.UNKNOW)
            continue

        # repaire lang
        next_lang = sub_lang[-1]
        for i in range(len(sub_lang)-1, -1, -1):
            if sub_lang[i] == Lang.UNKNOW:
                sub_lang[i] = next_lang
            next_lang = sub_lang[i]
        
        # combines same lang
        sub_text_, sub_lang_ = [], []
        for text, lang in zip(sub_text, sub_lang):
            if len(sub_text_) > 0 and sub_lang_[-1] == lang:
                sub_text_[-1] += text
            else:
                sub_text_.append(text)
                sub_lang_.append(lang)
        sub_text, sub_lang = sub_text_, sub_lang_
        
        # judge sentence
        sub_sent = [ True if text[-1] in "，。！？；,.!?;" else False for text in sub_text ]
        
        return sub_text, sub_lang, sub_sent
    
    def __call__(self, utt_id, utt_text, context=Lang.CN):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: input(context={context})> utt_id={utt_id}, utt_text=`{utt_text}`\n")
        
        sub_text, sub_lang, sub_sent = self._split_text(utt_text)
        
        if context is None: context = ""
        if context == Lang.CN:
            _, utt_text = self.textnorm_cn(utt_id, "".join(sub_text))
        elif context == Lang.EN:
            _, utt_text = self.textnorm_en(utt_id, "".join(sub_text))
        else:
            # smart decision
            utt_text = ""
            for i in range(len(sub_text)):
                if (i == len(sub_text) - 1 or sub_sent[i]) and (i == 0 or sub_sent[i-1]) and sub_lang[i] == Lang.EN:
                    _, utt_text_ = self.textnorm_en(utt_id, sub_text[i])
                else:
                    _, utt_text_ = self.textnorm_cn(utt_id, sub_text[i])
                utt_text += utt_text_

        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: output(context={context})> utt_id={utt_id}, utt_text=`{utt_text}`\n")
        
        return utt_id, utt_text
        

def main():
    
    file, context, loglv = sys.stdin, "", 0
    
    # parse arguments
    help_str = f"usage: text-normalizer OPTIONS... [FILE]\n\n"
    help_str += f"Text normalizer for Chinese or English text, version={__version__}\n\n"
    help_str += f"Print normalized results of lines from each FILE to standard output.\n"
    help_str += f"With no FILE, or when FILE is -, read standard input.\n\n"
    help_str += f"Mandatory arguments to long options are mandatory for short options too.\n"
    help_str += f"    -h, --help               show this help message and exit\n"
    help_str += f"    -l, --loglv LOGLEVEL     set log level, the optional value is 0, 1 and 2, default={loglv}\n"
    help_str += f"    -c, --context CONTEXT    set language context, the optional value is CN, EN or \"\", default=\"{context}\"\n"
    help_str += f"    -v, --version            output version information and exit\n\n"
    
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if len(a) > 1 and a[0] == "-":
            if a == "-h" or a == "--help":
                print(help_str)
                sys.exit(0)
            elif a == "-l" or a == "--loglv":
                i += 1
                loglv = int(sys.argv[i])
            elif a == "-c" or a == "--context":
                i += 1
                context = sys.argv[i]
            elif a == "-v" or a == "--version":
                print(f"text-normalizer, version={__version__}"
                      f"Copyright (c) 2023 wwyuan2023\n"
                      f"MIT License <https://mit-license.org/>\n\n"
                      f"Written by Wuwen YUAN.\n")
                sys.exit(0)
            else:
                print(f"Unkown argument {a}\n\n{help_str}")
                sys.exit(-1)
        else:
            file = sys.stdin if a == "-" else a
        i += 1
    
    textnormalizer = TextNormalizer(loglv=loglv)

    fid = open(file, 'rt') if not hasattr(file, 'read') else file
    for line in fid:
        # read one line
        line = line.strip()
        if line == '': continue
        for i in range(len(line)):
            if line[i].isspace():
                break
        utt_id, utt_text = line[:i].strip(), line[i:].strip()
        if utt_text == '': continue

        # text normalization
        utt_id, norm_text = textnormalizer(utt_id, utt_text, context=context)

        # output
        line = f'{utt_id}    {norm_text}\n'
        sys.stdout.write(line)

        if loglv > 0: # format print
            line = f"{utt_id}    "
            slen = len(line)
            line += f"orig={utt_text}\n"
            line += "".ljust(slen)
            line += f"norm={norm_text}\n"
            sys.stderr.write(line)
    
    if fid.fileno() not in {0, 1, 2}:
        fid.close()


if __name__ == "__main__":
    
    main()
    