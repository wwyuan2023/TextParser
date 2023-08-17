# coding: utf-8

import os, sys
import re
import math
import copy

import textparser
from textparser import Config
from textparser.utils import Syllable, SegText
from textparser.utils import GPOS, Lang
from textparser.third_part import G2p


class FSM(object):
    def __init__(self, fsm_path, self_cost=1., max_path=50, loglv=0):
        self.loglv = loglv
        self.self_cost = self_cost
        self.max_path = max_path
        self.PSet = set()
        self.fsm = dict()
        self.ibeg = None
        self.iend = None
        self.max_cost = 100
        
        # load model
        self._load(fsm_path)

        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Initialize Success! \n")
    
    def _load(self, fsm_path):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: load fsm from {fsm_path}\n")
        with open(fsm_path, 'rt') as f:
            for line in f:
                line = line.strip()
                if line == '': continue
                mr = re.match(r'^(\d+)$', line)
                if mr:
                    self.iend = mr.group(1)
                    continue
                arr = line.split()
                if len(arr) <= 4: arr.append(0)
                if arr[2] == '<s>': self.ibeg = arr[0]
                if arr[0] not in self.fsm:
                    self.fsm[arr[0]] = {}
                self.fsm[arr[0]][arr[2]] = (float(arr[4]), arr[1])
                self.PSet.add(arr[2])
        
        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: load from {fsm_path} done! \n")
        if self.loglv > 2:
            sys.stderr.write(f"{func_name}: {self.fsm}")
        
    def _paths_ext(self, pstrs, scorts, paths):
        dpaths = []
        for i in range(len(pstrs)):
            pstr = pstrs[i]
            newpaths = []
            for path in paths:
                pcloned = path.copy()
                pcloned[0] += scorts[i] # self cost
                inode = pcloned.pop(-1)

                if self.fsm[inode].get(pstr) is not None:
                    cost, inode = self.fsm[inode][pstr]
                    pcloned += [pstr, inode]
                    pcloned[0] += cost
                    newpaths.append(pcloned)
                    continue
                if self.fsm[inode].get('<eps>') is not None:
                    for _ in range(5):
                        cost, inode = self.fsm[inode]['<eps>']
                        pcloned += ['<eps>']
                        pcloned[0] += cost
                        if self.fsm[inode].get(pstr) is not None: break
                        if self.fsm[inode].get('<eps>') is None: break
                    if self.fsm[inode].get(pstr) is not None:
                        cost, inode = self.fsm[inode][pstr]
                        pcloned += [pstr, inode]
                        pcloned[0] += cost
                        newpaths.append(pcloned)
                        continue
                # death path
                pcloned[0] += self.max_cost
                pcloned += [pstr, inode]
                newpaths.append(pcloned) # no die
                if self.loglv > 0:
                    func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
                    sys.stderr.write(f"{func_name}: Death path, {inode}: {pstr}: {pcloned}\n")
            # combine path
            dpaths += newpaths
        
        # prun path
        dpaths = self._paths_prun(self.max_path, dpaths)
        return dpaths
    
    def _paths_combine(self, paths):
        paths = sorted(paths, key=lambda x:x[0])
        newpaths = [paths[0]]
        for i in range(1, len(paths)):
            if newpaths[-1][-1] == paths[i][-1]:
                if newpaths[-1][0] > paths[i][0]:
                    newpaths[0] = paths[i]
            else:
                newpaths.append(paths[i])
        return newpaths
    
    def _paths_prun(self, max_path, paths):
        if max_path <= 0 or len(paths) < max_path: return paths
        paths = sorted(paths, key=lambda x: x[0])
        return paths[:max_path]
    
    def _paths_printer(self, paths):
        _str = "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n"
        _str += f"\ttotal path = {len(paths)}\n"
        for i, path in enumerate(paths, 1):
            _str += f"\t{i:4d}:{path[0]:.3f} {path[1:]}\n"
        _str += "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n"
        return _str
    
    def _best_path(self, paths):
        one_best = self._paths_prun(1, paths)[0]
        return one_best[1:]

    def __call__(self, hpstrs):
        paths = [ [0., self.ibeg] ]
        # sentence start
        paths = self._paths_ext(['<s>'], [0], paths)
        
        for i in range(len(hpstrs)):
            pstrs = [x for x in hpstrs[i].keys()]
            scorts = [hpstrs[i][x]*self.self_cost for x in hpstrs[i].keys()]
            # extend each pos
            paths = self._paths_ext(pstrs, scorts, paths)

            if self.loglv > 1:
                sys.stderr.write(f"\t--> {hpstrs[i]} : \n{self._paths_printer(paths)}")
        
        # sentence end
        paths = self._paths_ext(['</s>'], [0], paths)
        if self.loglv > 1:
            sys.stderr.write(f"\t--> </s> : \n{self._paths_printer(paths)}")

        # select one best
        best = self._best_path(paths)
        if self.loglv > 1:
            sys.stderr.write(f"best={best}\n")

        # fill result
        result = []
        for p in best:
            if p not in ['<s>', '</s>', '<eps>']:
                result.append(p)

        # stupid to try exception
        if len(result) < len(hpstrs):
            for i in range(len(hpstrs) - len(result)):
                result.append(result[-1])

        return result


