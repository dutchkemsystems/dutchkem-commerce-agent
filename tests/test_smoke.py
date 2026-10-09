import os, sys
def test_root():
    assert os.path.isdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def test_py():
    assert sys.version_info >= (3, 10)
