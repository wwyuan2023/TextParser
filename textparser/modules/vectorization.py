#coding: utf-8

import os, sys
import numpy as np

from textparser import Config
from textparser.utils import GPOS, SenType, Syllable, Phoneme, Tone, Lang, SegText, is_punctuation
from textparser.version import __version__


def one_hot(index, n_class):
    # assert index < n_class, f"{index} < {n_class}"
    hot = [0. for _ in range(n_class)]
    hot[index%n_class] = 1.
    return hot


class Vectorization(object):
    def __init__(self, loglv=0):
        self.loglv = loglv
        
        self.max_syllable = Config.max_syllable

        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Initialize Success.\n")
    
    def update(self):
        pass

    def __call__(self, utt_id, segtext):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: input> utt_id={utt_id}, segtext=`{segtext}`\n")
        
        segtext = self._add_sentype(segtext)
        segtext = self._insert_sil(segtext)
        
        outputs = []
        pws = 0 # position of word in sentence
        for i in range(len(segtext)):
            #print(f"!!!!!!!!!! {utt_id}  ", segtext.segtext[i])
            py = segtext.get_py(i)
            if py is None: continue
            cx, lang, stype = segtext.get_cx(i), segtext.get_lang(i), segtext.get_sentype(i)
            outputs += self.vectoring(lang, py, cx, stype, pws)
            if len(py) == 1 and Syllable.is_sil(py[0]):
                pws = 0
            else:
                pws += len(py)
        
        vector = np.array(outputs, dtype=np.int8)

        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: output> utt_id={utt_id}, segtext=`{segtext}`\n")
        
        return utt_id, segtext, vector
    
    def _insert_sil(self, segtext):
        # 句末是否为sil
        for i in range(len(segtext)-1, -1, -1):
            if segtext.get_py(i) is not None:
                break
        py = segtext.get_py(i)
        if py is None or not Syllable.is_sil(py[0]):
            segtext.append() # 追加空元素
            segtext.set_wpc(-1, "。", ["sil0"], "w")
            segtext.set_lang(-1, segtext.get_lang(-2))
            segtext.set_sentype(-1, segtext.get_sentype(-2))
        
        # 开头是否为sil
        for i in range(len(segtext)):
            if segtext.get_py(i) is not None:
                break
        py = segtext.get_py(i)
        if py is not None or not Syllable.is_sil(py[0]):
            segtext.insert(0) # 插入空元素
            segtext.set_wpc(0, SenType.idx2sentype(segtext.get_sentype(1)), ["sil0"], "w")
            segtext.set_lang(0, segtext.get_lang(1))
            segtext.set_sentype(0, segtext.get_sentype(1))
        
        return segtext
    
    def _add_sentype(self, segtext):
        # 添加句子类型
        stype = 0
        for i in range(len(segtext)-1, -1, -1):
            wd = segtext.get_wd(i, '')
            cx = segtext.get_cx(i, '')
            if(GPOS.is_punc(cx) and is_punctuation(wd)):
                stype = SenType.sentype2idx(wd)
            segtext.set_sentype(i, stype)
        
        return segtext
    
    def vectoring(self, lang, pys, cx, stype, pws):
        outs = []
        py_num = len(pys)
        for j in range(py_num):
            py = pys[j]
            py, tone = py[:-1], int(py[-1])
            phns = Syllable.s2p(py) # "wu" -> ("CNuw")
            phn_num = len(phns)
            for k in range(phn_num):
                vec = []
                phn = phns[k]
                vec += Phoneme.one_hot(phn)                     # phoneme, [0, 90)
                vec += Tone.one_hot(tone, lang)                 # tone, [90, 99)
                vec += one_hot(1 if k + 1 == phn_num else 0, 2) # syllable boundary, [99, 101)
                vec += one_hot(1 if j + 1 == py_num else 0, 2)  # word boundary, [101, 103)
                vec += GPOS.one_hot(cx)                         # GPOS, [103, 164)
                vec += SenType.one_hot(stype)                   # sentence type, [164, 174)
                vec += Lang.one_hot(lang)                       # language id, [174, 176)
                vec += one_hot(pws+j, self.max_syllable)        # position of syllable in sentence, [176, 256)
                outs.append(vec)
        return outs
    
    def devectoring(self, vector:np.ndarray):
        # decode vector list to prosody dict
        prosody = list()
        if len(vector) == 0: return prosody
        
        vector = vector.astype(np.int32)
        wr = np.arange(vector.shape[1])
        
        for i in range(len(vector)):
            prosody.append(dict())
            prosody[-1]["phoneme"] = Phoneme.idx2phn(np.sum(vector[i,:90] * wr[:90]))
            prosody[-1]["tone"] = Tone.idx2tone(sum(vector[i,90:99] * wr[:9]))
            prosody[-1]["syllable_boundary"] = int(sum(vector[i,99:101] * wr[:2]))
            prosody[-1]["word_boundary"] = int(sum(vector[i,101:103] * wr[:2]))
            prosody[-1]["gpos"] = GPOS.idx2gpos(sum(vector[i,103:164] * wr[:61]))
            prosody[-1]["sent_type"] = SenType.idx2sentype(sum(vector[i,164:174] * wr[:10]))
            prosody[-1]["lang"] = Lang.idx2lang(sum(vector[i,174:176] * wr[:2]))
            prosody[-1]["position"] = int(sum(vector[i,176:256] * wr[:80]))
        
        return prosody


