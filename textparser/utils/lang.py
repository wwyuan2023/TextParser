# coding: utf-8

class Lang:
    lang_num = 2
    
    UNKNOW = ''
    DEFAULT = 'CN'
    CN = 'CN'
    EN = 'EN'

    @staticmethod
    def lang2idx(lang):
        if lang == Lang.CN:
            return 0
        return 1
    
    @staticmethod
    def idx2lang(idx):
        if idx == 0:
            return Lang.CN
        elif idx == 1:
            return Lang.EN
        return Lang.UNKNOW
    
    @staticmethod
    def one_hot(lang):
        hot = [0. for _ in range(Lang.lang_num)]
        hot[Lang.lang2idx(lang)] = 1.
        return hot