class SegmenterCN(object):
    def __init__(self, res_root_dir=None, loglv=0):
        self.loglv = loglv
        
        # default resource paths
        if res_root_dir is None: res_root_dir = textparser.__path__[0]
        self.dict_paths = [
            os.path.join(res_root_dir, path)
            for path in Config.cn_dict_paths
        ]
        posfsm_path = os.path.join(res_root_dir, Config.cn_pos_path)

        self.files_mtime = dict()
        
        # load dict
        self.max_word_length = -1
        self.wordict = dict()
        for dict_path in self.dict_paths:
            self.wordict.update(self._load(dict_path))
            self.files_mtime[dict_path] = int(os.stat(dict_path).st_mtime)
        if self.max_word_length > Config.max_word_length:
            self.max_word_length = Config.max_word_length
        
        # create pos fsm
        self.pos_fsm = FSM(posfsm_path, 1.8, 20, loglv=loglv)
        self.files_mtime[posfsm_path] = int(os.stat(posfsm_path).st_mtime)
        
        # constant values
        self.WEIGHT_SWORD = -math.log(0.000001) # 中文单字默认代价

        self.regex = [
            re.compile(r"^[零幺一两二三四五六七八九壹贰叁肆伍陆柒捌玖十百千万亿点佰仟拾廿]+$"),
            re.compile(r"([十百千万亿点佰仟拾])\s+([十百千万亿点佰仟拾])"),
            re.compile(r"^[零幺一两二三四五六七八九壹贰叁肆伍陆柒捌玖]+$"),
            re.compile(r"两$")
        ]
        self.dtable = (
            (1, None, None, (1,)),
            (2, None, None, (2,)),
            (3, None, None, (3,)),
            (4, None, None, (2,2)),
            (5, None, None, (2,3)),
            (6, None, None, (3,3)),
            (7, None, None, (4,3)),
            (8, None, None, (4,4)),
            (9, None, None, (3,3,3)),
            (10, None, None, (3,3,4)),
            (10, "四零零", None, (3,3,4)),
            (10, "八零零", None, (3,3,4)),
            (11, None, None, (3,4,4)),
            (11, "幺", None, (3,4,4)),
            (11, "零幺零", None, (3,4,4)),
            (12, None, None, (4,4,4)),
            (13, None, None, (3,3,3,4)),
        )

        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Initialize Success! \n")

    def _load(self, filename):
        wordict = {}
        def _parse_item(line):
            # e.g.: 
            # 然后 ran2-hou4;5.485;d=.194,c=1.736;P=.01025
            # 然后以六合为家 ran2-hou4-yi3-liu4-he2-wei2-jia1;.357;i=0
            line = line.strip().rstrip(',;')
            if line == '': return False
            word, line = line.split()
            arr = line.split(';')
            pinyin, weight, pos = arr[:3]
            flag = arr[3] if len(arr) >= 4 else None
            
            # struction
            weight = float(weight)
            pinyin = None if len(pinyin) == 0 else tuple(pinyin.split('-')) # ['ran2', 'hou4']
            if len(pos) == 0:
                hpos = {'w': 0}
            else:
                hpos = {} # {'d': 0.194, 'c': 1.736}
                for s in pos.split(','):
                    c, w = s.split('=')
                    hpos[c] = float(w)
            hflag = None
            if flag is not None:
                hflag = {} # {'P': 0.01025}
                for s in flag.split(','):
                    c, w = s.split('=')
                    hflag[c] = float(w)
            wordict[word] = (weight, pinyin, hpos, hflag)
            if len(word) > self.max_word_length: self.max_word_length = len(word)
            return True
        
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: load dictionay from {filename}\n")
        
        with open(filename, 'rt') as f:
            for line in f:
                if not _parse_item(line):
                    if self.loglv > 0: sys.stderr.write(f"{func_name}: parse item error: {line}\n")
        
        if self.loglv > 0: sys.stderr.write(f"{func_name}: word count = {len(wordict)}\n")
        return wordict
    
    def _get_info(self, word):
        return self.wordict.get(word)
    
    def _get_weight(self, word):
        info = self.wordict.get(word)
        if info is None: return None
        return info[0]
    
    def _get_pinyin(self, word):
        info = self.wordict.get(word)
        if info is None: return None
        return info[1]
    
    def _get_pos(self, word):
        info = self.wordict.get(word)
        if info is None: return None
        return info[2]
    
    def _get_flag(self, word):
        info = self.wordict.get(word)
        if info is None: return None
        return info[3]

    def update(self):
        for dict_path in self.dict_paths:
            if 'user' not in dict_path: continue
            if self.files_mtime[dict_path] != int(os.stat(dict_path).st_mtime):
                self.wordict.update(self._load(dict_path))
        
    def __call__(self, utt_id, utt_text, utt_mark):

        segtext = SegText()
        if utt_text == "": 
            return utt_id, segtext

        # split word
        sword, sinfo = self._split_word(utt_text)
        if len(sword) == 0 or len(sinfo) == 0:
            return  utt_id, segtext
        
        # number word rules
        sword, sinfo = self._number_adjust(sword, sinfo)

        # recgnoize Chinese nane
        if Config.cn_identy_chinese_name:
            sword, sinfo = self._cname_adjust(sword, sinfo)

        # predict pos
        pinyin, hpos = [x[0] for x in sinfo], [x[1] for x in sinfo]
        pos = self.pos_fsm(hpos)

        # check correspondence between `utt_text` and `utt_mark`
        success = False
        utt_len = sum([len(w) for w in sword])
        if utt_len == len(utt_mark):
            success = True
        elif self.loglv > 0:
            sys.stderr.write(f"SegmenterCN: id={utt_id}, Check correspondency ERROR, the mark will be droped!\n")
        
        # create segtext list
        start, end = 0, 0
        for i in range(len(sword)):
            segtext.append() # create one empty element
            segtext.set_wpc(-1, sword[i], pinyin[i], pos[i])
            segtext.set_lang(-1, Lang.CN)
            end += len(sword[i])
            if success:
                PMark = ""
                for k, mark in enumerate(utt_mark[start:end]):
                    if mark is not None: PMark += f"P{k}={mark},"
                if len(PMark) > 0: segtext.set_mark(-1, PMark)
            start = end
        
        return utt_id, segtext
        
    def _split_word(self, utt_text):
        N = len(utt_text)
        if N == 0: return None, None

        best_prob, prev = [None for _ in range(N+1)], [None for _ in range(N+1)]
        info = [None for _ in range(N+1)]
        best_prob[0] = 0
        for i in range(N):
            for j in range(i+1, min(N+1,i+1+self.max_word_length)):
                # matching an enty in the dict
                current_word = utt_text[i:j]
                current_info = self.wordict.get(current_word)  # (weight, pinyin, pos, flag)
                if current_info is None: continue
                # get the previous found path, if not exists, use the default value,
                # which means we may take the previous token as the path.
                prev_weight = best_prob[i] if best_prob[i] is not None else \
                    i * self.WEIGHT_SWORD # 出现这种情况就是存在未被识别的字符，这里给个最大值，使最优路径不是它，且继续运行！
                
                # calculate weight for current path.
                current_weight = prev_weight + current_info[0]
                
                # update the path
                if best_prob[j] is None or best_prob[j] > current_weight:
                    prev[j] = i
                    best_prob[j] = current_weight
                    info[j] = current_info[1:] # tuple(pinyin, pos, flag)
            
        # get boundaries
        boundaries = [None for _ in range(N+1)] # left boundary
        i = N
        while i > 0:
            boundaries[i] = 1
            if prev[i] is not None:
                i = prev[i]
            else:
                i -= 1 # 这就是存在未被识别的字符

        # fill the result
        sword, sinfo = [], []
        prev = 0
        for i in range(1, N+1):
            if boundaries[i] is not None:
                current_word = utt_text[prev:i]
                sword.append(current_word)
                if info[i] is not None:
                    sinfo.append(copy.deepcopy(info[i]))
                else:
                    sinfo.append((None, {'w':0}, None))
                prev = i
                
        return sword, sinfo
    
    def _number_adjust(self, sword, sinfo):
        sent_start = 0
        while True:
            N = len(sword)
            # 1. 甄别出号码、数值串
            start = -1
            for i in range(sent_start, N):
                mr = self.regex[0].match(sword[i])
                if mr:
                    start = i
                    break
            if start == -1: break
            end = start
            for i in range(start, N):
                mr = self.regex[0].match(sword[i])
                if mr:
                    end = i
                else:
                    break
            if start == end:
                sent_start = end + 1
                continue
            # 2. 提取数字文本，重新处理
            text = ""
            for i in range(start, end+1):
                text += sword[i]

            # 3. 先按权重拆分："七千万" => "七千 万"
            for w in "十百千万亿点佰仟拾":
                text = text.replace(w, f"{w} ")
            text = text.strip()

            # 4. 再合并相邻权重："七千 万" => "七千万"
            text = self.regex[1].sub("\g<1>\g<2>", text)

            # 5. 号码串按韵律表拆分
            tarr = text.split()
            text = ""
            for i in range(len(tarr)):
                mr = self.regex[2].match(tarr[i])
                if mr or len(tarr[i]) > 9:
                    text += self._number_adjust_i(tarr[i])
                    text += " "
                else:
                    text += tarr[i] + " "
            text = text.strip()

            # 6. 以"两"结尾的词，将"两"单独拆分出来
            _text = text
            text = self.regex[3].sub("", _text)
            liangflag = True if text != _text else False

            # 7. 返回结果
            _sword, _sinfo = sword[:start], sinfo[:start]
            for word in text.split():
                # 设置拼音、词性和人名规则标记
                pinyin = [self._get_pinyin(z)[0] for z in word]
                if len(pinyin) == 0: pinyin = None
                hpos = {"m": 0}
                hflag = {"P": 0.01,"S": 0.01,"X": 0,"F": 0,"L": 0,"E": 0,"T": 0}
                _sword += [word]
                _sinfo += [(pinyin, hpos, hflag)]
            if liangflag:
                _sword += ["两"]
                _sinfo += [copy.deepcopy(self._get_info("两")[1:])]
            sent_start = len(_sword)
            _sword += sword[end+1:]
            _sinfo += sinfo[end+1:]
            sword, sinfo = _sword, _sinfo

        return  sword, sinfo
    
    def _number_adjust_i(self, text):
        # match rule
        tlen = len(text)
        for i in range(len(self.dtable) - 1, -1, -1):
            rule = self.dtable[i]
            success = False
            if rule[0] == tlen: success = True
            if success and rule[1] is not None:
                if text[:len(rule[1])] != rule[1]: success = False
            if success and rule[2] is not None:
                if text[-len(rule[2]):] != rule[2]: success = False
            if success: break
        # result
        _text = ""
        if success:
            s = 0
            for n in rule[-1]:
                _text += text[s:s+n] + " "
                s += n
        else:
            for n in range(0, tlen, 4):
                _text += text[n:n+4] + " "
        
        return _text

    def _cname_adjust(self, sword, sinfo): # 中文人名识别
        
        if self.loglv > 1:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            _str = ""
            for x,y in zip(sword, sinfo):
                _str += f"{x}, {y}\n"
            sys.stderr.write(f"{func_name}: {_str}\n")

        pinyin, hpos, hflag = [x[0] for x in sinfo], [x[1] for x in sinfo], [x[2] for x in sinfo]
        wlen, bound = [len(x) for x in sword], [0 for _ in sword]
        slen = len(sword)

        # 补充几个数据，为了下面条件判断的方便
        wlen += [0 for _ in range(4)]
        bound += [0 for _ in range(4)]
        hpos += [None for _ in range(4)]
        hflag += [None for _ in range(4)]

        _flag_get = lambda hflag, k, v=0: v if hflag is None else hflag.get(k, v)
        _pos_have = lambda hpos, k: False if hpos is None else k in hpos

        # 1. 规则能够处理的情况，例如：老张、张氏、李总等
        prefix = "小老阿"
        suffix = "总工姓氏老导某哥家"
        #### 1.1. 单姓+后缀
        i = -1
        while i + 1 < slen - 1:
            i += 1
            if wlen[i] != 1 or wlen[i+1] != 1: continue
            if hflag[i] is None or _flag_get(hflag[i], 'X') <= 0: continue
            if sword[i+1] not in suffix: continue
            bound[i], bound[i+1] = 1, -1
            i += 1
        if self.loglv > 1:
            sys.stderr.write(f"{func_name}: 1.1>bound={bound}\n")
        #### 1.2. 前缀+单姓
        i = -1
        while i + 1 < slen - 1:
            i += 1
            if wlen[i] != 1 or wlen[i+1] != 1: continue
            if hflag[i] is None or _flag_get(hflag[i], 'X') <= 0: continue
            if sword[i] not in prefix: continue
            bound[i], bound[i+1] = 1, -1
            i += 1
        if self.loglv > 1:
            sys.stderr.write(f"{func_name}: 1.2>bound={bound}\n")
        
        # 2. 根据人名长度判断
        #### 2.1. 四个散字（或一个双音节词+两个散字）的情况：复姓+名首字+名末字
        i = -1
        while i + 1 < slen - 2:
            i += 1
            if any([x!=0 for x in bound[i:i+4]]): continue
            if all([x==1 for x in wlen[i:i+4]]):
                if (_flag_get(hflag[i+3], 'S') >= 0.55) and _flag_get(hflag[i+3], 'L') <= 0.05: continue
                wd = sword[i] + sword[i+1]
                tflag = self._get_flag(wd)
                pn = _flag_get(tflag, 'X') * _flag_get(hflag[i+2], 'F') * _flag_get(hflag[i+3], 'L')
                pp, ps = _flag_get(hflag[i-1], 'P'), _flag_get(hflag[i+4], 'S')
                if pn >= 0.0016 or (pn >= 0.0001 and pp + ps >= 0.2):
                    bound[i] = 1
                    bound[i+1] = bound[i+2] = bound[i+3] = -1
                    i += 3
            elif wlen[i] == 2 and wlen[i+1] == 1 and wlen[i+2] == 1:
                if (_flag_get(hflag[i+2], 'S') >= 0.55) and _flag_get(hflag[i+2], 'L') <= 0.05: continue
                pn = _flag_get(hflag[i], 'X') * _flag_get(hflag[i+1], 'F') * _flag_get(hflag[i+2], 'L')
                pp, ps = _flag_get(hflag[i-1], 'P'), _flag_get(hflag[i+3], 'S')
                if pn >= 0.004 or (pn >= 0.0001 and pp + ps >= 0.2):
                    bound[i] = 1
                    bound[i+1] = bound[i+2] = -1
                    i += 2 
        if self.loglv > 1:
            sys.stderr.write(f"{func_name}: 2.1>bound={bound}\n")
                   
        #### 2.2. 三个散字（或一个双音节词+一个散字，或一个散字+一个双音节词）的情况：复姓+名末字/单姓+名首字+名末字
        i = -1
        while i + 1 < slen - 2:
            i += 1
            if any([x!=0 for x in bound[i:i+3]]): continue
            if all([x==1 for x in wlen[i:i+3]]):
                if (_flag_get(hflag[i+2], 'S') >= 0.55) and _flag_get(hflag[i+2], 'L') <= 0.05: continue
                pn = _flag_get(hflag[i], 'X') * _flag_get(hflag[i+1], 'F') * _flag_get(hflag[i+2], 'L')
                pp, ps = _flag_get(hflag[i-1], 'P'), _flag_get(hflag[i+3], 'S')
                if pn >= 0.001 or (pn >= 0.0001 and pp + ps >= 0.2):
                    bound[i] = 1
                    bound[i+1] = bound[i+2] = -1
                    i += 2
            elif wlen[i] == 2 and wlen[i+1] == 1:
                if (_flag_get(hflag[i+1], 'S') >= 0.55) and _flag_get(hflag[i+1], 'L') <= 0.05: continue
                if _pos_have(hpos[i], 'nr') and not _pos_have(hflag[i], 'X'): continue
                pn = _flag_get(hflag[i], 'X') * _flag_get(hflag[i+1], 'L')
                if pn <= 0: # 如果不是复姓
                    w1, w2 = sword[i][0], sword[i][1]
                    tflag1, tflag2 = self._get_flag(w1), self._get_flag(w2)
                    pn = _flag_get(tflag1, 'X') * _flag_get(tflag2, 'F') * _flag_get(hflag[i+1], 'L')
                pp, ps = _flag_get(hflag[i-1], 'P'), _flag_get(hflag[i+2], 'S')
                if pn >= 0.1 or (pn >= 0.05 and pp + ps >= 0.2):
                    bound[i], bound[i+1] = 1, -1
                    i += 1
            elif wlen[i] == 1 and wlen[i+1] == 2:
                w1, w2 = sword[i+1][0], sword[i+1][1]
                tflag1, tflag2 = self._get_flag(w1), self._get_flag(w2)
                pn = _flag_get(hflag[i], 'X') * _flag_get(tflag1, 'F') * _flag_get(tflag2, 'L')
                pp, ps = _flag_get(hflag[i-1], 'P'), _flag_get(hflag[i+2], 'S')
                if pn >= 0.05 or (pn >= 0.01 and pp + ps >= 0.2):
                    bound[i], bound[i+1] = 1, -1
                    i += 1
        if self.loglv > 1:
            sys.stderr.write(f"{func_name}: 2.2>bound={bound}\n")
        
        #### 2.3. 两个散字的情况：单姓+名末字/名首字+名末字
        i = -1
        while i + 1 < slen - 1:
            i += 1
            if bound[i] != 0 or bound[i+1] != 0: continue
            if wlen[i] != 1 or wlen[i+1] != 1: continue
            pn1 = _flag_get(hflag[i], 'X') * _flag_get(hflag[i+1], 'L')
            pn2 = _flag_get(hflag[i], 'F') * _flag_get(hflag[i+1], 'L')
            pp, ps = _flag_get(hflag[i-1], 'P'), _flag_get(hflag[i+2], 'S')

            if ( (pn1 >= 0.15 or (pn1 >= 0.1 and pp + ps >= 0.2))
                or (pn2 >= 0.25 or (pn2 >= 0.15 and pp + ps > 0.4))
            ):
                bound[i], bound[i+1] = 1, -1
                i += 1
        if self.loglv > 1:
            sys.stderr.write(f"{func_name}: 2.3>bound={bound}\n")
        
        # 3. 带歧义的情况：有关 羽
        # todo

        # 4. 修订结果
        if all([x==0 for x in bound]):
            return sword, sinfo

        s, e = 0, 0
        i = -1
        while i + 1 < slen:
            i += 1
            if bound[i] != 1: continue
            s, e = i, i + 1
            while e < slen:
                if bound[e] == 0: break
                e += 1
            f = False
            if s > 0 and _pos_have(hpos[s-1], 'm') and _pos_have(hpos[s], 'q'):
                f = True # 数词+量词姓组合
            if e < slen and _pos_have(hpos[e-1], 'm') and (_pos_have(hpos[e], 'q') or _pos_have(hpos[e], 't')):
                f = True # 数词+量词姓组合
            if not f: continue
            for j in range(s, e):
                bound[j] = 0
            i = e - 1

        # 5. 合并结果
        if all([x==0 for x in bound]):
            return sword, sinfo
        
        _sword, _sinfo = [], []
        i = -1
        while i + 1 < slen:
            i += 1
            if bound[i] == 0:
                _sword.append(sword[i])
                _sinfo.append(sinfo[i])
                continue
            wd = sword[i]
            py = [] if pinyin[i] is None else pinyin[i]
            i += 1
            while i < slen and bound[i] < 0:
                wd += sword[i]
                py += [] if pinyin[i] is None else pinyin[i]
                i += 1
            i -= 1
            if len(py) == 0: py = None
            pos = {'nr':0}; # 设置nr词性
            flag = {"P":0,"S":0,"F":0,"L":0,"X":0,"W":0,"T":0}
            _sword.append(wd)
            _sinfo.append((py, pos, flag))

        return  _sword, _sinfo

    
