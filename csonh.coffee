# CSONH (Concise Structured Object Notation for Humanity) - V3 Runtime Loader
#
# A strict, data-only, zero-dependency parser for CSONH configuration files.
# Compatible with CSONH Standard 1.0.
#
# Usage:
#   CSONH = require './csonh'
#   data = CSONH.parse("key: 'value'")

# ==========================================
# Data Structures
# ==========================================

TokenType =
  INDENT: 'INDENT'
  DEDENT: 'DEDENT'
  NEWLINE: 'NEWLINE'
  STRING: 'STRING'
  NUMBER: 'NUMBER'
  TRUE: 'TRUE'
  FALSE: 'FALSE'
  NULL: 'NULL'
  IDENTIFIER: 'IDENTIFIER'
  LBRACE: 'LBRACE'
  RBRACE: 'RBRACE'
  LBRACKET: 'LBRACKET'
  RBRACKET: 'RBRACKET'
  COLON: 'COLON'
  COMMA: 'COMMA'
  EOF: 'EOF'

class Token
  constructor: (@type, @value, @line, @col) ->

class LexerError extends Error
  constructor: (message, line, col) ->
    super "Lexer error at #{line}:#{col}: #{message}"
    @name = 'LexerError'
    @line = line
    @col = col

class ParseError extends Error
  constructor: (message, line, col) ->
    super "Parse error at #{line}:#{col}: #{message}"
    @name = 'ParseError'
    @line = line
    @col = col

# ==========================================
# Lexer
# ==========================================

