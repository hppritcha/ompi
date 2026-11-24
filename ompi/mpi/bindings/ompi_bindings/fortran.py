# Copyright (c) 2024-2026 Triad National Security, LLC. All rights
#                         reserved.
#
# Copyright (c) 2026      Jeffrey M. Squyres.  All rights reserved.
# $COPYRIGHT$
#
# Additional copyrights may follow
#
# $HEADER$
# SPDX-License-Identifier: BSD-3-Clause-Open-MPI
#
"""Fortran binding generation code.

This takes as input a *.in file containing a list of prototypes for Fortran
subroutines with generic types. Using this file, it can generate the Fortran
subroutines in one file and the C wraping code in another for all prototypes
listed.
"""
from collections import namedtuple
import json
import os
import re
import sys
from ompi_bindings import consts, util
from ompi_bindings.fortran_type import FortranType
from ompi_bindings.parser import SourceTemplate


# Cache of { f08/f90 : {function_name_lower: [standard dummy-argument names]} } loaded
# from pympistandard.  None means "not yet attempted"; an empty dict means
# "attempted but unavailable" (the generator then falls back to the names
# hard-coded in the *.in PROTOTYPE lines).
_STANDARD_PARAMETER_NAMES = None


def standard_parameter_names(pympistd_dir, use_f90):
    """Load the standard MPI F08 dummy-argument names from pympistandard.

    The Open MPI templates use generic internal names (e.g. 'x', 'x1') for
    the choice-buffer arguments; the C back-end code refers to those names.
    The user-visible mpi_f08 interfaces, however, must use the parameter
    names mandated by the MPI standard so that keyword arguments work.  This
    returns, per function, the ordered list of standard F08 dummy names
    (excluding ierror), which the Fortran generator substitutes for the
    template names -- without touching the C back-end.
    """
    global _STANDARD_PARAMETER_NAMES
    lang = "f90" if use_f90 else "f08"
    if _STANDARD_PARAMETER_NAMES is not None:
        return _STANDARD_PARAMETER_NAMES[lang]
    names = { "f90": {}, "f08": {} }
    if pympistd_dir:
        src = os.path.join(pympistd_dir, 'src')
        if os.path.isdir(src):
            sys.path.insert(0, src)
            import pympistandard as std
            std.use_api_version(1)
            for key, proc in std.PROCEDURES.items():
                for kind in ['f08', 'f90']:
                    kind_attr = getattr(proc.express, kind, None)
                    if kind_attr is None:
                        continue
                    names[kind][key.lower()] = [p.name.lower() for p in kind_attr.parameters
                                          if p.name.lower() != consts.FORTRAN_ERROR_NAME]
                # The large count version, under the name of its *.c.in_obc
                # template (e.g. mpi_type_get_envelope_c)
                embiggen = getattr(proc.express, 'embiggen', None)
                kind_attr = getattr(embiggen, 'f08', None) if embiggen is not None else None
                if kind_attr is not None:
                    names['f08'].setdefault(key.lower() + '_c',
                                            [p.name.lower() for p in kind_attr.parameters
                                             if p.name.lower() != consts.FORTRAN_ERROR_NAME])
    _STANDARD_PARAMETER_NAMES = names
    return names[lang]


