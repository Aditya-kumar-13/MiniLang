from lark import Lark, Transformer, v_args, exceptions, Tree, Token
from lark.visitors import Interpreter
import operator
from typing import Any, Dict, Union

class InterpreterError(Exception):
    """Custom exception for interpreter errors"""
    pass

class TypeMismatchError(InterpreterError):
    """Exception for type mismatches"""
    pass

class UndefinedVariableError(InterpreterError):
    """Exception for undefined variables"""
    pass

class InvalidOperationError(InterpreterError):
    """Exception for invalid operations"""
    pass

class LangInterpreter(Interpreter):
    def __init__(self):
        self.variables = {} 
        self.output = []  
        
    def program(self, tree):
        """Execute all statements in the program"""
        results = []
        for stmt in tree.children:
            result = self.visit(stmt)
            if result is not None:
                results.append(result)
        return results
    
    def statement(self, tree):
        """Handle individual statements"""
        return self.visit(tree.children[0])
    
    def declaration(self, tree):
        """Handle variable declarations: let var = value type;"""
        var_name = str(tree.children[0])
        value = self.visit(tree.children[1])
        type_name = str(tree.children[2])
        
        if var_name in self.variables:
            raise InterpreterError(f"Variable '{var_name}' is already declared")
        
        expected_type = type_name
        actual_type = self._get_type(value)
        
        if expected_type != actual_type:
            raise TypeMismatchError(
                f"Type mismatch for variable '{var_name}': expected {expected_type}, got {actual_type}"
            )
        
        self.variables[var_name] = {
            'value': value,
            'type': expected_type
        }
        
        return None 
    
    def assignment(self, tree):
        """Handle variable assignments: var = value;"""
        var_name = str(tree.children[0])
        value = self.visit(tree.children[1])
        
        if var_name not in self.variables:
            raise UndefinedVariableError(f"Variable '{var_name}' is not defined")
        
        expected_type = self.variables[var_name]['type']
        actual_type = self._get_type(value)
        
        if expected_type != actual_type:
            raise TypeMismatchError(
                f"Type mismatch for variable '{var_name}': expected {expected_type}, got {actual_type}"
            )
        
        self.variables[var_name]['value'] = value
        return None 
    
    def print_statement(self, tree):
        """Handle print statements: print(expr);"""
        if len(tree.children) == 0:
            output = ""
            print(output)
            self.output.append(output)
            return None  
        else:
            print_args_node = tree.children[0]
            values = []
            for child in print_args_node.children:
                value = self.visit(child)
                values.append(str(value))
            
            output = "".join(values)
            print(output)
            self.output.append(output)
            return None  
    
    def print_args(self, tree):
        """Handle print arguments - just pass through the children"""
        return tree
    
    def if_statement(self, tree):
        """Handle if-else statements"""
        if len(tree.children) == 0:
            raise InterpreterError("Empty if statement")
            
        condition = self.visit(tree.children[0])
        
        if not isinstance(condition, bool):
            raise TypeMismatchError("Condition in if statement must be boolean")
        
        if condition:
            if len(tree.children) > 1:
                if_block = tree.children[1]
                return self.visit(if_block)
            else:
                raise InterpreterError("If statement missing body")
        elif len(tree.children) > 2:
            else_block = tree.children[2]
            return self.visit(else_block)
        else:
            return None
    
    def block(self, tree):
        """Handle code blocks"""
        results = []
        for stmt in tree.children:
            result = self.visit(stmt)
            if result is not None:
                results.append(result)
        return results if results else None
    
    def add(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._arithmetic_op(left, right, operator.add, "+")
    
    def sub(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._arithmetic_op(left, right, operator.sub, "-")
    
    def mul(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._arithmetic_op(left, right, operator.mul, "*")
    
    def div(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        if right == 0:
            raise InvalidOperationError("Division by zero")
        return self._arithmetic_op(left, right, operator.truediv, "/")
    
    def mod(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        if right == 0:
            raise InvalidOperationError("Modulo by zero")
        return self._arithmetic_op(left, right, operator.mod, "%")
    
    def eq(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, operator.eq, "==")
    
    def ne(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, operator.ne, "!=")
    
    def lt(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, operator.lt, "<")
    
    def le(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, operator.le, "<=")
    
    def gt(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, operator.gt, ">")
    
    def ge(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, operator.ge, ">=")
    
    def and_op(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        if not isinstance(left, bool) or not isinstance(right, bool):
            raise TypeMismatchError("Logical operations require boolean operands")
        return left and right
    
    def or_op(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        if not isinstance(left, bool) or not isinstance(right, bool):
            raise TypeMismatchError("Logical operations require boolean operands")
        return left or right
    
    def not_op(self, tree):
        operand = self.visit(tree.children[0])
        if not isinstance(operand, bool):
            raise TypeMismatchError("Logical NOT requires boolean operand")
        return not operand
    
    def neg(self, tree):
        operand = self.visit(tree.children[0])
        if not isinstance(operand, (int, float)):
            raise TypeMismatchError("Unary minus requires numeric operand")
        return -operand
    
    def pos(self, tree):
        operand = self.visit(tree.children[0])
        if not isinstance(operand, (int, float)):
            raise TypeMismatchError("Unary plus requires numeric operand")
        return +operand
    
    def number(self, tree):
        n = tree.children[0]
        try:
            return int(n)
        except ValueError:
            return float(n)
    
    def string(self, tree):
        s = tree.children[0]
        return str(s)[1:-1]
    
    def boolean(self, tree):
        token = tree.children[0]
        return str(token).lower() == 'true'
    
    def variable(self, tree):
        name = tree.children[0]
        var_name = str(name)
        if var_name not in self.variables:
            raise UndefinedVariableError(f"Variable '{var_name}' is not defined")
        return self.variables[var_name]['value']
    
    def _get_type(self, value):
        """Get the type name of a value"""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "str"
        else:
            return "unknown"
    
    def _arithmetic_op(self, left, right, op, op_name):
        """Handle arithmetic operations with type checking"""
        if isinstance(left, str) or isinstance(right, str):
            if op_name == "+" and (isinstance(left, str) or isinstance(right, str)):
                return str(left) + str(right)
            else:
                raise TypeMismatchError(f"Cannot perform {op_name} on string operands")
        
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise TypeMismatchError(f"Arithmetic operation {op_name} requires numeric operands")
        
        result = op(left, right)
        
        if isinstance(left, int) and isinstance(right, int) and op_name != "/":
            return int(result)
        
        return result
    
    def _comparison_op(self, left, right, op, op_name):
        """Handle comparison operations with type checking"""
        if type(left) != type(right):
            if not ((isinstance(left, (int, float)) and isinstance(right, (int, float)))):
                raise TypeMismatchError(f"Cannot compare {self._get_type(left)} and {self._get_type(right)}")
        
        return op(left, right)
    
    def get_output(self):
        """Get all print outputs"""
        return self.output
    
    def clear_output(self):
        """Clear print outputs"""
        self.output = []

class LarkInterpreter:
    def __init__(self, grammar_file):
        """Initialize the interpreter with a grammar file"""
        with open(grammar_file, 'r') as f:
            grammar = f.read()
        
        self.parser = Lark(grammar, start='program', parser='earley')
        self.interpreter = LangInterpreter()
    
    def interpret(self, code):
        """Interpret the given code"""
        try:
            tree = self.parser.parse(code)
            
            result = self.interpreter.visit(tree)
            
            return result, None
            
        except exceptions.LarkError as e:
            return None, f"Syntax Error: {str(e)}"
        except InterpreterError as e:
            return None, f"Runtime Error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected Error: {str(e)}"
    
    def get_variables(self):
        """Get current variable state"""
        return self.interpreter.variables
    
    def get_output(self):
        """Get print outputs"""
        return self.interpreter.get_output()

def main():
    """Main function to run the interpreter"""
    interpreter = LarkInterpreter('grammar.lark')
    
    print("Lark Interpreter with Print Support - Type 'exit' to quit")
    print("Syntax:")
    print("  Declaration: let var = value type;")
    print("  Assignment: var = value;")
    print("  Print: print(expr) or print(expr1, expr2, ...);")
    print("  If statement: if (condition) [ statements ] else [ statements ]")
    print()
    
    while True:
        try:
            code = input(">>> ")
            if code.strip().lower() == 'exit':
                break
            
            if code.strip():
                result, error = interpreter.interpret(code)
                
                if error:
                    print(f"Error: {error}")
                else:
                    if result:
                        if isinstance(result, list):
                            for r in result:
                                if r is not None:
                                    if isinstance(r, list):
                                        for sub_r in r:
                                            if sub_r is not None:
                                                print(sub_r)
                                    else:
                                        print(r)
                        else:
                            print(result)
                
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()