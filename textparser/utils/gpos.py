# coding: utf-8

class GPOS:
    gpos_num = 61
    gpos_list = (
        'a',  # 形容词
        'c',  # 连词
        'd',  # 副词
        'f',  # 方位词
        'i',  # 成语
        'm',  # 数词
        'n',  # 普通名词
        'nr', # 人名
        'nx', # 外语
        'nz', # 专有名词
        'o',  # 拟声词
        'p',  # 介词
        'q',  # 量词
        'r',  # 代词
        't',  # 时间名词
        'u',  # 助词
        'v',  # 动词
        'w',  # 标点符号
        'y',  # 语气词
        
        'cc',     # Coordinating conjunction 
        'cd',     # Cardinal number
        'colon',  #  
        'comma',  #
        'dash',   # 
        'dt',     # Determiner
        'ex',     # Existential there 
        'fw',     # Foreign Word 
        'hyphen', # 
        'in',     # Preposision or subordinating conjunction
        'jj',     # Adjective 
        'jjr',    # Adjective, comparative
        'jjs',    # Adjective, superlative
        'lrb',    # 
        'md',     # Modal 
        'nn',     # Noun, singular or mass 
        'nnp',    # Proper Noun, singular 
        'nnps',   # Proper Noun, plural 
        'nns',    # Noun, plural 
        'pdt',    # Predeterminer 
        'pos',    # Possessive Ending
        'prp',    # Personal Pronoun 
        'prpg',   # Possessive Pronoun 
        'rb',     # Adverb 
        'rbr',    # Adverb, comparative 
        'rbs',    # Adverb, superlative 
        'rp',     # Particle 
        'rrb',    #  
        'sent',   # 
        'sym',    # Symbol 
        'to',     # To
        'uh',     # Interjection 
        'vb',     # Verb, base form 
        'vbd',    # Verb, past tense 
        'vbg',    # Verb, gerund or persent participle 
        'vbn',    # Verb, past participle 
        'vbp',    # Verb, non-3rd person singular present 
        'vbz',    # Verb, 3rd person singular present 
        'wdt',    # Wh-determiner 
        'wp',     # Wh-pronoun 
        'wpg',    # Possessive wh-pronoun 
        'wrb',    # Wh-adverb
    )
    gpos_dict = {
        'a': 0,
        'c': 1,
        'd': 2,
        'f': 3,
        'i': 4,
        'm': 5,
        'n': 6,
        'nr': 7,
        'nx': 8,
        'nz': 9,
        'o': 10,
        'p': 11,
        'q': 12,
        'r': 13,
        't': 14,
        'u': 15,
        'v': 16,
        'w': 17,
        'y': 18,
        
        'cc': 19, 
        'cd': 20, 
        'colon': 21, 
        'comma': 22, 
        'dash': 23, 
        'dt': 24, 
        'ex': 25, 
        'fw': 26, 
        'hyphen': 27, 
        'in': 28, 
        'jj': 29, 
        'jjr': 30, 
        'jjs': 31, 
        'lrb': 32, 
        'md': 33, 
        'nn': 34, 
        'nnp': 35, 
        'nnps': 36, 
        'nns': 37, 
        'pdt': 38, 
        'pos': 39, 
        'prp': 40, 
        'prpg': 41, 
        'rb': 42, 
        'rbr': 43, 
        'rbs': 44, 
        'rp': 45, 
        'rrb': 46, 
        'sent': 47, 
        'sym': 48, 
        'to': 49, 
        'uh': 50, 
        'vb': 51, 
        'vbd': 52, 
        'vbg': 53, 
        'vbn': 54, 
        'vbp': 55, 
        'vbz': 56, 
        'wdt': 57, 
        'wp': 58, 
        'wpg': 59, 
        'wrb': 60,
    }
    
    @staticmethod
    def gpos2idx(gpos):
        return GPOS.gpos_dict.get(gpos, GPOS.gpos_dict['n'])
    
    @staticmethod
    def idx2gpos(idx):
        if -GPOS.gpos_num <= idx < GPOS.gpos_num:
            return GPOS.gpos_list[idx]
        return 'n'
    
    @staticmethod
    def is_punc(gpos): # punctuation mark
        if gpos in ['w', 'sent', 'comma', 'dash', 'hyphen', 'colon', 'sym', 'lrb', 'rrb']:
            return True
        return False
    
    @staticmethod
    def one_hot(gpos):
        hot = [0. for _ in range(GPOS.gpos_num)]
        hot[GPOS.gpos2idx(gpos)] = 1.
        return hot


if __name__ == "__main__":
    
    print(GPOS.one_hot('n'))
    