class FortranBinding:
    """Class for generating the binding for a single function."""

    def __init__(self, prototype, out, template=None, bigcount=False, needs_ts=False,
                 gen_f90=False, param_names=None):
        # Generate bigcount interface version
        self.bigcount = bigcount
        self.fn_name = template_fn_name(template)
        self.out = out
        self.template = template
        self.needs_ts = needs_ts
        self.gen_f90 = gen_f90
        self.has_ierror = util.prototype_has_ierror(self.template.prototype)
        # A function (e.g. MPI_Aint_add) returns its result through the C
        # wrapper's return value
        self.result = None
        if util.prototype_is_function(self.template.prototype):
            self.result = self.template.prototype.return_type.construct(
                name=self.fn_name, fn_name=self.fn_name, bigcount=bigcount, gen_f90=gen_f90)
        self.parameters = []
        for param in self.template.prototype.params:
            self.parameters.append(param.construct(fn_name=self.fn_name,
                                                   bigcount=bigcount,
                                                   gen_f90=gen_f90))
        # For Fortran generation, replace the template's internal parameter
        # names with the standard MPI F08 dummy-argument names.  Only done
        # when the count of standard names matches (i.e. the prototype and the
        # standard agree on the number of non-ierror arguments); otherwise the
        # template names are kept so a misaligned prototype never silently
        # emits a wrong name.  The C back-end (print_c_source) constructs its
        # own FortranBinding without param_names, so it is unaffected.
        if param_names is not None and len(param_names) == len(self.parameters):
            for param, std_name in zip(self.parameters, param_names):
                param.name = std_name

    def dump(self, *pargs, **kwargs):
        """Write to the output file."""
        self.out.dump(*pargs, **kwargs)

    @property
    def procedure_keyword(self):
        """Return the Fortran keyword for the kind of procedure."""
        return 'subroutine' if self.result is None else 'function'

    @property
    def f_name(self):
        """Return the name of the Fortran procedure."""
        return util.fortran_name(self.fn_name, bigcount=self.bigcount, gen_f90=self.gen_f90,
                                 needs_ts=self.needs_ts)

    def _fn_name_suffix(self):
        """Return a suffix for function names."""
        return '_c' if self.bigcount else ''

    @property
    def c_func_name(self):
        """Produce the final C func name from base_name."""
        module = 'f90' if self.gen_f90 else 'f08'
        return f'ompi_{self.fn_name}_wrapper_{module}{self._fn_name_suffix()}'

    @property
    def inner_call(self):
        """Produce the name of the function to call in the body of the C code."""
        return f'PMPI_{self.fn_name.capitalize()}{self._fn_name_suffix()}'

    def _use(self):
        """Determine the Fortran use-statements needed."""
        use = {}
        types = self.parameters if self.result is None else self.parameters + [self.result]
        for param in types:
            for mod, name in param.use():
                if mod not in use:
                    use[mod] = set()
                use[mod].add(name)
        return use

    def _use_stmts(self):
        """Return a list of required use statments."""
        use = self._use()
        stmts = []
        # Sort both the modules and the names within each module so the
        # generated code is identical between builds.  Sorting the names
        # is required: set iteration order depends on PYTHONHASHSEED.
        # The module order already follows the parameter order, but
        # sorting it too keeps the output stable if that ever changes.
        for mod, names in sorted(use.items()):
            names = ', '.join(sorted(names))
            stmts.append(f'use :: {mod}, only: {names}')
        return stmts

    def _include_stmts(self):
        """Return a list of required includes needed."""
        includes = []
        names = []
        types = self.parameters if self.result is None else self.parameters + [self.result]
        for param in types:
            name = param.include()
            if name != '':
                if name in names:
                    continue
                includes.append(f'include \'{name}\'')
                names.append(f'{name}')
        return includes

    def _print_fortran_interface(self):
        """Output the C subroutine binding for the Fortran code."""
        name = self.c_func_name
        self.dump('    interface')

        # Print the subroutine and parameter list, breaking parameters across lines
        subroutine_start = f'        {self.procedure_keyword} {name}('
        params = [name for param in self.parameters for name in param.cbinding_params()]
        if self.has_ierror:
            params.append(consts.FORTRAN_ERROR_NAME)
        lines = util.break_param_lines_fortran(start=subroutine_start, params=params, end=') &')
        for line in lines:
            self.dump(line)
        self.dump(f'            BIND(C, name="{name}")')

        use_stmts = self._use_stmts()
        for stmt in use_stmts:
            self.dump(f'            {stmt}')
        self.dump('            implicit none')
        include_stmts = self._include_stmts()
        for stmt in include_stmts:
            self.dump(f'            {stmt}')
        for param in self.parameters:
            for line in param.declare_cbinding_fortran().split('\n'):
                self.dump(f'            {line}')
        if self.has_ierror:
            self.dump(f'            INTEGER, INTENT(OUT) :: {consts.FORTRAN_ERROR_NAME}')
        if self.result is not None:
            self.dump(f'            {self.result.declare_result(name)}')
        self.dump(f'        end {self.procedure_keyword} {name}')
        self.dump('    end interface')

    def _print_fortran_header(self, is_interface=False):
        """Print the header, including use stmts, dummy variable decls, etc..

        This does not include the subroutine line.
        """
        # Use statements
        use_stmts = self._use_stmts()
        for stmt in use_stmts:
            self.dump(f'    {stmt}')
        self.dump('    implicit none')
        # Include statements
        include_stmts = self._include_stmts()
        for stmt in include_stmts:
            self.dump(f'    {stmt}')
        # Parameters/dummy variable declarations
        for param in self.parameters:
            if is_interface:
                self.dump_lines(param.interface_predeclare())
            self.dump_lines(param.declare())
        # Add the integer error manually
        if self.has_ierror:
            if self.gen_f90 == True:
                self.dump(f'    INTEGER, INTENT(OUT) :: {consts.FORTRAN_ERROR_NAME}')
            else:
                self.dump(f'    INTEGER, OPTIONAL, INTENT(OUT) :: {consts.FORTRAN_ERROR_NAME}')
        if self.result is not None:
            self.dump(f'    {self.result.declare_result(self.f_name)}')

    def _print_fortran_subroutine(self):
        """Output the Fortran subroutine (or function) line."""
        params = [param.name for param in self.parameters]
        if self.has_ierror:
            params.append(consts.FORTRAN_ERROR_NAME)
        lines = util.break_param_lines_fortran(f'{self.procedure_keyword} {self.f_name}(', params, ')')
        for line in lines:
            self.dump(line)

    def _print_fortran_subroutine_end(self):
        """Output the Fortran end subroutine (or function) line."""
        self.dump(f'end {self.procedure_keyword} {self.f_name}')

    def dump_lines(self, line_text):
        for line in line_text.split('\n'):
            line = line.rstrip()
            if line:
                self.dump(f'    {line}')

    def print_f_source(self):
        """Output the main MPI Fortran subroutine."""
        self._print_fortran_subroutine()
        self._print_fortran_header()

        # Temporaries
        if self.has_ierror:
            self.dump(f'    INTEGER :: {consts.C_ERROR_TMP_NAME}')
        for param in self.parameters:
            self.dump_lines(param.declare_tmp())

        # Interface for call to C function
        self.dump()
        self._print_fortran_interface()
        self.dump()

        # Output in pre C function call methods

        for param in self.parameters:
            self.dump_lines(param.pre_c_call())

        # Call into the C function
        if self.result is None:
            call_start = f'    call {self.c_func_name}('
        else:
            call_start = f'    {self.f_name} = {self.c_func_name}('
        params = [arg for param in self.parameters for arg in param.cbinding_arguments()]
        if self.has_ierror:
            params.append(consts.C_ERROR_TMP_NAME)
        lines = util.break_param_lines_fortran(start=call_start, params=params, end=')')
        for line in lines:
            self.dump(line)

        # Convert error type
        if self.has_ierror:
            if self.gen_f90:
                self.dump(f'    {consts.FORTRAN_ERROR_NAME} = {consts.C_ERROR_TMP_NAME}')
            else:
                self.dump(f'    if (present({consts.FORTRAN_ERROR_NAME})) {consts.FORTRAN_ERROR_NAME} = {consts.C_ERROR_TMP_NAME}')

        for param in self.parameters:
            self.dump_lines(param.post())

        self._print_fortran_subroutine_end()

    def print_c_source(self):
        """Output the C source and function that the Fortran calls into."""
        if self.template is None:
            return
        parameters = [param.c_parameter() for param in self.parameters]
        # Append the integer error, if the procedure has one
        if self.has_ierror:
            parameters.append(f'MPI_Fint *{consts.C_ERROR_NAME}')
        parameters = ', '.join(parameters)
        # Just put the signature here to silence `-Wmissing-prototypes`
        c_func = self.c_func_name
        c_return_type = 'void' if self.result is None else self.result.c_return_type()
        self.dump(f'{c_return_type} {c_func}({parameters});')
        self.dump(f'{c_return_type} {c_func}({parameters})')
        count_type, disp_type, count_fint_type = ('MPI_Count', 'MPI_Aint', 'MPI_Count') if self.bigcount else ('int', 'int', 'MPI_Fint')
        self.template.print_body(c_func, out=self.out,
                                 replacements={'INNER_CALL': self.inner_call,
                                               'COUNT_TYPE': count_type,
                                               'COUNT_FINT_TYPE': count_fint_type,
                                               'DISP_TYPE': disp_type,
                                               'BIGCOUNT_SUFFIX': '_c' if self.bigcount else '',
                                               'LOGICAL_TYPE': 'int'})

    def print_interface(self):
        """Output just the Fortran interface for this binding."""
        self._print_fortran_subroutine()
        self._print_fortran_header(is_interface=True)
        self._print_fortran_subroutine_end()


