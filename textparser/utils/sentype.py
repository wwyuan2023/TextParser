# coding: utf-8

class SenType:
    sentype_num = 10
    sentype_list = (
        "。",
        "！",
        "？",
        "！？",
        "？！",
        "，",
        "；",
        "：",
        "…",
        "——"
    )
    sentype_dict = {
        "。": 0,
        "！": 1,
        "？": 2,
        "！？": 3,
        "？！": 4,
        "，": 5,
        "；": 6,
        "：": 7,
        "…": 8,
        "——": 9,
    }

    @staticmethod
    def sentype2idx(sentype):
        return SenType.sentype_dict.get(sentype, 0)
    
    @staticmethod
    def idx2sentype(idx):
        if -SenType.sentype_num <= idx < SenType.sentype_num:
            return SenType.sentype_list[idx]
        return SenType.sentype_list[0]
    
    @staticmethod
    def one_hot(idx):
        hot = [0. for _ in range(SenType.sentype_num)]
        hot[idx] = 1.
        return hot

if __name__ == "__main__":
    
    
    print(SenType.idx2sentype(3))
    print(SenType.one_hot(3))