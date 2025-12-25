"""
CSONH 1.0.1 Compliance Test Suite (Python)
Run with: pytest tests/test_csonh.py
"""
import sys
import os
import pytest
from textwrap import dedent

# Add parent directory to path to import csonh.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import csonh

# ==========================================
# 1. Basic Structures
# ==========================================

def test_empty_object():
    assert csonh.loads("{}") == {}
    assert csonh.loads("") == {}      # Empty file -> {}
    assert csonh.loads("# Comment") == {}

def test_basic_object():
    src = "key: 'value'"
    assert csonh.loads(src) == {"key": "value"}

def test_implicit_object_structure():
    src = dedent("""
    server:
      host: 'localhost'
      port: 8080
    """)
    assert csonh.loads(src) == {"server": {"host": "localhost", "port": 8080}}

def test_arrays():
    assert csonh.loads("[1, 2, 3]") == [1, 2, 3]
    assert csonh.loads("[\n  1,\n  2,\n  3\n]") == [1, 2, 3]

# ==========================================
# 2. Strict Separation
# ==========================================

def test_reject_space_separated_array():
    """Ensure [1 2] is rejected (must have comma)"""
    with pytest.raises(csonh.ParseError):
        csonh.loads("[1 2]")

def test_reject_space_separated_object():
    """Ensure {a:1 b:2} is rejected"""
    with pytest.raises(csonh.ParseError):
        csonh.loads("{a:1 b:2}")

# ==========================================
# 3. Top-Level Seal
# ==========================================

def test_reject_trailing_junk():
    """Ensure content after root object is rejected"""
    with pytest.raises(csonh.ParseError):
        csonh.loads("key: 1\ngarbage")

def test_reject_trailing_junk_array():
    with pytest.raises(csonh.ParseError):
        csonh.loads("[1, 2] junk")

# ==========================================
# 4. Strings & Dedenting
# ==========================================

def test_triple_quote_dedent():
    src = "msg: '''\n  Line 1\n  Line 2\n  '''"
    assert csonh.loads(src) == {"msg": "Line 1\nLine 2"}

def test_triple_quote_immediate_dedent():
    """Relaxed dedenting rule"""
    src = "msg: '''Line 1\n  Line 2\n  '''"
    assert csonh.loads(src) == {"msg": "Line 1\nLine 2"}

def test_unicode_escape():
    # Standard JSON-style hex escape
    assert csonh.loads(r"char: '\u0041'") == {"char": "A"}

# ==========================================
# 5. Numbers & Booleans
# ==========================================

def test_numbers():
    assert csonh.loads("i: 42") == {"i": 42}
    assert csonh.loads("f: 3.14") == {"f": 3.14}
    assert csonh.loads("h: 0xFF") == {"h": 255}
    assert csonh.loads("b: 0b10") == {"b": 2}

def test_booleans_case_sensitive():
    assert csonh.loads("a: yes") == {"a": True}
    with pytest.raises(csonh.ParseError):
        csonh.loads("b: NO") 

# ==========================================
# 6. Security & Rejection
# ==========================================

def test_reject_interpolation():
    with pytest.raises(csonh.LexerError):
        csonh.loads('a: "val #{x}"')

def test_allow_interpolation_literal_single_quote():
    # Single quotes don't interpolate, so this is just a string
    assert csonh.loads("a: 'val #{x}'") == {"a": "val #{x}"}

def test_reject_arithmetic():
    with pytest.raises((csonh.ParseError, csonh.LexerError)):
        csonh.loads("a: 1 + 2")