def print_f_source_header(out):
    """Print the fortran f08 file header."""
    out.dump(f'! {consts.GENERATED_MESSAGE}')
    out.dump('#include "ompi/mpi/fortran/configure-fortran-output.h"')


def print_profiling_rename_macros(templates, out, args):
    """Print macros for renaming functions for the profiling interface.

    Previously hardcoded in mpi-f08-rename.h.
    """
    gen_f90 = True if args.fort_std == 'f90' else False
    out.dump('#if OMPI_BUILD_MPI_PROFILING')
    # The nbc and obc templates of a procedure share its generic name
    done = set()
    for template in templates:
        has_buffers = util.prototype_has_buffers(template.prototype)
        needs_ts = has_buffers and args.generate_ts_suffix
        fn_name = template_fn_name(template)
        names = set()
        if template_has_regular(template):
            names.add(util.fortran_name(fn_name, gen_f90=gen_f90, needs_ts=needs_ts))
        # Check for bigcount version
        if template_has_bigcount(template):
            names.add(util.fortran_name(fn_name, gen_f90=gen_f90, bigcount=True, needs_ts=needs_ts))
        interface_name = util.fortran_generic_interface_name(fn_name)
        names.add(interface_name)
        if util.prototype_bigcount_is_separate(template.prototype):
            names.add(util.fortran_generic_interface_name(fn_name, bigcount=True))
        for name in sorted(names - done):
            out.dump(f'#define {name} P{name}')
        done |= names
    out.dump('#endif /* OMPI_BUILD_MPI_PROFILING */')


