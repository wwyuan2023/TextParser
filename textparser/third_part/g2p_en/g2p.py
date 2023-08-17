# -*- coding: utf-8 -*-
'''
By kyubyong park(kbpark.linguist@gmail.com) and Jongseok Kim(https://github.com/ozmig77)
https://www.github.com/kyubyong/g2p
'''

import os, re, sys
import numpy as np

class CMUSylBnd:
    def is_silence(ph:str):
        return ph in ['sil', 'sil0', 'pau', 'pau0']
    def is_vowel(ph:str):
        return ph[0] in 'aeiou'
    def is_voiced(ph:str):
        return ph not in ['ch', 'f', 'hh', 'k', 'p', 's', 'sh', 't', 'th']
    def has_vowel_in_list(lst:list):
        for ph in lst:
            if CMUSylBnd.is_vowel(ph):
                return True
        return False
    def syl_boundary(syl:list, phs:list):
        '''return True if this should be a syllalbe boundary
            this is of course phone set dependent
            syl: pre syllable list
            phs: current phoneme list
        '''
        if len(phs) == 0: return True
        elif CMUSylBnd.is_silence(phs[0]): return True
        elif not CMUSylBnd.has_vowel_in_list(phs): return False # no more vowels so reset *all* code
        elif not CMUSylBnd.has_vowel_in_list(syl): return False # need a vowel
        elif phs[0] == 'ng': return False
        elif phs[0] == 'hh': return True
        elif CMUSylBnd.is_vowel(phs[0]): return True
        elif CMUSylBnd.is_vowel(phs[1]): return True
        else:
            # kw/dr/tr/pl...
            if phs[1] == 'l' and phs[0] in 'bfgkp': return True
            elif phs[1] == 'r' and phs[0] in 'bdfgkpt': return True
            elif phs[1] == 'y' and phs[0] in 'bdfgklmnptv': return True
            elif phs[1] == 'w' and phs[0] in 'bdgkpstz': return True
            elif phs[0] == 's':
                if phs[1] in 'mnptk':
                    if CMUSylBnd.is_vowel(syl[-1]): return False
                    else: return True
                return False
        return False
    def split_syl(phs:list):
        phs = [x.lower() for x in phs] # fmt: ['ey1', 'b', 'r', 'ah0', 'hh', 'ae1', 'm']
        syls = [[]] # fmt: [['ey1'], ['b', 'r', 'ah0'], ['hh', 'ae1', 'm']]
        while len(phs) > 0:
            ph = phs.pop(0)
            syls[-1].append(ph)
            if CMUSylBnd.syl_boundary(syls[-1], phs):
                syls.append([])
        syls.pop(-1)
        outs = [] # fmt: ['(ey)1', '(b_r_ah)0', '(hh_ae_m)1']
        regex = re.compile('\d+')
        for s in syls:
            s = '(' + '_'.join(s) + ')'
            stress = '0'
            mr = regex.search(s)
            if mr:
                stress = mr.group()
            if int(stress) > 1: stress = '1'
            s = regex.sub('', s)
            outs.append(s + stress)
        return outs