class _CSONHLexer
  constructor: (source) ->
    # Normalize CRLF
    @source = source.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
    if @source.charCodeAt(0) == 0xFEFF
      @source = @source.slice(1)
    
    @pos = 0
    @line = 1
    @col = 1
    @length = @source.length
    
    @indentStack = [0]
    @indentUnit = null
    @indentChar = null

  error: (message) ->
    throw new LexerError(message, @line, @col)

  peek: (offset = 0) ->
    pos = @pos + offset
    if pos >= @length then null else @source[pos]

  advance: ->
    if @pos >= @length then return null
    ch = @source[@pos]
    @pos++
    if ch == '\n'
      @line++
      @col = 1
    else
      @col++
    ch

  skipWhitespace: ->
    while @peek() in [' ', '\t']
      @advance()

  skipLineComment: ->
    while @peek() and @peek() != '\n'
      @advance()

  skipBlockComment: ->
    isBlockStyle = (@col - 3) <= 1
    startLine = @line
    startCol = @col
    
    while @pos < @length
      if @peek() == '#' and @peek(1) == '#' and @peek(2) == '#'
        @advance(); @advance(); @advance() # Consume ###
        if isBlockStyle
          while @peek() and @peek() != '\n'
            @advance()
        return
      @advance()
    @error "Unterminated block comment (started at #{startLine}:#{startCol})"

  readString: (quoteChar) ->
    startLine = @line
    startCol = @col - 1
    
    # Triple Quote Check
    if @peek() == quoteChar and @peek(1) == quoteChar
      @advance(); @advance()
      return @readTripleQuotedString(quoteChar, startLine, startCol)
    
    content = []
    while true
      ch = @peek()
      if ch == null then @error "Unterminated string"
      if ch == quoteChar
        @advance()
        break
      if ch == '\n' then @error "Newline in single-line string"
      
      # Reject Interpolation in Double Quotes
      if quoteChar == '"' and ch == '#' and @peek(1) == '{'
        @error "Interpolation \#{} not allowed in CSONH"
      
      if ch == '\\'
        @advance()
        content.push @readEscape()
      else
        content.push ch
        @advance()
    content.join('')

  readTripleQuotedString: (quoteChar, startLine, startCol) ->
    content = []
    while true
      ch = @peek()
      if ch == null then @error "Unterminated triple-quoted string (started at #{startLine}:#{startCol})"
      
      if ch == quoteChar and @peek(1) == quoteChar and @peek(2) == quoteChar
        @advance(); @advance(); @advance()
        break
      
      if quoteChar == '"' and ch == '#' and @peek(1) == '{'
        @error "Interpolation \#{} not allowed in CSONH"
      
      content.push ch
      @advance()
    
    { type: 'TRIPLE_QUOTED', quoteChar: quoteChar, content: content.join('') }

  readEscape: ->
    ch = @peek()
    if ch == null then @error "Incomplete escape sequence"
    @advance()
    escapes = { 'n': '\n', 'r': '\r', 't': '\t', '\\': '\\', "'": "'", '"': '"' }
    if ch of escapes then return escapes[ch]
    if ch == 'u' then return @readUnicodeEscape()
    @error "Invalid escape sequence: \\#{ch}"

  readUnicodeEscape: ->
    hexChars = []
    for i in [0...4]
      ch = @peek()
      if ch == null or !/[0-9a-fA-F]/.test(ch)
        @error "Invalid unicode escape"
      hexChars.push ch
      @advance()
    String.fromCharCode(parseInt(hexChars.join(''), 16))

  readNumber: ->
    start = @pos
    isNegative = false
    if @peek() == '-'
      isNegative = true
      @advance()
    
    if @peek() == '0'
      nxt = @peek(1)
      if nxt in ['x', 'X'] 
        @advance(); @advance()
        val = @readBase(16, /[0-9a-fA-F]/)
        return if isNegative then -val else val
      if nxt in ['b', 'B']
        @advance(); @advance()
        val = @readBase(2, /[01]/)
        return if isNegative then -val else val
      if nxt in ['o', 'O']
        @advance(); @advance()
        val = @readBase(8, /[0-7]/)
        return if isNegative then -val else val
      if nxt and /[0-9]/.test(nxt) then @error "Leading zeros not allowed"
    
    val = @readDecimal()
    if isNegative then -val else val

  readBase: (base, validRegex) ->
    digits = []
    while @peek() and validRegex.test(@peek())
      digits.push @peek()
      @advance()
    if digits.length == 0 then @error "Invalid base-#{base} number"
    parseInt(digits.join(''), base)

  readDecimal: ->
    chars = []
    if @peek() == '.'
      chars.push '.'
      @advance()
    
    while @peek() and /[0-9]/.test(@peek())
      chars.push @peek()
      @advance()
      
    if @peek() == '.' and chars.length > 0 and chars[0] != '.'
      if @peek(1) == '.' then @error "Range operator '..' not allowed"
      chars.push '.'
      @advance()
      while @peek() and /[0-9]/.test(@peek())
        chars.push @peek()
        @advance()
    
    ch = @peek()
    if ch in ['e', 'E']
      chars.push ch
      @advance()
      ch = @peek()
      if ch in ['+', '-']
        chars.push ch
        @advance()
      if not @peek() or not /[0-9]/.test(@peek()) then @error "Invalid scientific notation"
      while @peek() and /[0-9]/.test(@peek())
        chars.push @peek()
        @advance()
    
    numStr = chars.join('')
    if numStr.indexOf('.') != -1 or numStr.indexOf('e') != -1 or numStr.indexOf('E') != -1
      parseFloat(numStr)
    else
      parseInt(numStr, 10)

  readIdentifier: ->
    chars = []
    first = @peek()
    if not first or not (/[a-zA-Z_$]/.test(first))
      @error "Invalid identifier start: #{first}"
    
    while @peek() and /[a-zA-Z0-9_$]/.test(@peek())
      chars.push @peek()
      @advance()
    chars.join('')

  measureIndent: ->
    indent = 0
    indentChars = []
    while @peek() and @peek() in [' ', '\t']
      indentChars.push @peek()
      @advance()
      indent++
    
    if not @peek() or @peek() == '#' or @peek() == '\n'
      return []
      
    if indentChars.length > 0
      charType = if indentChars[0] == ' ' then 'space' else 'tab'
      for c in indentChars
        cType = if c == ' ' then 'space' else 'tab'
        if cType != charType then @error "Mixed tabs and spaces"
      
      if @indentChar == null then @indentChar = charType
      else if @indentChar != charType then @error "Inconsistent indent character"
    
    current = @indentStack[@indentStack.length - 1]
    tokens = []
    
    if indent > current
      if @indentUnit == null then @indentUnit = indent - current
      else if (indent - current) % @indentUnit != 0
        @error "Inconsistent indentation (unit #{@indentUnit}, got #{indent - current})"
      
      levels = (indent - current) / (@indentUnit or 1)
      for i in [0...levels]
        newLevel = @indentStack[@indentStack.length - 1] + (@indentUnit or 1)
        @indentStack.push newLevel
        tokens.push new Token(TokenType.INDENT, null, @line, @col)
        
    else if indent < current
      if indent not in @indentStack then @error "Dedent mismatch"
      while @indentStack[@indentStack.length - 1] > indent
        @indentStack.pop()
        tokens.push new Token(TokenType.DEDENT, null, @line, @col)
        
    tokens

  tokenize: ->
    tokens = []
    atLineStart = true
    
    while @pos < @length
      if atLineStart
        tokens = tokens.concat(@measureIndent())
        atLineStart = false
      
      @skipWhitespace()
      if @pos >= @length then break
      
      ch = @peek()
      
      if ch == '#'
        if @peek(1) == '#' and @peek(2) == '#'
          @advance(); @advance(); @advance()
          @skipBlockComment()
        else
          @advance()
          @skipLineComment()
        continue
      
      if ch == '\n'
        @advance()
        tokens.push new Token(TokenType.NEWLINE, null, @line, @col)
        atLineStart = true
        continue
      
      tokenMap = 
        '{': TokenType.LBRACE, '}': TokenType.RBRACE
        '[': TokenType.LBRACKET, ']': TokenType.RBRACKET
        ':': TokenType.COLON, ',': TokenType.COMMA
        
      if ch of tokenMap
        @advance()
        tokens.push new Token(tokenMap[ch], ch, @line, @col)
        continue
      
      if ch in ['"', "'"]
        @advance()
        tokens.push new Token(TokenType.STRING, @readString(ch), @line, @col)
        continue
      
      if /[0-9]/.test(ch) or (ch == '.' and @peek(1) and /[0-9]/.test(@peek(1)))
        tokens.push new Token(TokenType.NUMBER, @readNumber(), @line, @col)
        continue
        
      if ch == '-' and @peek(1) and (/[0-9]/.test(@peek(1)) or @peek(1) == '.')
        tokens.push new Token(TokenType.NUMBER, @readNumber(), @line, @col)
        continue
      
      if /[a-zA-Z_$]/.test(ch)
        ident = @readIdentifier()
        keywordMap =
          'true': [TokenType.TRUE, true], 'yes': [TokenType.TRUE, true], 'on': [TokenType.TRUE, true]
          'false': [TokenType.FALSE, false], 'no': [TokenType.FALSE, false], 'off': [TokenType.FALSE, false]
          'null': [TokenType.NULL, null]
          
        if ident of keywordMap
          [tType, tVal] = keywordMap[ident]
          tokens.push new Token(tType, tVal, @line, @col)
        else
          tokens.push new Token(TokenType.IDENTIFIER, ident, @line, @col)
        continue
      
      @error "Unexpected character: #{ch}"
      
    while @indentStack.length > 1
      @indentStack.pop()
      tokens.push new Token(TokenType.DEDENT, null, @line, @col)
    
    tokens.push new Token(TokenType.EOF, null, @line, @col)
    tokens

