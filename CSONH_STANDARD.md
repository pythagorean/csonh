# CSONH Specification

**Version:** 1.0  
**Date:** December 24, 2025  
**Status:** Stable

CSONH (Concise Structured Object Notation for Humanity) is a strict, data-only configuration format that combines JSON's clarity with YAML's readability. This document defines the complete specification for CSONH 1.0.

## Design Principles

1. **Data-Only**: No executable code, expressions, or dynamic evaluation
2. **Human-Readable**: Comments, optional commas, indentation-based structure
3. **Type-Safe**: Explicit type system with unambiguous parsing rules
4. **Safe by Default**: No surprises, no string interpolation, no code execution

## Document Structure

A CSONH document parses to either an **object** or an **array**.

**Valid top-level forms:**
```coffee
# Object (most common for configuration files)
host: 'localhost'
port: 8080

# Array
[1, 2, 3]

# Empty or comment-only files
# Result: {} (empty object)
```

**Not supported:** Single primitive values at document root (e.g., just `42` or `"hello"`). Documents must be structured as objects or arrays.

## Core Features

### Objects

**Indentation-based (implicit braces):**
```coffee
database:
  host: 'localhost'
  port: 5432
  credentials:
    user: 'admin'
    password: 'secret'
```

**Explicit braces:**
```coffee
{host: 'localhost', port: 5432}
```

**Newline-separated (commas optional):**
```coffee
{
  host: 'localhost'
  port: 5432
}
```

**Trailing commas allowed:**
```coffee
{a: 1, b: 2,}
```

### Arrays

**Comma-separated:**
```coffee
[1, 2, 3, 4, 5]
```

**Newline-separated (commas optional):**
```coffee
[
  'authentication'
  'caching'
  'logging'
]
```
*Note:* Items on the same line **must** be separated by commas. Whitespace-only separation (e.g., ```[1 2 3]```) 
is **not supported** to prevent ambiguity.

**Trailing commas allowed:**
```coffee
[1, 2, 3,]
```

### Primitive Values

#### Strings

**Single and double quotes:**
```coffee
name: 'MyApp'
description: "A simple application"
```

**Triple quotes for multiline (auto-dedenting):**
```coffee
message: '''
  This is a multiline string.
  Indentation is automatically removed.
  '''
```

**Supported escape sequences:**
- `\n` - newline
- `\r` - carriage return
- `\t` - tab
- `\\` - literal backslash
- `\'` - single quote
- `\"` - double quote
- `\uXXXX` - unicode character

#### Numbers

**Integers and floats:**
```coffee
count: 42
negative: -17
pi: 3.14159
percentage: .95
ratio: 5.
```

**Scientific notation:**
```coffee
large: 1.2e10
small: 1e-5
explicit: 1e+3
```

**Hexadecimal:**
```coffee
color: 0xFF5733
address: 0x1A2B
```

**Binary:**
```coffee
mask: 0b11110000
flags: 0B10101010
```

**Octal:**
```coffee
permissions: 0o755
mode: 0O644
```

**Leading zero rules:**
- `0` alone is valid (zero)
- `0.5` is valid (decimal)
- `0123` with no prefix is **invalid** (ambiguous)
- Use `0o123` for octal or `123` for decimal

#### Booleans

**Literal values:**
```coffee
enabled: true
disabled: false
```

**CoffeeScript aliases:**
```coffee
active: yes
inactive: no
power: on
standby: off
```

**Important:** Boolean keywords are **case-sensitive** and only recognized as exact lowercase matches. Any other form requires quoting:

```coffee
# Boolean values (bare, lowercase)
enabled: yes        # → true
disabled: no        # → false

# Strings (quoted)
country: 'NO'       # → "NO" (Norway country code)
answer: 'YES'       # → "YES" (string)
command: "on"       # → "on" (string, not boolean)
```

This design prevents the "Norway Problem" where `NO` might accidentally be parsed as `false`.

#### Null

```coffee
optional: null
```

### Comments

**Line comments:**
```coffee
# This is a comment
host: 'localhost'  # Inline comment
```

**Block comments:**
```coffee
###
Multi-line
block comment
###

config: ###inline### 'value'
```

**Comment behavior:**
- Line comments: `#` to end of line
- Block comments: `###...###` (non-nesting)
- Comments inside quoted strings are literal text

### Keys

**Bare identifiers:**
```coffee
simpleKey: 'value'
myKey: 'value'
_private: 'value'
$special: 'value'
```

Bare keys must start with a letter, underscore, or dollar sign, followed by letters, digits, underscores, or dollar signs.

**Quoted keys for special cases:**
```coffee
'key with spaces': 'value'
'my-hyphenated-key': 'value'
'123numeric': 'value'
"another-key": 'value'
```

Use quoted keys for:
- Spaces or special characters
- Keys starting with numbers  
- Hyphens or punctuation
- Reserved words as keys

### Indentation

**Indentation defines structure:**
```coffee
root:
  level1:
    level2: 'deep value'
```

