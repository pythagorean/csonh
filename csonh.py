"""
CSONH (Concise Structured Object Notation for Humanity) - Runtime Loader

A strict, data-only, zero-dependency parser for CSONH configuration files.
Compatible with CSONH Standard 1.0.

Usage:
    import csonh
    
    # Load from string
    data = csonh.loads('''
    server:
        host: 'localhost'
        port: 8080  # Default port
    ''')
    
    # Load from file
    with open('config.csonh', 'r') as f:
        data = csonh.load(f)
"""

import re
from dataclasses import dataclass
from typing import List, TextIO, Union, Any
from enum import Enum, auto

__all__ = ['load', 'loads', 'ParseError', 'LexerError']

# ==========================================
# Data Structures
# ==========================================

class TokenType(Enum):
    # Indentation
    INDENT = auto()
    DEDENT = auto()
    NEWLINE = auto()
    
    # Literals
    STRING = auto()
    NUMBER = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    IDENTIFIER = auto()
    
    # Symbols
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    COLON = auto()       # :
    COMMA = auto()       # ,
    
    # End
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int

class LexerError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"Lexer error at {line}:{col}: {message}")
        self.line = line
        self.col = col

class ParseError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        super().__init__(f"Parse error at {line}:{col}: {message}")
        self.line = line
        self.col = col

# ==========================================
# Lexer
# ==========================================

