from lark import Lark, Transformer, v_args, exceptions, Tree, Token
import llvmlite.ir as ir
import llvmlite.binding as llvm
from typing import Dict, Any, Union
import sys

class CompilerError(Exception):
    """Custom exception for compiler errors"""
    pass

class TypeMismatchError(CompilerError):
    """Exception for type mismatches"""
    pass

class UndefinedVariableError(CompilerError):
    """Exception for undefined variables"""
    pass

class InvalidOperationError(CompilerError):
    """Exception for invalid operations"""
    pass

class LLVMCodeGenerator(Transformer):
    def __init__(self):
        self.module = ir.Module(name="program")
        self.builder = None
        self.func = None
        self.variables = {}  # Maps variable names to (LLVM value, type)
        self.types = {
            'int': ir.IntType(32),
            'float': ir.DoubleType(),
            'bool': ir.IntType(1),
            'str': ir.PointerType(ir.IntType(8))  # Strings as i8*
        }
        self.printf = None
        self.block_stack = []  # For tracking loop blocks

    def _init_main_function(self):
        """Initialize the main function in the LLVM module"""
        func_type = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_type, name="main")
        entry_block = self.func.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry_block)

        # Declare printf function
        printf_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
        self.printf = ir.Function(self.module, printf_type, name="printf")

    def program(self, tree):
        self._init_main_function()
        for stmt in tree.children:
            self.visit(stmt)
        # Return 0 from main
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(ir.IntType(32), 0))
        return self.module

    def statement(self, tree):
        return self.visit(tree.children[0])

    def declaration(self, tree):
        var_name = str(tree.children[0])
        value = self.visit(tree.children[1])
        type_name = str(tree.children[2])

        if var_name in self.variables:
            raise CompilerError(f"Variable '{var_name}' is already declared")

        llvm_type = self.types.get(type_name)
        if not llvm_type:
            raise CompilerError(f"Unknown type '{type_name}'")

        # Allocate memory for the variable
        ptr = self.builder.alloca(llvm_type, name=var_name)
        # Ensure value type matches declared type
        if value.type != llvm_type:
            raise TypeMismatchError(f"Type mismatch for '{var_name}': expected {type_name}, got {value.type}")
        self.builder.store(value, ptr)
        self.variables[var_name] = (ptr, llvm_type)
        return None

    def assignment(self, tree):
        var_name = str(tree.children[0])
        value = self.visit(tree.children[1])

        if var_name not in self.variables:
            raise UndefinedVariableError(f"Variable '{var_name}' is not defined")

        ptr, var_type = self.variables[var_name]
        if value.type != var_type:
            raise TypeMismatchError(f"Type mismatch for '{var_name}': expected {var_type}, got {value.type}")
        self.builder.store(value, ptr)
        return None

    def print_statement(self, tree):
        if not tree.children:
            # Empty print statement
            fmt = ir.Constant(ir.ArrayType(ir.IntType(8), 1), bytearray(b"\n\0"))
            fmt_ptr = self.builder.alloca(fmt.type)
            self.builder.store(fmt, fmt_ptr)
            fmt_ptr = self.builder.bitcast(fmt_ptr, ir.PointerType(ir.IntType(8)))
            self.builder.call(self.printf, [fmt_ptr])
            return None

        print_args_node = tree.children[0]
        for arg in print_args_node.children:
            value = self.visit(arg)
            if isinstance(value.type, ir.IntType) and value.type.width == 1:  # Boolean
                fmt = ir.Constant(ir.ArrayType(ir.IntType(8), 6), bytearray(b"%d\n\0"))
                fmt_ptr = self.builder.alloca(fmt.type)
                self.builder.store(fmt, fmt_ptr)
                fmt_ptr = self.builder.bitcast(fmt_ptr, ir.PointerType(ir.IntType(8)))
                self.builder.call(self.printf, [fmt_ptr, value])
            elif isinstance(value.type, ir.IntType):  # Integer
                fmt = ir.Constant(ir.ArrayType(ir.IntType(8), 6), bytearray(b"%d\n\0"))
                fmt_ptr = self.builder.alloca(fmt.type)
                self.builder.store(fmt, fmt_ptr)
                fmt_ptr = self.builder.bitcast(fmt_ptr, ir.PointerType(ir.IntType(8)))
                self.builder.call(self.printf, [fmt_ptr, value])
            elif isinstance(value.type, ir.DoubleType):  # Float
                fmt = ir.Constant(ir.ArrayType(ir.IntType(8), 6), bytearray(b"%f\n\0"))
                fmt_ptr = self.builder.alloca(fmt.type)
                self.builder.store(fmt, fmt_ptr)
                fmt_ptr = self.builder.bitcast(fmt_ptr, ir.PointerType(ir.IntType(8)))
                self.builder.call(self.printf, [fmt_ptr, value])
            elif isinstance(value.type, ir.PointerType):  # String
                fmt = ir.Constant(ir.ArrayType(ir.IntType(8), 4), bytearray(b"%s\0"))
                fmt_ptr = self.builder.alloca(fmt.type)
                self.builder.store(fmt, fmt_ptr)
                fmt_ptr = self.builder.bitcast(fmt_ptr, ir.PointerType(ir.IntType(8)))
                self.builder.call(self.printf, [fmt_ptr, value])
        return None

    def print_args(self, tree):
        return tree

    def if_statement(self, tree):
        condition = self.visit(tree.children[0])
        if condition.type != ir.IntType(1):
            raise TypeMismatchError("If condition must be boolean")

        with self.builder.if_else(condition) as (then, otherwise):
            with then:
                self.visit(tree.children[1])
            with otherwise:
                if len(tree.children) > 2:
                    self.visit(tree.children[2])
        return None

    def while_statement(self, tree):
        # Create blocks
        cond_block = self.func.append_basic_block("while_cond")
        body_block = self.func.append_basic_block("while_body")
        exit_block = self.func.append_basic_block("while_exit")

        # Branch to condition block
        self.builder.branch(cond_block)

        # Condition block
        self.builder.position_at_end(cond_block)
        condition = self.visit(tree.children[0])
        if condition.type != ir.IntType(1):
            raise TypeMismatchError("While condition must be boolean")
        self.block_stack.append((cond_block, exit_block))
        self.builder.cbranch(condition, body_block, exit_block)

        # Body block
        self.builder.position_at_end(body_block)
        self.visit(tree.children[1])
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        # Position builder at exit block
        self.builder.position_at_end(exit_block)
        self.block_stack.pop()
        return None

    def block(self, tree):
        for stmt in tree.children:
            self.visit(stmt)
        return None

    def add(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._arithmetic_op(left, right, "add")

    def sub(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._arithmetic_op(left, right, "sub")

    def mul(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._arithmetic_op(left, right, "mul")

    def div(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._arithmetic_op(left, right, "div")

    def mod(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._arithmetic_op(left, right, "mod")

    def eq(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, "eq")

    def ne(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, "ne")

    def lt(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, "lt")

    def le(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, "le")

    def gt(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, "gt")

    def ge(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return self._comparison_op(left, right, "ge")

    def and_op(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        if left.type != ir.IntType(1) or right.type != ir.IntType(1):
            raise TypeMismatchError("Logical AND requires boolean operands")
        return self.builder.and_(left, right)

    def or_op(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        if left.type != ir.IntType(1) or right.type != ir.IntType(1):
            raise TypeMismatchError("Logical OR requires boolean operands")
        return self.builder.or_(left, right)

    def not_op(self, tree):
        operand = self.visit(tree.children[0])
        if operand.type != ir.IntType(1):
            raise TypeMismatchError("Logical NOT requires boolean operand")
        return self.builder.not_(operand)

    def neg(self, tree):
        operand = self.visit(tree.children[0])
        if not isinstance(operand.type, (ir.IntType, ir.DoubleType)):
            raise TypeMismatchError("Unary minus requires numeric operand")
        return self.builder.neg(operand)

    def pos(self, tree):
        operand = self.visit(tree.children[0])
        if not isinstance(operand.type, (ir.IntType, ir.DoubleType)):
            raise TypeMismatchError("Unary plus requires numeric operand")
        return operand

    def number(self, tree):
        n = tree.children[0]
        try:
            return ir.Constant(ir.IntType(32), int(n))
        except ValueError:
            return ir.Constant(ir.DoubleType(), float(n))

    def string(self, tree):
        s = str(tree.children[0])[1:-1] + "\0"
        const = ir.Constant(ir.ArrayType(ir.IntType(8), len(s)), bytearray(s.encode('utf-8')))
        global_var = ir.GlobalVariable(self.module, const.type, name=f"str_{len(self.module.global_variables)}")
        global_var.initializer = const
        global_var.linkage = 'internal'
        return self.builder.bitcast(global_var, ir.PointerType(ir.IntType(8)))

    def boolean(self, tree):
        token = tree.children[0]
        return ir.Constant(ir.IntType(1), 1 if str(token).lower() == 'true' else 0)

    def variable(self, tree):
        var_name = str(tree.children[0])
        if var_name not in self.variables:
            raise UndefinedVariableError(f"Variable '{var_name}' is not defined")
        ptr, var_type = self.variables[var_name]
        return self.builder.load(ptr)

    def _arithmetic_op(self, left, right, op_name):
        if isinstance(left.type, ir.PointerType) or isinstance(right.type, ir.PointerType):
            if op_name == "add":
                # String concatenation
                if isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.PointerType):
                    raise CompilerError("String concatenation not supported in this compiler")
                raise TypeMismatchError(f"Cannot perform {op_name} on string operands")
        if left.type != right.type:
            raise TypeMismatchError(f"Type mismatch in {op_name}: {left.type} and {right.type}")
        if isinstance(left.type, ir.IntType):
            if op_name == "add":
                return self.builder.add(left, right)
            elif op_name == "sub":
                return self.builder.sub(left, right)
            elif op_name == "mul":
                return self.builder.mul(left, right)
            elif op_name == "div":
                return self.builder.sdiv(left, right)
            elif op_name == "mod":
                return self.builder.srem(left, right)
        elif isinstance(left.type, ir.DoubleType):
            if op_name == "add":
                return self.builder.fadd(left, right)
            elif op_name == "sub":
                return self.builder.fsub(left, right)
            elif op_name == "mul":
                return self.builder.fmul(left, right)
            elif op_name == "div":
                return self.builder.fdiv(left, right)
            elif op_name == "mod":
                raise InvalidOperationError("Modulo not supported for float")
        raise TypeMismatchError(f"Unsupported types for {op_name}")

    def _comparison_op(self, left, right, op_name):
        if left.type != right.type:
            if not (isinstance(left.type, (ir.IntType, ir.DoubleType)) and
                    isinstance(right.type, (ir.IntType, ir.DoubleType))):
                raise TypeMismatchError(f"Cannot compare {left.type} and {right.type}")
        if isinstance(left.type, (ir.IntType, ir.DoubleType)):
            if isinstance(left.type, ir.IntType):
                if op_name == "eq":
                    return self.builder.icmp_signed("==", left, right)
                elif op_name == "ne":
                    return self.builder.icmp_signed("!=", left, right)
                elif op_name == "lt":
                    return self.builder.icmp_signed("<", left, right)
                elif op_name == "le":
                    return self.builder.icmp_signed("<=", left, right)
                elif op_name == "gt":
                    return self.builder.icmp_signed(">", left, right)
                elif op_name == "ge":
                    return self.builder.icmp_signed(">=", left, right)
            else:
                if op_name == "eq":
                    return self.builder.fcmp_ordered("==", left, right)
                elif op_name == "ne":
                    return self.builder.fcmp_ordered("!=", left, right)
                elif op_name == "lt":
                    return self.builder.fcmp_ordered("<", left, right)
                elif op_name == "le":
                    return self.builder.fcmp_ordered("<=", left, right)
                elif op_name == "gt":
                    return self.builder.fcmp_ordered(">", left, right)
                elif op_name == "ge":
                    return self.builder.fcmp_ordered(">=", left, right)
        raise TypeMismatchError(f"Cannot compare {left.type} and {right.type}")

class LLVMCompiler:
    def __init__(self, grammar_file):
        with open(grammar_file, 'r') as f:
            grammar = f.read()
        self.parser = Lark(grammar, start='program', parser='earley')
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        self.target = llvm.Target.from_default_triple()
        self.target_machine = self.target.create_target_machine()
        self.execution_engine = None

    def compile(self, code, output_file="a.out"):
        try:
            tree = self.parser.parse(code)
            codegen = LLVMCodeGenerator()
            module = codegen.visit(tree)

            # Optimize the module
            pm = llvm.create_module_pass_manager()
            pm.add_dead_code_elimination_pass()
            pm.add_instruction_combining_pass()
            pm.run(module)

            # Write object file
            obj = self.target_machine.emit_object(module)
            with open(output_file, 'wb') as f:
                f.write(obj)
            return module, None
        except exceptions.LarkError as e:
            return None, f"Syntax Error: {str(e)}"
        except CompilerError as e:
            return None, f"Compiler Error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected Error: {str(e)}"

def main():
    compiler = LLVMCompiler('grammar.lark')
    print("LLVM Compiler - Type 'exit' to quit")
    print("Syntax:")
    print("  Declaration: let var = value type;")
    print("  Assignment: var = value;")
    print("  Print: print[expr] or print[expr1, expr2, ...];")
    print("  If statement: if [condition] [ statements ] else [ statements ]")
    print("  While loop: while [condition] [ statements ]")
    print()

    while True:
        try:
            code = input(">>> ")
            if code.strip().lower() == 'exit':
                break
            if code.strip():
                module, error = compiler.compile(code)
                if error:
                    print(f"Error: {error}")
                else:
                    print("Compiled successfully to 'a.out'")
                    print("LLVM IR:")
                    print(str(module))
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()