**Rules:**
- Use **either** tabs **or** spaces (not mixed)
- First indent increase establishes the unit (e.g., 2 spaces, 4 spaces, 1 tab)
- All subsequent indents must be multiples of this unit
- Dedents must match a prior indentation level exactly
- Empty lines and comment-only lines don't affect indentation

**Valid examples:**
```coffee
# 2-space indentation
app:
  name: 'MyApp'
  config:
    debug: yes

# 4-space indentation
app:
    name: 'MyApp'
    config:
        debug: yes
```

**Invalid:** Mixing 2 and 3 spaces, or mixing tabs and spaces.

## Advanced Features

### Multiline String Dedenting

Triple-quoted strings automatically remove common leading whitespace:

```coffee
query: '''
  SELECT *
  FROM users
  WHERE active = true
  '''
```

Result: `"SELECT *\nFROM users\nWHERE active = true"`

**How it works:**
1. If the closing `'''` is on its own line, it defines the dedent level
2. That amount of whitespace is removed from each line
3. Windows line endings (`\r\n`) are normalized to `\n`

### Duplicate Keys

When the same key appears multiple times, the last value wins:

```coffee
{a: 1, a: 2}  # Result: {a: 2}
```

### UTF-8 and Line Endings

- **Encoding:** UTF-8 (BOM ignored if present)
- **Line endings:** Both `\n` (Unix) and `\r\n` (Windows) supported

## Safety Features

### No Code Execution

CSONH explicitly rejects all executable constructs:

**Arithmetic and expressions:**
```coffee
timeout: 5 * 60 * 1000  # ❌ REJECTED
result: 10 + 5          # ❌ REJECTED
```

**String interpolation:**
```coffee
name: "Hello #{user}"   # ❌ REJECTED (double quotes)
path: 'C:\#{dir}'       # ✓ ALLOWED (single quotes treat #{} as literal)
```

**Regular expressions:**
```coffee
pattern: /abc/          # ❌ REJECTED
```

**Ranges:**
```coffee
numbers: [1..10]        # ❌ REJECTED
```

**Bareword variables:**
```coffee
x: someVariable         # ❌ REJECTED
```

**Special values:**
```coffee
x: undefined            # ❌ REJECTED
x: NaN                  # ❌ REJECTED
x: Infinity             # ❌ REJECTED
```

### What IS Allowed

Only literal data values:
- Quoted strings (single, double, or triple)
- Numbers (integers, floats, hex, binary, octal)
- Booleans (`true`, `false`, `yes`, `no`, `on`, `off`)
- Null (`null`)
- Objects (with literal values)
- Arrays (with literal values)
- Comments

## Error Handling

CSONH parsers raise errors for:

- Mixed indentation (tabs and spaces)
- Inconsistent indent width
- Missing colons in key-value pairs
- Unmatched brackets or braces
- Unclosed strings, arrays, or objects
- Trailing content after valid structure
- Any rejected construct (expressions, interpolation, etc.)

## Compatibility

### With CoffeeScript

**Compatible:**
- Object and array syntax
- Comment syntax (`#` and `###...###`)
- Indentation rules
- Boolean aliases (`yes`/`no`/`on`/`off`)
- Number formats (hex, binary, octal)

**Diverges:**
- Triple-quoted strings auto-dedent in CSONH
- Booleans are case-sensitive in CSONH
- Expressions and operators rejected
- String interpolation rejected

### With YAML

**Advantages over YAML:**
- No ambiguous parsing (Norway Problem solved)
- No unintended type coercion
- No complex merge keys or anchors
- Explicit, predictable behavior

### With JSON

**Advantages over JSON:**
- Comments supported
- Trailing commas allowed
- Indentation-based structure (no braces required)
- Multiple number formats
- Multiline strings with auto-dedenting

## Validation

This specification is validated by a comprehensive test suite of 120 tests covering:

- All data types and edge cases
- Indentation behavior (2-space, 4-space, tabs, mixed, CRLF)
- Number formats (integers, floats, scientific notation, hex, binary, octal)
- String processing (escapes, multiline, dedenting)
- Comment behavior (line, block, nesting, inline)
- Boolean keywords (case-sensitivity, quoted vs. unquoted)
- Error cases (mixed indentation, bareword values, expressions)
- File edge cases (empty, comment-only, whitespace-only, BOM)
- Document structure (top-level forms, trailing content)

Every feature defined in this specification has corresponding test coverage.

## Implementation

Reference implementations are available in:
- **Python 3.7+** (`csonh.py`)
- **CoffeeScript/Node.js** (`csonh.coffee`)

Both implementations pass the complete validation suite and produce identical results.

## License

CSONH specification and reference implementations: MIT License

## Version History

**1.0** (December 24, 2025)
- Initial stable release
- Complete specification
- Reference implementations in Python and CoffeeScript
- 120-test validation suite

---

**The CSONH 1.0 specification is stable. The format will not change.**  
Bug reports and implementation improvements are welcome via GitHub issues.