class GPosBTree(object):
    def __init__(self, btree_path, loglv):
        self.loglv = loglv
        self.btree = dict()
        
        # load model
        self._load(btree_path)
        
        # trace 
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Initialize Success.\n")
        if self.loglv > 2:
            sys.stderr.write("{func_name}: binary tree[{name}]\n")
            for node in self.btree:
                sys.stderr.write(f"{func_name}: {node}\n")
    
    def _load(self, btree_path):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(
                f"{func_name}: load binary tree from {btree_path}\n")
        with open(btree_path, 'rt') as f:
            for line in f:
                line = line.strip()
                if line == '': continue
                mr = re.match(r'^\[(.+)\]$', line)
                if mr: break
            for line in f:
                line = line.strip()
                if line == '': continue
                assert line == '{'
                break
            for line in f:
                line = line.strip()
                if line == '': continue
                if line == '}': break
                arr = line.split()
                assert len(arr) == 4
                arr = [x.strip('",-') for x in arr]
                self.btree.update({arr[0]: {'QS': arr[1], 'YES': arr[2], 'NO': arr[3], 'LEAF': False}})
                self.btree.update({arr[2]: {'LEAF': True}})
                self.btree.update({arr[3]: {'LEAF': True}})
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: load binary tree from {btree_path} done! \n")
        if self.loglv > 2:
            sys.stderr.write(f"{func_name}: {self.btree}")
    
    def decision(self, word):
        node = '0'
        while not self.btree[node]['LEAF']:
            qs = self.btree[node]['QS']
            i, v = int(qs[1]), qs[3] # e.g., C3=D
            if word[i-1] == v:
                node = self.btree[node]['YES']
            else:
                node = self.btree[node]['NO']
        return node
    
    def __call__(self, word):
        if not re.search(r'[a-zA-Z\'\-]', word):
            return {'sym': 0}
        word = '0' + word.upper() + '000'
        word = word[:2] + word[-4:]
        ret = self.decision(word)
        hpos = {}
        for r in ret.split(','):
            k, v = r.split('=')
            hpos[k] = float(v)
        return hpos