class G2p(object):
    def __init__(self):
        super().__init__()
        self.graphemes = ["<pad>", "<unk>", "</s>"] + list("abcdefghijklmnopqrstuvwxyz")
        self.phonemes = ["<pad>", "<unk>", "<s>", "</s>"] + \
            ['AA0', 'AA1', 'AA2', 'AE0', 'AE1', 'AE2', 'AH0', 'AH1', 'AH2', 'AO0',
             'AO1', 'AO2', 'AW0', 'AW1', 'AW2', 'AY0', 'AY1', 'AY2', 'B', 'CH', 'D', 'DH',
             'EH0', 'EH1', 'EH2', 'ER0', 'ER1', 'ER2', 'EY0', 'EY1',
             'EY2', 'F', 'G', 'HH',
             'IH0', 'IH1', 'IH2', 'IY0', 'IY1', 'IY2', 'JH', 'K', 'L',
             'M', 'N', 'NG', 'OW0', 'OW1',
             'OW2', 'OY0', 'OY1', 'OY2', 'P', 'R', 'S', 'SH', 'T', 'TH',
             'UH0', 'UH1', 'UH2', 'UW',
             'UW0', 'UW1', 'UW2', 'V', 'W', 'Y', 'Z', 'ZH']
        self.g2idx = {g: idx for idx, g in enumerate(self.graphemes)}
        self.idx2g = {idx: g for idx, g in enumerate(self.graphemes)}
        
        self.p2idx = {p: idx for idx, p in enumerate(self.phonemes)}
        self.idx2p = {idx: p for idx, p in enumerate(self.phonemes)}
        
        self.load_variables()

    def load_variables(self):
        dirname = os.path.dirname(__file__)
        self.variables = np.load(os.path.join(dirname,'checkpoint20.npz'))
        self.enc_emb = self.variables["enc_emb"]  # (29, 64). (len(graphemes), emb)
        self.enc_w_ih = self.variables["enc_w_ih"]  # (3*128, 64)
        self.enc_w_hh = self.variables["enc_w_hh"]  # (3*128, 128)
        self.enc_b_ih = self.variables["enc_b_ih"]  # (3*128,)
        self.enc_b_hh = self.variables["enc_b_hh"]  # (3*128,)

        self.dec_emb = self.variables["dec_emb"]  # (74, 64). (len(phonemes), emb)
        self.dec_w_ih = self.variables["dec_w_ih"]  # (3*128, 64)
        self.dec_w_hh = self.variables["dec_w_hh"]  # (3*128, 128)
        self.dec_b_ih = self.variables["dec_b_ih"]  # (3*128,)
        self.dec_b_hh = self.variables["dec_b_hh"]  # (3*128,)
        self.fc_w = self.variables["fc_w"]  # (74, 128)
        self.fc_b = self.variables["fc_b"]  # (74,)

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def grucell(self, x, h, w_ih, w_hh, b_ih, b_hh):
        rzn_ih = np.matmul(x, w_ih.T) + b_ih
        rzn_hh = np.matmul(h, w_hh.T) + b_hh

        rz_ih, n_ih = rzn_ih[:, :rzn_ih.shape[-1] * 2 // 3], rzn_ih[:, rzn_ih.shape[-1] * 2 // 3:]
        rz_hh, n_hh = rzn_hh[:, :rzn_hh.shape[-1] * 2 // 3], rzn_hh[:, rzn_hh.shape[-1] * 2 // 3:]

        rz = self.sigmoid(rz_ih + rz_hh)
        r, z = np.split(rz, 2, -1)

        n = np.tanh(n_ih + r * n_hh)
        h = (1 - z) * n + z * h

        return h

    def gru(self, x, steps, w_ih, w_hh, b_ih, b_hh, h0=None):
        if h0 is None:
            h0 = np.zeros((x.shape[0], w_hh.shape[1]), np.float32)
        h = h0  # initial hidden state
        outputs = np.zeros((x.shape[0], steps, w_hh.shape[1]), np.float32)
        for t in range(steps):
            h = self.grucell(x[:, t, :], h, w_ih, w_hh, b_ih, b_hh)  # (b, h)
            outputs[:, t, ::] = h
        return outputs

    def encode(self, word):
        chars = list(word) + ["</s>"]
        x = [self.g2idx.get(char, self.g2idx["<unk>"]) for char in chars]
        x = np.take(self.enc_emb, np.expand_dims(x, 0), axis=0)

        return x

    def predict(self, word):
        # encoder
        enc = self.encode(word)
        enc = self.gru(enc, len(word) + 1, self.enc_w_ih, self.enc_w_hh,
                       self.enc_b_ih, self.enc_b_hh, h0=np.zeros((1, self.enc_w_hh.shape[-1]), np.float32))
        last_hidden = enc[:, -1, :]

        # decoder
        dec = np.take(self.dec_emb, [2], axis=0)  # 2: <s>
        h = last_hidden

        preds = []
        for i in range(20):
            h = self.grucell(dec, h, self.dec_w_ih, self.dec_w_hh, self.dec_b_ih, self.dec_b_hh)  # (b, h)
            logits = np.matmul(h, self.fc_w.T) + self.fc_b
            pred = logits.argmax()
            if pred == 3: break  # 3: </s>
            preds.append(pred)
            dec = np.take(self.dec_emb, [pred], axis=0)

        preds = [self.idx2p.get(idx, "<unk>") for idx in preds]
        return preds

    def __call__(self, word):
        word = word.lower()
        word = re.sub(r'[^a-z]', '', word)
        if word == '': return None
        # fmt: ['ey1', 'b', 'r', 'ah0', 'hh', 'ae1', 'm']
        prons = self.predict(word)
        # fmt: ['(ey)1', '(b_r_ah)0', '(hh_ae_m)1']
        syls = CMUSylBnd.split_syl(prons)
        return syls

if __name__ == '__main__':
    texts = [
        "I have $250 in my pocket.", # number -> spell-out
        "popular pets, e.g. cats and dogs", # e.g. -> for example
        "I refuse to collect the refuse around here.", # homograph
        "I'm an activationist.", # newly coined word
        "MX",
        "ttti, a2.",
    ]
    g2p = G2p()
    for text in texts:
        for word in text.split():
            out = g2p(word)
            print(word, out)

