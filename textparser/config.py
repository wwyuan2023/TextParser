# coding: utf-8

import os, sys

class Config:
    
    max_word_length = 13
    max_syllable = 80
    
    cn_identy_chinese_name = True

    cn_dict_paths = ("resources/cn.dict.v1", "resources/cn.dict.user")
    en_dict_paths = ("resources/en-us.dict.v1", "resources/en-us.dict.user")
    cn_pos_path = "resources/cn.pos.v1"
    en_pos_path = "resources/en.pos.v1"
    en_guesspos_path = "resources/en.guesspos.v1"
    cn_special_symbols_paths = ("resources/cn.special_symbols.v1", )
    polyphone_paths = ("resources/cn.polyphone.v1", "resources/en-us.polyphone.v1", )
    

