"""Fortran binding generation code.

This takes as input a *.in file containing the prototype of a Fortran function
with generic types. Both the Fortran subroutine and a wrapping C function can
generated from this file.
"""
from abc import ABC, abstractmethod
import argparse
import re

FORTRAN_ERROR_NAME = 'ierror'
C_ERROR_NAME = 'ierr'
C_ERROR_TMP_NAME = 'c_ierr'
GENERATED_MESSAGE = 'THIS FILE WAS AUTOMATICALLY GENERATED. DO NOT EDIT BY HAND.'
PROTOTYPE_RE = re.compile(r'^\w+\((\s*\w+\s+\w+(:\w+)?\s*,?)+\)$')


class FortranType(ABC):

    def __init__(self, name, fn_name, bigcount=False, **kwargs):
        self.name = name
        self.fn_name = fn_name
        self.bigcount = bigcount
        # A dependent type/parameter, such as a count
        self.dep_param = None
        self.used_counters = 0

    TYPES = {}

    @classmethod
    def add(cls, type_name):
        """Decorator for adding types."""
        def wrapper(class_):
            cls.TYPES[type_name] = class_
            return class_
        return wrapper

    @classmethod
    def get(cls, type_name):
        return cls.TYPES[type_name]

    @property
    def fn_api_name(self):
        """Return the MPI API name to be used in error messages, etc.."""
        return c_api_func_name(self.fn_name, bigcount=self.bigcount).upper()

    @property
    def tmp_c_name(self):
        """Return a temporary name for use in C."""
        return f'c_{self.name}'

    @property
    def tmp_c_name2(self):
        """Return a secondary temporary name for use in C."""
        return f'c_{self.name}2'

    def tmp_counter(self):
        """Get a temporary counter variable to be used in a loop."""
        name = f'{self.name}_i_{self.used_counters}'
        self.used_counters += 1
        return name

    @abstractmethod
    def declare(self):
        """Return a declaration for the type."""

    def declare_cbinding_fortran(self):
        """Return the C binding declaration as seen from Fortran."""
        return self.declare()

    def argument(self):
        """Return the value to pass as an argument."""
        return self.name

    def use(self):
        """Return list of (module, name) for a Fortran use-statement."""
        return []

    @abstractmethod
    def c_parameter(self):
        """Return the parameter expression to be used in the C function."""

    def c_declare_tmp(self):
        """Code to declare temporary variables for conversions, etc.."""
        return []

    def c_shortcut_condition(self):
        """Shortcut conditional code.

        If the conditional evaluates to true in C, then code defined in
        c_shortcut_code() for all other parameters will be run and the
        underlying C function will not be called.
        """
        return None

    def c_shortcut_code(self):
        """Shortcut code to run if a parameter defines a shortcut condition."""
        return []

    def c_prepare(self):
        """Code to be called before being passed to underlying C function."""
        return []

    def c_argument(self):
        """Return the value to pass as an argument in the C code."""
        return self.name

    def c_post(self):
        """Code to be run after a call to the underlying C function."""
        return []


#
# Definitions of generic types in Fortran and how these can be converted
# to and from C.
#


@FortranType.add('BUFFER')
class BufferType(FortranType):
    def declare(self):
        return f'OMPI_FORTRAN_IGNORE_TKR_TYPE, INTENT(IN) :: {self.name}'

    def c_parameter(self):
        return f'char *{self.name}'

    def c_argument(self):
        return f'OMPI_F2C_BOTTOM({self.name})'


@FortranType.add('COUNT')
class CountType(FortranType):
    def declare(self):
        if self.bigcount:
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def use(self):
        return [('mpi_f08_types', 'MPI_COUNT_KIND')]

    def c_parameter(self):
        type_ = 'MPI_Count' if self.bigcount else 'MPI_Fint'
        return f'{type_} *{self.name}'

    def c_argument(self):
        return f'*{self.name}' if self.bigcount else f'OMPI_FINT_2_INT(*{self.name})'


@FortranType.add('DATATYPE')
class DatatypeType(FortranType):
    def declare(self):
        return f'TYPE(MPI_Datatype), INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def argument(self):
        return f'{self.name}%MPI_VAL'

    def use(self):
        return [('mpi_f08_types', 'MPI_Datatype')]

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

    def c_prepare(self):
        return [f'MPI_Datatype {self.tmp_c_name} = PMPI_Type_f2c(*{self.name});']

    def c_argument(self):
        return self.tmp_c_name


