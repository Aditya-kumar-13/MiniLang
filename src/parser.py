from lark import Lark, Transformer, v_args, Visitor, Token, Tree

class DeclarationCollector(Visitor):
    def __init__(self):
        self.variables = {}
        self.declarations = []

    def assign_num(self, tree):
        name = str(tree.children[0])
        value_node = tree.children[1]
        typ = str(tree.children[2])
        if name in self.variables:
            raise ValueError(f"Variable '{name}' is already declared.")
        self.declarations.append((name, value_node, typ))


class Interpreter(Transformer):
    def __init__(self):
        self.variables = {}

    def start(self, items):
        for stmt in items:
            if callable(stmt):
                stmt()

    def process_declarations(self, declarations):
        for name, value_node, typ in declarations:
            if isinstance(value_node, Token):
                value = value_node.value
                try:
                    if typ == "int":
                        self.variables[name] = int(float(value))
                    elif typ == "float":
                        self.variables[name] = float(value)
                    elif typ == "bool":
                        self.variables[name] = value == "True"
                    elif typ == "str":
                        self.variables[name] = str(value.strip('"'))
                    elif typ == "char":
                        self.variables[name] = str(value)[0]
                except ValueError:
                    raise ValueError(f"Invalid value for type {typ}: {value}")
            else:
                value = self.transform(value_node)
                if typ == "int":
                    self.variables[name] = int(value)
                elif typ == "float":
                    self.variables[name] = float(value)
                elif typ == "bool":
                    self.variables[name] = bool(value)
                elif typ == "str":
                    self.variables[name] = str(value)
                elif typ == "char":
                    self.variables[name] = str(value)[0]

    def assign_num(self, _):
        return lambda: None  # already processed in DeclarationCollector

    def reassign(self, items):
        name = str(items[0])
        value = self.transform(items[1])
        if name not in self.variables:
            raise NameError(f"Variable '{name}' is not defined.")
        expected_type = type(self.variables[name])
        if not isinstance(value, expected_type):
            try:
                value = expected_type(value)
            except Exception:
                raise TypeError(f"Cannot assign type {type(value)} to {expected_type}")
        self.variables[name] = value
        return lambda: None

    def print_stmt(self, items):
        val = items[0]
        return lambda: print(val)

    def if_stmt(self, items):
        condition = items[0]
        stmts = items[1:]
        return lambda: [stmt() for stmt in stmts] if condition else None

    # Expression Operations
    @v_args(inline=True)
    def add(self, a, b): return a + b

    @v_args(inline=True)
    def sub(self, a, b): return a - b

    @v_args(inline=True)
    def mul(self, a, b): return a * b

    @v_args(inline=True)
    def div(self, a, b): return a / b

    @v_args(inline=True)
    def neg(self, a): return -a

    @v_args(inline=True)
    def lt(self, a, b): return a < b

    @v_args(inline=True)
    def lte(self, a, b): return a <= b

    @v_args(inline=True)
    def gt(self, a, b): return a > b

    @v_args(inline=True)
    def gte(self, a, b): return a >= b

    @v_args(inline=True)
    def eq(self, a, b): return a == b

    @v_args(inline=True)
    def neq(self, a, b): return a != b

    # Literals
    def true(self, _): return True
    def false(self, _): return False

    def NAME(self, token):
        name = str(token)
        if name in self.variables:
            return self.variables[name]
        raise NameError(f"Variable '{name}' not defined")

    def NUMBER(self, token):
        try:
            return int(token)
        except ValueError:
            return float(token)

    def STRING(self, token):
        return token[1:-1]  # remove quotes

    def CHARACTER(self, token):
        return token[1:-1]

# Load grammar
with open("grammar.lark") as f:
    grammar = f.read()

# Example program
code = """
let a = 10 as int
print(a)
"""

# Compile
parser = Lark(grammar, parser="lalr", start="start", lexer="contextual")
tree = parser.parse(code)

# Collect declarations
collector = DeclarationCollector()
collector.visit(tree)

# Interpret
interpreter = Interpreter()
interpreter.process_declarations(collector.declarations)
interpreter.transform(tree)