def print_c_source_header(out):
    """Print the header of the C source file."""
    out.dump(f'/* {consts.GENERATED_MESSAGE} */')
    out.dump('#include "ompi_config.h"')
    out.dump('#include "mpi.h"')
    out.dump('#include "ompi/errhandler/errhandler.h"')
    out.dump('#include "ompi/mpi/fortran/mpif-h/status-conversion.h"')
    out.dump('#include "ompi/mpi/fortran/base/constants.h"')
    out.dump('#include "ompi/mpi/fortran/base/fint_2_int.h"')
    out.dump('#include "ompi/mpi/fortran/base/fortran_base_strings.h"')
    out.dump('#include "ompi/mpi/fortran/base/fortran_base_topo_neighbors.h"')
    out.dump('#include "ompi/mpi/fortran/base/ts.h"')
    out.dump('#include "ompi/request/request.h"')
    out.dump('#include "ompi/request/grequest.h"')
    out.dump('#include "ompi/communicator/communicator.h"')
    out.dump('#include "ompi/win/win.h"')
    out.dump('#include "ompi/file/file.h"')
    out.dump('#include "ompi/errhandler/errhandler.h"')
    out.dump('#include "ompi/datatype/ompi_datatype.h"')
    out.dump('#include "ompi/attribute/attribute.h"')
    out.dump('#include "ompi/mca/coll/base/coll_base_util.h"')
    out.dump('#include "ompi/mpi/fortran/use-mpi-f08/base/bigcount.h"')
    out.dump('#include "ompi/mpi/fortran/use-mpi-f08/base/datarep_f08.h"')


def print_binding(prototype, lang, out, bigcount=False, template=None, needs_ts=False, gen_f90=False, param_names=None):
    """Print the binding with or without bigcount."""
    binding = FortranBinding(prototype, out=out, bigcount=bigcount, template=template, needs_ts=needs_ts,
                             gen_f90=gen_f90, param_names=param_names)
    if lang == 'fortran':
        binding.print_f_source()
    else:
        binding.print_c_source()


# As for the C bindings, a procedure whose large count version differs
# from the regular one in more than the kinds of its arguments (e.g.
# MPI_Type_get_envelope, which has an extra num_large_counts argument) has
# two templates: <name>.c.in_nbc ("no big count") for just the regular
# version, and <name>_c.c.in_obc ("only big count") for just the large
# count version.
NBC_TEMPLATE_SUFFIX = '.c.in_nbc'
OBC_TEMPLATE_SUFFIX = '.c.in_obc'


def load_function_templates(prototype_files):
    """Load the templates from a file list."""
    templates = []
    for fname in prototype_files:
        template = SourceTemplate.load(fname, type_constructor=FortranType.construct)
        template.no_bigcount = fname.endswith(NBC_TEMPLATE_SUFFIX)
        template.only_bigcount = fname.endswith(OBC_TEMPLATE_SUFFIX)
        if template.only_bigcount and not template.prototype.name.endswith('_c'):
            raise util.BindingError(f'{fname}: the procedure name of a {OBC_TEMPLATE_SUFFIX} '
                                    'template must end in _c')
        templates.append(template)
    return templates


def template_fn_name(template):
    """Return the base name of the procedure, without the _c of an obc template."""
    name = template.prototype.name
    return name[:-len('_c')] if getattr(template, 'only_bigcount', False) else name


def template_has_regular(template):
    """Does the template give the regular version of the procedure?"""
    return not getattr(template, 'only_bigcount', False)


def template_has_bigcount(template):
    """Does the template give the large count version of the procedure?"""
    if getattr(template, 'only_bigcount', False):
        return True
    if getattr(template, 'no_bigcount', False):
        return False
    return util.prototype_has_bigcount(template.prototype)


