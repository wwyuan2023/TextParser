# coding: utf-8

import os, sys

from .config import Config
from .modules import TextNormalizer, Segmenter, Pronunciation, Vectorization

class TextParser(object):
    def __init__(self, res_roor_dir=None, loglv=0):
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

    def __call__(self, utt_id, utt_text):
        if self.loglv > 0:
            func_name = f"{self.__class__.__name__}::{sys._getframe().f_code.co_name}"
            sys.stderr.write(f"{func_name}: Parse input text, utt_id={utt_id}, utt_text=`{utt_text}`\n")
        
        utt_id, utt_text = self.textnorm(utt_id, utt_text)
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


def main(fid=sys.stdin):
    loglv = 0 if len(sys.argv) <= 1 else int(sys.argv[1])
    outdir = None if len(sys.argv) <= 2 else sys.argv[2]
    
    if outdir is not None and not os.path.exists(outdir):
        os.makedirs(outdir)
    
    parser = TextParser(loglv=loglv)

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
        utt_id, utt_segtext, utt_vector = parser(utt_id, utt_text)

        # save
        if outdir is not None:
            outpath = os.path.join(outdir, f"{utt_id}.vec{utt_vector.shape[1]}")
            sys.stderr.write(f"Save to {outpath}, shape={utt_vector.shape}\n")
            utt_vector.tofile(outpath)

        # output
        line  = f"{utt_id}    {utt_text}\n"
        line += f"{utt_id}    {utt_segtext}\n"
        sys.stdout.write(line)
        
    return 

if __name__ == "__main__":

    main()
