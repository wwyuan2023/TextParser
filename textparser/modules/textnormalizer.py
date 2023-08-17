# coding: utf-8

import os, sys
import re

#from opencc import OpenCC
from zhconv import convert

import textparser
from textparser import Config
from textparser.utils import DBC2SBC, Syllable


class Num2Wrd(object):
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


class TextNormalizer(object):
    def __init__(self, res_root_dir=None, loglv=0):
        self.loglv = loglv
        self.dtable = dict()
        
        # default resource paths
        if res_root_dir is None: res_root_dir = textparser.__path__[0]
        res_paths = [
            os.path.join(res_root_dir, path)
            for path in Config.cn_special_symbols_paths
        ]

        self.files_mtime = dict()
        
        rulelist = list()
        for res_path in res_paths:
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
        
        self.N2W = Num2Wrd()
        #elf.T2S = OpenCC('t2s')

    def _load(self, filename):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
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
                        assert 0 < int(idx_) < len(tknlist)
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

    def _rule_printer(self, rule:list):
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
    
    def _token_printer(self, token:list):
        _str = "-----------------------------\n"
        for tk in token:
            _str += f"tokenize: {tk[0]} `{tk[1]}`"
            if len(tk) > 2:
                _str += f" `{tk[2]}`"
            _str += "\n"
        _str += "-----------------------------\n"
        return _str

    def tokenize(self, istr:str):
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
            # identy pinyin mark, such as `(chong2)`
            if (((i + 4 < N) and tokenlist[i][0] == 'H')
                and (tokenlist[i+1][0] == tokenlist[i+4][0] == 'F')
                and (  (tokenlist[i+1][1] == '(' and tokenlist[i+4][1] == ')')
                    or (tokenlist[i+1][1] == '（' and tokenlist[i+4][1] == '）')
                    or (tokenlist[i+1][1] == '[' and tokenlist[i+4][1] == ']')
                    or (tokenlist[i+1][1] == '【' and tokenlist[i+4][1] == '】')
                    or (tokenlist[i+1][1] == '/' and tokenlist[i+4][1] == '/')
                )
                and (tokenlist[i+2][0] == 'Y' and tokenlist[i+3][0] == 'S')
                and (Syllable.is_py(tokenlist[i+2][1]) and 0 <= int(tokenlist[i+3][1]) <= 5)
            ):
                if len(outputs) > 0 and outputs[-1][0] == 'H':
                    outputs[-1][1] += tokenlist[-1][1]
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
        if self.loglv > 1:
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
                    if self.loglv >= 2:
                        sys.stderr.write(f"Match Rule:\n")
                        sys.stderr.write(self._rule_printer(rule))
                        sys.stderr.write(f"Failed, ret = {ret}\n")
                    continue
                # match success
                rule_matched = rule
                break

            weight, tknlist, tknprop, result = rule_matched
            if self.loglv > 1:
                sys.stderr.write(f"Match success:\n")
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
            val, content = int(val), int(content)
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
            if condition == 'c':
                if not match_c(val, opr, tokens[ii][1]): res = -3
            elif condition == 'z':
                if not match_z(val, opr, tokens[ii][1]): res = -4
            elif condition == 'b':
                if not match_b(val, opr, tokens[ii][1]): res = -5
            elif condition == 'd':
                if not match_d(val, opr, tokens[ii][1]): res = -6
            elif condition == 'h':
                if not match_h(val, opr, tokens[ii][1]): res = -7
            elif condition == 't':
                if not match_t(val, opr, tokens[ii][1]): res = -8
            
            if isor == -1 and res < 0: return res
            elif isor == 1 and res == 0: orres = 1

        if isorres == 1 and orres != 1: return -9

        return len(tknlist) - 1 # 返回匹配的token数量
    
    def replace(self, tokens, result, link_rule):
        def dtable2workd(fh:str, flag:int):
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
                outputs.append(dtable2workd(str_con, 0 if opr == 'f' else 1))
            else: #  opr in 'msilo':
                outputs.append(self.N2W(str_con, opr))

        return outputs
    
    def update(self):
        pass

    def __call__(self, utt_id, utt_text):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: input> utt_id={utt_id}, utt_text=`{utt_text}`\n")
            
        # utt_text = self.T2S.convert(utt_text)
        utt_text = convert(utt_text, 'zh-hans')
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

def main(file=sys.stdin):
    loglv = 0
    if len(sys.argv) > 1:
        loglv = int(sys.argv[1])
    
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
        utt_id, norm_text = textnormalizer(utt_id, utt_text)

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
    






