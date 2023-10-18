# coding: utf-8

import re


def is_chinese(_char):
    return u'\u4e00' <= _char <= u'\u9fa5'

def is_all_chinese(strs):
    for _char in strs:
        if not u'\u4e00' <= _char <= u'\u9fa5':
            return False
    return True

def is_contains_chinese(strs):
    for _char in strs:
        if u'\u4e00' <= _char <= u'\u9fa5':
            return True
    return False

def is_english_lower(_char):
    return 97 <= ord(_char) <= 123

def is_english_upper(_char):
    return 65 <= ord(_char) <= 90

def is_english(_char):
    return is_english_lower(_char) or is_english_upper(_char)

def is_all_english(strs):
    for _char in strs:
        if not is_english(_char):
            return False
    return True

def is_quantifier(strs):
    if re.match('^[零幺两一二三四五六七八九十百千万亿点]+$', strs):
        return True
    return False

def DBC2SBC(ustring):
    '''全角转半角'''
    rstring = ""
    for uchar in ustring:
        inside_code = ord(uchar)
        if inside_code == 0x3000:
            inside_code = 0x0020
        else:
            inside_code -= 0xfee0
            if not(0x0021 <= inside_code <= 0x7e):
                rstring += uchar
                continue
        rstring += chr(inside_code)
    return rstring

def SBC2DBC(ustring):
    '''半角转全角'''
    rstring = ""
    for uchar in ustring:
        inside_code = ord(uchar)
        if inside_code == 0x0020:
            inside_code = 0x3000
        else:
            if not(0x0021 <= inside_code <= 0x7e):
                rstring += uchar
                continue
            inside_code += 0xfee0
        rstring += chr(inside_code)
    return rstring

def is_punctuation(_char):
    return _char in "，。！？！；：……——"


if __name__ == "__main__":
    
    print("中", is_chinese("中"))
    print("中a国", is_all_chinese("中a国"))
    print("中a国", is_contains_chinese("中a国"))
    print("a", is_english_lower("a"))
    print("a", is_english_upper("a"))
    print("一百二十三", is_quantifier("一百二十三"))
    print("全角转半角。", DBC2SBC("全角转半角。"))
    print("半角转全角.", SBC2DBC("半角转全角."))