class IntType(FortranType):
    def declare(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

    def c_argument(self):
        return f'OMPI_FINT_2_INT(*{self.name})'


@FortranType.add('RANK')
class RankType(IntType):
    pass


@FortranType.add('TAG')
class TagType(IntType):
    pass


@FortranType.add('COMM')
class CommType(FortranType):
    def declare(self):
        return f'TYPE(MPI_Comm), INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def argument(self):
        return f'{self.name}%MPI_VAL'

    def use(self):
        return [('mpi_f08_types', 'MPI_Comm')]

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

    def c_prepare(self):
        return [f'MPI_Comm {self.tmp_c_name} = PMPI_Comm_f2c(*{self.name});']

    def c_argument(self):
        return self.tmp_c_name


@FortranType.add('STATUS')
class StatusType(FortranType):
    def declare(self):
        return f'TYPE(MPI_Status), INTENT(OUT) :: {self.name}'

    def use(self):
        return [('mpi_f08_types', 'MPI_Status')]

    def c_parameter(self):
        # TODO: Is this correct? (I've listed it as TYPE(MPI_Status) in the binding)
        return f'MPI_Fint *{self.name}'

    def c_prepare(self):
        return [
            f'OMPI_FORTRAN_STATUS_DECLARATION({self.tmp_c_name}, {self.tmp_c_name2});',
            f'OMPI_FORTRAN_STATUS_SET_POINTER({self.tmp_c_name}, {self.tmp_c_name2}, {self.name});'
        ]

    def c_argument(self):
        return self.tmp_c_name

    def c_post(self):
        return [f'OMPI_FORTRAN_STATUS_RETURN({self.tmp_c_name}, {self.tmp_c_name2}, {self.name}, {C_ERROR_TMP_NAME});']


@FortranType.add('SHORTCUT_COUNT')
class ShortcutCountType(FortranType):
    """Shortcut count type.

    This type is an integer that, when 0, can be used to shortcut a call to the
    underyling C binding. Other types may implement a `c_shortcut` method that
    will return code to execute upon a shortcut operation.

    The shortcut conditional is placed right after c temporary declarations but
    before the c prepare code.
    """

    def declare(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

    def c_shortcut_condition(self):
        return f'OPAL_UNLIKELY(0 == OMPI_FINT_2_INT(*{self.name}))'

    def c_argument(self):
        return f'OMPI_FINT_2_INT(*{self.name})'


def allocate_array(name, malloc_expr, fn_api_name):
    """Generate code for allocating an array and checking the result."""
    return [
        f'{name} = malloc({malloc_expr});',
        f'if (NULL == {name}) {{',
        f'    {C_ERROR_TMP_NAME} = OMPI_ERRHANDLER_NOHANDLE_INVOKE(MPI_ERR_NO_MEM, "{fn_api_name}");',
        f'    *{C_ERROR_NAME} = OMPI_INT_2_FINT({C_ERROR_TMP_NAME});',
        '    return;',
        '}',
    ]


@FortranType.add('REQUEST_ARRAY')
class RequestArrayType(FortranType):
    def declare(self):
        return f'TYPE(MPI_Request), INTENT(INOUT) :: {self.name}({self.dep_param.name})'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}({self.dep_param.name})'

    def argument(self):
        return f'{self.name}(:)%MPI_VAL'

    def use(self):
        return [('mpi_f08_types', 'MPI_Request')]

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

    def c_declare_tmp(self):
        return [f'MPI_Request *{self.tmp_c_name};']

    def c_prepare(self):
        tmp_name = self.tmp_c_name
        code = allocate_array(tmp_name,
                              f'{self.dep_param.c_argument()} * sizeof(MPI_Request)',
                              self.fn_api_name)
        i = self.tmp_counter()
        code.extend([
            f'for (int {i} = 0; {i} < {self.dep_param.c_argument()}; ++{i}) {{',
            f'    {tmp_name}[{i}] = PMPI_Request_f2c({self.name}[{i}]);',
            '}',
        ])
        return code

    def c_argument(self):
        return self.tmp_c_name

    def c_post(self):
        i = self.tmp_counter()
        return [
            f'if (MPI_SUCCESS == {C_ERROR_TMP_NAME}) {{',
            f'    for (int {i} = 0; {i} < {self.dep_param.c_argument()}; ++{i}) {{',
            f'        {self.name}[{i}] = {self.tmp_c_name}[{i}]->req_f_to_c_index;',
            '    }',
            '}',
            f'free({self.tmp_c_name});',
        ]


@FortranType.add('STATUS_ARRAY')
class StatusArrayType(FortranType):
    def declare(self):
        return f'TYPE(MPI_Status), INTENT(OUT) :: {self.name}(*)'

    def use(self):
        return [('mpi_f08_types', 'MPI_Status')]

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

    def c_declare_tmp(self):
        return [f'MPI_Status *{self.tmp_c_name};']

    def c_prepare(self):
        return allocate_array(self.tmp_c_name,
                              f'{self.dep_param.c_argument()} * sizeof(MPI_Status)',
                              self.fn_api_name)

    def c_argument(self):
        return self.tmp_c_name

    def c_post(self):
        i = self.tmp_counter()
        return [
            f'if (MPI_SUCCESS == {C_ERROR_TMP_NAME}) {{',
            f'    for (int {i} = 0; {i} < {self.dep_param.c_argument()}; ++{i}) {{',
            f'        if (!OMPI_IS_FORTRAN_STATUSES_IGNORE({self.name}) &&',
            f'            !OMPI_IS_FORTRAN_STATUS_IGNORE(&{self.name}[{i}])) {{',
            f'            PMPI_Status_c2f(&{self.tmp_c_name}[{i}], &{self.name}[{i} * (sizeof(MPI_Status) / sizeof(int))]);',
            '        }',
            '    }',
            '}',
            f'free({self.tmp_c_name});'
        ]


class PrototypeParseError(Exception):
    """Thrown when a parsing error is encountered."""


def c_api_func_name(fn_name, bigcount=False):
    """Produce the actual MPI API function name to call into."""
    suffix = '_c' if bigcount else ''
    return f'MPI_{fn_name.capitalize()}{suffix}'


def c_api_func_name_profile(fn_name, bigcount=False):
    """Produce the actual PMPI API function name to call into."""
    return f'P{c_api_func_name(fn_name, bigcount)}'


def print_header():
    """Print the fortran f08 file header."""
    print('#include "ompi/mpi/fortran/configure-fortran-output.h"')
    print('#include "mpi-f08-rename.h"')


class FortranBinding:

    def __init__(self, fname, bigcount=False):
        self.bigcount = bigcount
        with open(fname) as fp:
            data = []
            for line in fp:
                data.append(line.strip())
            data = ' '.join(data)
            data = data.strip()
            if PROTOTYPE_RE.match(data) is None:
                raise PrototypeParseError('Invalid function prototype for Fortran interface')
            start = data.index('(')
            end = data.index(')')
            self.fn_name = data[:start].strip()

            parameters = data[start+1:end].split(',')
            self.parameters = []
            param_map = {}
            dep_params = {}
            for param in parameters:
                param = param.strip()
                type_, name = param.split()
                type_ = FortranType.get(type_)
                # Check for 'param:other_param' parameters, indicating a
                # dependency on that other parameter (such as for a count)
                if ':' in name:
                    name, dep_name = name.split(':')
                    dep_params[name] = dep_name
                param = type_(name, self.fn_name, bigcount=bigcount)
                self.parameters.append(param)
                param_map[name] = param
            # Set dependent parameters for those that need them
            for name, dep_name in dep_params.items():
                param_map[name].dep_param = param_map[dep_name]

    def _fn_name_suffix(self):
        """Return a suffix for function names."""
        return '_c' if self.bigcount else ''

    @property
    def fortran_f08_name(self):
        """Produce the final f08 name from base_name."""
        return f'MPI_{self.fn_name.capitalize()}_f08{self._fn_name_suffix()}'

    @property
    def c_func_name(self):
        """Produce the final C func name from base_name."""
        return f'ompi_{self.fn_name}_wrapper_f08{self._fn_name_suffix()}'

    def _param_list(self):
        return ','.join(type_.name for type_ in self.parameters)

    def _use(self):
        """Determine the Fortran use-statements needed."""
        use = {}
        for param in self.parameters:
            for mod, name in param.use():
                if mod not in use:
                    use[mod] = set()
                use[mod].add(name)
        return use

    def _use_stmts(self):
        """Return a list of required use statments."""
        use = self._use()
        stmts = []
        for mod, names in use.items():
            names = ', '.join(names)
            stmts.append(f'use :: {mod}, only: {names}')
        return stmts

    def _print_fortran_interface(self):
        """Output the C subroutine binding for the Fortran code."""
        name = self.c_func_name
        print('    interface')
        print(f'        subroutine {name}({self._param_list()},{FORTRAN_ERROR_NAME}) &')
        print(f'            BIND(C, name="{name}")')
        use_stmts = self._use_stmts()
        for stmt in use_stmts:
            print(f'            {stmt}')
        print('            implicit none')
        for param in self.parameters:
            print(f'            {param.declare_cbinding_fortran()}')
        print(f'            INTEGER, INTENT(OUT) :: {FORTRAN_ERROR_NAME}')
        print(f'        end subroutine {name}')
        print('    end interface')

    def print_f_source(self):
        """Output the main MPI Fortran subroutine."""
        print(f'! {GENERATED_MESSAGE}')

        print_header()

        sub_name = self.fortran_f08_name
        c_func = self.c_func_name
        print('subroutine', f'{sub_name}({self._param_list()},{FORTRAN_ERROR_NAME})')
        # Use statements
        use_stmts = self._use_stmts()
        for stmt in use_stmts:
            print(f'    {stmt}')
        print('    implicit none')
        # Parameters/dummy variable declarations
        types = []
        for param in self.parameters:
            print(f'    {param.declare()}')
        # Add the integer error manually
        print(f'    INTEGER, OPTIONAL, INTENT(OUT) :: {FORTRAN_ERROR_NAME}')
        # Temporaries
        print(f'    INTEGER :: {C_ERROR_TMP_NAME}')

        # Interface for call to C function
        print()
        self._print_fortran_interface()
        print()

        # Call into the C function
        args = ','.join(param.argument() for param in self.parameters)
        print(f'    call {c_func}({args},{C_ERROR_TMP_NAME})')
        # Convert error type
        print(f'    if (present({FORTRAN_ERROR_NAME})) {FORTRAN_ERROR_NAME} = {C_ERROR_TMP_NAME}')

        print(f'end subroutine {sub_name}')

    def print_c_source(self):
        """Output the C source and function that the Fortran calls into."""
        print(f'/* {GENERATED_MESSAGE} */')
        print('#include "ompi_config.h"')
        print('#include "mpi.h"')
        print('#include "ompi/errhandler/errhandler.h"')
        print('#include "ompi/mpi/fortran/mpif-h/status-conversion.h"')
        print('#include "ompi/mpi/fortran/base/constants.h"')
        print('#include "ompi/mpi/fortran/base/fint_2_int.h"')
        print('#include "ompi/request/request.h"')
        parameters = [param.c_parameter() for param in self.parameters]
        # Always append the integer error
        parameters.append(f'MPI_Fint *{C_ERROR_NAME}')
        parameters = ', '.join(parameters)
        # Just put the signature here to silence `-Wmissing-prototypes`
        c_func = self.c_func_name
        print(f'void {c_func}({parameters});')
        print(f'void {c_func}({parameters})')
        print('{')
        print(f'    int {C_ERROR_TMP_NAME}; ')

        # First the temporary declarations
        for param in self.parameters:
            for line in param.c_declare_tmp():
                print(f'    {line}')

        # Shortcut conditions, if any
        for param in self.parameters:
            condition = param.c_shortcut_condition()
            if condition is None:
                continue
            print(f'    if ({condition}) {{')
            print(f'        *{C_ERROR_NAME} = OMPI_INT_2_FINT(MPI_SUCCESS);')
            for other_param in self.parameters:
                for line in other_param.c_shortcut_code():
                    print(f'        {line}')
            print('    }')

        # Prepare code for temporaries, etc.
        for param in self.parameters:
            for line in param.c_prepare():
                print(f'    {line}')

        # Call into the C API
        c_api_func = c_api_func_name_profile(self.fn_name, bigcount=self.bigcount)
        arguments = [param.c_argument() for param in self.parameters]
        arguments = ', '.join(arguments)
        print(f'    {C_ERROR_TMP_NAME} = {c_api_func}({arguments});')

        # Post-processing code
        print(f'    *{C_ERROR_NAME} = OMPI_INT_2_FINT({C_ERROR_TMP_NAME});')
        for param in self.parameters:
            for line in param.c_post():
                print(f'    {line}')
        print('}')


def main():
    parser = argparse.ArgumentParser(description='generate fortran binding files')
    parser.add_argument('lang', choices=('fortran', 'c'), help='generate dependent files in C or Fortran')
    parser.add_argument('template', help='template file to use')
    parser.add_argument('--bigcount', action='store_true', help='generate bigcount interface for function')
    args = parser.parse_args()

    binding = FortranBinding(args.template, bigcount=args.bigcount)
    if args.lang == 'fortran':
        binding.print_f_source()
    else:
        binding.print_c_source()


if __name__ == '__main__':
    main()
