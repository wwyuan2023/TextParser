# coding: utf-8

import os, sys
import re

import textparser
from textparser import Config
from textparser.utils import Syllable, SegText
from textparser.utils import GPOS, Lang
from textparser.third_part import CMUSylBnd, G2p


class Pronunciation(object):
    def __init__(self, res_root_dir=None, loglv=0):
        self.loglv = loglv
        
        # default resource paths
        if res_root_dir is None: res_root_dir = textparser.__path__[0]
        polyphone_paths = [
            os.path.join(res_root_dir, path)
            for path in Config.polyphone_paths
        ]

        self.files_mtime = dict()
        
        # load polyphone rule
        self.rules = dict()
        for path in polyphone_paths:
            self._load(path)
            self.files_mtime[path] = int(os.stat(path).st_mtime)
        
        # sort by weight
        for poly in self.rules:
            self.rules[poly] = tuple(sorted(self.rules[poly], key=lambda x: x[0], reverse=True))
        
        # trace 
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: {len(self.rules)} polyphone rule be loaded.\n")
        if self.loglv > 1:
            sys.stderr.write(f"{func_name}: polyphone word={self.rules.keys()}\n")
        if self.loglv > 2:
            for poly in self.rules:
                sys.stderr.write("{func_name}: [{poly}]\n")
                for rule in self.rules[poly]:
                    sys.stderr.write(f"{func_name}: {self._rule_printer(rule)}")
        
        # abbreviation
        abbr = ("i'll", "(ay_l)1", "it's", "(ih_t_s)1", "don't", "(d_ow_n_t)1", "didn't", "(d_ih)1-(d_ax_n_t)0", "isn't", "(ih)1-(z_ax_n_t)0", "doesn't", "(d_ah)1-(z_ax_n_t)0",
         "that's", "(dh_ae_t_s)1", "won't", "(w_ow_n_t)1", "aren't", "(aa_r_n_t)1", "there's", "(dh_eh_r_z)1", "here's", "(hh_ih_r_z)1", "we're", "(w_ih_r)1", "wouldn't", "(w_uh_d_n_t)1",
         "wasn't", "(w_aa)1-(z_ax_n_t)0", "they're", "(dh_eh_r)1", "weren't", "(w_er_n_t)1", "i'm", "(ay_m)1", "he's", "(hh_ih_z)1", "you're", "(y_uh_r)1", "y'r", "(y_uh_r)1", "haven't", "(hh_ae)1-(v_ax_n_t)0",
         "we've", "(w_ih_v)1", "i've", "(ay_v)1", "hadn't", "(hh_ae)1-(d_ax_n_t)0", "they've", "(dh_ey_v)1", "shouldn't", "(sh_uh)1-(d_ax_n_t)0", "i'd", "(ay_d)1", "they'll", "(dh_ey_l)1",
         "you've", "(y_uh_v)1", "you'll", "(y_uh_l)1", "i'll", "(ay_l)1", "we'd", "(w_ih_d)1", "he'd", "(hh_ih_d)1", "he'll", "(hh_ih_l)1", "they'd", "(dh_ey_d)1", "you'd", "(y_uh_d)1",
         "it'll", "(ih)1-(t_ax_l)0", "who've", "(hh_uw_v)1", "needn't", "(n_iy)1-(d_ax_n_t)0", "she'd", "(sh_ih_d)1", "who'd", "(hh_uh_d)1", "she'll", "(sh_ih_l)1",
         "there'll", "(dh_eh_l)1", "there'd", "(dh_eh_d)1", "it'd", "(ih)1-(t_ax_d)0", "who'll", "(hh_uh_l)1", "that'll", "(dh_ae)1-(t_ax_l)0", "mightn't", "(m_ay)1-(t_ax_n_t)0",
         "would've", "(w_uh)1-(d_ax_v)0", "mustn't", "(m_ah)1-(s_ax_n_t)0", "how'd", "(hh_ow_d)1", "could've", "(k_uh)1-(d_ax_v)0", "hasn't", "(hh_ae)1-(z_ax_n_t)0", "couldn't", "(k_uh)1-(d_ax_n_t)0",
         "can't", "(k_ae_n_t)1", "we'll", "(w_ih_l)1", "bless'em", "(b_l_eh)1-(z_ax_m)0", "this's", "(dh_ih)1-(s_ih_z)0")
        self.abbr_table = dict(zip(abbr[::2],abbr[1::2]))
        
        # 拼音标记
        self.pyregex = re.compile('^P(\d+)=([a-z]+)(\d)$')

        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Initialize Success.\n")
        
    def _load(self, filename):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: load polyphone from {filename}\n")
        
        with open(filename, 'rt') as f:
            poly = ''
            for line in f:
                line = re.sub(r'\s+', '', line)
                if line == '' or line[0] == '#': continue
                mr = re.match(r'^\[(.+)\]$', line)
                if mr:
                    poly = mr.group(1)
                    if poly not in self.rules:
                        self.rules[poly] = []
                    continue
                mr = re.match(r'^(\d+)\?(.+:)(.+?),([a-z]+?)$', line)
                assert mr, f"line={line}\n"
                weight, cond, pinyin, pos = mr.group(1), mr.group(2), mr.group(3), mr.group(4)
                rule = [int(weight), pinyin, pos]
                line = cond
                while True:
                    mr = re.match(r'^\((.+?)\)[\(:]', line)
                    assert mr, f"line={line}\n"
                    line = line[mr.end(1)+1:]
                    c = mr.group(1) # fmt: start,end,[!][c|z|p];s1;s2;…;sn
                    mr = re.match(r'^([^,]+?),([^,]+?),([czp!]{1,2});(.+)$', c)
                    assert mr, f"c={c}, line={line}"
                    start, end, czp, sn = int(mr.group(1)), int(mr.group(2)), mr.group(3), mr.group(4).strip(';')
                    assert len(czp) == 1 or czp[0] == '!', f"czp={czp}, line={line}"
                    matched = [start, end, czp, ';'+sn+';']
                    rule.append(tuple(matched))
                    if line[0] == ':': break
                self.rules[poly].append(rule)
                continue
    
    def _rule_printer(self, rule):
        weight, pinyin, pos = rule[:3]
        _str = f"{weight}?"
        for matched in rule[3:]:
            _str += f"({matched[0]},{matched[1]},{matched[2]}{matched[3]})"
        _str += f":{pinyin},{pos}\n"
        return _str

    def _match_rule(self, segtext, idx, rule):
        for matched in rule[3:]:
            start, end, czp, cond = matched
            nidx = idx + start
            
            if nidx < 0 or nidx > len(segtext): # out of range
                return False
            
            success = True
            if czp[-1] == 'c':
                cx = ';' + segtext.get_cx(nidx, '') + ';'
                if cx not in cond: success = False
            elif czp[-1] == 'z':
                ws = [';'+w+';' for w in segtext.get_wd(nidx, '')]
                success = any([w in cond for w in ws])
            else: #'p'
                wd = ';' + segtext.get_wd(nidx, '') + ';'
                if wd not in cond: success = False
            
            if czp[0] == '!': success = not success
            if not success: return False
        return True
    
    def _predict(self, segtext):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
        for idx in range(len(segtext)):
            wd = segtext.get_wd(idx)
            if wd is None: continue
            wd = wd.upper()
            if wd not in self.rules: continue
            if self.loglv > 1:
                sys.stderr.write(f"{func_name}: predicting polyphone `{wd}` ...\n")
            for rule in self.rules[wd]:
                if not self._match_rule(segtext, idx, rule):
                    if self.loglv > 2:
                        sys.stderr.write(f"{func_name}: try to match rule failure, rule={self._rule_printer(rule)}")
                    continue
                if self.loglv > 1:
                    sys.stderr.write(f"{func_name}: try to match rule success, rule={self._rule_printer(rule)}")
                segtext.set_py(idx, rule[1])
                segtext.set_cx(idx, rule[2])
                break
        return segtext

    def update(self):
        pass

    def __call__(self, utt_id, segtext):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: input> utt_id={utt_id}, segtext=`{segtext}`\n")
        
        if len(segtext) == 0: return utt_id, segtext

        segtext = self._predict(segtext)
        segtext = self._changetone_yibu(segtext)
        segtext = self._changetone_33(segtext)
        segtext = self._changepron_functionword(segtext)
        segtext = self._changepron_abbr(segtext)
        segtext = self._changepron_mark(segtext)
        
        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: output> utt_id={utt_id}, segtext=`{segtext}`\n")
        
        return utt_id, segtext
    
    def _changetone_yibu(self, segtext): # 一不变调
        for idx in range(len(segtext)):
            if segtext.get_lang(idx) != Lang.CN: continue
            cur_word = segtext.get_wd(idx, '')
            if cur_word != '一' and cur_word != '不': continue
            pre_word, nxt_word = '', ''  # 前/后汉字
            pre_tone, nxt_tone = -1, -1  # 前/后音调
            pre_gpos, nxt_gpos = '', ''  # 前/后词性
            if idx > 0:
                wd, py, cx = segtext.get_wpc(idx-1, '', '', '')
                pre_word = wd[-1] if len(wd) > 0 else ''
                pre_tone = int(py[-1][-1]) if len(py) > 0 and len(py[-1]) > 0 else -1
                pre_gpos = cx
            if idx < len(segtext) - 1:
                wd, py, cx = segtext.get_wpc(idx+1, '', '', '')
                nxt_word = wd[0] if len(wd) > 0 else ''
                nxt_tone = int(py[0][-1]) if len(py) > 0 and len(py[0]) > 0 else -1
                nxt_gpos = cx
            if cur_word == '不':
                # 后接4调变2调
                if nxt_tone == 4:
                    segtext.set_py(idx, 'bu2')
            else: # cur_word == '一'
                # 后接轻声；或特殊关键字前；或前汉字为“第”：读1调
                if nxt_tone == 5 or nxt_word in '元月日号至' or pre_word == '第':
                    segtext.set_py(idx, 'yi1')
                # 前后是数词：读1调
                elif pre_gpos == 'm' or nxt_gpos == 'm':
                    segtext.set_py(idx, 'yi1')
                # 后接123调变4调
                elif 1 <= nxt_tone <= 3:
                    segtext.set_py(idx, 'yi4')
                # 后接4调变2调
                elif nxt_tone == 4:
                    segtext.set_py(idx, 'yi2')
        return segtext
    
    def _changetone_33(self, segtext):
        nxt_tone = -1  # 后一个声调
        for idx in range(len(segtext) - 1, -1, -1):
            if segtext.get_lang(idx) != Lang.CN:
                nxt_tone = -1
                continue
            pinyin = segtext.get_py(idx)
            if pinyin is None:
                nxt_tone = -1
                continue
            if len(pinyin) >= 1:
                new_pinyin = list(pinyin).copy()
                modify = False
                for i in range(len(pinyin) - 1, -1, -1):
                    if int(pinyin[i][-1]) == 3 and nxt_tone == 3:
                        new_pinyin[i] = pinyin[i][:-1] + '2'
                        modify = True
                    nxt_tone = int(new_pinyin[i][-1])
                if modify:
                    segtext.set_py(idx, new_pinyin)

            nxt_tone = int(pinyin[0][-1])
        return segtext
    
    def _changepron_functionword(self, segtext):
        # to/of/the/...
        for idx in range(len(segtext)):
            if segtext.get_lang(idx, Lang.UNKNOW) != Lang.EN: continue
            wd = segtext.get_wd(idx, '').upper()
            if wd == "OF":
                # of: 辅音后通常读作/(ax_v)0/，元音后通常读作/(ah_v)0/，句子首重读/(ao_f)1/
                if( (idx == 0 or idx == len(segtext) - 1)
                    or (idx > 0 and segtext.get_cx(idx-1) in ['comma', 'sent', 'colon', '', 'sym'])
                    or (idx + 1 < len(segtext) and segtext.get_cx(idx+1) in ['comma', 'sent', 'colon', '', 'sym'])
                ):
                    segtext.set_py(idx, '(ao_f)1')
                elif idx > 0:
                    pinyin = segtext.get_py(idx-1)
                    if pinyin is None:
                        segtext.set_py(idx, '(ao_f)1')
                    elif CMUSylBnd.is_vowel(Syllable.s2p(pinyin[-1])[-1][len(Lang.EN):]):
                        segtext.set_py(idx, '(ax_v)0')
                    else:
                        segtext.set_py(idx, '(ah_v)0')
                continue
            if wd == "THE":
                # the: 辅音前通常读作/(dh_ax)0/，元音前通常读作/(dh_ih)0/，句尾重读/(dh_ih)0/
                if( idx - 1 == len(segtext)
                    or (idx + 1 < len(segtext) and segtext.get_cx(idx+1) in ['comma', 'sent', 'colon', '', 'sym'])
                ):
                    segtext.set_py(idx, '(dh_ih)0')
                elif idx < len(segtext) - 1:
                    pinyin = segtext.get_py(idx+1)
                    if pinyin is None:
                        segtext.set_py(idx, '(dh_ax)0')
                    elif CMUSylBnd.is_vowel(Syllable.s2p(pinyin[0])[0][len(Lang.EN):]):
                        segtext.set_py(idx, '(dh_ih)0')
                    else:
                        segtext.set_py(idx, '(dh_ax)0')
                continue
            if wd == "TO":
                # to: 辅音前通常读作/(t_ax)0/，元音前通常读作/(t_uh)0/，但当重读时读作/(t_uw)1/，句尾重读/(t_uw)1/
                if( (idx == 0 or idx == len(segtext) - 1)
                    or (idx > 0 and segtext.get_cx(idx-1) in ['comma', 'sent', 'colon', '', 'sym'])
                    or (idx + 1 < len(segtext) and segtext.get_cx(idx+1) in ['comma', 'sent', 'colon', '', 'sym'])
                ):
                    segtext.set_py(idx, '(t_uw)1')
                elif idx < len(segtext) - 1:
                    pinyin = segtext.get_py(idx+1)
                    if pinyin is None:
                        segtext.set_py(idx, '(t_uw)1')
                    elif CMUSylBnd.is_vowel(Syllable.s2p(pinyin[0])[0][len(Lang.EN):]):
                        segtext.set_py(idx, '(t_uh)0')
                    else:
                        segtext.set_py(idx, '(t_ax)0')
                continue
            if wd == "'s":
                # 's: 清音后通常读作/(s)0/，浊音后通常读作/(z)0/，句首读/(eh_s)1/
                if idx == 0 or (idx > 0 and segtext.get_cx(idx-1) in ['comma', 'sent', 'colon', '', 'sym']):
                    segtext.set_py(idx, '(eh_s)1')
                elif idx > 0:
                    pinyin = segtext.get_py(idx-1)
                    if pinyin is None:
                        segtext.set_py(idx, '(eh_s)1')
                    elif CMUSylBnd.is_voiced(Syllable.s2p(pinyin[-1])[-1][len(Lang.EN):]):
                        segtext.set_py(idx, '(z)0')
                    else:
                        segtext.set_py(idx, '(s)0')
                continue
                        
        return segtext 
    
    def _changepron_abbr(self, segtext):
        for idx in range(1, len(segtext)):
            if segtext.get_lang(idx, Lang.UNKNOW) != Lang.EN: continue
            wd = segtext.get_wd(idx-1, '').lower() + segtext.get_wd(idx, '').lower()
            if wd in self.abbr_table:
                segtext.set_py(idx-1, self.abbr_table[wd])
                segtext.set_py(idx, None)
                continue
            wd = segtext.get_wd(idx, '').lower()
            if wd in ["'s", "'d", "'m", "'ll", "'re", "'ve", "'em"]:
                cur_pinyin = segtext.get_py(idx)
                pre_pinyin = segtext.get_py(idx-1)
                if cur_pinyin is not None and pre_pinyin is not None:
                    ptone = pre_pinyin[-1][-1]
                    pphn = Syllable.s2p(pre_pinyin[-1])
                    cphn = Syllable.s2p(cur_pinyin[0])[0]
                    psyl = Syllable.p2s(list(pphn) + [cphn]) + ptone
                    segtext.set_py(idx-1, pre_pinyin[:-1] + [psyl])
                    segtext.set_py(idx, None)
        return segtext
    
    def _changepron_mark(self, segtext):
        for idx in range(1, len(segtext)):
            if segtext.get_lang(idx, Lang.UNKNOW) != Lang.CN: continue
            mark = segtext.get_mark(idx)
            if mark is None: continue
            for mk in mark.strip(',').split(','):
                mr = self.pyregex.match(mk)
                if not mr: continue
                i, py, tn = int(mr.group(1)), mr.group(2), mr.group(3)
                # check
                if not(0 < int(tn) < 6) or not(Syllable.is_py(py)): continue
                pinyin = segtext.get_py(idx)
                if pinyin is None:
                    pinyin = py + tn
                    continue
                if i > len(pinyin): continue
                pinyin = list(pinyin)
                pinyin[i] = py + tn
                segtext.set_py(idx, pinyin)
        return segtext


def main(file=sys.stdin):
    loglv = 0
    if len(sys.argv) > 1:
        loglv = int(sys.argv[1])
    
    pronunciation = Pronunciation(loglv=loglv)

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

        # polyphone rule
        segtext = SegText(utt_text)
        utt_id, segtext = pronunciation(utt_id, segtext)

        # output
        line = f"{utt_id}    {segtext.printer()}\n"
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