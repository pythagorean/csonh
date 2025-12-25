# CSONH - Concise Structured Object Notation for Humanity

A strict, data-only configuration format that's easy to read and write. Zero dependencies.

**CSONH** = JSON's clarity + YAML's readability + strict safety guarantees.

## Quick Start

### Python

```python
import csonh

# From string
config = csonh.loads('''
server:
  host: 'localhost'
  port: 8080
  debug: yes
''')

# From file
with open('config.csonh', 'r') as f:
    config = csonh.load(f)
```

### CoffeeScript / Node.js

```coffeescript
CSONH = require('./csonh')

# From string
config = CSONH.parse '''
server:
  host: 'localhost'
  port: 8080
  debug: yes
'''

# From file (Node.js)
fs = require('fs')
source = fs.readFileSync('config.csonh', 'utf8')
config = CSONH.parse(source)
```

## Installation

### Direct Use (No Package Manager)

**Python:** Copy `csonh.py` to your project  
**CoffeeScript:** Copy `csonh.coffee` to your project

### Via Package Manager (Coming Soon)

**Python:** `pip install csonh`  
**Node.js:** `npm install csonh`

## Features

- **Human-friendly:** Indentation-based like Python/YAML
- **Type-safe:** Integers, floats, hex/binary/octal, booleans, null
- **Comments:** Line (`#`) and block (`###...###`)
- **Multiline strings:** Triple-quoted with auto-dedenting
- **Strict:** No code execution, no arithmetic, no surprises
- **Zero dependencies:** Single file, standard library only

## Example

```csonh
# Application configuration
app:
  name: 'MyApp'
  version: '1.2.3'

# Database settings
database:
  host: 'localhost'
  port: 5432
  pool:
    min: 2
    max: 10

# Feature flags
features: [
  'authentication',
  'caching',
  'logging'
]

# Environment-specific
production:
  debug: no
  workers: 8

development:
  debug: yes
  workers: 1
```

Result:
```python
{
  'app': {'name': 'MyApp', 'version': '1.2.3'},
  'database': {'host': 'localhost', 'port': 5432, 'pool': {'min': 2, 'max': 10}},
  'features': ['authentication', 'caching', 'logging'],
  'production': {'debug': False, 'workers': 8},
  'development': {'debug': True, 'workers': 1}
}
```

## What Makes CSONH Different

**Safe by design:**
- ❌ No string interpolation (`#{}`)
- ❌ No arithmetic expressions
- ❌ No code execution
- ❌ No bareword values
- ✅ Just data

**Precise behavior:**
- Unambiguous parsing (unlike YAML)
- Complete specification
- Consistent across implementations

## Language Support

- ✅ **Python 3.7+** - `csonh.py`
- ✅ **CoffeeScript/Node.js** - `csonh.coffee`

Both implementations pass the same 120-test validation suite.

## Documentation

Full specification: [`CSONH_STANDARD.md`](CSONH_STANDARD.md)

## License

MIT License - See [LICENSE](LICENSE) file

## Contributing

CSONH 1.0 specification is final and stable. The format will not change.

Bug reports and implementation improvements are welcome via GitHub issues.

## Credits

Developed in team collaboration with (in no particular order): 

Claude (Anthropic), ChatGPT (OpenAI), and Gemini (Google)