# ==========================================
# Parser
# ==========================================

class _CSONHParser
  constructor: (tokens) ->
    @tokens = tokens
    @pos = 0

  error: (message) ->
    token = @current()
    throw new ParseError(message, token.line, token.col)

  current: ->
    if @pos < @tokens.length then @tokens[@pos] else @tokens[@tokens.length - 1]

  peek: (offset = 0) ->
    pos = @pos + offset
    if pos < @tokens.length then @tokens[pos] else @tokens[@tokens.length - 1]

  advance: ->
    if @pos < @tokens.length then @pos++
    @current()

  expect: (tokenType) ->
    if @current().type != tokenType
      @error "Expected #{tokenType}, got #{@current().type}"
    token = @current()
    @advance()
    token

  skipNewlines: ->
    while @current().type == TokenType.NEWLINE
      @advance()

  processEscapes: (content) ->
    if content.indexOf('\\') == -1 then return content
    res = []
    i = 0
    len = content.length
    while i < len
      ch = content[i]
      if ch == '\\'
        i++
        if i >= len then break
        esc = content[i]
        escapes = {'n':'\n', 'r':'\r', 't':'\t', '\\':'\\', "'":"'", '"':'"'}
        if esc of escapes
          res.push escapes[esc]
        else if esc == 'u'
          if i + 4 < len
            try
              hex = content.substr(i + 1, 4)
              res.push String.fromCharCode(parseInt(hex, 16))
              i += 4
            catch
              res.push '\\u'
              res.push content.substr(i + 1, 4)
              i += 4
          else
            res.push '\\u'
        else
          res.push '\\'
          res.push esc
      else
        res.push ch
      i++
    res.join('')

  dedentString: (quoteChar, content) ->
    hasFirst = content.startsWith('\n') or (content.length > 0 and content.split('\n')[0].trim() == '')
    
    # Check last line
    lines = content.split('\n')
    lastLine = lines[lines.length - 1]
    hasLast = content.endsWith('\n') or (content.length > 0 and lastLine.trim() == '')
    
    if hasLast
      if hasFirst and content.indexOf('\n') != -1
        content = content.substring(content.indexOf('\n') + 1)
      
      if content.indexOf('\n') != -1
        lastNl = content.lastIndexOf('\n')
        closingIndent = content.length - lastNl - 1
        closingStr = content.substring(lastNl + 1)
        
        if closingStr.trim() == ''
          content = content.substring(0, lastNl)
          lines = content.split('\n')
          dedented = []
          for line in lines
            if line == ''
              dedented.push line
            else if line.startsWith(' '.repeat(closingIndent))
              dedented.push line.substring(closingIndent)
            else if line.startsWith('\t'.repeat(closingIndent))
              dedented.push line.substring(closingIndent)
            else
              dedented.push line
          content = dedented.join('\n')
    
    @processEscapes(content)

  parseValue: ->
    token = @current()
    if token.type == TokenType.STRING
      val = token.value
      @advance()
      if typeof val == 'object' and val.type == 'TRIPLE_QUOTED'
        return @dedentString(val.quoteChar, val.content)
      return val
    
    if token.type == TokenType.NUMBER
      @advance()
      return token.value
      
    if token.type in [TokenType.TRUE, TokenType.FALSE]
      @advance()
      return token.value
      
    if token.type == TokenType.NULL
      @advance()
      return null
      
    if token.type == TokenType.LBRACE
      return @parseBracedObject()
      
    if token.type == TokenType.LBRACKET
      return @parseArray()
      
    if token.type == TokenType.IDENTIFIER
      @error "Bareword '#{token.value}' rejected as value"
      
    @error "Expected value, got #{token.type}"

  parseKey: ->
    token = @current()
    if token.type == TokenType.STRING
      key = token.value
      @advance()
      if typeof key == 'object' and key.type == 'TRIPLE_QUOTED'
        return @dedentString(key.quoteChar, key.content)
      return key
      
    if token.type == TokenType.IDENTIFIER
      @advance()
      return token.value
      
    @error "Expected key, got #{token.type}"

  parseBracedObject: ->
    @expect TokenType.LBRACE; @skipNewlines()
    while @current().type == TokenType.INDENT then @advance()
    obj = {}
    
    while @current().type != TokenType.RBRACE
      if @current().type == TokenType.EOF then @error "Unclosed object"
      while @current().type == TokenType.INDENT then @advance()
      if @current().type == TokenType.RBRACE then break
      
      key = @parseKey()
      @expect TokenType.COLON; @skipNewlines()
      
      # Fixture 1 Fix: Check for INDENT
      if @current().type == TokenType.INDENT
        obj[key] = @parseIndentedObject()
      else if @current().type == TokenType.LBRACE
        obj[key] = @parseBracedObject()
      else if @current().type == TokenType.LBRACKET
        obj[key] = @parseArray()
      else
        while @current().type == TokenType.INDENT then @advance()
        obj[key] = @parseValue()
        
      @skipNewlines()
      while @current().type == TokenType.DEDENT then @advance()
      
      # STRICT SEPARATION CHECK
      if @current().type == TokenType.COMMA
        @advance(); @skipNewlines()
      else if @current().type == TokenType.NEWLINE
        @skipNewlines()
      else if @current().type != TokenType.RBRACE
        @error "Expected comma or newline between object entries"
        
    while @current().type == TokenType.DEDENT then @advance()
    @expect TokenType.RBRACE
    obj

  parseArray: ->
    @expect TokenType.LBRACKET; @skipNewlines()
    while @current().type == TokenType.INDENT then @advance()
    arr = []
    
    while @current().type != TokenType.RBRACKET
      if @current().type == TokenType.EOF then @error "Unclosed array"
      while @current().type == TokenType.INDENT then @advance()
      if @current().type == TokenType.RBRACKET then break
      
      arr.push @parseValue()
      @skipNewlines()
      
      while @current().type == TokenType.DEDENT then @advance()
      
      # STRICT SEPARATION CHECK
      if @current().type == TokenType.COMMA
        @advance(); @skipNewlines()
      else if @current().type == TokenType.NEWLINE
        @skipNewlines()
      else if @current().type != TokenType.RBRACKET
        @error "Expected comma or newline between array elements"
    
    while @current().type == TokenType.DEDENT then @advance()
    @expect TokenType.RBRACKET
    arr

  parseIndentedObject: ->
    obj = {}
    @expect TokenType.INDENT; @skipNewlines()
    
    while @current().type not in [TokenType.DEDENT, TokenType.EOF]
      key = @parseKey()
      @expect TokenType.COLON; @skipNewlines()
      
      if @current().type == TokenType.INDENT
        val = @parseIndentedObject()
      else if @current().type == TokenType.LBRACE
        val = @parseBracedObject()
      else if @current().type == TokenType.LBRACKET
        val = @parseArray()
      else
        val = @parseValue()
        
      obj[key] = val
      @skipNewlines()
      
    if @current().type == TokenType.DEDENT then @advance()
    obj

  parse: ->
    @skipNewlines()
    if @current().type == TokenType.EOF then return {}
    
    if @current().type == TokenType.LBRACKET
      res = @parseArray()
      @skipNewlines()
      if @current().type != TokenType.EOF then @error "Trailing junk after top-level array"
      return res
      
    if @current().type == TokenType.LBRACE
      res = @parseBracedObject()
      @skipNewlines()
      if @current().type != TokenType.EOF then @error "Trailing junk after top-level object"
      return res
      
    # Root key-value check
    isKv = false
    if @current().type in [TokenType.IDENTIFIER, TokenType.STRING]
      if @peek(1).type == TokenType.COLON then isKv = true
      
    if not isKv and @current().type not in [TokenType.LBRACE, TokenType.LBRACKET]
      @error "Root must be object or array"
      
    obj = {}
    while @current().type != TokenType.EOF
      if @current().type in [TokenType.IDENTIFIER, TokenType.STRING]
        key = @parseKey()
        @expect TokenType.COLON; @skipNewlines()
        
        if @current().type == TokenType.INDENT
          val = @parseIndentedObject()
        else if @current().type == TokenType.LBRACE
          val = @parseBracedObject()
        else if @current().type == TokenType.LBRACKET
          val = @parseArray()
        else
          val = @parseValue()
          
        obj[key] = val
        @skipNewlines()
      else
        break
    
    # TOP LEVEL SEAL
    if @current().type != TokenType.EOF
       @error "Unexpected content at top level"
    
    obj

# ==========================================
# Public API
# ==========================================

module.exports =
  parse: (source) ->
    lexer = new _CSONHLexer(source)
    tokens = lexer.tokenize()
    parser = new _CSONHParser(tokens)
    parser.parse()
  
  LexerError: LexerError
  ParseError: ParseError