class SegmenterEN(object):
    def __init__(self, res_root_dir=None, loglv=0):
        self.loglv = loglv
        
        # default resource paths
        if res_root_dir is None: res_root_dir = textparser.__path__[0]
        self.dict_paths = [
            os.path.join(res_root_dir, path)
            for path in Config.en_dict_paths
        ]
        posfsm_path = os.path.join(res_root_dir, Config.en_pos_path)
        postree_path = os.path.join(res_root_dir, Config.en_guesspos_path)

        self.files_mtime = dict()
                
        # create pos fsm
        self.pos_fsm = FSM(posfsm_path, 1.3, 50, loglv)
        self.files_mtime[posfsm_path] = int(os.stat(posfsm_path).st_mtime)
        
        # g2p for oov
        self.g2p = G2p()

        # guess pos for oov
        self.w2p = GPosBTree(postree_path, loglv)
        self.files_mtime[postree_path] = int(os.stat(postree_path).st_mtime)
        
        # load dict
        self.wordict = dict()
        for dict_path in self.dict_paths:
            self.wordict.update(self._load(dict_path))
            self.files_mtime[dict_path] = int(os.stat(dict_path).st_mtime)
        
        # regex compile
        self.regex = [
            re.compile(r'\.$'),
            re.compile(r'^([a-z]+)$', re.I),
            re.compile(r'^([\'"])(.+)$'),
            re.compile(r'^([a-z]+)(n\'t|\'ll|\'ve|\'re|\'s|\'m|\'d|\'em|\')$', re.I),
            re.compile(r'^([a-z]+)(\'n\')([a-z])$', re.I),
            re.compile(r'^([a-z\']+)(.+)$', re.I),
            re.compile(r'^([^a-zA-Z]+)(.+)$', re.I),
        ]

        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Initialize Success! \n")

    def _load(self, filename):
        wordict = {}
        def _parse_item(line):
            # e.g.: 
            # MERRIN m_eh1-r_ih_n0;0;nnp=0
            # AID ey_d1;0;vb=2.478,nn=.111,nnp=3.864
            line = line.strip('').rstrip(',;')
            if line == '': return False
            word, line = line.split()
            arr = line.split(';')
            pinyin, pos = arr[0], arr[2]
            if len(pinyin) == 0:
                pinyin = self.g2p(word)
            else:
                pinyin = arr[0].split('-')
                for i, py in enumerate(pinyin):
                    if not Syllable.is_sil(py):
                        pinyin[i] = "(" + py[:-1] + ")" + py[-1] # n_ow1 -> (n_ow)1
            if len(pos) == 0:
                hpos = self.w2p(word)
            else:
                hpos = {} # {'vb':2.478,'nn'=.111,'nnp':3.864}
                for s in pos.split(','):
                    c, w = s.split('=')
                    hpos[c] = float(w)
            wordict[word] = (pinyin, hpos)
            return True
        
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: load dictionay for {filename}\n")
        
        with open(filename, 'rt') as f:
            for line in f:
                if not _parse_item(line):
                    if self.loglv > 0: sys.stderr.write(f"{func_name}: parse item error: {line}\n")
        
        if self.loglv > 0:
             sys.stderr.write(f"{func_name}: word count = {len(wordict)}\n")
        return wordict
    
    def _get_pinyin(self, word):
        info = self.wordict.get(word)
        if info is None: return None
        return info[0]
    
    def _get_pos(self, word):
        info = self.wordict.get(word)
        if info is None: return None
        return info[1]

    def update(self):
        for dict_path in self.dict_paths:
            if 'user' not in dict_path: continue
            if self.files_mtime[dict_path] != int(os.stat(dict_path).st_mtime):
                self.wordict.update(self._load(dict_path))

    def __call__(self, utt_id, utt_text, utt_mark):
        segtext = SegText()
        if utt_text == "": 
            return utt_id, segtext

        # split word
        sword, sinfo = self._split_word(utt_text)
        if len(sword) == 0 or len(sinfo) == 0:
            return  utt_id, segtext
        
        # full fill pinyin and pos
        pinyin = [x[0] if x is not None else None for x in sinfo]
        hpos = [x[1] if x is not None else None for x in sinfo]
        pinyin = self._fill_pinyin(sword, pinyin)
        hpos = self._fill_pos(sword, hpos)

        # predict pos
        pos = self.pos_fsm(hpos)
        
        # create segtext list
        for i in range(len(sword)):
            segtext.append() # create one empty element
            segtext.set_wpc(-1, sword[i], pinyin[i], pos[i])
            segtext.set_lang(-1, Lang.EN)
            segtext.set_mark(-1, None)
        
        return utt_id, segtext
    
    def _split_word(self, utt_text):
        if len(utt_text) == 0: return None, None

        utt_text = self.regex[0].sub(' .', utt_text) # T. => T ., maybe dot is sent
        arr_text = utt_text.split()

        sword, sinfo = [], []
        while len(arr_text) > 0:
            word = arr_text.pop(0)
            info = self.wordict.get(word.upper())
            if info is not None:
                sword.append(word)
                sinfo.append(info)
                continue
            elif self.regex[1].match(word):
                sword.append(word)
                sinfo.append(None)
                continue

            # 根据规则拆分
            mr = self.regex[2].match(word) # '^([\'"])(.+)$'
            if mr:
                arr_text.insert(0, mr.group(2))
                arr_text.insert(0, mr.group(1))
                continue
            mr = self.regex[3].match(word) # '^([a-z]+)(n\'t|\'ll|\'ve|\'re|\'s|\'m|\'d|\'em|\')$'
            if mr:
                arr_text.insert(0, mr.group(2))
                arr_text.insert(0, mr.group(1))
                continue
            mr = self.regex[4].match(word) # '^([a-z]+)(\'n\')([a-z])$'
            if mr:
                arr_text.insert(0, mr.group(3))
                arr_text.insert(0, mr.group(2))
                arr_text.insert(0, mr.group(1))
                continue
            mr = self.regex[5].match(word) # '^([a-z\']+)(.+)$'
            if mr:
                arr_text.insert(0, mr.group(2))
                arr_text.insert(0, mr.group(1))
                continue
            mr = self.regex[6].match(word) # '^([^a-zA-Z]+)(.+)$'
            if mr:
                arr_text.insert(0, mr.group(2))
                arr_text.insert(0, mr.group(1))
                continue
            sword.append(word)
            sinfo.append(None)
        
        return sword, sinfo
    
    def _fill_pinyin(self, sword, pinyin):
        for i in range(len(sword)):
            if pinyin[i] is None or len(pinyin[i]) == 0:
                pinyin[i] = self.g2p(sword[i])
        return pinyin

    def _fill_pos(self, sword, hpos):
        for i in range(len(sword)):
            if hpos[i] is None or len(hpos[i]) == 0:
                hpos[i] = self.w2p(sword[i])
        return hpos