def vectorization(file=sys.stdin, outdir=None, loglv=0):
    
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    
    vectorization = Vectorization(loglv)
    
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
    
        # vectorization
        segtext = SegText(utt_text)
        utt_id, segtext, vector = vectorization(utt_id, segtext)
        
        # save and output
        outpath = os.path.join(outdir, f"{utt_id}.vec{vector.shape[1]}")
        sys.stderr.write(f"Save to {outpath}, shape={vector.shape}\n")
        vector.tofile(outpath)
            
        # checking
        if loglv >= 2:
            prosody = vectorization.devectoring(vector)
            for p in prosody:
                print(p)
    
    if fid.fileno() not in {0, 1, 2}:
        fid.close()


def devectorization(file=sys.stdin):
    vectorization = Vectorization()
    fid = open(file, 'rb') if not hasattr(file, 'read') else file
    if fid.fileno() == 0:
        buff = fid.buffer.read()
    else:
        buff = fid.read()
    vector = np.frombuffer(buff, dtype=np.float32).reshape(-1, 256)
    prosody = vectorization.devectoring(vector)
    for p in prosody:
        print(p)
    if fid.fileno() not in {0, 1, 2}:
        fid.close()


def main():
    
    file, outdir, _d, loglv = sys.stdin, None, False, 0
    
    # parse arguments
    help_str = f"usage: text-vectorization OPTIONS... [FILE]\n\n"
    help_str += f"Text vectorization for Chinese or English segtext, version={__version__}\n\n"
    help_str += f"Print vectorization results of lines from each FILE to standard output.\n"
    help_str += f"With no FILE, or when FILE is -, read standard input.\n\n"
    help_str += f"Mandatory arguments to long options are mandatory for short options too.\n"
    help_str += f"    -h, --help               show this help message and exit\n"
    help_str += f"    -d                       de-vectorization for debug, FILE must be vectorization file\n"
    help_str += f"    -l, --loglv LOGLEVEL     set log level,  the optional value is 0, 1 and 2, default={loglv}\n"
    help_str += f"    -o, --outdir OUTDIR      directory to save vectorization of parsed result\n"
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
            elif a == "-o" or a == "--outdir":
                i += 1
                outdir = sys.argv[i]
            elif a == "-d":
                _d = True
            elif a == "-v" or a == "--version":
                print(f"text-parser, version={__version__}"
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
    assert (outdir is None and _d) or (outdir is not None and not _d), f"--outdir or -d must be given!\n"
    
    if _d:
        devectorization(file)
    else:
        vectorization(file, outdir, loglv=loglv)


if __name__ == "__main__":

    main()
    