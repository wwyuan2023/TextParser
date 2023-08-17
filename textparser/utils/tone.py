# coding: utf-8

from .lang import Lang

class Tone:
    tone_num = 9 # sil: 0; CN: 1~5; EN: 0~2
    
    @staticmethod
    def tone2idx(tone, lang):
        idx = tone
        if idx <= 0:
            idx = 0
        elif lang == Lang.CN:
            if idx < 0: idx = 0
            if idx > 5: idx = 5
        elif lang == Lang.EN:
            idx += 6
        return idx
    
    @staticmethod
    def idx2tone(idx):
        if idx > 5: idx -= 6
        return idx
    
    @staticmethod
    def one_hot(tone, lang):
        hot = [0. for _ in range(Tone.tone_num)]
        hot[Tone.tone2idx(tone, lang)] = 1.
        return hot


if __name__ == "__main__":
    
    print()
    

