import functools
import operator

from emoji import get_emoji_regexp


def get_emoji(self, em):
    em_regex = get_emoji_regexp()
    em_split_emoji = em_regex.split(em)
    em_split_whitespace = [substr.split() for substr in em_split_emoji]
    em_split = functools.reduce(operator.concat, em_split_whitespace)
    return [x for x in em_split if em_regex.match(x)]