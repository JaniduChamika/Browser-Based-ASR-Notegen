try:
    import pyctcdecode
    print("pyctcdecode ok")
except ImportError:
    print("pyctcdecode missing")

try:
    import ctclib
    print("ctclib ok (kenlm might be present)")
except ImportError:
    pass

try:
    import kenlm
    print("kenlm ok")
except ImportError:
    print("kenlm missing")
