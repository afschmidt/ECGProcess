#!/usr/bin/env python3
import numpy as np
from ecgprocess.utils.general import (
    string_concat,
)


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_strong_concat():
    '''
    Testing different inputs
    '''
    assert string_concat('hello', 'world') == 'hello, world'
    assert string_concat('hello', 'world', sep='\n') == 'hello\nworld'
    assert string_concat(np.nan, 'world', sep=': ') == 'world'
    assert string_concat(1.0, 'world', sep=': ') == '1.0: world'