class Segmenter(object):
    def __init__(self, res_root_dir=None, loglv=0):
        self.loglv = loglv
        self.segmenter_cn = SegmenterCN(res_root_dir, loglv)
        self.segmenter_en = SegmenterEN(res_root_dir, loglv)

        # compile regex
        self.regex = {
            '^([\u4e00-\u9fa5]+)': re.compile(r'^([\u4e00-\u9fa5]+)'),
            '^([a-zA-Z\']+)': re.compile(r'^([a-zA-Z\']+)'),
            '^(\(([a-zA-Z]+)(\d)\))': re.compile(r'^(\(([a-zA-Z]+)(\d)\))'),
            '^(\s+)': re.compile(r'^(\s+)'),
        }
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Initialize Success.\n")
    
    def update(self):
        self.segmenter_cn.update()
        self.segmenter_en.update()

    def _replace_blank_text(self, utt_id, utt_text):
        utt_text = utt_text.strip()
        if utt_text == '': utt_text = '。'
        return utt_id, utt_text
    
    def _split_text(self, utt_text:str):
        # 中英文拆分，同时识别出拼音标记
        sub_text, sub_lang, sub_mark = [], [], []
        pre_lang = Lang.UNKNOW
        while utt_text != '':
            # Chinese
            mr = self.regex['^([\u4e00-\u9fa5]+)'].match(utt_text)
            if mr:
                r1 = mr.group(1)
                utt_text = utt_text[mr.end(1):]
                if pre_lang != Lang.CN:
                    sub_text.append(r1)
                    sub_lang.append(Lang.CN)
                    sub_mark.append([None for _ in range(len(r1))])
                else:
                    sub_text[-1] += r1
                    sub_mark[-1] += [None for _ in range(len(r1))]
                pre_lang = Lang.CN
                continue
            # Enligsh
            mr = self.regex['^([a-zA-Z\']+)'].match(utt_text)
            if mr:
                r1 = mr.group(1)
                utt_text = utt_text[mr.end(1):]
                if pre_lang != Lang.EN:
                    sub_text.append(r1)
                    sub_lang.append(Lang.EN)
                    sub_mark.append([None])
                else:
                    sub_text[-1] += r1
                    sub_mark[-1] += [None for _ in range(len(r1))]
                pre_lang = Lang.EN
                continue
            # Pinyin mark
            mr = self.regex['^(\(([a-zA-Z]+)(\d)\))'].match(utt_text)
            if mr:
                py, tone = mr.group(2), mr.group(3)
                if Syllable.is_py(py) and int(tone) <= 5 and pre_lang == Lang.CN:
                    utt_text = utt_text[mr.end(1):]
                    sub_mark[-1][-1] = py + tone
                    continue
            # Symbol: blank
            mr = self.regex['^(\s+)'].match(utt_text)
            if mr:
                utt_text = utt_text[mr.end(1):]
                if pre_lang == Lang.EN:
                    sub_text[-1] += ' '
                    sub_mark[-1] += [None]
                continue
            # Symbol: others
            r1 = utt_text[0]
            utt_text = utt_text[1:]
            if len(sub_text) > 0:
                sub_text[-1] += r1
                sub_mark[-1] += [None for _ in range(len(r1))]
            else:
                sub_text.append(r1)
                sub_lang.append(Lang.UNKNOW)
                sub_mark.append([None])
            continue

        # repaire lang
        next_lang = sub_lang[-1]
        for i in range(len(sub_lang)-1, -1, -1):
            if sub_lang[i] == Lang.UNKNOW:
                sub_lang[i] = next_lang
            next_lang = sub_lang[i]
        
        return sub_text, sub_lang, sub_mark
        
    def __call__(self, utt_id, utt_text):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: input> utt_id={utt_id}, utt_text=`{utt_text}`\n")
        
        utt_id, utt_text = self._replace_blank_text(utt_id, utt_text)
        sub_text, sub_lang, sub_mark = self._split_text(utt_text)

        segtext = SegText()
        for i in range(len(sub_text)):
            if sub_lang[i] == Lang.EN:
                _, segtext_ = self.segmenter_en(utt_id, sub_text[i], sub_mark[i])
            else:
                _, segtext_ = self.segmenter_cn(utt_id, sub_text[i], sub_mark[i])
            segtext += segtext_
        
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: output> utt_id={utt_id}, segtext=`{segtext}`\n")
        
        return utt_id, segtext


def main(file=sys.stdin):
    loglv = 0
    if len(sys.argv) > 1:
        loglv = int(sys.argv[1])
    
    segmenter = Segmenter(loglv=loglv)

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

        # split word
        utt_id, segtext = segmenter(utt_id, utt_text)

        # output
        line = f'{utt_id}    {segtext.printer()}\n'
        sys.stdout.write(line)

        if loglv > 0: # format print
            line = f"{utt_id}    "
            slen = len(line)
            line += f"{utt_text}\n"
            line += "".ljust(slen)
            line += f"{segtext.printer()}\n"
            sys.stderr.write(line)
    
    if fid.fileno() not in {0, 1, 2}:
        fid.close()

if __name__ == "__main__":
    
    main()