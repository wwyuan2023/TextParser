# coding: utf-8

import os, sys

from textparser import Config
from textparser.modules import TextNormalizer, Segmenter, Pronunciation, Vectorization
from textparser.utils import Lang
from textparser.version import __version__

class TextParser(object):
    def __init__(self, res_roor_dir=None, context=Lang.CN, loglv=0):
        self.context = context
        self.loglv = loglv
        self.max_utt_length = Config.max_syllable # max syllale number of each sub-utterance

        self.textnorm = TextNormalizer(res_roor_dir, loglv=loglv)
        self.segmeter = Segmenter(res_roor_dir, loglv=loglv)
        self.pronuciation = Pronunciation(res_roor_dir, loglv=loglv)
        self.vectorization = Vectorization(loglv=loglv)
        
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Successful !\n")
    
    def update(self):
        try:
            self.textnorm.update()
            self.segmeter.update()
            self.pronuciation.update()
            self.vectorization.update()
        except:
            pass

    def __call__(self, utt_id, utt_text, context=None):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Parse input text, utt_id={utt_id}, utt_text=`{utt_text}`\n")
        
        utt_id, utt_text = self.textnorm(utt_id, utt_text, context=self.context if context is None else context)
        utt_id, utt_segtext = self.segmeter(utt_id, utt_text)
        utt_id, utt_segtext = self.pronuciation(utt_id, utt_segtext)
        utt_id, utt_segtext, utt_vector = self.vectorization(utt_id, utt_segtext)

        if self.loglv > 0:
            sys.stderr.write(f"{func_name}: Parse done! utt_id={utt_id}, utt_segtext=`{utt_segtext}`\n")
        if self.loglv > 2:
            sys.stderr.write(f"{func_name}: Devector, utt_id={utt_id}\n")
            prosody = self.vectorization.devectoring(utt_vector)
            for p in prosody:
                sys.stderr.write(f"utt_id={utt_id}: {p}\n")

        return utt_id, utt_segtext, utt_vector


def main():

    # parse arguments
    file, outdir, context, loglv = sys.stdin, None, Lang.CN, 0
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if len(a) > 1 and a[0] == "-":
            if a == "-l" or a == "--loglv":
                i += 1
                loglv = int(sys.argv[i])
            elif a == "-c" or a == "--context":
                i += 1
                context = sys.argv[i]
            elif a == "-o" or a == "--outdir":
                i += 1
                outdir = sys.argv[i]
            elif a == "-v" or a == "--version":
                print(f"{sys.argv[0]}, version={__version__}")
                sys.exit(0)
            else:
                assert a[0] != "-", f"Unkown argument {a}\n"
        else:
            file = sys.stdin if a == "-" else a
        i += 1
    
    if outdir is not None and not os.path.exists(outdir):
        os.makedirs(outdir)
    
    # construnt instance
    parser = TextParser(context=context, loglv=loglv)

    fid = open(file, 'rt') if not hasattr(file, 'read') else file
    for line in fid:
        # read one line
        line = line.strip()
        if line == '': continue
        for i in range(len(line)):
            if line[i].isspace():
                break
        utt_id, utt_text = line[:i].strip(), line[i:].strip()
        if utt_text == '':
            continue

        # text normalization
        utt_id, utt_segtext, utt_vector = parser(utt_id, utt_text, context=context)

        # save
        if outdir is not None:
            outpath = os.path.join(outdir, f"{utt_id}.vec{utt_vector.shape[1]}")
            sys.stderr.write(f"Save to {outpath}, shape={utt_vector.shape}\n")
            utt_vector.tofile(outpath)

        # output
        line  = f"{utt_id}    {utt_text}\n"
        line += f"{utt_id}    {utt_segtext}\n"
        sys.stdout.write(line)
    
    if fid.fileno() not in {0, 1, 2}:
        fid.close()
        
    return 

if __name__ == "__main__":

    main()