def generate_code(args, out):
    """Generate binding code based on arguments."""
    templates = load_function_templates(args.prototype_files)

    if args.fort_std == 'f08' or args.fort_std == None:
        gen_f90 = False
    else:
        gen_f90 = True

    # Standard dummy-argument names are only applied to the Fortran
    # interfaces, never to the C back-end (whose body refers to the template's
    # internal names)
    std_names = standard_parameter_names(args.pympistd_dir, use_f90=gen_f90) if (args.lang == 'fortran') else {}

    if args.lang == 'fortran':
        print_f_source_header(out)
        out.dump()
        print_profiling_rename_macros(templates, out, args)
        out.dump()
    else:
        print_c_source_header(out)

    for template in templates:
        has_buffers = util.prototype_has_buffers(template.prototype)
        needs_ts = has_buffers and args.generate_ts_suffix

        # use-mpi needs generated procedure only for the suffixed ts functions
        # Rest are covered by mpif-h already
        # TODO: will need to change if mpifhh is removed or significantly refactored
        if gen_f90 and not needs_ts:
            continue
        out.dump()
        param_names = std_names.get('mpi_' + template.prototype.name.lower())
        if template_has_regular(template):
            print_binding(template.prototype, args.lang, out, template=template, needs_ts=needs_ts,
                          gen_f90=gen_f90, param_names=param_names)
        if template_has_bigcount(template) and gen_f90 == False:
            out.dump()
            # The C wrapper is always built; it is only called if the
            # Fortran procedure is.
            guard = (args.lang == 'fortran' and
                     util.prototype_bigcount_needs_distinct_kinds(template.prototype))
            if guard:
                out.dump(f'#if {util.DISTINCT_COUNT_ADDRESS_KINDS}')
            print_binding(template.prototype, args.lang, bigcount=True, out=out, template=template,
                          needs_ts=needs_ts, param_names=param_names)
            if guard:
                out.dump('#endif')


def generate_interface(args, out):
    """Generate the Fortran interface files."""
    out.dump(f'! {consts.GENERATED_MESSAGE}')

    templates = load_function_templates(args.prototype_files)
    print_profiling_rename_macros(templates, out, args)

    if args.fort_std == 'f08' or args.fort_std == None:
        print("I am setting gen_f90 to false")
        gen_f90 = False
    else:
        print("I am setting gen_f90 to true")
        gen_f90 = True

    # The interface specifications are part of the user-visible use mpi(_f08)
    # modules, so they use the standard MPI dummy-argument names too.
    std_names = standard_parameter_names(args.pympistd_dir, use_f90=gen_f90)

    for template in templates:
        # use mpi has no large count versions
        if gen_f90 and not template_has_regular(template):
            continue
        ext_name = util.ext_api_func_name(template_fn_name(template))
        # The regular and large count versions of a procedure with nbc and
        # obc templates are in two interface blocks for the same generic
        # name, which Fortran allows.
        out.dump(f'interface {ext_name}')
        has_buffers = util.prototype_has_buffers(template.prototype)
        needs_ts = has_buffers and args.generate_ts_suffix
        param_names = std_names.get('mpi_' + template.prototype.name.lower())
        if template_has_regular(template):
            binding = FortranBinding(template.prototype, template=template, needs_ts=needs_ts,
                                     gen_f90=gen_f90, out=out, param_names=param_names)
            binding.print_interface()
        if template_has_bigcount(template) and gen_f90 == False:
            if util.prototype_bigcount_is_separate(template.prototype):
                # The bigcount version cannot be told apart from the regular
                # one, so it gets its own generic name, e.g. MPI_Op_create_c
                out.dump(f'end interface {ext_name}')
                ext_name = util.ext_api_func_name(template_fn_name(template), bigcount=True)
                out.dump(f'interface {ext_name}')
            elif template_has_regular(template):
                out.dump()
            # If the two versions differ only in INTEGER(KIND=MPI_ADDRESS_KIND)
            # vs. INTEGER(KIND=MPI_COUNT_KIND), they cannot be told apart when
            # the kinds are the same; the standard then omits the _c version.
            guard = util.prototype_bigcount_needs_distinct_kinds(template.prototype)
            if guard:
                out.dump(f'#if {util.DISTINCT_COUNT_ADDRESS_KINDS}')
            binding_c = FortranBinding(template.prototype, out=out, template=template,
                                       needs_ts=needs_ts, bigcount=True, param_names=param_names)
            binding_c.print_interface()
            if guard:
                out.dump('#endif')
        out.dump(f'end interface {ext_name}')
