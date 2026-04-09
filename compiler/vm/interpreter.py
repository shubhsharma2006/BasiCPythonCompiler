from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from compiler.vm.bytecode import BytecodeFunction, BytecodeModule


class VMError(RuntimeError):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        super().__init__()
        self.value = value


class RaisedSignal(Exception):
    def __init__(self, value):
        super().__init__()
        self.value = value


@dataclass
class ModuleObject:
    name: str
    filename: str
    namespace: dict[str, object]


@dataclass
class Closure:
    function: BytecodeFunction
    closure_scopes: list[dict[str, object]]


@dataclass
class ClassObject:
    name: str
    methods: dict[str, BytecodeFunction]


@dataclass
class InstanceObject:
    class_object: ClassObject
    fields: dict[str, object] = field(default_factory=dict)


@dataclass
class BoundMethod:
    instance: InstanceObject | ModuleObject
    function: object


@dataclass
class TryHandler:
    target: int
    stack_depth: int


@dataclass
class Frame:
    module: ModuleObject
    function: BytecodeFunction
    globals: dict[str, object]
    locals: dict[str, object] = field(default_factory=dict)
    closure_scopes: list[dict[str, object]] = field(default_factory=list)
    stack: list[object] = field(default_factory=list)
    try_stack: list[TryHandler] = field(default_factory=list)
    ip: int = 0

    @property
    def is_module(self) -> bool:
        return self.function.name == "<module>"