class _CSONHLexer:
    def __init__(self, source: str):
        self.source = source.replace('\r\n', '\n').replace('\r', '\n')
        if self.source.startswith('\ufeff'):
            self.source = self.source[1:]
        
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(self.source)
        
        self.indent_stack = [0]
        self.indent_unit = None
        self.indent_char = None
        
    def error(self, message: str):
        raise LexerError(message, self.line, self.col)
    
    def peek(self, offset=0):
        pos = self.pos + offset
        if pos >= self.length:
            return None
        return self.source[pos]
    
    def advance(self):
        if self.pos >= self.length:
            return None
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch
    
    def skip_whitespace(self):
        while self.peek() and self.peek() in ' \t':
            self.advance()
    
    def skip_line_comment(self):
        while self.peek() and self.peek() != '\n':
            self.advance()
    
    def skip_block_comment(self):
        # Determine if block-style (at start of line) or inline
        is_block_style = (self.col - 3) <= 1
        start_line = self.line
        start_col = self.col
        
        while self.pos < self.length:
            if self.peek() == '#' and self.peek(1) == '#' and self.peek(2) == '#':
                self.advance(); self.advance(); self.advance() # Consume ###
                if is_block_style:
                    while self.peek() and self.peek() != '\n':
                        self.advance()
                return
            self.advance()
        self.error(f"Unterminated block comment (started at {start_line}:{start_col})")
    
    def read_string(self, quote_char):
        start_line = self.line
        start_col = self.col - 1
        
        # Triple Quote Check
        if self.peek() == quote_char and self.peek(1) == quote_char:
            self.advance(); self.advance()
            return self.read_triple_quoted_string(quote_char, start_line, start_col)
        
        # Single/Double Quote
        content = []
        while True:
            ch = self.peek()
            if ch is None: self.error("Unterminated string")
            if ch == quote_char:
                self.advance()
                break
            if ch == '\n': self.error("Newline in single-line string")
            
            # Reject Interpolation in Double Quotes
            if quote_char == '"' and ch == '#' and self.peek(1) == '{':
                self.error("Interpolation #{} not allowed in CSONH")
                
            if ch == '\\':
                self.advance()
                content.append(self.read_escape())
            else:
                content.append(ch)
                self.advance()
        return ''.join(content)

    def read_triple_quoted_string(self, quote_char, start_line, start_col):
        content = []
        while True:
            ch = self.peek()
            if ch is None: self.error(f"Unterminated triple-quoted string (started at {start_line}:{start_col})")
            
            if ch == quote_char and self.peek(1) == quote_char and self.peek(2) == quote_char:
                self.advance(); self.advance(); self.advance()
                break
            
            if quote_char == '"' and ch == '#' and self.peek(1) == '{':
                self.error("Interpolation #{} not allowed in CSONH")
                
            content.append(ch)
            self.advance()
        return ('TRIPLE_QUOTED', quote_char, ''.join(content))

    def read_escape(self):
        ch = self.peek()
        if ch is None: self.error("Incomplete escape sequence")
        self.advance()
        escapes = {'n': '\n', 'r': '\r', 't': '\t', '\\': '\\', "'": "'", '"': '"'}
        if ch in escapes: return escapes[ch]
        if ch == 'u': return self.read_unicode_escape()
        self.error(f"Invalid escape sequence: \\{ch}")

    def read_unicode_escape(self):
        hex_chars = []
        for _ in range(4):
            ch = self.peek()
            if ch is None or ch not in '0123456789abcdefABCDEF':
                self.error("Invalid unicode escape")
            hex_chars.append(ch)
            self.advance()
        return chr(int(''.join(hex_chars), 16))

    def read_number(self):
        start = self.pos
        is_negative = False
        if self.peek() == '-':
            is_negative = True
            self.advance()
        
        if self.peek() == '0':
            nxt = self.peek(1)
            # Guard clauses for EOF checks
            if nxt and nxt in 'xX': self.advance(); self.advance(); return -self.read_base(16, '0123456789abcdefABCDEF') if is_negative else self.read_base(16, '0123456789abcdefABCDEF')
            if nxt and nxt in 'bB': self.advance(); self.advance(); return -self.read_base(2, '01') if is_negative else self.read_base(2, '01')
            if nxt and nxt in 'oO': self.advance(); self.advance(); return -self.read_base(8, '01234567') if is_negative else self.read_base(8, '01234567')
            if nxt and nxt.isdigit(): self.error("Leading zeros not allowed")
            
        return -self.read_decimal() if is_negative else self.read_decimal()

    def read_base(self, base, valid_chars):
        digits = []
        while self.peek() and self.peek() in valid_chars:
            digits.append(self.peek())
            self.advance()
        if not digits: self.error(f"Invalid base-{base} number")
        return int(''.join(digits), base)

    def read_decimal(self):
        chars = []
        if self.peek() == '.':
            chars.append('.')
            self.advance()
        
        while self.peek() and self.peek().isdigit():
            chars.append(self.peek())
            self.advance()
            
        if self.peek() == '.' and chars and chars[0] != '.':
            if self.peek(1) == '.': self.error("Range operator '..' not allowed")
            chars.append('.')
            self.advance()
            while self.peek() and self.peek().isdigit():
                chars.append(self.peek())
                self.advance()
        
        # Guard clauses for EOF checks on scientific notation
        ch = self.peek()
        if ch and ch in 'eE':
            chars.append(ch)
            self.advance()
            ch = self.peek()
            if ch and ch in '+-':
                chars.append(ch)
                self.advance()
            if not self.peek() or not self.peek().isdigit(): self.error("Invalid scientific notation")
            while self.peek() and self.peek().isdigit():
                chars.append(self.peek())
                self.advance()
                
        num_str = ''.join(chars)
        return float(num_str) if '.' in num_str or 'e' in num_str.lower() else int(num_str)

    def read_identifier(self):
        chars = []
        if not self.peek() or not (self.peek().isalpha() or self.peek() in '_$'):
            self.error(f"Invalid identifier start: {self.peek()}")
        while self.peek() and (self.peek().isalnum() or self.peek() in '_$'):
            chars.append(self.peek())
            self.advance()
        return ''.join(chars)

    def measure_indent(self):
        indent = 0
        indent_chars = []
        # Guard clause for EOF check
        while self.peek() and self.peek() in ' \t':
            indent_chars.append(self.peek())
            self.advance()
            indent += 1
            
        if not self.peek() or self.peek() == '#' or self.peek() == '\n':
            return []
            
        # Strict Indent Logic
        if indent_chars:
            char_type = 'space' if indent_chars[0] == ' ' else 'tab'
            if any(('space' if c == ' ' else 'tab') != char_type for c in indent_chars):
                self.error("Mixed tabs and spaces")
            if self.indent_char is None: self.indent_char = char_type
            elif self.indent_char != char_type: self.error(f"Inconsistent indent character")

        current = self.indent_stack[-1]
        tokens = []
        
        if indent > current:
            if self.indent_unit is None: self.indent_unit = indent - current
            elif (indent - current) % self.indent_unit != 0:
                self.error(f"Inconsistent indentation (unit {self.indent_unit}, got {indent - current})")
            
            levels = (indent - current) // (self.indent_unit or 1)
            for _ in range(levels):
                self.indent_stack.append(self.indent_stack[-1] + (self.indent_unit or 1))
                tokens.append(Token(TokenType.INDENT, None, self.line, self.col))
        elif indent < current:
            if indent not in self.indent_stack: self.error("Dedent mismatch")
            while self.indent_stack[-1] > indent:
                self.indent_stack.pop()
                tokens.append(Token(TokenType.DEDENT, None, self.line, self.col))
        return tokens

    def tokenize(self):
        tokens = []
        at_line_start = True
        
        while self.pos < self.length:
            if at_line_start:
                tokens.extend(self.measure_indent())
                at_line_start = False
            
            self.skip_whitespace()
            if self.pos >= self.length: break
            
            ch = self.peek()
            # Comments
            if ch == '#':
                if self.peek(1) == '#' and self.peek(2) == '#':
                    self.advance(); self.advance(); self.advance()
                    self.skip_block_comment()
                else:
                    self.advance()
                    self.skip_line_comment()
                continue
                
            if ch == '\n':
                self.advance()
                tokens.append(Token(TokenType.NEWLINE, None, self.line, self.col))
                at_line_start = True
                continue
                
            token_map = {'{': TokenType.LBRACE, '}': TokenType.RBRACE, 
                         '[': TokenType.LBRACKET, ']': TokenType.RBRACKET, 
                         ':': TokenType.COLON, ',': TokenType.COMMA}
                         
            if ch in token_map:
                self.advance()
                tokens.append(Token(token_map[ch], ch, self.line, self.col))
                continue
                
            if ch in '"\'':
                self.advance()
                tokens.append(Token(TokenType.STRING, self.read_string(ch), self.line, self.col))
                continue
                
            if ch.isdigit() or (ch == '.' and self.peek(1) and self.peek(1).isdigit()):
                tokens.append(Token(TokenType.NUMBER, self.read_number(), self.line, self.col))
                continue
            if ch == '-' and self.peek(1) and (self.peek(1).isdigit() or self.peek(1) == '.'):
                tokens.append(Token(TokenType.NUMBER, self.read_number(), self.line, self.col))
                continue
                
            if ch.isalpha() or ch in '_$':
                ident = self.read_identifier()
                keyword_map = {
                    'true': (TokenType.TRUE, True), 'yes': (TokenType.TRUE, True), 'on': (TokenType.TRUE, True),
                    'false': (TokenType.FALSE, False), 'no': (TokenType.FALSE, False), 'off': (TokenType.FALSE, False),
                    'null': (TokenType.NULL, None)
                }
                if ident in keyword_map:
                    t_type, t_val = keyword_map[ident]
                    tokens.append(Token(t_type, t_val, self.line, self.col))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, ident, self.line, self.col))
                continue
                
            self.error(f"Unexpected character: {ch}")
            
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            tokens.append(Token(TokenType.DEDENT, None, self.line, self.col))
        tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return tokens

