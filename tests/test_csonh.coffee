# CSONH 1.0 Compliance Test Suite (CoffeeScript)
# Run with: coffee tests/test_csonh.coffee

CSONH = require '../csonh'
assert = require 'assert'

console.log "Running CSONH Compliance Tests..."
passed = 0
failed = 0

run = (name, testFn) ->
  try
    testFn()
    # console.log "  ✓ #{name}" # Uncomment for verbose
    passed++
  catch e
    console.error "  ✗ #{name} FAILED"
    console.error "    #{e.message}"
    failed++

# ==========================================
# 1. Basic Structures
# ==========================================

run "Empty Object", ->
  assert.deepStrictEqual CSONH.parse("{}"), {}
  assert.deepStrictEqual CSONH.parse(""), {}
  assert.deepStrictEqual CSONH.parse("# Comment"), {}

run "Basic Object", ->
  assert.deepStrictEqual CSONH.parse("key: 'value'"), {key: 'value'}

run "Implicit Structure", ->
  src = """
  server:
    host: 'localhost'
    port: 8080
  """
  assert.deepStrictEqual CSONH.parse(src), {server: {host: 'localhost', port: 8080}}

run "Arrays", ->
  assert.deepStrictEqual CSONH.parse("[1, 2, 3]"), [1, 2, 3]

# ==========================================
# 2. Strict Separation
# ==========================================

run "Reject Space Separated Array", ->
  assert.throws -> CSONH.parse("[1 2]")

run "Reject Space Separated Object", ->
  assert.throws -> CSONH.parse("{a:1 b:2}")

# ==========================================
# 3. Top-Level Seal
# ==========================================

run "Reject Trailing Junk", ->
  assert.throws -> CSONH.parse("key: 1\ngarbage")

run "Reject Trailing Junk Array", ->
  assert.throws -> CSONH.parse("[1, 2] junk")

# ==========================================
# 4. Strings & Dedenting
# ==========================================

run "Triple Quote Dedent", ->
  src = """
  msg: '''
    Line 1
    Line 2
    '''
  """
  # Note: CoffeeScript multiline string in test source preserves indent
  # CSONH parser removes it.
  assert.deepStrictEqual CSONH.parse(src), {msg: "Line 1\nLine 2"}

run "Triple Quote Immediate Dedent", ->
  src = "msg: '''Line 1\n  Line 2\n  '''"
  assert.deepStrictEqual CSONH.parse(src), {msg: "Line 1\nLine 2"}

# ==========================================
# 5. Numbers & Booleans
# ==========================================

run "Numbers", ->
  assert.deepStrictEqual CSONH.parse("i: 42"), {i: 42}
  assert.deepStrictEqual CSONH.parse("f: 3.14"), {f: 3.14}
  assert.deepStrictEqual CSONH.parse("h: 0xFF"), {h: 255}

run "Booleans Case Sensitive", ->
  assert.deepStrictEqual CSONH.parse("a: yes"), {a: true}
  assert.deepStrictEqual CSONH.parse("b: NO"), {b: "NO"}

# ==========================================
# 6. Security
# ==========================================

run "Reject Interpolation", ->
  assert.throws -> CSONH.parse('a: "val #{x}"')

run "Reject Arithmetic", ->
  assert.throws -> CSONH.parse("a: 1 + 2")

# Summary
console.log "---------------------------------------------------"
if failed == 0
  console.log "✨ ALL TESTS PASSED (#{passed}/#{passed})"
  process.exit 0
else
  console.log "💥 #{failed} TESTS FAILED"
  process.exit 1