class BytecodeInterpreter:
    def __init__(self, module_loader: Callable[[str, str], BytecodeModule] | None = None) -> None:
        self.output: list[str] = []
        self.module_loader = module_loader
        self.modules: dict[str, ModuleObject] = {}
        self.bytecode_modules: dict[str, BytecodeModule] = {}
        self.loading: set[str] = set()
        self.builtins: dict[str, object] = {
            "len": self._builtin_len,
            "range": self._builtin_range,
        }

    def run(self, module: BytecodeModule) -> str:
        try:
            self._execute_module(module)
        except RaisedSignal as signal:
            raise VMError(f"unhandled exception: {self._format_value(signal.value)}") from None
        return "\n".join(self.output) + ("\n" if self.output else "")

    def _execute_module(self, module: BytecodeModule) -> ModuleObject:
        existing = self.modules.get(module.filename)
        if existing is not None:
            return existing

        module_object = ModuleObject(name=module.name, filename=module.filename, namespace={})
        self.bytecode_modules[module.filename] = module
        for exported_name, function_key in module.top_level_bindings.items():
            module_object.namespace[exported_name] = module.functions[function_key]
        self.modules[module.filename] = module_object
        self.loading.add(module.filename)
        try:
            self._execute_function(module.entrypoint, [], module_object)
        finally:
            self.loading.discard(module.filename)
        return module_object

    def _execute_function(
        self,
        function: BytecodeFunction,
        args: list[object],
        module: ModuleObject,
        closure_scopes: list[dict[str, object]] | None = None,
    ):
        frame = Frame(module=module, function=function, globals=module.namespace, closure_scopes=list(closure_scopes or []))
        frame.locals.update(zip(function.params, args))
        try:
            while frame.ip < len(function.instructions):
                instruction = function.instructions[frame.ip]
                frame.ip += 1
                try:
                    self._execute_instruction(frame, instruction)
                except RaisedSignal as signal:
                    if not self._handle_exception(frame, signal):
                        raise
        except ReturnSignal as signal:
            return signal.value
        return None

    def _execute_instruction(self, frame: Frame, instruction) -> None:
        op = instruction.opcode
        arg = instruction.arg

        if op == "LOAD_CONST":
            frame.stack.append(arg)
            return
        if op == "LOAD_NAME":
            if arg in frame.locals:
                frame.stack.append(frame.locals[arg])
                return
            for scope in frame.closure_scopes:
                if arg in scope:
                    frame.stack.append(scope[arg])
                    return
            if arg in frame.globals:
                frame.stack.append(frame.globals[arg])
                return
            if arg in self.builtins:
                frame.stack.append(self.builtins[arg])
                return
            raise VMError(f"undefined name {arg!r}")
        if op == "STORE_NAME":
            value = frame.stack.pop()
            if frame.is_module:
                frame.globals[arg] = value
            else:
                frame.locals[arg] = value
            return
        if op == "POP_TOP":
            if frame.stack:
                frame.stack.pop()
            return
        if op == "BUILD_LIST":
            count = int(arg)
            values = [frame.stack.pop() for _ in range(count)]
            values.reverse()
            frame.stack.append(values)
            return
        if op == "BUILD_TUPLE":
            count = int(arg)
            values = [frame.stack.pop() for _ in range(count)]
            values.reverse()
            frame.stack.append(tuple(values))
            return
        if op == "BUILD_CLASS":
            class_name, method_specs = arg
            methods: dict[str, BytecodeFunction] = {}
            for method_name, function_key in method_specs:
                methods[method_name] = self._lookup_function(frame.module, function_key)
            frame.stack.append(ClassObject(name=class_name, methods=methods))
            return
        if op == "TRY_EXCEPT":
            frame.try_stack.append(TryHandler(target=int(arg), stack_depth=len(frame.stack)))
            return
        if op == "END_TRY":
            if frame.try_stack:
                frame.try_stack.pop()
            return
        if op == "GET_ITER":
            frame.stack.append(iter(frame.stack.pop()))
            return
        if op == "FOR_ITER":
            iterator = frame.stack[-1]
            try:
                frame.stack.append(next(iterator))
            except StopIteration:
                frame.stack.pop()
                frame.ip = int(arg)
            return
        if op == "BINARY_SUBSCR":
            index = frame.stack.pop()
            collection = frame.stack.pop()
            try:
                frame.stack.append(collection[index])
            except (IndexError, KeyError, TypeError) as exc:
                raise VMError(str(exc)) from None
            return
        if op == "LOAD_ATTR":
            obj = frame.stack.pop()
            frame.stack.append(self._load_attr(obj, arg))
            return
        if op == "STORE_ATTR":
            value = frame.stack.pop()
            obj = frame.stack.pop()
            self._store_attr(obj, arg, value)
            return
        if op == "BINARY_OP":
            right = frame.stack.pop()
            left = frame.stack.pop()
            frame.stack.append(self._binary_op(arg, left, right))
            return
        if op == "COMPARE_OP":
            right = frame.stack.pop()
            left = frame.stack.pop()
            frame.stack.append(self._compare_op(arg, left, right))
            return
        if op == "UNARY_OP":
            operand = frame.stack.pop()
            frame.stack.append(self._unary_op(arg, operand))
            return
        if op == "TO_BOOL":
            frame.stack.append(bool(frame.stack.pop()))
            return
        if op == "JUMP":
            frame.ip = int(arg)
            return
        if op == "JUMP_IF_FALSE":
            condition = frame.stack.pop()
            if not bool(condition):
                frame.ip = int(arg)
            return
        if op == "JUMP_IF_TRUE":
            condition = frame.stack.pop()
            if bool(condition):
                frame.ip = int(arg)
            return
        if op == "CALL_FUNCTION":
            func_name, argc = arg
            args = [frame.stack.pop() for _ in range(argc)]
            args.reverse()
            callable_obj = frame.locals.get(func_name, frame.globals.get(func_name))
            if callable_obj is None:
                for scope in frame.closure_scopes:
                    if func_name in scope:
                        callable_obj = scope[func_name]
                        break
            if callable_obj is None:
                callable_obj = self.builtins.get(func_name)
            if callable_obj is None:
                raise VMError(f"cannot call {func_name!r}")
            frame.stack.append(self._invoke_callable(callable_obj, args, frame.module))
            return
        if op == "CALL_METHOD":
            method_name, argc = arg
            args = [frame.stack.pop() for _ in range(argc)]
            args.reverse()
            obj = frame.stack.pop()
            callable_obj = self._load_attr(obj, method_name)
            frame.stack.append(self._invoke_callable(callable_obj, args, frame.module))
            return
        if op == "MAKE_FUNCTION":
            function = self._lookup_function(frame.module, arg)
            captured_scopes = [frame.locals, *frame.closure_scopes]
            frame.stack.append(Closure(function=function, closure_scopes=captured_scopes))
            return
        if op == "IMPORT_MODULE":
            frame.stack.append(self._import_module(arg, frame.module.filename))
            return
        if op == "IMPORT_FROM":
            module_name, export_name = arg
            module_object = self._import_module(module_name, frame.module.filename)
            if export_name not in module_object.namespace:
                raise VMError(f"module {module_name!r} has no attribute {export_name!r}")
            frame.stack.append(module_object.namespace[export_name])
            return
        if op == "PRINT":
            value = frame.stack.pop()
            self.output.append(self._format_value(value))
            return
        if op == "RAISE":
            raise RaisedSignal(frame.stack.pop() if frame.stack else None)
        if op == "RETURN_VALUE":
            raise ReturnSignal(frame.stack.pop() if frame.stack else None)

        raise VMError(f"unsupported opcode {op!r}")

    def _import_module(self, module_name: str, requester_filename: str) -> ModuleObject:
        if self.module_loader is None:
            raise VMError(f"cannot import {module_name!r} without a module loader")
        module = self.module_loader(module_name, requester_filename)
        if module.filename in self.loading:
            existing = self.modules.get(module.filename)
            if existing is not None:
                return existing
        return self._execute_module(module)

    def _lookup_function(self, module: ModuleObject, function_key: str) -> BytecodeFunction:
        loaded = self.bytecode_modules.get(module.filename)
        if loaded is None or function_key not in loaded.functions:
            raise VMError(f"unknown function {function_key!r}")
        return loaded.functions[function_key]

    def _handle_exception(self, frame: Frame, signal: RaisedSignal) -> bool:
        if not frame.try_stack:
            return False
        handler = frame.try_stack.pop()
        del frame.stack[handler.stack_depth:]
        frame.stack.append(signal.value)
        frame.ip = handler.target
        return True

    def _invoke_callable(self, callable_obj, args: list[object], module: ModuleObject):
        if isinstance(callable_obj, BytecodeFunction):
            return self._execute_function(callable_obj, args, module)
        if isinstance(callable_obj, Closure):
            return self._execute_function(callable_obj.function, args, module, callable_obj.closure_scopes)
        if isinstance(callable_obj, BoundMethod):
            if isinstance(callable_obj.function, BytecodeFunction):
                return self._execute_function(callable_obj.function, [callable_obj.instance, *args], module)
            if callable(callable_obj.function):
                return callable_obj.function(callable_obj.instance, *args)
            raise VMError("invalid bound method")
        if isinstance(callable_obj, ClassObject):
            instance = InstanceObject(class_object=callable_obj)
            initializer = callable_obj.methods.get("__init__")
            if initializer is not None:
                self._execute_function(initializer, [instance, *args], module)
            elif args:
                raise VMError(f"class {callable_obj.name!r} takes no arguments")
            return instance
        if callable(callable_obj):
            try:
                return callable_obj(*args)
            except TypeError as exc:
                raise VMError(str(exc)) from None
        raise VMError(f"cannot call {callable_obj!r}")

    def _load_attr(self, obj, attr_name: str):
        if isinstance(obj, ModuleObject):
            if attr_name not in obj.namespace:
                raise VMError(f"module {obj.name!r} has no attribute {attr_name!r}")
            return obj.namespace[attr_name]
        if isinstance(obj, InstanceObject):
            if attr_name in obj.fields:
                return obj.fields[attr_name]
            method = obj.class_object.methods.get(attr_name)
            if method is not None:
                return BoundMethod(instance=obj, function=method)
            raise VMError(f"instance of {obj.class_object.name!r} has no attribute {attr_name!r}")
        if isinstance(obj, ClassObject):
            method = obj.methods.get(attr_name)
            if method is not None:
                return method
            raise VMError(f"class {obj.name!r} has no attribute {attr_name!r}")
        raise VMError(f"cannot access attribute {attr_name!r} on {type(obj).__name__}")

    def _store_attr(self, obj, attr_name: str, value) -> None:
        if isinstance(obj, InstanceObject):
            obj.fields[attr_name] = value
            return
        if isinstance(obj, ModuleObject):
            obj.namespace[attr_name] = value
            return
        raise VMError(f"cannot set attribute {attr_name!r} on {type(obj).__name__}")

    @staticmethod
    def _builtin_range(*args):
        if len(args) not in {1, 2, 3}:
            raise VMError("range() expects 1 to 3 arguments")
        normalized: list[int] = []
        for index, value in enumerate(args, start=1):
            if not isinstance(value, int) or isinstance(value, bool):
                raise VMError(f"range() argument {index} must be int")
            normalized.append(value)
        return range(*normalized)

    @staticmethod
    def _builtin_len(*args):
        if len(args) != 1:
            raise VMError("len() expects exactly 1 argument")
        value = args[0]
        if not isinstance(value, (list, tuple, str)):
            raise VMError(f"len() expects a list, tuple, or string, got {type(value).__name__}")
        return len(value)

    @staticmethod
    def _binary_op(op: str, left, right):
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        if op == "%":
            return left % right
        raise VMError(f"unsupported binary operator {op!r}")

    @staticmethod
    def _compare_op(op: str, left, right):
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        raise VMError(f"unsupported comparison operator {op!r}")

    @staticmethod
    def _unary_op(op: str, operand):
        if op == "-":
            return -operand
        if op == "not":
            return not bool(operand)
        raise VMError(f"unsupported unary operator {op!r}")

    @staticmethod
    def _format_value(value) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, float):
            return f"{value:g}"
        if value is None:
            return "None"
        return str(value)