# ==========================================
# Parser
# ==========================================

class _CSONHParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        
    def error(self, message: str):
        token = self.current()
        raise ParseError(message, token.line, token.col)
        
    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]
    
    def peek(self, offset=0):
        pos = self.pos + offset
        return self.tokens[pos] if pos < len(self.tokens) else self.tokens[-1]
        
    def advance(self):
        if self.pos < len(self.tokens): self.pos += 1
        return self.current()
        
    def expect(self, token_type):
        if self.current().type != token_type:
            self.error(f"Expected {token_type.name}, got {self.current().type.name}")
        token = self.current()
        self.advance()
        return token
        
    def skip_newlines(self):
        while self.current().type == TokenType.NEWLINE: self.advance()

    def process_escapes(self, content):
        if '\\' not in content: return content
        res = []
        i = 0
        while i < len(content):
            ch = content[i]
            if ch == '\\':
                i += 1
                if i >= len(content): break
                esc = content[i]
                escapes = {'n':'\n', 'r':'\r', 't':'\t', '\\':'\\', "'":"'", '"':'"'}
                if esc in escapes: res.append(escapes[esc])
                elif esc == 'u':
                    if i+4 < len(content):
                        try: res.append(chr(int(content[i+1:i+5], 16))); i+=4
                        except: res.append('\\u'); res.append(content[i+1:i+5]); i+=4
                    else: res.append('\\u')
                else: res.append('\\'); res.append(esc)
            else: res.append(ch)
            i += 1
        return "".join(res)

    def dedent_string(self, quote_char, content):
        # Relaxed Dedent Logic: Check boundaries
        has_first = content.startswith('\n') or (content and content.split('\n', 1)[0].strip() == '')
        has_last = content.endswith('\n') or (content and content.rsplit('\n', 1)[-1].strip() == '')
        
        if has_last:
            if has_first and '\n' in content: content = content.split('\n', 1)[1]
            if '\n' in content:
                last_nl = content.rfind('\n')
                closing_indent = len(content[last_nl+1:])
                if content[last_nl+1:].strip() == '':
                    content = content[:last_nl]
                    lines = content.split('\n')
                    dedented = []
                    for line in lines:
                        if line == '': dedented.append(line)
                        elif line.startswith(' ' * closing_indent): dedented.append(line[closing_indent:])
                        elif line.startswith('\t' * closing_indent): dedented.append(line[closing_indent:])
                        else: dedented.append(line)
                    content = '\n'.join(dedented)
        
        return self.process_escapes(content)

    def parse_value(self):
        token = self.current()
        if token.type == TokenType.STRING:
            val = token.value
            self.advance()
            if isinstance(val, tuple) and val[0] == 'TRIPLE_QUOTED':
                return self.dedent_string(val[1], val[2])
            return val
        if token.type == TokenType.NUMBER: self.advance(); return token.value
        if token.type in (TokenType.TRUE, TokenType.FALSE): self.advance(); return token.value
        if token.type == TokenType.NULL: self.advance(); return None
        if token.type == TokenType.LBRACE: return self.parse_braced_object()
        if token.type == TokenType.LBRACKET: return self.parse_array()
        if token.type == TokenType.IDENTIFIER: self.error(f"Bareword '{token.value}' rejected as value")
        self.error(f"Expected value, got {token.type.name}")

    def parse_key(self):
        token = self.current()
        if token.type == TokenType.STRING:
            key = token.value
            self.advance()
            if isinstance(key, tuple) and key[0] == 'TRIPLE_QUOTED': return self.dedent_string(key[1], key[2])
            return key
        if token.type == TokenType.IDENTIFIER: self.advance(); return token.value
        self.error(f"Expected key, got {token.type.name}")

    def parse_braced_object(self):
        self.expect(TokenType.LBRACE); self.skip_newlines()
        while self.current().type == TokenType.INDENT: self.advance()
        obj = {}
        while self.current().type != TokenType.RBRACE:
            if self.current().type == TokenType.EOF: self.error("Unclosed object")
            while self.current().type == TokenType.INDENT: self.advance()
            if self.current().type == TokenType.RBRACE: break
            
            key = self.parse_key()
            self.expect(TokenType.COLON); self.skip_newlines()
            
            # Check for structural INDENT before consuming cosmetic ones
            if self.current().type == TokenType.INDENT:
                obj[key] = self.parse_indented_object()
            elif self.current().type == TokenType.LBRACE:
                obj[key] = self.parse_braced_object()
            elif self.current().type == TokenType.LBRACKET:
                obj[key] = self.parse_array()
            else:
                # Skip cosmetic indents for scalar values
                while self.current().type == TokenType.INDENT: self.advance()
                obj[key] = self.parse_value()
            
            self.skip_newlines()
            while self.current().type == TokenType.DEDENT: self.advance()
            
            # STRICT SEPARATION CHECK
            if self.current().type == TokenType.COMMA: 
                self.advance()
                self.skip_newlines()
            elif self.current().type == TokenType.NEWLINE: 
                self.skip_newlines()
            elif self.current().type != TokenType.RBRACE:
                self.error("Expected comma or newline between object entries")
            
        while self.current().type == TokenType.DEDENT: self.advance()
        self.expect(TokenType.RBRACE)
        return obj

    def parse_array(self):
        self.expect(TokenType.LBRACKET); self.skip_newlines()
        while self.current().type == TokenType.INDENT: self.advance()
        arr = []
        while self.current().type != TokenType.RBRACKET:
            if self.current().type == TokenType.EOF: self.error("Unclosed array")
            while self.current().type == TokenType.INDENT: self.advance()
            if self.current().type == TokenType.RBRACKET: break
            
            arr.append(self.parse_value())
            self.skip_newlines()
            while self.current().type == TokenType.DEDENT: self.advance()
            
            # STRICT SEPARATION CHECK
            if self.current().type == TokenType.COMMA: 
                self.advance()
                self.skip_newlines()
            elif self.current().type == TokenType.NEWLINE: 
                self.skip_newlines()
            elif self.current().type != TokenType.RBRACKET:
                self.error("Expected comma or newline between array elements")
            
        while self.current().type == TokenType.DEDENT: self.advance()
        self.expect(TokenType.RBRACKET)
        return arr

    def parse_indented_object(self):
        obj = {}
        self.expect(TokenType.INDENT); self.skip_newlines()
        while self.current().type not in (TokenType.DEDENT, TokenType.EOF):
            key = self.parse_key()
            self.expect(TokenType.COLON); self.skip_newlines()
            
            if self.current().type == TokenType.INDENT: val = self.parse_indented_object()
            elif self.current().type == TokenType.LBRACE: val = self.parse_braced_object()
            elif self.current().type == TokenType.LBRACKET: val = self.parse_array()
            else: val = self.parse_value()
            
            obj[key] = val
            self.skip_newlines()
        if self.current().type == TokenType.DEDENT: self.advance()
        return obj

    def parse(self):
        self.skip_newlines()
        if self.current().type == TokenType.EOF: return {}
        
        if self.current().type == TokenType.LBRACKET: 
            res = self.parse_array()
            self.skip_newlines()
            if self.current().type != TokenType.EOF: self.error("Trailing junk after top-level array")
            return res
            
        if self.current().type == TokenType.LBRACE: 
            res = self.parse_braced_object()
            self.skip_newlines()
            if self.current().type != TokenType.EOF: self.error("Trailing junk after top-level object")
            return res
        
        is_kv = False
        if self.current().type in (TokenType.IDENTIFIER, TokenType.STRING):
            if self.peek(1).type == TokenType.COLON: is_kv = True
        
        if not is_kv and self.current().type not in (TokenType.LBRACE, TokenType.LBRACKET):
             self.error("Root must be object or array")

        obj = {}
        while self.current().type != TokenType.EOF:
            if self.current().type in (TokenType.IDENTIFIER, TokenType.STRING):
                key = self.parse_key()
                self.expect(TokenType.COLON); self.skip_newlines()
                if self.current().type == TokenType.INDENT: val = self.parse_indented_object()
                elif self.current().type == TokenType.LBRACE: val = self.parse_braced_object()
                elif self.current().type == TokenType.LBRACKET: val = self.parse_array()
                else: val = self.parse_value()
                obj[key] = val
                self.skip_newlines()
            else: break
            
        # TOP LEVEL SEAL: Check for trailing junk after implicit object loop
        if self.current().type != TokenType.EOF:
             self.error("Unexpected content at top level")
             
        return obj

# ==========================================
# Public API
# ==========================================

def loads(source: str) -> Union[dict, list]:
    """Parse CSONH source string."""
    lexer = _CSONHLexer(source)
    parser = _CSONHParser(lexer.tokenize())
    return parser.parse()

def load(fp: TextIO) -> Union[dict, list]:
    """Parse CSONH from a file-like object."""
    return loads(fp.read())
