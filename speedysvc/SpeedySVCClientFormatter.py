import json
import inspect
from pathlib import Path
from typing import Union, Optional
from inspect import Parameter, signature

from speedysvc.serialisation.RawSerialisation import RawSerialisation


FIND_TEXT = '# NOTE: This file was auto-generated by SpeedySVCService,'


class SpeedySVCClientFormatter:
    def __init__(self,
                 server_class,
                 port: int,
                 service_name: str,
                 client_imports: Optional[str] = None):

        self.server_class = server_class
        self.port = port
        self.service_name = service_name
        self.client_imports = client_imports

    def save_client_boilerplate(self,
                                class_name: str,
                                path: Union[Path, str],
                                check=True):

        if check and Path(path).exists() and FIND_TEXT not in Path(path).read_text('utf-8', 'ignore'):
            raise Exception(f"Service client file {path} already exists without autogenerated header")

        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.format_client_boilerplate(class_name))

    def format_client_boilerplate(self, class_name: str):
        out = [
            f'''# NOTE: This file was auto-generated by SpeedySVCService, \n'''
            f'''#       and it's usually best not to modify it directly\n'''
            f'''from typing import Union, List, Tuple\n'''
            f'''from speedysvc.service_method import service_method\n'''
            f'''from speedysvc.SpeedySVCClient import SpeedySVCClient\n'''
            f'''from speedysvc.compression.compression_types import snappy_compression\n'''
            f'''{self.client_imports.strip() if self.client_imports else ''}'''
            f'''\n\n'''
            f'''class {class_name}(SpeedySVCClient):\n'''
            f'''    def __init__(self,\n'''
            f'''                 address: Union[List, Tuple, str] = "shm://{self.service_name}:{self.port}",\n'''
            f'''                 use_spinlock: bool = True,\n'''
            f'''                 use_in_process_lock: bool = True,\n'''
            f'''                 compression_inst=snappy_compression):\n'''
            f'''        SpeedySVCClient.__init__(self, address, use_spinlock, use_in_process_lock, compression_inst)\n'''
            f'''        \n'''
        ]
        imports = []
        for method_name in dir(self.server_class):
            #print("METHOD:", method_name, hasattr(getattr(self.server_class, method_name), 'metadata'))
            if hasattr(getattr(self.server_class, method_name), 'metadata'):
                imports, i = self.__get_client_boilerplate(method_name, imports)
                out.append(i)

        # FIXME: Move to top of file!
        out.append('\n')
        out.append('\n'.join(imports))
        out.append('\n')
        return ''.join(out)

    def __get_client_boilerplate(self, method_name, imports):
        method = getattr(self.server_class, method_name)
        metadata = method.metadata

        sig = signature(method)
        positional = []
        keyword = []
        var_positional = None
        var_keyword = None

        for param_name, param in sig.parameters.items():
            if param.kind == Parameter.POSITIONAL_ONLY:
                positional.append(param.name)
            elif param.kind == Parameter.POSITIONAL_OR_KEYWORD:
                positional.append(param.name)
            elif param.kind == Parameter.VAR_POSITIONAL:
                var_positional = param.name
            elif param.kind == Parameter.KEYWORD_ONLY:
                keyword.append(param.name)
            elif param.kind == Parameter.VAR_KEYWORD:
                var_keyword = param.name
            else:
                raise TypeError(f"Parameter type {param.kind} is unknown for {param.name}")

        if hasattr(method, '__doc__') and method.__doc__ and method.__doc__.strip():
            # Copy the docstring, if there is one
            doc = (
                f'''        """''' +
                method.__doc__ +
                f'''"""\n'''
            )
        else:
            doc = ''

        # Don't send "self" to be serialised
        if positional and positional[0] == 'self':
            del positional[0]

        # ct = call type (to allow reducing duplication while preserving indent below..)
        ct = 'call' if not metadata.returns_iterator else 'iter'

        params_serialiser = metadata.params_serialiser.__name__
        return_serialiser = metadata.return_serialiser.__name__

        for serialiser_name in (params_serialiser, return_serialiser):
            import_statement = f'from speedysvc.serialisation.{serialiser_name} import {serialiser_name}'
            if import_statement not in imports:
                imports.append(import_statement)

        # Find the decorator for this method, and add the indent level
        decorator = self.get_decorator_for_function(method_name)
        decorator = '\n'.join('    '+i for i in decorator.split('\n')).rstrip()+'\n'

        if metadata.params_serialiser == RawSerialisation:
            # TODO: Add support for return type annotation etc
            return imports, (
                    decorator +
                    f'''    def {method_name}(self, data: bytes):\n''' +
                    doc +
                    f'''        return self._{ct}_remote_raw(self.{method_name}.metadata,\n'''
                    f'''                                     b{json.dumps(method_name)},\n'''
                    f'''                                     data)\n'''
                    f'''        \n'''
            )
        elif var_keyword and keyword:
            i = []
            for k in keyword:
                i.append(
                    f'''        {var_keyword}[{json.dumps(k)}] = {k}\n'''
                )
            return imports, (
                    decorator +
                    f'''   def {method_name}{str(sig)}:\n''' +
                    doc +
                    ''.join(i) +
                    f'''       return self._{ct}_remote(self.{method_name}.metadata,\n'''
                    f'''                                b{json.dumps(method_name)},\n'''
                    f'''                                ({', '.join(positional)},),\n'''
                    f'''                                {var_positional},\n'''
                    f'''                                {var_keyword})\n'''
                    f'''       \n'''
            )
        elif keyword:
            i = '''{%s}''' % ', '.join(f'{json.dumps(k)}: {k}' for k in keyword)
            return imports, (
                decorator +
                f'''    def {method_name}{str(sig)}:\n''' +
                doc +
                f'''        return self._{ct}_remote(self.{method_name}.metadata,\n'''
                f'''                                 b{json.dumps(method_name)}, \n'''
                f'''                                 ({', '.join(positional)},),\n'''
                f'''                                 {var_positional},\n'''
                f'''                                 {i})\n'''
                f'''        \n'''
            )
        else:
            # Keywords are expensive - just use ordinary params
            return imports, (
                decorator +
                f'''    def {method_name}{str(sig)}:\n''' +
                doc +
                f'''        return self._{ct}_remote(self.{method_name}.metadata,\n'''
                f'''                                 b{json.dumps(method_name)}, \n'''
                f'''                                 ({', '.join(positional)},),\n'''
                f'''                                 {var_positional},\n'''
                f'''                                 {var_keyword})\n'''
                f'''        \n'''
            )

    def get_decorator_for_function(self, function_name: str):
        py_file_path = inspect.getfile(self.server_class)

        with open(py_file_path, 'r', encoding='utf-8') as f:
            lines = list(f.readlines())

        indent_level = None
        found_on_line = None
        found_class = False

        # Find the class and the line of the method we're looking for
        for x, line in enumerate(lines):
            if not found_class:
                if line.lstrip().startswith(f'class {self.server_class.__name__}(') or \
                   line.lstrip().startswith(f'class {self.server_class.__name__}:'):
                    found_class = True
            elif line.lstrip().startswith(f'def {function_name}('):
                found_on_line = x
                indent_level = len(line) - len(line.lstrip())
                break

        if found_on_line is None or found_class is False:
            raise Exception(f"Function {function_name} in class {self.server_class.__name__} not found")

        # Find the start of the @service_method decorator
        out = []
        found_decorator_on_line = None
        for x, line in enumerate(reversed(lines[:found_on_line])):
            #print(found_on_line, found_on_line - x, function_name, line.rstrip())
            if line.lstrip().startswith('@service_method'):
                if line[:indent_level].strip():
                    raise Exception(f"Invalid indentation on line {found_on_line - x}: {line.rstrip()}")
                found_decorator_on_line = found_on_line - x
                out.append(line[indent_level:])
                break

        if found_decorator_on_line is None:
            raise Exception(f"Unable to find decorator for method {function_name} in class {self.server_class.__name__}")

        # Now get the decorator itself
        for x, line in enumerate(lines[found_decorator_on_line:]):
            if line.lstrip().startswith('@') or line.lstrip().startswith('def'):
                break
            elif line[:indent_level].strip():
                raise Exception(f"Invalid indentation on line {x + found_decorator_on_line}: {line.rstrip()}")
            out.append(line[indent_level:])
        return ''.join(out)
