import sys
from lark import Lark, Transformer, Tree, Token
from llvmlite import ir, binding

binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

class LLVMCodeGen:
    def __init__(self):
        self.module = ir.Module(name="main_module")
        self.builder = None
        self.func = None
        
        # Symbol table for variables
        self.variables = {}
        
        self._create_main_function()
        
        self.types = {
            'int': ir.IntType(32),
            'float': ir.FloatType(),
            'str': ir.IntType(8).as_pointer(),
            'bool': ir.IntType(1)
        }
        
        self._create_printf()
    
    def _create_main_function(self):
        """Create the main function"""
        func_type = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_type, name="main")
        block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
    
    def _create_printf(self):
        """Create printf function declaration"""
        printf_ty = ir.FunctionType(ir.IntType(32), [ir.IntType(8).as_pointer()], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")
    
    def _get_llvm_type(self, type_name):
        """Convert type name to LLVM type"""
        return self.types.get(type_name, ir.IntType(32))
    
    def _create_format_string(self, value_type):
        """Create format string for printf based on type"""
        if value_type == ir.IntType(32):
            fmt = "%d\n"
        elif value_type == ir.FloatType():
            fmt = "%f\n"
        elif value_type == ir.IntType(1):
            fmt = "%d\n"
        elif isinstance(value_type, ir.PointerType) and value_type.pointee == ir.IntType(8):
            fmt = "%s\n"
        else:
            fmt = "%s\n"
        
        fmt_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt) + 1), bytearray(fmt.encode("utf8") + b'\0'))
        global_fmt = ir.GlobalVariable(self.module, fmt_str.type, name=f"fmt_{len(self.module.globals)}")
        global_fmt.linkage = 'internal'
        global_fmt.global_constant = True
        global_fmt.initializer = fmt_str
        
        return self.builder.bitcast(global_fmt, ir.IntType(8).as_pointer())
    
    def process_tree(self, tree):
        """Process the parse tree and generate LLVM IR"""
        self._process_node(tree)
        self.builder.ret(ir.Constant(ir.IntType(32), 0))
        return self.module
    
    def _process_node(self, node):
        """Process a parse tree node"""
        if isinstance(node, Token):
            return self._process_token(node)
        elif isinstance(node, Tree):
            return self._process_tree_node(node)
        else:
            return node
    
    def _process_token(self, token):
        """Process terminal tokens"""
        if token.type == 'SIGNED_NUMBER':
            if '.' in str(token):
                return ir.Constant(ir.FloatType(), float(token))
            else:
                return ir.Constant(ir.IntType(32), int(token))
        elif token.type == 'ESCAPED_STRING':
            string_val = str(token)[1:-1]  
            string_val = string_val.replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\').replace('\\"', '"')
            
            string_bytes = bytearray(string_val.encode('utf-8') + b'\0')
            string_const = ir.Constant(ir.ArrayType(ir.IntType(8), len(string_bytes)), string_bytes)
            
            global_str = ir.GlobalVariable(self.module, string_const.type, name=f"str_{len(self.module.globals)}")
            global_str.linkage = 'internal'
            global_str.global_constant = True
            global_str.initializer = string_const
            
            return self.builder.bitcast(global_str, ir.IntType(8).as_pointer())
        elif token.type == 'TRUE':
            return ir.Constant(ir.IntType(1), 1)
        elif token.type == 'FALSE':
            return ir.Constant(ir.IntType(1), 0)
        elif token.type == 'IDENTIFIER':
            return str(token)
        elif token.type == 'TYPE_NAME':
            return str(token)
        else:
            return str(token)
    
    def _process_tree_node(self, tree):
        """Process tree nodes based on their rule"""
        rule = tree.data
        children = [self._process_node(child) for child in tree.children]
        
        if rule == 'program':
            for child in children:
                pass  # Statements already processed
            return None
        
        elif rule == 'declaration':
            identifier = children[0]
            expr_value = children[1]
            type_name = children[2]
            
            llvm_type = self._get_llvm_type(type_name)
            var_ptr = self.builder.alloca(llvm_type, name=identifier)
            
            if expr_value.type != llvm_type:
                if llvm_type == ir.IntType(32) and expr_value.type == ir.FloatType():
                    expr_value = self.builder.fptosi(expr_value, llvm_type)
                elif llvm_type == ir.FloatType() and expr_value.type == ir.IntType(32):
                    expr_value = self.builder.sitofp(expr_value, llvm_type)
                elif llvm_type == ir.IntType(1):
                    expr_value = self.builder.icmp_signed('!=', expr_value, ir.Constant(expr_value.type, 0))
            
            self.builder.store(expr_value, var_ptr)
            self.variables[identifier] = var_ptr
            return None
        
        elif rule == 'assignment':
            identifier = children[0]
            expr_value = children[1]
            
            if identifier not in self.variables:
                raise NameError(f"Variable '{identifier}' not declared")
            
            var_ptr = self.variables[identifier]
            var_type = var_ptr.type.pointee
            
            if expr_value.type != var_type:
                if var_type == ir.IntType(32) and expr_value.type == ir.FloatType():
                    expr_value = self.builder.fptosi(expr_value, var_type)
                elif var_type == ir.FloatType() and expr_value.type == ir.IntType(32):
                    expr_value = self.builder.sitofp(expr_value, var_type)
                elif var_type == ir.IntType(1):
                    expr_value = self.builder.icmp_signed('!=', expr_value, ir.Constant(expr_value.type, 0))
            
            self.builder.store(expr_value, var_ptr)
            return None
        
        elif rule == 'print_statement':
            if children and children[0] is not None:
                print_args = children[0] if isinstance(children[0], list) else [children[0]]
                for arg in print_args:
                    if arg is not None:
                        fmt_ptr = self._create_format_string(arg.type)
                        self.builder.call(self.printf, [fmt_ptr, arg])
            return None
        
        elif rule == 'print_args':
            return [child for child in children if child is not None]
        
        elif rule == 'if_statement':
            condition = children[0]
            
            if condition.type != ir.IntType(1):
                condition = self.builder.icmp_signed('!=', condition, ir.Constant(condition.type, 0))
            
            then_bb = self.func.append_basic_block(name="if_then")
            else_bb = None
            if len(children) > 2:  # Has else block
                else_bb = self.func.append_basic_block(name="if_else")
            merge_bb = self.func.append_basic_block(name="if_merge")
            
            if else_bb:
                self.builder.cbranch(condition, then_bb, else_bb)
            else:
                self.builder.cbranch(condition, then_bb, merge_bb)
            
            self.builder.position_at_end(then_bb)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_bb)
            
            if else_bb:
                self.builder.position_at_end(else_bb)
                if not self.builder.block.is_terminated:
                    self.builder.branch(merge_bb)
            
            self.builder.position_at_end(merge_bb)
            return None
        
        elif rule == 'while_statement':
            loop_cond = self.func.append_basic_block(name="while_cond")
            loop_body = self.func.append_basic_block(name="while_body")
            loop_exit = self.func.append_basic_block(name="while_exit")

            self.builder.branch(loop_cond)

            self.builder.position_at_end(loop_cond)
            
            condition = self._process_node(tree.children[0])
            if condition.type != ir.IntType(1):
                condition = self.builder.icmp_signed('!=', condition, ir.Constant(condition.type, 0))
            self.builder.cbranch(condition, loop_body, loop_exit)

            self.builder.position_at_end(loop_body)
            self._process_node(tree.children[1])  
            if not self.builder.block.is_terminated:
                self.builder.branch(loop_cond)

            self.builder.position_at_end(loop_exit)
            return None

        
        elif rule == 'block':
            for child in children:
                pass  
            return None
        
        elif rule == 'variable':
            identifier = children[0]
            if identifier not in self.variables:
                raise NameError(f"Variable '{identifier}' not declared")
            var_ptr = self.variables[identifier]
            return self.builder.load(var_ptr, name=identifier)
        
        elif rule == 'number':
            return children[0]  
        
        elif rule == 'string':
            return children[0]  
        
        elif rule == 'boolean':
            return children[0]  
        
        elif rule == 'add':
            left, right = children[0], children[1]
            if left.type == ir.FloatType() or right.type == ir.FloatType():
                if left.type != ir.FloatType():
                    left = self.builder.sitofp(left, ir.FloatType())
                if right.type != ir.FloatType():
                    right = self.builder.sitofp(right, ir.FloatType())
                return self.builder.fadd(left, right)
            return self.builder.add(left, right)
        
        elif rule == 'sub':
            left, right = children[0], children[1]
            if left.type == ir.FloatType() or right.type == ir.FloatType():
                if left.type != ir.FloatType():
                    left = self.builder.sitofp(left, ir.FloatType())
                if right.type != ir.FloatType():
                    right = self.builder.sitofp(right, ir.FloatType())
                return self.builder.fsub(left, right)
            return self.builder.sub(left, right)
        
        elif rule == 'mul':
            left, right = children[0], children[1]
            if left.type == ir.FloatType() or right.type == ir.FloatType():
                if left.type != ir.FloatType():
                    left = self.builder.sitofp(left, ir.FloatType())
                if right.type != ir.FloatType():
                    right = self.builder.sitofp(right, ir.FloatType())
                return self.builder.fmul(left, right)
            return self.builder.mul(left, right)
        
        elif rule == 'div':
            left, right = children[0], children[1]
            if left.type == ir.FloatType() or right.type == ir.FloatType():
                if left.type != ir.FloatType():
                    left = self.builder.sitofp(left, ir.FloatType())
                if right.type != ir.FloatType():
                    right = self.builder.sitofp(right, ir.FloatType())
                return self.builder.fdiv(left, right)
            return self.builder.sdiv(left, right)
        
        elif rule == 'eq':
            left, right = children[0], children[1]
            if left.type == ir.FloatType() or right.type == ir.FloatType():
                if left.type != ir.FloatType():
                    left = self.builder.sitofp(left, ir.FloatType())
                if right.type != ir.FloatType():
                    right = self.builder.sitofp(right, ir.FloatType())
                return self.builder.fcmp_ordered('==', left, right)
            return self.builder.icmp_signed('==', left, right)
        
        elif rule == 'ne':
            left, right = children[0], children[1]
            if left.type == ir.FloatType() or right.type == ir.FloatType():
                if left.type != ir.FloatType():
                    left = self.builder.sitofp(left, ir.FloatType())
                if right.type != ir.FloatType():
                    right = self.builder.sitofp(right, ir.FloatType())
                return self.builder.fcmp_ordered('!=', left, right)
            return self.builder.icmp_signed('!=', left, right)
        
        elif rule == 'lt':
            left, right = children[0], children[1]
            if left.type == ir.FloatType() or right.type == ir.FloatType():
                if left.type != ir.FloatType():
                    left = self.builder.sitofp(left, ir.FloatType())
                if right.type != ir.FloatType():
                    right = self.builder.sitofp(right, ir.FloatType())
                return self.builder.fcmp_ordered('<', left, right)
            return self.builder.icmp_signed('<', left, right)
        
        elif rule == 'gt':
            left, right = children[0], children[1]
            if left.type == ir.FloatType() or right.type == ir.FloatType():
                if left.type != ir.FloatType():
                    left = self.builder.sitofp(left, ir.FloatType())
                if right.type != ir.FloatType():
                    right = self.builder.sitofp(right, ir.FloatType())
                return self.builder.fcmp_ordered('>', left, right)
            return self.builder.icmp_signed('>', left, right)
        
        elif rule == 'and_op':
            left, right = children[0], children[1]
            if left.type != ir.IntType(1):
                left = self.builder.icmp_signed('!=', left, ir.Constant(left.type, 0))
            if right.type != ir.IntType(1):
                right = self.builder.icmp_signed('!=', right, ir.Constant(right.type, 0))
            return self.builder.and_(left, right)
        
        elif rule == 'or_op':
            left, right = children[0], children[1]
            if left.type != ir.IntType(1):
                left = self.builder.icmp_signed('!=', left, ir.Constant(left.type, 0))
            if right.type != ir.IntType(1):
                right = self.builder.icmp_signed('!=', right, ir.Constant(right.type, 0))
            return self.builder.or_(left, right)
        
        elif rule == 'not_op':
            operand = children[0]
            if operand.type != ir.IntType(1):
                operand = self.builder.icmp_signed('!=', operand, ir.Constant(operand.type, 0))
            return self.builder.not_(operand)
        
        elif rule == 'neg':
            operand = children[0]
            if operand.type == ir.FloatType():
                return self.builder.fsub(ir.Constant(ir.FloatType(), 0.0), operand)
            return self.builder.sub(ir.Constant(ir.IntType(32), 0), operand)
        
        else:
            return children[0] if children else None

def main():
    if len(sys.argv) != 2:
        print("Usage: python llvm_compiler.py <source_file>")
        sys.exit(1)
    
    with open('grammar.lark', 'r') as f:
        grammar = f.read()
    
    with open(sys.argv[1], 'r') as f:
        source_code = f.read()
    
    try:
        parser = Lark(grammar, start='program')
        tree = parser.parse(source_code)
        
        codegen = LLVMCodeGen()
        module = codegen.process_tree(tree)
        
        print(str(module))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()