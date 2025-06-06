from lark import Lark, Transformer
from lark import v_args

with open("grammar.lark") as f:
    grammar = f.read()

parser = Lark(grammar, parser="lalr")

class Interpreter(Transformer):
    def __init__(self):
        self.env = {}
        self.types = {}

    def decl_stmt(self, items):
        name = str(items[0])
        value = items[1]
        typ = str(items[2])
        if typ == "int" and not isinstance(value, int):
            raise TypeError(f"{name} must be int")
        self.env[name] = value
        self.types[name] = typ

    def assign_stmt(self, items):
        name = str(items[0])
        value = items[1]
        if name not in self.env:
            raise NameError(f"{name} not declared")
        expected_type = self.types[name]
        if expected_type == "int" and not isinstance(value, int):
            raise TypeError(f"{name} must be int")
        self.env[name] = value

    def expr_stmt(self, items):
        _ = items[0]  # We evaluate but don't use the result

    def print_stmt(self, items):
        value = items[0]
        print(value)

    def if_stmt(self, items):
        cond = items[0]
        then_block = items[1:-1]
        else_block = items[-1]
        block = then_block if cond else else_block
        for stmt in block:
            if callable(stmt):
                stmt()

    def condition(self, items):
        left, op_token, right = items
        op = str(op_token)
        return {
            "==": left == right,
            "!=": left != right,
            ">": left > right,
            "<": left < right,
            ">=": left >= right,
            "<=": left <= right
        }[op]


    # def comparator(self, children):
    #     print("comparator children:", children)
    #     return str(children[0])

    def add(self, items): return items[0] + items[1]
    def sub(self, items): return items[0] - items[1]
    def mul(self, items): return items[0] * items[1]
    def div(self, items): return items[0] // items[1]

    def number(self, token): return int(token[0])
    def var(self, token):
        name = str(token[0])
        if name not in self.env:
            raise NameError(f"{name} is not defined")
        return self.env[name]

def run(code):
    tree = parser.parse(code)
    interp = Interpreter()
    interp.transform(tree)

if __name__ == "__main__":
    code = """
        let a = 3 int;
        print(a);
        a=a+2;
        if (a > 2) {
            print(a * 2);
        }
        print(a + 2);
    """
    run(code)
