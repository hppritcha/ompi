#!/usr/bin/env python3

# Note: keep the various ***{*** ... ***}*** comments.  They help in
# locating where the python code generates sections, eg of #ifdef
# #endif pairs.  I have the *** directly in front of each print() that
# opens/closes a section.

import re
import sys
import os
from pprint import pprint
from dataclasses import dataclass
from enum import Enum, auto

os.environ['MPISTANDARD'] = 'mpi-standard';
sys.path.append('mpi-standard')
sys.path.append('py-mpi-standard/src')
import pympistandard as std
std.use_api_version(1)

# Tell whether we're generating code for a Fortran08 short or
# long interface.  Ex in MPI_SEND(, count,.. ) is count
# INTEGER or INTEGER(KIND=MPI_COUNT_KIND).
class WhichInterface(Enum):
    SHORT = auto()
    LONG = auto()

class NeedsConversion(Enum):
    ALWAYS = auto()
    NEVER = auto()
    CONDITIONAL = auto()

#class ArgConversionRequirement(Enum):
#    UNEXAMINED = auto()
#    PASSTHROUGH = auto()
#    ALWAYS_NEEDS_CONERSION = auto()
#    MIGHT_NEED_CONERSION = auto() # would have an ifdef

# If the user checks out the git repo vs just the tar file
# xxxxxxxxxxxx not sure right offhand how to do that, if we
# want to use opal_config.h we'd have to run during configure, but
# only do so if the tree was from git because we don't want to
# burden tarfile users with all the python and mpi-standard
# dependencies
class GenerationMode(Enum):
    USE_GENERAL_PURPOSE_IFDEFS = auto()
    USE_CONFIG_H_SIZES = auto()

class CVarState(Enum):
    UNEXAMINED = auto()
    ALWAYS_PASSTHROUGH = auto()
    NEEDS_CVAR = auto() # might remove this one xxxxxx
    DECLARED = auto()
    INVAL_IS_CONVERTED = auto()
    OUTVAL_IS_CONVERTED = auto()

@dataclass
class ProcessingState:
    fortran_size_interface = WhichInterface.SHORT
    c_size_interface = WhichInterface.SHORT
    logical_name = None  # of function we're on, eg 'mpi_allgatherv'
    fn = None            # std.PROCEDURES[logical_name]
    fout = None          # file handle we're currently writing to
    generation_mode = GenerationMode.USE_GENERAL_PURPOSE_IFDEFS

context = ProcessingState

@dataclass
class ArgInfo:
    # the argument name at the Fortran call into C, eg "sendbuf", "count"
    # etc in void ompi_isend_f(char *sendbuf, MPI_Fint *count, ...)
    fvarname= None

    needs_conversion: NeedsConversion = NeedsConversion.NEVER # default until updated
    # Preprocessor #if (...) expression for when this arg needs conversion into c_something
    ifdef_for_conversion = None
    cvarname = None # only used in the "if conversion" paths
    cvar_state = CVarState.UNEXAMINED

#xxxx
    cvar_is_separate = True
    cexpression = None  # this is the code that would be used in the MPI call
    # if it's its own new variable it'll be "c_something"
    # the arg's info from the standard's express.f90.parameters[x]
    f90parameter: std.f90.F90Parameter = None
    inval_is_converted = False
    outval_is_converted = False
    # if this arg contains integer information pertaining to array sizes for other args
    intval_to_provide = None
    intval_varname = None
    intval_to_consume = None
    #array_size_varname: str = None
    # is this arg an array
    is_array = False

# Defaults.  Read these later from opal_config.h
sizeof_type = {
    'int' : 4,
    'MPI_Count' : 8,
    'MPI_Offset' : 8,
    'MPI_Aint' : 8,
    'INTEGER' : 4,
    'LOGICAL' : 4,
    'INTEGER(KIND=MPI_COUNT_KIND)' : 8,
    'INTEGER(KIND=MPI_OFFSET_KIND)' : 8,
    'INTEGER(KIND=MPI_ADDRESS_KIND)' : 8,
}

# opal_config.h has things like
# #define OMPI_SIZEOF_FORTRAN_INTEGER 4
# #define OMPI_SIZEOF_FORTRAN_DOUBLE_PRECISION 8
def read_opal_config_sizes(fname):
    print(f"Reading #defines from {fname}")
    config_h_defs = {
        'int'                            : 'SIZEOF_INT',
        'MPI_Count'                      : 'OMPI_MPI_COUNT_SIZE',
        'MPI_Offset'                     : 'OMPI_MPI_OFFSET_SIZE',
        'MPI_Aint'                       : 'SIZEOF_PTRDIFF_T',
        'INTEGER'                        : 'OMPI_SIZEOF_FORTRAN_INTEGER',
        'LOGICAL'                        : 'OMPI_SIZEOF_FORTRAN_LOGICAL',
        'INTEGER(KIND=MPI_COUNT_KIND)'   : 'OMPI_MPI_COUNT_SIZE',
        'INTEGER(KIND=MPI_OFFSET_KIND)'  : 'OMPI_MPI_OFFSET_SIZE',
        'INTEGER(KIND=MPI_ADDRESS_KIND)' : 'SIZEOF_PTRDIFF_T',
    }
    with open(fname, "r") as fin:
        for line in fin:
            for what_type in config_h_defs:
                cconst = config_h_defs[what_type]
                m = re.match(fr"^\s*#define\s+{cconst}\s+([0-9]+)", line)
                if m:
                    sizeof_type[what_type] = m.group(1)
                    print(f"  {what_type:<32} size: {m.group(1)} (from {cconst})")
    return

def main():
    global context

    # cmdline is either nothing (meaning produce general purpose code with
    # ifdefs) or an opal_config.h file
    if (len(sys.argv) >= 2):
        context.generation_mode = GenerationMode.USE_CONFIG_H_SIZES
        read_opal_config_sizes(sys.argv[1])
        # example_opal_config_h = 'ompi/opal/include/opal_config.h'

    generate_prototypes_mpi_h()

    body_by_hand = {
        'mpi_f_sync_reg': True,
        'mpi_sizeof': True,
        'mpi_keyval_create': True,
        'mpi_comm_create_keyval': True,
        'mpi_type_create_keyval': True,
        'mpi_win_create_keyval': True,
        'mpi_register_datarep': True,
        'mpi_attr_get': True,
        'mpi_attr_put': True,
    }

    for fn in std.all_f90_procedures():
        context.fn = fn
        logical_name = fn.name
        context.logical_name = logical_name
        filename = re.sub('mpi_', '', logical_name) + "_f.c"
        print('Generating ' + filename)
        # pprint(vars(fn))
        with open("Gen/" + filename, "w") as fout:
            context.fout = fout
            print('#include \"ompi_config.h\"', file=context.fout)
            print('#include \"ompi/mpi/fortran/mpif-h/bindings.h\"', file=fout)
            print('#include \"ompi/mpi/fortran/base/constants.h\"', file=fout)
            print('', file=fout)

# Make aliases (or mini-wrapper fns) for things like mpi_send__() -> ompi_send_f().
# Will later define ompi_send_f() as well as ompi_send_c_f() but the latter doesn't
# need aliases because there aren't F77 bindings for the long interface.  The
# ompi_send_c_f() is just used by the F08 interface when they want to implement a
# long interface call.
#
# Anyway that's why this part only sets up entrypoint aliases/definitions for the
# short interface:
            context.fortran_size_interface = WhichInterface.SHORT
            print_f_entrypoint_definitions()

            make_static_for_func_name_if_no_comm_win_file_in_args()

            if (body_by_hand.get(logical_name, False)):
                print('', file=fout)
                print(f"#include \"byhand_{filename}\"", file=fout)
                continue

            print_f_definition()
            print_f_body()

# xxxxxxxxx put this back later
#           if (fn.has_embiggenment()):
#               context.fortran_size_interface = WhichInterface.LONG
#               print_f_definition()
#               print_f_body()

# Some wrappers call ompi_something() instead of MPI_Something() and
# if so, they trigger an errhandler on non-success.  If it's an MPI function
# w/o a comm/win/file connected to it, then the errorhandler-triggering macro
# wants a function name.  So that's why this subset of functions gets a
#     static const char FUNC_NAME[] = "MPI_Something";
# added before the main function definition.
#
# It's probably harmless to universally add these, but browsing the old
# by-hand files they were only created for this subset of functions.

def make_static_for_func_name_if_no_comm_win_file_in_args():
    global context
    fn = context.fn
    logical_name = context.logical_name
    fout = context.fout

    name_upcase = logical_name.upper()        # eg 'MPI_ALLGATHERV'

    comm_or_etc_found_in_args = False
    for arg in fn.express.f90.parameters:
        if (arg.kind.iso_c_small == 'MPI_Comm'):
            comm_or_etc_found_in_args = True
        if (arg.kind.iso_c_small == 'MPI_Win'):
            comm_or_etc_found_in_args = True
        if (arg.kind.iso_c_small == 'MPI_File'):
            comm_or_etc_found_in_args = True

    # In the original code there's a short list that sets the name to
    # MPI_Comm_create_keyval_f, MPI_keyval_create_f, MPI_Type_create_keyval_f
    # MPI_Type_match_size_f
    # vs most that set them to MPI_WAITALL, MPI_WAITANY etc
    # I'm going to stick with the fully upper case MPI_WAITALL style
    if (not comm_or_etc_found_in_args):
        print(f"static const char FUNC_NAME[] = \"{name_upcase}\";", file=fout)

# Each Fortran file exists (via soft links) as both abort_f.c and pabort_f.c
# for example.  The latter is built with OMPI_BUILD_MPI_PROFILING.  The files
# will define ompi_abort_f() and pompi_abort_f() respectively.  The bindings
# printed here create mpi_abort__() etc to call ompi_abort_f().
#
# The structure is
#   #if ! OMPI_BUILD_MPI_PROFILING   (eg if this is abort_f.c)
#     #if OPAL_HAVE_WEAK_SYMBOLS     (if we can make pragmas)
#       pragma to point mpi_abort__ etc at ompi_abort_f
#     #else
#       create tiny wrapper functions where mpi_abort__ etc call ompi_abort_f
#     #endif
#   #else                            (eg for pabort_f.c)
#     #if OPAL_HAVE_WEAK_SYMBOLS     (if we can make pragmas)
#       pragma to point pmpi_abort__ etc at ompi_abort_f
#     #else
#       create tiny wrapper functions where pmpi_abort__ etc call ompi_abort_f
#     #endif
#
#     #define ompi_abort_f pompi_abort_f (to change the main function def in )
#   #endif

def print_f_entrypoint_definitions():
    global context
    logical_name = context.logical_name
    fout = context.fout

    print("#if ! OMPI_BUILD_MPI_PROFILING // {", file=fout)
    print_weak_pragmas_or_miniwrappers('mode:mpi')
    print("#else // }{", file=fout)
    print_weak_pragmas_or_miniwrappers('mode:pmpi')

# Now we're past all the pragmas/entry-wrappers, and are about to move on to the
# definition of ompi_abort_f().  For the profiling version this is where we redefine
# ompi_abort_f to pompi_abort_f
    print("#define "
        + "o" + logical_name + '_f'         # eg ompi_abort_f
        + ' '
        + "po" + logical_name + '_f',       # eg pompi_abort_f
        file=fout)
    print("#endif // }", file=fout)

# Here we generate
#   #if OPAL_HAVE_WEAK_SYMBOLS     (if we can make pragmas)
#     pragma to point [p]mpi_abort__ etc at ompi_abort_f
#   #else
#     create tiny wrapper functions where [p]mpi_abort__ etc call ompi_abort_f
#   #endif

def print_weak_pragmas_or_miniwrappers(mode_pmpi_or_mpi):
    global context
    fn = context.fn
    logical_name = context.logical_name
    fout = context.fout

# if OPAL_HAVE_WEAK_SYMBOLS, we produce definitions for the 4 basic F entries
# (eg for pmpi_allgatherv_ etc in this part of the ifdef due to MPI_PROFILING)
# ***{***
    print("#if OPAL_HAVE_WEAK_SYMBOLS // {", file=fout)
    name_suffix = re.sub('mpi_', '', logical_name)  # eg 'allgatherv'
    name_suffix_c = name_suffix.capitalize()        # eg 'Allgatherv'
    name_suffix_upcase = name_suffix.upper()        # eg 'ALLGATHERV'
    if (mode_pmpi_or_mpi == 'mode:mpi'):
        tmplist = (
            f"MPI_{name_suffix_upcase}",
            f"mpi_{name_suffix}",
            f"mpi_{name_suffix}_",
            f"mpi_{name_suffix}__")
    else:
        tmplist = (
            f"PMPI_{name_suffix_upcase}",
            f"pmpi_{name_suffix}",
            f"pmpi_{name_suffix}_",
            f"pmpi_{name_suffix}__")

    for mpi_foo_ in (tmplist):
        print(f"#pragma weak {mpi_foo_} = ompi_{name_suffix}_f", file=fout)
    print("", file=fout)
# Create aliases for PMPI_Foo_f and PMPI_Foo_f08 too, probably called from
# f08 wrappers (?)
    if (mode_pmpi_or_mpi == 'mode:mpi'):
        tmplist = (
            f"MPI_{name_suffix_c}_f",
            f"MPI_{name_suffix_c}_f08")
    else:
        tmplist = (
            f"PMPI_{name_suffix_c}_f",
            f"PMPI_{name_suffix_c}_f08")
    for name in (tmplist):
        print(f"#pragma weak {name} = ompi_{name_suffix}_f", file=fout)
# else generate 4 functions that resemble
# void pmpi_allgather_(char *sbuf, ..) { pompi_allgather_f(sbuf, ..); }
# We don't really need to use the OMPI_GENERATE_F77_BINDINGS macro for this, but
# for ease of diff against existing files I'll initially code it that way (that
# macro is used for functions that return ierr, eg the typeical MPI case)
# ***} else {***
    print("#else // }{", file=fout)
# so if there's an ierr return value we'll create an OMPI_GENERATE_F77_BINDINGS
# else we'll generate 4 small function definitions directly
    if (mode_pmpi_or_mpi == 'mode:mpi'):
        prefix_upcase = "MPI"
        prefix_lowcase = "mpi"
    else:
        prefix_upcase = "PMPI"
        prefix_lowcase = "pmpi"

    if (fn.express.f90.return_kind is None):
        print(f"OMPI_GENERATE_F77_BINDINGS ({prefix_upcase}_{name_suffix_upcase},", file=fout)
        print(f"                           {prefix_lowcase}_{name_suffix},", file=fout)
        print(f"                           {prefix_lowcase}_{name_suffix}_,", file=fout)
        print(f"                           {prefix_lowcase}_{name_suffix}__,", file=fout)
        print(f"                           ompi_{name_suffix}_f,", file=fout)
        print(f"                           ("
            + f90_arginfo_to_fndef_parameters_in_c(
            fn.express.f90.parameters) + '),', file=fout)
        print(f"                           ("
            + f90_arginfo_to_fncall_parameters_in_c(
            fn.express.f90.parameters) + ') )', file=fout)
    else:
        c_return_type = f90_return_kind_to_c_return_type(fn.express.f90.return_kind)
# Printing 4 function definitions of the form
# MPI_Aint pmpi_aint_add_(MPI_Aint *base, MPI_Aint *diff) { return pompi_aint_add_f(base, diff); }
        tmplist = (
            f"PMPI_{name_suffix_upcase}",
            f"pmpi_{name_suffix}",
            f"pmpi_{name_suffix}_",
            f"pmpi_{name_suffix}__")
        for pmpi_foo_ in (tmplist):
            print(f"{c_return_type} {pmpi_foo_}"
                + f'({f90_arginfo_to_fndef_parameters_in_c(fn.express.f90.parameters)}) '
                + f'{{ return ompi_{name_suffix}_f('
                + f'{f90_arginfo_to_fncall_parameters_in_c(fn.express.f90.parameters)}); }}'
                , file=fout)

# ***}***
    print("#endif // }", file=fout)

# Ex of what the below produces:
#
# void
# ompi_allgatherv_f(char *sendbuf,MPI_Fint *sendcount, MPI_Fint *sendtype,
#                   char *recvbuf, MPI_Fint *recvcounts, MPI_Fint *displs,
#                   MPI_Fint *recvtype, MPI_Fint *comm, MPI_Fint *ierr)
def print_f_definition():
    fn = context.fn
    logical_name = context.logical_name
    fout = context.fout

    name_suffix = re.sub('mpi_', '', logical_name)  # eg 'allgatherv'

    # is this a typical MPI routine with no return or is it like MPI_Wtime:
    print('', file=fout)
    if (fn.express.f90.return_kind is None):
        print(f"void", file=fout)
    else:
        c_return_type = f90_return_kind_to_c_return_type(fn.express.f90.return_kind)
        print(f"{c_return_type}", file=fout)

    ompi_fn_name = f"ompi_{name_suffix}_f"
    if (context.fortran_size_interface == WhichInterface.LONG):
        ompi_fn_name = f"ompi_{name_suffix}_c_f"
    print(f"{ompi_fn_name}("
        + f90_arginfo_to_fndef_parameters_in_c(fn.express.f90.parameters)
        + ')'
        , file=fout)

def generate_prototypes_mpi_h():
    with open("Gen/prototypes_mpi_generated.h", "w") as fout:
        for fn in std.all_f90_procedures():
            interfaces = [WhichInterface.SHORT]
            if fn.has_embiggenment():
                interfaces = [interfaces, WhichInterface.LONG]
            for interface in interfaces:
                context.fortran_size_interface = interface
                name_suffix = re.sub('mpi_', '', fn.name)  # eg 'allgatherv'
                if (interface == WhichInterface.LONG):
                    name_suffix = f"{name_suffix}_c"
                args = f90_arginfo_to_fndef_parameters_in_c(fn.express.f90.parameters)

# The old prototypes_mpi.h had a macro that generated this for example for mpi_abort:
#   /* Prototype the actual OMPI function */
#   OMPI_DECLSPEC void ompi_abort_f (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   /* Prototype the 4 versions of the MPI mpif.h name */
#   OMPI_DECLSPEC void mpi_abort (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   OMPI_DECLSPEC void mpi_abort_ (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   OMPI_DECLSPEC void mpi_abort__ (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   OMPI_DECLSPEC void MPI_ABORT (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   /* Prototype the use mpi/use mpi_f08 names  */
#   OMPI_DECLSPEC void MPI_Abort_f08 (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   OMPI_DECLSPEC void MPI_Abort_f (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   /* Prototype the actual POMPI function */
#   OMPI_DECLSPEC void pompi_abort_f (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   /* Prototype the 4 versions of the PMPI mpif.h name */
#   OMPI_DECLSPEC void pmpi_abort (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   OMPI_DECLSPEC void pmpi_abort_ (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   OMPI_DECLSPEC void pmpi_abort__ (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   OMPI_DECLSPEC void PMPI_ABORT (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   /* Prototype the use mpi/use mpi_f08 PMPI names  */
#   OMPI_DECLSPEC void PMPI_Abort_f08 (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);
#   OMPI_DECLSPEC void PMPI_Abort_f (MPI_Fint *comm, MPI_Fint *errorcode, MPI_Fint *ierr);

                for mpi_foo in ( \
                        f"ompi_{name_suffix}_f",
                        f"mpi_{name_suffix}",
                        f"mpi_{name_suffix}_",
                        f"mpi_{name_suffix}__",
                        f"MPI_{name_suffix.upper()}",
                        f"MPI_{name_suffix.capitalize()}_f08",
                        f"MPI_{name_suffix.capitalize()}_f",
                        f"pompi_{name_suffix}_f",
                        f"pmpi_{name_suffix}",
                        f"pmpi_{name_suffix}_",
                        f"pmpi_{name_suffix}__",
                        f"PMPI_{name_suffix.upper()}",
                        f"PMPI_{name_suffix.capitalize()}_f08",
                        f"PMPI_{name_suffix.capitalize()}_f"):
                    if (fn.express.f90.return_kind is None):
                        c_return_type = 'void'
                    else:
                        c_return_type = f90_return_kind_to_c_return_type(fn.express.f90.return_kind)

                    print(f"OMPI_DECLSPEC {c_return_type} {mpi_foo}({args});", file=fout)
# xxx consider doing the above for long interface, eg MPI_Send_c

    return

def buffer_can_be_in_place(logical_name, arg, argidx):
    arg_that_can_be_in_place = {
        'mpi_gather': 0,
        'mpi_gatherv': 0,
        'mpi_scatter': 3,
        'mpi_scatterv': 4,
        'mpi_allgather': 0,
        'mpi_allgatherv': 0,
        'mpi_alltoall': 0,
        'mpi_alltoallv': 0,
        'mpi_alltoallw': 0,
        'mpi_reduce': 0,
        'mpi_allreduce': 0,
        'mpi_reduce_scatter_block': 0,
        'mpi_reduce_scatter': 0,
        'mpi_scan': 0,
        'mpi_exscan': 0,
    }

    i = arg_that_can_be_in_place.get(logical_name, -1)
    if (i != -1 and argidx == i):
        return True

    return False

# This is used while building a C call, so for example we're in ompi_send_f()
# or ompi_send_c_f() where a poly int is now specifically MPI_Fint / MPI_Count etc.
# patterns:
#   comm:
#   userbuf:
#   fint_count:
#   aint_count:
#   oint_count:
#   array_of_fint_counts:
#   array_of_aint_counts:
#   array_of_oint_counts:
#   datatype:
#   array_of_datatypes:
def identify_pattern_for_arg(fn, arg, argidx):
    if (arg.kind.name == 'BUFFER'):
        return('userbuf')
    elif (arg.kind.name == 'DATATYPE'):
        if (arg.dimensions == ''):
            return('datatype')
        elif (arg.dimensions == '(*)'):
            return('array_of_datatypes')
        else:
            return('xxx')
    elif (arg.kind.name == 'POLYXFER_NUM_ELEM_NNI'):
        if (arg.dimensions == ''):
            return('fint_count')
        elif (arg.dimensions == '(*)'):
            return('array_of_fint_counts')
        else:
            return('xxx')


def find_size(fn, arg_name):
    array_size = {
        # will probably leave spawn* by hand
        'MPI_COMM_SPAWN:ARRAY_OF_ERRCODES' : 'MAXPROCS',
        # spawn multiple has
        #   count = number of commands
        #   array_of_maxprocs size: count integers
        #   array_errcds size: sum of all of array_of_maxprocs
        'MPI_COMM_SPAWN_MULTIPLE:ARRAY_OF_COMMANDS' : 'COUNT',
        'MPI_COMM_SPAWN_MULTIPLE:ARRAY_OF_ARGV' : 'COUNT',
        'MPI_COMM_SPAWN_MULTIPLE:ARRAY_OF_MAXPROCS' : 'COUNT',
        'MPI_COMM_SPAWN_MULTIPLE:ARRAY_OF_INFO' : 'COUNT',
        'MPI_COMM_SPAWN_MULTIPLE:ARRAY_OF_ERRCODES' : 'fintsum ARRAY_OF_MAXPROCS COUNT',
        'MPI_CART_COORDS:COORDS' : 'MAXDIMS',
        'MPI_DIMS_CREATE:DIMS' : 'NDIMS',
        'MPI_CART_CREATE:DIMS' : 'NDIMS',
        'MPI_CART_CREATE:PERIODS' : 'NDIMS',
        'MPI_CART_GET:DIMS' : 'MAXDIMS',
        'MPI_CART_GET:PERIODS' : 'MAXDIMS',
        'MPI_CART_GET:COORDS' : 'MAXDIMS',
        'MPI_CART_MAP:DIMS' : 'NDIMS',
        'MPI_CART_MAP:PERIODS' : 'NDIMS',
        'MPI_CART_RANK:COORDS' : 'cartdim COMM',
        'MPI_CART_SUB:REMAIN_DIMS' : 'cartdim COMM',
        'MPI_GRAPH_CREATE:INDEX' : 'NNODES',
        'MPI_GRAPH_CREATE:EDGES' : 'fintlast INDEX NNODES',
        'MPI_GRAPH_GET:INDEX' : 'MAXINDEX',
        'MPI_GRAPH_GET:EDGES' : 'MAXEDGES',
        'MPI_GRAPH_MAP:INDEX' : 'NNODES',
        'MPI_GRAPH_MAP:EDGES' : 'fintlast INDEX NNODES',
        'MPI_GRAPH_NEIGHBORS:NEIGHBORS' : 'MAXNEIGHBORS',
        'MPI_GROUP_EXCL:RANKS' : 'N',
        'MPI_GROUP_INCL:RANKS' : 'N',
        'MPI_GROUP_RANGE_EXCL:RANGES' : 'N', # it's N 3-tuples of ints anyway
        'MPI_GROUP_RANGE_INCL:RANGES' : 'N', # it's N 3-tuples of ints anyway
        'MPI_GROUP_TRANSLATE_RANKS:RANKS1' : 'N',
        'MPI_GROUP_TRANSLATE_RANKS:RANKS2' : 'N',
        'MPI_DIST_GRAPH_CREATE:SOURCES' : 'N',
        'MPI_DIST_GRAPH_CREATE:DEGREES' : 'N',
        'MPI_DIST_GRAPH_CREATE:DESTINATIONS' : 'fintsum DEGREES N',
        'MPI_DIST_GRAPH_CREATE:WEIGHTS' : 'fintsum DEGREES N',
        'MPI_DIST_GRAPH_CREATE_ADJACENT:SOURCES' : 'INDEGREE',
        'MPI_DIST_GRAPH_CREATE_ADJACENT:SOURCEWEIGHTS' : 'INDEGREE',
        'MPI_DIST_GRAPH_CREATE_ADJACENT:DESTINATIONS' : 'OUTDEGREE',
        'MPI_DIST_GRAPH_CREATE_ADJACENT:DESTWEIGHTS' : 'OUTDEGREE',
        'MPI_DIST_GRAPH_NEIGHBORS:SOURCES' : 'MAXINDEGREE',
        'MPI_DIST_GRAPH_NEIGHBORS:SOURCEWEIGHTS' : 'MAXINDEGREE',
        'MPI_DIST_GRAPH_NEIGHBORS:DESTINATIONS' : 'MAXOUTDEGREE',
        'MPI_DIST_GRAPH_NEIGHBORS:DESTWEIGHTS' : 'MAXOUTDEGREE',
        'MPI_PREADY_LIST:ARRAY_OF_PARTITIONS' : 'LENGTH',
        'MPI_STARTALL:ARRAY_OF_REQUESTS' : 'commsize COUNT',
        'MPI_TESTALL:ARRAY_OF_REQUESTS' : 'commsize COUNT',
        'MPI_TESTALL:ARRAY_OF_STATUSES' : 'commsize COUNT',
        'MPI_TESTANY:ARRAY_OF_REQUESTS' : 'commsize COUNT',
        'MPI_TESTANY:ARRAY_OF_STATUSES' : 'commsize COUNT',
        'MPI_TESTSOME:ARRAY_OF_REQUESTS' : 'commsize INCOUNT',
        'MPI_TESTSOME:ARRAY_OF_STATUSES' : 'commsize INCOUNT',
        'MPI_TESTSOME:ARRAY_OF_INDICES' : 'commsize OUTCOUNT', # only valid post-call, is okay
        'MPI_WAITALL:ARRAY_OF_REQUESTS' : 'commsize COUNT',
        'MPI_WAITALL:ARRAY_OF_STATUSES' : 'commsize COUNT',
        'MPI_WAITANY:ARRAY_OF_REQUESTS' : 'commsize COUNT',
        'MPI_WAITANY:ARRAY_OF_STATUSES' : 'commsize COUNT',
        'MPI_WAITSOME:ARRAY_OF_REQUESTS' : 'commsize INCOUNT',
        'MPI_WAITSOME:ARRAY_OF_STATUSES' : 'commsize INCOUNT',
        'MPI_WAITSOME:ARRAY_OF_INDICES' : 'commsize OUTCOUNT', # only valid post-call, is okay
        'MPI_TYPE_CREATE_HINDEXED:ARRAY_OF_BLOCKLENGTHS' : 'COUNT',
        'MPI_TYPE_CREATE_HINDEXED:ARRAY_OF_DISPLACEMENTS' : 'COUNT',
        'MPI_TYPE_CREATE_HINDEXED_BLOCK:ARRAY_OF_DISPLACEMENTS' : 'COUNT',
        'MPI_TYPE_CREATE_INDEXED_BLOCK:ARRAY_OF_DISPLACEMENTS' : 'COUNT',
        'MPI_TYPE_CREATE_STRUCT:ARRAY_OF_BLOCKLENGTHS' : 'COUNT',
        'MPI_TYPE_CREATE_STRUCT:ARRAY_OF_DISPLACEMENTS' : 'COUNT',
        'MPI_TYPE_CREATE_STRUCT:ARRAY_OF_TYPES' : 'COUNT',
        'MPI_TYPE_CREATE_DARRAY:ARRAY_OF_GSIZES' : 'NDIMS',
        'MPI_TYPE_CREATE_DARRAY:ARRAY_OF_DISTRIBS' : 'NDIMS',
        'MPI_TYPE_CREATE_DARRAY:ARRAY_OF_DARGS' : 'NDIMS',
        'MPI_TYPE_CREATE_DARRAY:ARRAY_OF_PSIZES' : 'NDIMS',
        'MPI_TYPE_CREATE_SUBARRAY:ARRAY_OF_SIZES' : 'NDIMS',
        'MPI_TYPE_CREATE_SUBARRAY:ARRAY_OF_SUBSIZES' : 'NDIMS',
        'MPI_TYPE_CREATE_SUBARRAY:ARRAY_OF_STARTS' : 'NDIMS',
        'MPI_TYPE_INDEXED:ARRAY_OF_BLOCKLENGTHS' : 'COUNT',
        'MPI_TYPE_INDEXED:ARRAY_OF_DISPLACEMENTS' : 'COUNT',
        'MPI_TYPE_GET_CONTENTS:ARRAY_OF_INTEGERS' : 'MAX_INTEGERS', # sort of true, is okay
        'MPI_TYPE_GET_CONTENTS:ARRAY_OF_ADDRESSES' : 'MAX_INTEGERS',
        'MPI_TYPE_GET_CONTENTS:ARRAY_OF_DATATYPES' : 'MAX_INTEGERS',
        'MPI_ALLGATHERV:RECVCOUNTS' : 'commsize COMM',
        'MPI_ALLGATHERV:DISPLS' : 'commsize COMM',
        'MPI_ALLGATHERV_INIT:RECVCOUNTS' : 'commsize COMM',
        'MPI_ALLGATHERV_INIT:DISPLS' : 'commsize COMM',
        'MPI_ALLTOALLV:SENDCOUNTS' : 'commsize COMM',
        'MPI_ALLTOALLV:SDISPLS' : 'commsize COMM',
        'MPI_ALLTOALLV:RECVCOUNTS' : 'commsize COMM',
        'MPI_ALLTOALLV:RDISPLS' : 'commsize COMM',
        'MPI_ALLTOALLV_INIT:SENDCOUNTS' : 'commsize COMM',
        'MPI_ALLTOALLV_INIT:SDISPLS' : 'commsize COMM',
        'MPI_ALLTOALLV_INIT:RECVCOUNTS' : 'commsize COMM',
        'MPI_ALLTOALLV_INIT:RDISPLS' : 'commsize COMM',
        'MPI_ALLTOALLW:SENDCOUNTS' : 'commsize COMM',
        'MPI_ALLTOALLW:SDISPLS' : 'commsize COMM',
        'MPI_ALLTOALLW:SENDTYPES' : 'commsize COMM',
        'MPI_ALLTOALLW:RECVCOUNTS' : 'commsize COMM',
        'MPI_ALLTOALLW:RDISPLS' : 'commsize COMM',
        'MPI_ALLTOALLW:RECVTYPES' : 'commsize COMM',
        'MPI_ALLTOALLW_INIT:SENDCOUNTS' : 'commsize COMM',
        'MPI_ALLTOALLW_INIT:SDISPLS' : 'commsize COMM',
        'MPI_ALLTOALLW_INIT:SENDTYPES' : 'commsize COMM',
        'MPI_ALLTOALLW_INIT:RECVCOUNTS' : 'commsize COMM',
        'MPI_ALLTOALLW_INIT:RDISPLS' : 'commsize COMM',
        'MPI_ALLTOALLW_INIT:RECVTYPES' : 'commsize COMM',
        'MPI_GATHERV:RECVCOUNTS' : 'commsize COMM',
        'MPI_GATHERV:DISPLS' : 'commsize COMM',
        'MPI_SCATTERV:SENDCOUNTS' : 'commsize COMM',
        'MPI_SCATTERV:DISPLS' : 'commsize COMM',
        'MPI_SCATTERV_INIT:SENDCOUNTS' : 'commsize COMM',
        'MPI_SCATTERV_INIT:DISPLS' : 'commsize COMM',
        'MPI_REDUCE_SCATTER:RECVCOUNTS' : 'commsize COMM',
        'MPI_REDUCE_SCATTER_INIT:RECVCOUNTS' : 'commsize COMM',
        'MPI_GATHERV_INIT:RECVCOUNTS' : 'commsize COMM',
        'MPI_GATHERV_INIT:DISPLS' : 'commsize COMM',
        'MPI_REDUCE_SCATTER:RECVCOUNTS' : 'commsize COMM',
        'MPI_IALLGATHERV:RECVCOUNTS' : 'commsize COMM',
        'MPI_IALLGATHERV:DISPLS' : 'commsize COMM',
        'MPI_IALLTOALLV:SENDCOUNTS' : 'commsize COMM',
        'MPI_IALLTOALLV:SDISPLS' : 'commsize COMM',
        'MPI_IALLTOALLV:RECVCOUNTS' : 'commsize COMM',
        'MPI_IALLTOALLV:RDISPLS' : 'commsize COMM',
        'MPI_IALLTOALLW:SENDCOUNTS' : 'commsize COMM',
        'MPI_IALLTOALLW:SDISPLS' : 'commsize COMM',
        'MPI_IALLTOALLW:SENDTYPES' : 'commsize COMM',
        'MPI_IALLTOALLW:RECVCOUNTS' : 'commsize COMM',
        'MPI_IALLTOALLW:RDISPLS' : 'commsize COMM',
        'MPI_IALLTOALLW:RECVTYPES' : 'commsize COMM',
        'MPI_IGATHERV:RECVCOUNTS' : 'commsize COMM',
        'MPI_IGATHERV:DISPLS' : 'commsize COMM',
        'MPI_ISCATTERV:SENDCOUNTS' : 'commsize COMM',
        'MPI_ISCATTERV:DISPLS' : 'commsize COMM',
        'MPI_IREDUCE_SCATTER:RECVCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLGATHERV:RECVCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLGATHERV:DISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLGATHERV_INIT:RECVCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLGATHERV_INIT:DISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLV:SENDCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLV:SDISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLV:RECVCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLV:RDISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLV_INIT:SENDCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLV_INIT:SDISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLV_INIT:RECVCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLV_INIT:RDISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW:SENDCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW:SDISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW:SENDTYPES' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW:RECVCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW:RDISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW:RECVTYPES' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW_INIT:SENDCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW_INIT:SDISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW_INIT:SENDTYPES' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW_INIT:RECVCOUNTS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW_INIT:RDISPLS' : 'commsize COMM',
        'MPI_NEIGHBOR_ALLTOALLW_INIT:RECVTYPES' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLGATHERV:RECVCOUNTS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLGATHERV:DISPLS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLV:SENDCOUNTS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLV:SDISPLS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLV:RECVCOUNTS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLV:RDISPLS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLW:SENDCOUNTS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLW:SDISPLS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLW:SENDTYPES' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLW:RECVCOUNTS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLW:RDISPLS' : 'commsize COMM',
        'MPI_INEIGHBOR_ALLTOALLW:RECVTYPES' : 'commsize COMM',
    }
    tmp = array_size.get(f"{fn.express.f90.name}:{arg_name}", None)
    if (tmp):
        # print(f"  {fn.express.f90.name}:{arg_name} : {tmp}  [found]")
        return tmp

    print(f"*** error {fn.express.f90.name} arg {arg_name} cant find size")
    exit(-1)
    return "?"

# Incoming args:
#     fn (so we can access the whole list of arguments)
#     argname = 'COMM' for example which by default means we want its Comm_size
#     what_int_value = if it's not 'default' it could be 'cartdim' for example
#                      in which case we want Cart_dim of COMM instead of its
#                      Comm_size.
#     arginfo = where we store the results
#
# Example of the context this function is used from:
# In MPI_Scatterv(, SENDCOUNTS, .., COMM) suppose we're processing SENDCOUNTS,
# and it has identified "COMM" as an argument from which it will need a size,
# we call this function with argname='COMM' and what_int_value='default' and
# fill in the info field representing info['COMM'] with its size.
def preprocess_arg_for_size(fn, argname, what_int_value, arginfo):
    for arg in (fn.express.f90.parameters):
        if (arg.name == argname):
            if (arg.kind.name == 'COMMUNICATOR'):
                c_comm = arginfo.cvarname
                arginfo.array_size_varname = f"{argname}_intval"
                if (what_int_value == 'cartdim'):
                    arginfo.array_size_formula = f"MPI_Cartdim_get(({c_comm}), &{arginfo.array_size_varname});"
                else:
                    arginfo.array_size_formula = f"MPI_Comm_size((*{c_comm}), &{arginfo.array_size_varname});"

# For each arg there's fortran type for short/long interface at
#   arg.kind.f90_small and arg.kind.f08_large
# And for C we need to pick which interface is the best match.  If the
# Fortran app is built -i8 for example it's possible the short-interface
# Fortran call might be better off calling the long-interface C call.  In
# general we'll pick the interface that supports ints >= what fortran
# is using.
#
# In the default mode where we're producing general purpose code this
# isn't necessarily going to pick the optimal path since it doesn't know
# the type sizes.  If the user has autodoubled fortran and regular C they
# would want to use the mode that regenerates the code specifically for
# their case.
def pick_best_match_c_size_interface():
    global context
    fn = context.fn
    context.c_size_interface = context.fortran_size_interface

    if (context.c_size_interface == WhichInterface.LONG):
        # we're already LONG, no need to check if we should promote
        return(context.c_size_interface)

    # promote if any of the integer args have fsize < csize
    for arg in (fn.express.f90.parameters):

        # skip over the non-integer/logical args
        if (arg.kind.lis != 'integer' and
                arg.kind.lis != 'non-negative integer' and
                arg.kind.lis != 'positive integer' and
                arg.kind.lis != 'logical'):
            continue

        # what are size and type of int argument on fortran's side
        ftype = arg.kind.f90_small
        if (context.fortran_size_interface == WhichInterface.LONG):
            try:
                ftype = arg.kind.f08_large
            except:
                pass
        fsize = sizeof_type[ftype]

        # type and size of arg for C call (promote the interface if needed)
        ctype = arg.kind.iso_c_small
        csize = sizeof_type[ctype]
        if (csize < fsize):
            context.c_size_interface == WhichInterface.LARGE
            return(context.c_size_interface)

    return(context.c_size_interface)

# The chandle could be expressions, like "c_request[i]"
# The fhandle is already dereferenced, so it might be something
# like *SENDCOUNT or SENDCOUNTS[i]
#def print_conversion(arg, chandle, fhandle):
#   if (arg.kind.lis == 'handle'):
#       if (arg.kind.name == 'COMMUNICATOR'):
#           f2c_func = 'MPI_Comm_f2c'
#       elif (arg.kind.name == 'DATATYPE'):
#           f2c_func = 'MPI_Datatype_f2c'
#       elif (arg.kind.name == 'REQUEST'):
#           f2c_func = 'MPI_Request_f2c'
#       elif (arg.kind.name == 'WINDOW'):
#           f2c_func = 'MPI_Win_f2c'
#       elif (arg.kind.name == 'FILE'):
#           f2c_func = 'MPI_File_f2c'
#       elif (arg.kind.name == 'GROUP'):
#           f2c_func = 'MPI_Group_f2c'
#       elif (arg.kind.name == 'INFO'):
#           f2c_func = 'MPI_Info_f2c'
#       elif (arg.kind.name == 'OPERATION'):
#           f2c_func = 'MPI_Op_f2c'
#       elif (arg.kind.name == 'ERRHANDLER'):
#           f2c_func = 'MPI_Errhandler_f2c'
#       elif (arg.kind.name == 'SESSION'):
#           f2c_func = 'MPI_Session_f2c'
#       elif (arg.kind.name == 'MESSAGE'):
#           f2c_func = 'MPI_Message_f2c'
#       else:
#           print(f"*** ERROR, unhandled {arg.name} (lis:{arg.kind.lis}) has ctype {carg.type} (is handle)")
#           exit(-1)

#       print(f"{chandle} = {f2c_func}(*fhandle);", file=context.fout)
#   elif (arg.kind.lis == 'string'):
#       return "char *"
#   else:
#       print(f"*** ERROR, unhandled {arg.name} (lis:{arg.kind.lis}) has ctype {carg.type} (is handle)")
#       exit(-1)

# A c_something variable was created as either a base tyep or an array of them
# (or some form of a string / array of strings).
def arg_to_ccall_usageg(arg, carg, cvarname):
    if (arg.kind.lis == 'string'):
        return cvarname
    elif (arg.kind.lis == 'array of strings'):
        return cvarname
    elif (arg.kind.lis == 'array of array of strings'):
        return cvarname

    if (arg.dimensions == '(3, *)'):
        return cvarname
    elif (arg.dimensions == '(MPI_STATUS_SIZE, *)'):
        return cvarname
    elif (arg.dimensions == '(*)'):
        return cvarname

    if (arg.kind.name == 'BUFFER'
            or arg.kind.name == 'C_BUFFER'
            or arg.kind.name == 'C_BUFFER2'):
        return cvarname

# The rest are non-arrays and are either c_var or &c_var
    if (carg.type == carg.base_type):
        return cvarname
    elif (carg.type == f"{carg.base_type}*"):
        return f"&{cvarname}"
    else:
        print(f"*** ERROR, unexpected type {carg.type} vs base_type {carg.base_type} for arg {arg.name}")
        exit(-1)

def print_f_body():
    global context
    fn = context.fn
    logical_name = context.logical_name
    fout = context.fout

# A short-interface F77 call doesn't necessarily have to call into a
# short-interface C call.  Promote to the larger C interface if the
# Fortran call has any int args that are larger than in the C version:
    context.c_size_interface = pick_best_match_c_size_interface()

    print('{', file=fout) # ***{***
    print('MPI_Count i = 0, j = 0;', file=fout)

# Initialize an ArgInfo for every arg
    info = {}
    for arg in (fn.express.f90.parameters):
        info[arg.name] = ArgInfo()
        info[arg.name].fvarname = arg.name

# All args get c_something vars created for them. For arrays they might
# become pointers to the original fortran array.
    for arg in (fn.express.f90.parameters):
        ctype = arg.kind.iso_c_small
        if (context.c_size_interface == WhichInterface.LONG):
            try:
                ctype = arg.kind.iso_c_large
            except:
                pass

        info[arg.name].cvarname = f"c_{arg.name}"

        if (arg.kind.lis == 'string'):
            print(f"char *{info[arg.name].cvarname} = 0;", file=fout)
            continue
        elif (arg.kind.lis == 'array of strings'):
            print(f"char **{info[arg.name].cvarname} = 0;", file=fout)
            continue
        elif (arg.kind.lis == 'array of array of strings'):
            print(f"char ***{info[arg.name].cvarname} = 0;", file=fout)
            continue

        if (arg.kind.name == 'BUFFER'
                or arg.kind.name == 'C_BUFFER'
                or arg.kind.name == 'C_BUFFER2'):
            print(f"void *{info[arg.name].cvarname} = 0;", file=fout)
            continue

        if (arg.dimensions == '(3, *)'):
            print(f"{ctype} *{info[arg.name].cvarname}[3] = 0;", file=fout)
        elif (arg.dimensions == '(MPI_STATUS_SIZE, *)'):
            print(f"{ctype} *{info[arg.name].cvarname} = 0;", file=fout)
        elif (arg.dimensions == '(*)'):
            print(f"{ctype} *{info[arg.name].cvarname} = 0;", file=fout)
        elif (arg.dimensions == '(MPI_STATUS_SIZE)'):
            print(f"{ctype} {info[arg.name].cvarname} = 0;", file=fout)
        elif (arg.dimensions == ''):
            print(f"{ctype} {info[arg.name].cvarname} = 0;", file=fout)
        else:
            print(f"*** ERROR, unexpected dimensions {arg.dimensions} for arg {arg.name}")
            exit(-1)
    print('', file=fout)

# The first args that we translate and save with 'c_*' names are all
# the Comm inputs.  These are done first since they get used during
# array-size processing which is the next step.
    for arg in (fn.express.f90.parameters):
        if (arg.kind.name == 'COMMUNICATOR'
                and arg.dimensions == ''
                and (arg.direction == std.Direction.IN
                or arg.direction == std.Direction.INOUT)):
            info[arg.name].needs_conversion = NeedsConversion.ALWAYS
            # print(f"MPI_Comm {info[arg.name].cvarname};", file=fout) # (is already declared)
            print(f"{info[arg.name].cvarname} = MPI_Comm_f2c("
                + f"* {info[arg.name].fvarname});",
                file=fout)
            # info[arg.name].cvar_state = CVarState.INVAL_IS_CONVERTED

# Process all args looking for array sizes
# 1. query each arg for which args it wants to pull size info from
#    and record that in info[dependent_arg_name].intval_to_provide
#    and in info[arg_name].intval_to_consume.
#    For example when we see an arg 'SENDCOUNTS', we would lookup
#    that it needs the commsize of argument 'COMM' so we would
#    record that as
#      info['COMM'].intval_to_provide = 'commsize COMM'
#      info['SENDCOUNTS'].intval_to_consume = 'COMM'
#    thus tagging the 'COMM' argument to indicate somebody needs a
#    commsize from it, and later having the SENDCOUNTS arg know which
#    precomputed intval its size comes from.
# 2. declare an int/MPI_Count for every arg that was tagged with an intval_to_provide
# 3. set the required value for all the args that are simple scalars first
#    (setting up the intval from an array requires these intvals to already
#    be available first)
# 4. then move on to setting the required value for the args that are arrays
#
# As an example I'll use
#   MPI_DIST_GRAPH_CREATE(..., N, SOURCES, DEGREES, DESTINATIONS, ...)
#   - SOURCES : array of N entries
#   - DEGREES : array of N entries
#   - DESTINATIONS : array of (DEGREES[0]+DEGREES[1]+...+DEGREES[n-1]) entries
# to describe what task is being performed in each section below.

# Example result from this section (using mpi_dist_graph_create):
#   size_encoding for 'SOURCES' is 'N'
#   size_encoding for 'DEGREES' is 'N'
#   size_encoding for 'DESTINATIONS' is 'fintsum DEGREES N'
# processing 'SOURCES' we store
#   info['N'].intval_to_provide = 'dereference N'
#   info['SOURCES'].intval_to_consume = 'N'
# processing 'DEGREES' we store
#   info['N'].intval_to_provide = 'dereference N'
#   info['DEGREES'].intval_to_consume = 'N'
# processing 'DESTINATIONS' we store
#   info['N'].intval_to_provide = 'dereference N'
#   info['DEGREES'].intval_to_provide = 'fintsum DEGREES N'
#   info['DESTINATIONS'].intval_to_consume = 'DEGREES'
# So each arg that has something else depending on its int value
# is getting tagged with what is required from it.
    for arg in (fn.express.f90.parameters):
        # skip non-arrays
        if (arg.dimensions == ''):
            continue
        # and skip buffers (which have dimension '(*)' like an array would)
        if (arg.kind.name == 'BUFFER'
                or arg.kind.name == 'C_BUFFER'
                or arg.kind.name == 'C_BUFFER2'):
            continue
        # and skip scalar status (which have dimension '(MPI_STATUS_SIZE)')
        if (arg.dimensions == '(MPI_STATUS_SIZE)'):
            continue
        # and special case skip spawn's ARGV
        if (fn.name == 'mpi_comm_spawn' and arg.name == 'ARGV'):
            continue

        size_encoding = find_size(fn, arg.name)
        # This might be a simple var name like COMM
        # or can have a few encodings like
        # "fintsum DEGREES N" that means DEGREES is
        # an arary of size N and we want the sum of
        # everything in DEGREES.  Or "commdeg COMM"
        # that means to take the cart_degree of COMM
        m2 = re.match(fr"^([^\s]+)\s+([^\s]+)$", size_encoding)
        m3 = re.match(fr"^([^\s]+)\s+([^\s]+)\s+([^\s]+)$", size_encoding)
        if (m2):
            # ex: 'cartdim COMM',
            argname = m2.group(2)
            info[argname].intval_to_provide = size_encoding
            info[arg.name].intval_to_consume = argname
        elif (m3):
            # ex: 'fintsum DEGREES N',
            intval_to_provide = size_encoding
            argname_array = m3.group(2)
            argname_scalar = m3.group(3)
            info[argname_scalar].intval_to_provide = f"dereference {argname_scalar}"
            info[argname_array].intval_to_provide = size_encoding
            info[arg.name].intval_to_consume = argname_array
        else:
            # ex: 'COUNT', which is taken to mean 'dereference COUNT'
            argname = size_encoding
            print(f"xxxxxxxxxxxxxxx {argname}")
            info[argname].intval_to_provide = f"dereference {argname}"
            info[arg.name].intval_to_consume = argname

# This section just prints variable definitions for the arguments
# whose integer values will be needed, ex (using mpi_dist_graph_create):
#   MPI_Count intval_N;
#   MPI_Count intval_DEGREES;
# As for whether to use int/MPI_Count, there's a mix of MPI_Fint and MPI_Count
# involved in the various count fields in MPI (or the sum of an array of ints),
# so going with MPI_Count as the default makes sense.  But commsize and cartdim
# both only take ordinary ints, so those two uses get plain ints.
    for arg in (fn.express.f90.parameters):
        if (info[arg.name].intval_to_provide != None):
            info[arg.name].intval_varname = f"intval_{arg.name}"
            if (re.match(r"commsize|cartdim ", info[arg.name].intval_to_provide)):
                print(f"int {info[arg.name].intval_varname};", file=fout)
            else:
                print(f"MPI_Count {info[arg.name].intval_varname};", file=fout)

# (processing the scalars first)
# Example result from this section (using mpi_dist_graph_create):
# The arguments tagged as having intval_to_provide are 'N' and 'DEGREES'
# but 'N' is the only one that's a non-array.  The data stored there is
#   info['N'].intval_to_provide = 'dereference N'
# so we produce the output
#   intval_N = *N;
#
# An example of another common case would be processing the 'COMM' arg in
# MPI_SCATTERV.  In that case when we processed one of the arrays it
# would have filled in info['COMM']intval_to_provide = 'commsize COMM'
# and here while processing 'COMM' we'd produce
# "MPI_Comm_size(c_COMM, &intval_COMM);"
    for arg in (fn.express.f90.parameters):
        if (arg.dimensions == ''
                and info[arg.name].intval_to_provide != None):
            if (info[arg.name].intval_to_provide == f'dereference {arg.name}'
                    or info[arg.name].intval_to_provide == f'{arg.name}'):
                print(f"{info[arg.name].intval_varname} = *{arg.name};",
                    file=fout)
            elif (info[arg.name].intval_to_provide == f'commsize {arg.name}'):
                print(f"MPI_Comm_size({info[arg.name].cvarname}, "
                    + f"&{info[arg.name].intval_varname});",
                    file=fout)
            elif (info[arg.name].intval_to_provide == f'cartdim {arg.name}'):
                print(f"MPI_Cartdim_get({info[arg.name].cvarname}, "
                    + f"&{info[arg.name].intval_varname});",
                    file=fout)
            else:
                print(f"*** ERROR, unrecognized intval_to_provide: "
                    + f"{info[arg.name].intval_to_provide}")
                exit(-1)

# Example result from this section (using mpi_dist_graph_create):
# The array argument 'DEGREES' has been tagged as needing its fintsum, eg:
#   info['DEGREES'].intval_to_provide = 'fintsum DEGREES N'
# so we generate the code
#   intval_DEGREES = 0;
#   for (i=0; i<intval_N; ++i) { intval_DEGREES += DEGREES[i]); }
    for arg in (fn.express.f90.parameters):
        if (arg.dimensions != ''
                and info[arg.name].intval_to_provide != None):

            size_encoding = info[arg.name].intval_to_provide
            m3 = re.match(fr"^([^\s]+)\s+([^\s]+)\s+([^\s]+)$", size_encoding)
            intval_to_provide = m3.group(1)
            if (m3):
                # ex: 'fintsum DEGREES N',
                operation = m3.group(1)
                argname_my_nelements = m3.group(3)
            else:
                print(f"*** ERROR, unrecognized size_encoding: "
                    + f"{size_encoding}")
                exit(-1)

            if (operation == 'fintsum'):
                print(f"{info[arg.name].intval_varname} = 0; "
                    + f"for (i=0; i<{info[argname_my_nelements].intval_varname}; ++i) "
                    + f"{{ {info[arg.name].intval_varname} += {arg.name}[i]; }}",
                    file=fout)
            elif (operation == 'fintlast'):
                print(f"{info[arg.name].intval_varname} = "
                    + f"{arg.name}[{info[argname_my_nelements].intval_varname} - 1]);",
                    file=fout)
            else:
                print(f"*** ERROR, unrecognized intval_to_provide: "
                    + f"{info[arg.name].intval_to_provide}")
                exit(-1)

# xxxxxxxxxxxxxxxxxxxxxxxx
# Conversions and/or pointing c_var directly at an incoming fortran array

    for arg in (fn.express.f90.parameters):
        if (arg.direction == std.Direction.IN
                or arg.direction == std.Direction.INOUT):

            ctype = arg.kind.iso_c_small
            if (context.c_size_interface == WhichInterface.LONG):
                try:
                    ctype = arg.kind.iso_c_large
                except:
                    pass

            # The comm inputs are the one thing already converted earlier
            # (because they were needed to calculate the dimensions for various arrays)
            if (arg.kind.name == 'COMMUNICATOR' and arg.dimensions == ''):
                continue

            if (arg.kind.lis == 'integer'
                    or arg.kind.lis == 'non-negative integer'
                    or arg.kind.lis == 'positive integer'):
                info[arg.name].needs_conversion = NeedsConversion.CONDITIONAL
                info[arg.name].ifdef_for_conversion = 'OMPI_SIZEOF_FORTRAN_INTEGER != SIZEOF_INT'
                print(f"#if {info[arg.name].ifdef_for_conversion}", file=fout)
                if (arg.dimensions == ''):
                    print(f"{info[arg.name].cvarname} = ({ctype}) *{info[arg.name].fvarname};", file=fout)
                elif (arg.dimensions == '(*)'):
                    # info[arg.name].intval_to_consume says what var's intval we need
                    tmp_arg = info[arg.name].intval_to_consume
                    print(f"for (i=0; i<{info[tmp_arg].intval_varname}; ++i) {{ {info[arg.name].cvarname}[i] = ({ctype}) {info[arg.name].fvarname}[i]; }}", file=fout)
                elif (arg.dimensions == '(3, *)'):
                    tmp_arg = info[arg.name].intval_to_consume
                    print(f"for (i=0; i<{info[tmp_arg].intval_varname}; ++i) {{ for (j=0; j<3; ++j) {{ {info[arg.name].cvarname}[3*i+j] = ({ctype}) {info[arg.name].fvarname}[3*i+j]; }} }}", file=fout)
                else:
                    print(f"ERROR, unrecognized dimensions {arg.dimensions} for integer array")
                    exit(-1)
                print(f"#else", file=fout)
                print(f"{info[arg.name].cvarname} = ({ctype}) *{info[arg.name].fvarname});", file=fout),
                print(f"#endif", file=fout)
            else:
                pass

    if False:
        if (arg.kind.lis == 'logical'):
            if (context.generation_mode == GenerationMode.USE_CONFIG_H_SIZES
                    and sizeof_type[ctype] == sizeof_type[ftype]):
                info[arg.name].needs_conversion = NeedsConversion.NEVER
            else:
                info[arg.name].needs_conversion = NeedsConversion.CONDITIONAL
                info[arg.name].ifdef_for_conversion = 'OMPI_SIZEOF_FORTRAN_LOGICAL != SIZEOF_INT'
                info[arg.name].cvarname = f"c_{arg.name}"
        elif (arg.kind.name == 'BUFFER'
                or arg.kind.name == 'C_BUFFER'
                or arg.kind.name == 'C_BUFFER2'):
            info[arg.name].needs_conversion = NeedsConversion.NEVER
        elif (arg.kind.name == 'ATTRIBUTE_VAL'):
            info[arg.name].needs_conversion = NeedsConversion.NEVER
        elif (arg.kind.name == 'ATTRIBUTE_VAL_10'):
            info[arg.name].needs_conversion = NeedsConversion.NEVER
        elif (arg.kind.name == 'EXTRA_STATE'):
            info[arg.name].needs_conversion = NeedsConversion.NEVER
        elif (arg.kind.name == 'FUNCTION'
                and
                (arg.func_type == 'COMM_ERRHANDLER_FUNCTION'
                or arg.func_type == 'FILE_ERRHANDLER_FUNCTION'
                or arg.func_type == 'WIN_ERRHANDLER_FUNCTION'
                or arg.func_type == 'SESSION_ERRHANDLER_FUNCTION'
                or arg.func_type == 'GREQUEST_QUERY_FUNCTION'
                or arg.func_type == 'GREQUEST_FREE_FUNCTION'
                or arg.func_type == 'GREQUEST_CANCEL_FUNCTION'
                or arg.func_type == 'USER_FUNCTION')):
            # This will later involve a typecast and a call into ompi_foo()
            # instead of MPI_Foo(), but it's almost a passthrough
            info[arg.name].needs_conversion = NeedsConversion.NEVER
        elif (arg.kind.name == 'POLYFUNCTION'
                and
                (arg.func_type == 'USER_FUNCTION')):
            info[arg.name].needs_conversion = NeedsConversion.NEVER
        elif (arg.kind.lis == 'handle'):
            if (arg.kind.name != 'COMMUNICATOR'
                    and arg.kind.name != 'DATATYPE'
                    and arg.kind.name != 'REQUEST'
                    and arg.kind.name != 'WINDOW'
                    and arg.kind.name != 'FILE'
                    and arg.kind.name != 'GROUP'
                    and arg.kind.name != 'INFO'
                    and arg.kind.name != 'OPERATION'
                    and arg.kind.name != 'ERRHANDLER'
                    and arg.kind.name != 'SESSION'
                    and arg.kind.name != 'MESSAGE'):
                print(f"*** ERROR, unhandled {arg.name} (lis:{arg.kind.lis}) has ctype {carg.type} (is handle)")
                exit(-1)
            info[arg.name].needs_conversion = NeedsConversion.ALWAYS
            info[arg.name].cvarname = f"c_{arg.name}"
        elif (arg.kind.lis == 'string'
                or arg.kind.lis == 'array of strings'
                or arg.kind.lis == 'array of array of strings'):
            info[arg.name].needs_conversion == NeedsConversion.ALWAYS
            info[arg.name].cvarname = f"c_{arg.name}"
        elif (arg.kind.lis == 'status'):
            info[arg.name].needs_conversion == NeedsConversion.ALWAYS
            info[arg.name].cvarname = f"c_{arg.name}"
        elif (arg.kind.lis == 'state'):
            info[arg.name].needs_conversion = NeedsConversion.NEVER
        else:
            print(f"*** ERROR, unhandled {arg.name} (klis:{arg.kind.lis} knam:{arg.kind.name}) has ctype {carg.type}")
            exit(-1)

# * if it's to be converted, what is the type of the c_something variable
# * what expression goes to MPI_Foo() for the arg, need to store two if conditionally converted
# Figure out which arguments are just going to be passthroughs.
# If an argument is an int or int array and same sized as the C arg
# it gets to be a simple passthrough.

        if False:
            if (True): # xxxxxx
                if (arg.direction == std.Direction.IN or
                        arg.direction == std.Direction.INOUT):
                    if (arg.dimensions == ''):
                        print(f"{info[arg.name].cvarname} = {f2c_func}(*{info[arg.name].fvarname});", file=fout)
                        info[arg.name].cvar_state == CVarState.INVAL_IS_CONVERTED
                    elif (arg.dimensions == '(*)'):
                        tmp_arg = info[arg.name].intval_to_consume
                        # now we have something like "fintsum DEGREES N'
                        # and we already have intval_DEGREES and intval_N
                        # precomputed.
                        print(f"for (i=0; i<{info[tmp_arg].intval_varname}; ++i) {{ {info[arg.name].cvarname}[i] = {f2c_func}({info[arg.name].fvarname}[i]); }}", file=fout)
                    else:
                        pass # xxxxxxxxxxx

                info[arg.name].cvar_state == CVarState.INVAL_IS_CONVERTED

            elif (arg.kind.lis == 'string'):
                if (arg.dimensions == ''):
                    print(f"ompi_fortran_string_f2c({info[arg.name].fvarname}, {info[arg.name].fvarname}_len, &{info[arg.name].cvarname});", file=fout)
                else:
                    print(f"  {arg.name} (lis:{arg.kind.lis}) has ctype {carg.type}")

                info[arg.name].cvar_state == CVarState.INVAL_IS_CONVERTED

            else:
                print(f"  {arg.name} (lis:{arg.kind.lis}) has ctype {carg.type}")

#           if (arg.kind.lis == 'handle'):
#       if ((carg.type == 'int' or carg.type == 'int*') and
#              (arg.kind.f90_small == 'INTEGER' or
#               arg.kind.f90_small == 'INTEGER(KIND=MPI_ADDRESS_KIND)' or
#               arg.kind.f90_small == 'INTEGER(KIND=MPI_OFFSET_KIND)' or
#               arg.kind.f90_small == 'INTEGER(KIND=MPI_COUNT_KIND)' or
#               arg.kind.f90_small == 'LOGICAL')
#       if (arg.dimensions == ''):
#           print(f"  {arg.name} has lis:{arg.kind.lis}")
# arg.kind.lis for scalars:
# lis:None : ATTRIBUTE_VAL and EXTRA_STATE
# lis:choice
# lis:function
# lis:handle
# lis:integer
# lis:logical
# lis:non-negative integer
# lis:positive integer
# lis:state
# lis:status
# lis:string

    for arg in (fn.express.f90.parameters):
        ctype = arg.kind.iso_c_small
        ftype = arg.kind.f90_small
        if (context.c_size_interface == WhichInterface.LONG):
            try:
                ctype = arg.kind.iso_c_large
            except:
                pass
        if (context.fortran_size_interface == WhichInterface.LONG):
            try:
                ftype = arg.kind.f08_large
            except:
                pass
#           typecast = 'xxxx'
#           typecast_dict = {
#               'COMM_ERRHANDLER_FUNCTION'    : 'ompi_errhandler_generic_handler_fn_t *',
#               'FILE_ERRHANDLER_FUNCTION'    : 'ompi_errhandler_generic_handler_fn_t *',
#               'WIN_ERRHANDLER_FUNCTION'     : 'ompi_errhandler_generic_handler_fn_t',
#               'SESSION_ERRHANDLER_FUNCTION' : 'xxxx',
#               'GREQUEST_QUERY_FUNCTION'     : 'MPI_Grequest_query_function *',
#               'GREQUEST_FREE_FUNCTION'      : 'MPI_Grequest_free_function *',
#               'GREQUEST_CANCEL_FUNCTION'    : 'MPI_Grequest_cancel_function *',
#               'USER_FUNCTION'               : 'xxxx'}
#           typecast = typecast_dict[arg.func_type]
#           info[arg.name].arg_for_mpi_call_if_passthrough = f"({typecast}) {info[arg.name].fvarname}"
# xxxxxxxxxxxx
# or arg.kind.lis == 'logical'):
# and sizeof_type[ctype] == sizeof_type[ftype]):
#   needs_conversion: NeedsConversion = NeedsConversion.NEVER # default until updated
#   ifdef_for_conversion = None
#   cvarname = None # only used in the "if conversion" paths
#   cvar_state = CVarState.UNEXAMINED
#   arg_for_mpi_call_if_passthrough
#   arg_for_mpi_call_if_converted
#           info[arg.name].cvar_state = CVarState.DECLARED
#           print(f"int {info[arg.name].cvarname};", file=fout)


#       if (info[arg.name].cvar_state == CVarState.UNEXAMINED):

#           info[arg.name].cvarname = f"c_{arg.name}"
#           if (arg.dimensions == ''):
#               print(f"{arg.kind.iso_c_small} {info[arg.name].cvarname};", file=fout)
#           elif (arg.dimensions == '(*)'):
#               print(f"{arg.kind.iso_c_small} *{info[arg.name].cvarname};", file=fout)
#           else:
#               print(f"xxxxxxxxxx {arg.kind.iso_c_small} *{info[arg.name].cvarname};", file=fout)
#           info[arg.name].cvar_state == CVarState.DECLARED

#           if (arg.direction == std.Direction.IN or
#                   arg.direction == std.Direction.INOUT):
#               if (arg.dimensions == ''):
#                   print_conversion(arg,
#                       f"{info[arg.name].cvarname}", f"*{info[arg.name].fvarname}")
#               elif (arg.dimensions == '(*)'):
#                   # now we have something like "fintsum DEGREES N'
#                   # and we already have intval_DEGREES and intval_N
#                   # precomputed.
#                   tmp_arg = info[arg.name].intval_to_consume
#                   print(f"for (i=0; i<{info[tmp_arg].intval_varname}; ++i) {{", file=fout)
#                   print_conversion(arg,
#                       f"{info[arg.name].cvarname}[i]", f"{info[arg.name].fvarname}[i]")
#                   print(f"}}", file=fout)
#               else:
#                   print(f"  {arg.name} (k.lis:{arg.kind.lis} k.name:{arg.kind.name}) has ctype {carg.type}")

#               info[arg.name].cvar_state == CVarState.INVAL_IS_CONVERTED


#               info[arg.name].cvarname = f"c_{arg.name}"
#               if (arg.dimensions == ''):
#                   print(f"{decl_string} {info[arg.name].cvarname};", file=fout)
#               elif (arg.dimensions == '(*)'):
#                   print(f"MPI_{decl_string} *{info[arg.name].cvarname};", file=fout)
#               else:
#                   print(f"xxxxxxxxxx MPI_{decl_string} *{info[arg.name].cvarname};", file=fout)

    fn_name_suffix = re.sub('mpi_', '', logical_name)  # eg 'allgatherv'
    MPI_Foo = context.logical_name # eg mpi_allgather
    MPI_Foo = f"MPI_{fn_name_suffix.capitalize()}"

    if (context.c_size_interface == WhichInterface.LONG):
        MPI_Foo = f"{MPI_Foo}_c"

    # is this a typical MPI routine with no return or is it like MPI_Wtime:
    print('', file=fout)
    if (fn.express.f90.return_kind is None):
        print(f"{MPI_Foo}(", file=fout)
    else:
        c_return_type = f90_return_kind_to_c_return_type(fn.express.f90.return_kind)
        print(f"{c_return_type} rv = {MPI_Foo}(", file=fout)

    first_iteration = True
    for arg in (fn.express.f90.parameters):
        if (arg.name == 'IERROR'):
            continue

        if (first_iteration):
            first_iteration = False
        else:
            print(",", file=fout)

        ctype = arg.kind.iso_c_small
        if (context.c_size_interface == WhichInterface.LONG):
            try:
                ctype = arg.kind.iso_c_large
            except:
                pass

        carg = find_c_arg(fn, arg.name)

        print(f"  {arg.name} with f90arg.kind.iso_c_small {ctype}")

# Example data:
# MPI_Isend's request:
#   f90arg.kind.iso_c_small is MPI_Request
#   carg.base_type is MPI_Request
#   carg.type is MPI_Request*
# MPI_Waitall's request array:
#   carg.array is []
#   f90arg.kind.iso_c_small is MPI_Request
#   carg.base_type is MPI_Request
#   carg.type is MPI_Request

# Expectations:
# calls either take base_type, addr of base_type, or array of base_type
#
# so if array: c_something is already array, so just pass in c_something
# if non-array and type is {base_type}* add &

        # pprint(vars(carg))
        # if (arg.dimensions == ''):
        #     argstring = f"{info[arg.name].cvarname}"
        #     if (carg.type == f"{ctype}*"):
        #         argstring = f"&{info[arg.name].cvarname}"
        # else:
        #     argstring = f"{info[arg.name].cvarname}"
        # print(argstring, file=fout)

        print(arg_to_ccall_usageg(arg, carg, info[arg.name].cvarname), file=fout)

    print(");", file=fout)

    print("}", file=fout)
    return

#           # See if the C version is int or int*
#           if (info[arg.name].needs_conversion == NeedsConversion.NEVER
#                   or info[arg.name].needs_conversion == NeedsConversion.CONDITIONAL):
#               if (carg.type == 'int'):
#                   info[arg.name].arg_for_mpi_call_if_passthrough = f"*{info[arg.name].fvarname}"
#               elif (carg.type == 'int*'):
#                   info[arg.name].arg_for_mpi_call_if_converted = f"{info[arg.name].fvarname}"
#           if (info[arg.name].needs_conversion == NeedsConversion.ALWAYS
#                   or info[arg.name].needs_conversion == NeedsConversion.CONDITIONAL):
#               if (carg.type == 'int'):
#                   info[arg.name].arg_for_mpi_call_if_passthrough = f"{info[arg.name].cvarname}"
#               elif (carg.type == 'int*'):
#                   info[arg.name].arg_for_mpi_call_if_converted = f"&{info[arg.name].cvarname}"



#       else:
#xxxxxxxxxxxxx
#           print(f"xxxxxxxxxx {arg.name} : {arg.kind.iso_c_small}")
#           continue
    return

#           print(f"// Note: {arg.name} will be used passthrough as "
#               f"{info[arg.name].cexpression}", file=fout)

# Now most args need c_something variables declared for them.  A few
# have been processed already above:
# 1. input comms
# 2. passthroughs
# and they would have had their info[arg.name].cvar_state set to
# INVAL_IS_CONVERTED and PASSTHROUGH.  Otherwise the args are in state
# UNEXAMINED.

    for arg in (fn.express.f90.parameters):
        carg = find_c_arg(fn, arg.name)
        if (carg == None):  # should just be the IERRORs, skip them
            continue
        if (arg.kind.name == 'BUFFER'
                or arg.kind.name == 'C_BUFFER'
                or arg.kind.name == 'C_BUFFER2'):
            info[arg.name].cvar_state = CVarState.PASSTHROUGH
            continue

        if (arg.kind.name == 'ATTRIBUTE_VAL'):
            info[arg.name].cvar_state = CVarState.PASSTHROUGH
            continue
        if (arg.kind.name == 'ATTRIBUTE_VAL_10'):
            info[arg.name].cvar_state = CVarState.PASSTHROUGH
            continue
        if (arg.kind.name == 'EXTRA_STATE'):
            info[arg.name].cvar_state = CVarState.PASSTHROUGH
            continue

        if (arg.kind.name == 'FUNCTION'
                and
                (arg.func_type == 'COMM_ERRHANDLER_FUNCTION'
                or arg.func_type == 'FILE_ERRHANDLER_FUNCTION'
                or arg.func_type == 'WIN_ERRHANDLER_FUNCTION'
                or arg.func_type == 'SESSION_ERRHANDLER_FUNCTION'
                or arg.func_type == 'GREQUEST_QUERY_FUNCTION'
                or arg.func_type == 'GREQUEST_FREE_FUNCTION'
                or arg.func_type == 'GREQUEST_CANCEL_FUNCTION'
                or arg.func_type == 'USER_FUNCTION')):
            # This will later involve a typecast and a call into ompi_foo()
            # instead of MPI_Foo(), but it's almost a passthrough
            info[arg.name].cvar_state = CVarState.PASSTHROUGH
            continue

        if (info[arg.name].cvar_state == CVarState.UNEXAMINED):

            info[arg.name].cvarname = f"c_{arg.name}"
            if (arg.dimensions == ''):
                print(f"{arg.kind.iso_c_small} {info[arg.name].cvarname};", file=fout)
            elif (arg.dimensions == '(*)'):
                print(f"{arg.kind.iso_c_small} *{info[arg.name].cvarname};", file=fout)
            else:
                print(f"xxxxxxxxxx {arg.kind.iso_c_small} *{info[arg.name].cvarname};", file=fout)
            info[arg.name].cvar_state == CVarState.DECLARED

#           if (arg.direction == std.Direction.IN or
#                   arg.direction == std.Direction.INOUT):
#               if (arg.dimensions == ''):
#                   print_conversion(arg,
#                       f"{info[arg.name].cvarname}", f"*{info[arg.name].fvarname}")
#               elif (arg.dimensions == '(*)'):
#                   # now we have something like "fintsum DEGREES N'
#                   # and we already have intval_DEGREES and intval_N
#                   # precomputed.
#                   tmp_arg = info[arg.name].intval_to_consume
#                   print(f"for (i=0; i<{info[tmp_arg].intval_varname}; ++i) {{", file=fout)
#                   print_conversion(arg,
#                       f"{info[arg.name].cvarname}[i]", f"{info[arg.name].fvarname}[i]")
#                   print(f"}}", file=fout)
#               else:
#                   print(f"  {arg.name} (k.lis:{arg.kind.lis} k.name:{arg.kind.name}) has ctype {carg.type}")

#               info[arg.name].cvar_state == CVarState.INVAL_IS_CONVERTED

            if (arg.kind.lis == 'handle'):
                if (arg.kind.name == 'COMMUNICATOR'):
                    decl_string = 'MPI_Comm'
                    f2c_func = 'MPI_Comm_f2c'
                elif (arg.kind.name == 'DATATYPE'):
                    decl_string = 'MPI_Datatype'
                    f2c_func = 'MPI_Datatype_f2c'
                elif (arg.kind.name == 'REQUEST'):
                    decl_string = 'MPI_Request'
                    f2c_func = 'MPI_Request_f2c'
                elif (arg.kind.name == 'WINDOW'):
                    decl_string = 'MPI_Win'
                    f2c_func = 'MPI_Win_f2c'
                elif (arg.kind.name == 'FILE'):
                    decl_string = 'MPI_File'
                    f2c_func = 'MPI_File_f2c'
                elif (arg.kind.name == 'GROUP'):
                    decl_string = 'MPI_Group'
                    f2c_func = 'MPI_Group_f2c'
                elif (arg.kind.name == 'INFO'):
                    decl_string = 'MPI_Info'
                    f2c_func = 'MPI_Info_f2c'
                elif (arg.kind.name == 'OPERATION'):
                    decl_string = 'MPI_Op'
                    f2c_func = 'MPI_Op_f2c'
                elif (arg.kind.name == 'ERRHANDLER'):
                    decl_string = 'MPI_Errhandler'
                    f2c_func = 'MPI_Errhandler_f2c'
                elif (arg.kind.name == 'SESSION'):
                    decl_string = 'MPI_Session'
                    f2c_func = 'MPI_Session_f2c'
                elif (arg.kind.name == 'MESSAGE'):
                    decl_string = 'MPI_Message'
                    f2c_func = 'MPI_Message_f2c'
                else:
                    print(f"*** ERROR, unhandled {arg.name} (lis:{arg.kind.lis}) has ctype {carg.type} (is handle)")
                    exit(-1)

#               info[arg.name].cvarname = f"c_{arg.name}"
#               if (arg.dimensions == ''):
#                   print(f"{decl_string} {info[arg.name].cvarname};", file=fout)
#               elif (arg.dimensions == '(*)'):
#                   print(f"MPI_{decl_string} *{info[arg.name].cvarname};", file=fout)
#               else:
#                   print(f"xxxxxxxxxx MPI_{decl_string} *{info[arg.name].cvarname};", file=fout)

                if (arg.direction == std.Direction.IN or
                        arg.direction == std.Direction.INOUT):
                    if (arg.dimensions == ''):
                        print(f"{info[arg.name].cvarname} = {f2c_func}(*{info[arg.name].fvarname});", file=fout)
                        info[arg.name].cvar_state == CVarState.INVAL_IS_CONVERTED
                    elif (arg.dimensions == '(*)'):
                        tmp_arg = info[arg.name].intval_to_consume
                        # now we have something like "fintsum DEGREES N'
                        # and we already have intval_DEGREES and intval_N
                        # precomputed.
                        print(f"for (i=0; i<{info[tmp_arg].intval_varname}; ++i) {{ {info[arg.name].cvarname}[i] = {f2c_func}({info[arg.name].fvarname}[i]); }}", file=fout)
                    else:
                        pass # xxxxxxxxxxx

                info[arg.name].cvar_state == CVarState.INVAL_IS_CONVERTED

            elif (arg.kind.lis == 'string'):
                if (arg.dimensions == ''):
                    print(f"ompi_fortran_string_f2c({info[arg.name].fvarname}, {info[arg.name].fvarname}_len, &{info[arg.name].cvarname});", file=fout)
                else:
                    print(f"  {arg.name} (lis:{arg.kind.lis}) has ctype {carg.type}")

                info[arg.name].cvar_state == CVarState.INVAL_IS_CONVERTED

            else:
                print(f"  {arg.name} (lis:{arg.kind.lis}) has ctype {carg.type}")

#           if (arg.kind.lis == 'handle'):
#       if ((carg.type == 'int' or carg.type == 'int*') and
#              (arg.kind.f90_small == 'INTEGER' or
#               arg.kind.f90_small == 'INTEGER(KIND=MPI_ADDRESS_KIND)' or
#               arg.kind.f90_small == 'INTEGER(KIND=MPI_OFFSET_KIND)' or
#               arg.kind.f90_small == 'INTEGER(KIND=MPI_COUNT_KIND)' or
#               arg.kind.f90_small == 'LOGICAL')
#       if (arg.dimensions == ''):
#           print(f"  {arg.name} has lis:{arg.kind.lis}")
# arg.kind.lis for scalars:
# lis:None : ATTRIBUTE_VAL and EXTRA_STATE
# lis:choice
# lis:function
# lis:handle
# lis:integer
# lis:logical
# lis:non-negative integer
# lis:positive integer
# lis:state
# lis:status
# lis:string

        info[arg.name].cvar_is_separate = True
        #xxxxxxxxxxxxxxxxx
        continue

# xxxxxxxxxxx

# Otherwise it gets a c_something
# var, and if it's IN/INOUT (and not an array since we don't have sizes
# yet) it gets its first f2c() or otherwise translation.
#
# Initially translate scalars only, since we don't yet have the data
# about array sizes, and that will come from some of the scalars.
# (declare all the c_something vars, but only translate the scalars)
    return

    if False:
        if (arg.dimensions == ''):
            # declaration for simple non-arrays
            info[arg.name].cvarname = f"c_{arg.name}"
            if (context.c_size_interface == WhichInterface.SHORT):
                print(f"{arg.kind.iso_c_small} {info[arg.name].cvarname};", file=fout)
            else:
                print(f"{arg.kind.iso_c_large} {info[arg.name].cvarname};", file=fout)
        else:
            # declaration for arrays
            info[arg.name].cvarname = f"c_{arg.name}"
            if (context.c_size_interface == WhichInterface.SHORT):
                print(f"{arg.kind.iso_c_small} *{info[arg.name].cvarname};", file=fout)
            else:
                print(f"{arg.kind.iso_c_large} *{info[arg.name].cvarname};", file=fout)

        # for arrays/buffers declare but don't initialize yet
#x      if (arg.dimensions != '' and
#x              info[arg.name].cvarname = f"c_{info[arg.name].fvarname}"
    #cvarname: str = None
    #cvar_is_separate: bool = False
    #cexpression: str = None  # this is the code that would be used in the MPI call


# For each arg that's a comm, give it a C variable definition
# And if it's IN/INOUT give it its f2c() value
# These are done first since we often need the comm's sizes
# when figuring out what size arrays are.
    for arg in (fn.express.f90.parameters):
        if (arg.kind.name == 'COMMUNICATOR' and arg.dimensions == ''):
            info[arg.name].cvarname = f"c_{arg.name}"
            print(f"MPI_Comm {info[arg.name].cvarname};", file=fout)
            if (arg.direction == std.Direction.IN or
                    arg.direction == std.Direction.INOUT):
                print(f"{info[arg.name].cvarname} = MPI_Comm_f2c("
                    + f"* {info[arg.name].fvarname});",
                    file=fout)



# Loop through our recognized patterns, tnen for each pattern loop
# through the args (I think this design makes it more explicit and
# visible what patterns we recognize).
    call_with_name = {}
    patterns = ('comm', 'userbuf', 'count', 'counts',
        'datatype', 'datatypes', 'disps')
    argidx = 0;
    for pattern in patterns:
        noop = 1

        for arg in (fn.express.f90.parameters):
            name = arg.name
            info[name] = ArgInfo()

            call_with_name[name] = name # ex later recvcounts might become c_recvcounts
# Userbufs can be inplace or bottom or an address.
# Fwiw, the other "choice" arguments that aren't 'BUFFER' are
# 'C_BUFFER' and 'C_BUFFER2' used in mpi_alloc_mem/mpi_buffer_detach.
# and those don't need to cover inplace/bottom
            print(f"  argidx {argidx}") # xxx

            if (arg.kind.name == 'BUFFER'):
                if (buffer_can_be_in_place(logical_name, arg, argidx)):
                    print(f"{name} = (char *) OMPI_F2C_IN_PLACE({name});", file=fout)
                print(f"{name} = (char *) OMPI_F2C_BOTTOM({name});", file=fout)

# input datatypes need converted
            if (arg.kind.name == 'DATATYPE'
                    and (arg.direction == std.Direction.IN or
                    arg.direction == std.Direction.INOUT)):
                print(f"MPI_Datatype c_{name} = PMPI_Type_f2c(*{name});", file=fout)
                call_with_name[name] = f"c_{name}"

# input counts
# 1. non-array case: count need a simple conversion at call-time
# 2. array case: need converted in a new var
            if (arg.kind.name == 'POLYXFER_NUM_ELEM_NNI'
                    and (arg.direction == std.Direction.IN or
                    arg.direction == std.Direction.INOUT)):
                if (arg.dimensions == ''):
                    call_with_name[name] = f"OMPI_FINT_2_INT(*{name})"
                if (arg.dimensions == '(*)'):
                    print(f"int c_{name} = malloc(sizeof(int) * <size>);", file=fout)
                    call_with_name[name] = f"c_{name}"
                else:
                    noop = 1 # xxx not sure

            argidx += 1

    print(f"P{fn.express.iso_c.name}(", file=fout) # eg MPI_Allgatherv
    for arg in (fn.express.f90.parameters):
        print(f"    {call_with_name[arg.name]}", file=fout)

    print('}', file=fout) # ***}***
#xxxxxx

        # c_type, c_dimension = f90_param_to_c_param_type(arg)

# The input is the f90 return type from MPI functions like
#     DOUBLE PRECISION MPI_Wtime()
#     INTEGER(KIND=MPI_ADDRESS_KIND) MPI_Aint_add(integer(...) base, integer(...) disp)
# and for output we want to know how to implement it in C, eg
#     ompi_fortran_double_precision_t ompi_wtime_f(...)
#     MPI_Aint ompi_aint_add_f(...)

def f90_return_kind_to_c_return_type(kind):
    f90type = kind.f90_small
    mapping = {
        'DOUBLE PRECISION' :               'ompi_fortran_double_precision_t',
        'INTEGER(KIND=MPI_ADDRESS_KIND)' : 'MPI_Aint',
    }

    result = mapping.get(f90type)
    if (result is not None):
        return(result)
    else:
        print('Not yet set up for [' + f90type + ']')
        exit(-1)

# Note, this returns a tuple since it might need to specify array
# dimensions like "int ranges[][3]" which would be ("int", "[][3]")
def f90_param_to_c_param_type(param):
    ctype = 'MPI_Fint *'
    dim = ''

    if (param.kind.lis == 'choice'):
        ctype = "char *"
        if (param.direction == std.Direction.IN):
            ctype = "const " + ctype
        return(ctype, dim)

    if (param.kind.lis == 'function'):
        func_type = param.func_type
        mapping = {
            'COPY_FUNCTION'               : 'ompi_fint_copy_attr_function',
            'DELETE_FUNCTION'             : 'ompi_fint_delete_attr_function',
            'COMM_COPY_ATTR_FUNCTION'     : 'ompi_aint_copy_attr_function',
            'COMM_DELETE_ATTR_FUNCTION'   : 'ompi_aint_delete_attr_function',
            'WIN_COPY_ATTR_FUNCTION'      : 'ompi_aint_copy_attr_function',
            'WIN_DELETE_ATTR_FUNCTION'    : 'ompi_aint_delete_attr_function',
            'TYPE_COPY_ATTR_FUNCTION'     : 'ompi_aint_copy_attr_function',
            'TYPE_DELETE_ATTR_FUNCTION'   : 'ompi_aint_delete_attr_function',
            'COMM_ERRHANDLER_FUNCTION'    : 'ompi_errhandler_fortran_handler_fn_t *',
            'WIN_ERRHANDLER_FUNCTION'     : 'ompi_errhandler_fortran_handler_fn_t *',
            'FILE_ERRHANDLER_FUNCTION'    : 'ompi_errhandler_fortran_handler_fn_t *',
            'GREQUEST_QUERY_FUNCTION'     : 'MPI_F_Grequest_query_function *',
            'GREQUEST_FREE_FUNCTION'      : 'MPI_F_Grequest_free_function *',
            'GREQUEST_CANCEL_FUNCTION'    : 'MPI_F_Grequest_cancel_function *',
            'USER_FUNCTION'               : 'ompi_op_fortran_handler_fn_t *',
            'DATAREP_CONVERSION_FUNCTION' : 'ompi_mpi2_fortran_datarep_conversion_fn_t *',
            'DATAREP_EXTENT_FUNCTION'     : 'ompi_mpi2_fortran_datarep_extent_fn_t *',
        }
        ctype = mapping.get(func_type, 'MPI_Fint *')
#       if (param.direction == std.Direction.IN):
#           ctype = "const " + ctype
        return(ctype, dim)

    f90type = param.kind.f90_small
    mapping = {
        # Most things map to               'MPI_Fint *',
        'INTEGER(KIND=MPI_ADDRESS_KIND)' : 'MPI_Aint *',
        'INTEGER(KIND=MPI_COUNT_KIND)'   : 'MPI_Count *',
        'INTEGER(KIND=MPI_OFFSET_KIND)'  : 'MPI_Offset *',
        'CHARACTER*(*)'                  : 'char *',
        'LOGICAL'                        : 'ompi_fortran_logical_t *',
        # the below is an F08 description, shows up in MPI_Status_f2f08() etc
        'TYPE(MPI_Status)'               : 'MPI_F08_status *',
    }

    ctype = mapping.get(f90type, 'MPI_Fint *')
    if (context.fortran_size_interface == WhichInterface.LONG):
        try:
            f90type = param.kind.f08_large
            ctype = mapping.get(f90type, 'MPI_Fint *')
        except:
            pass # stick with small if this arg doesn't have a large version
    # print(f"  [name={kind.name} f90_small={f90type}] => [{ctype}]")

# Figure out dimension based on a Fortran-formatted array dims
# Lots of these are either
#     (*)               : in C things are already pointers, no special treatment needed
#     (MPI_STATUS_SIZE) : also 1-d, so C doesn't need to do anything
# The most interesting dimension is from MPI_Group_range_excl()
# which is an array of 3-tuples.
#     "(3, *)"          : it would be MPI_Fint ranges[][3]
#     "(COUNT, *)"      : is just for spawn mult, and COUNT is a variable, so probably leave alone
    fdim = param.dimensions
    mapping = {
        ''                         : '',
        '(*)'                      : '',
        '(MPI_STATUS_SIZE)'        : '',
        '(MPI_STATUS_SIZE, *)'     : '', # consider '[][OMPI_FORTRAN_STATUS_SIZE]'
        '(3, *)'                   : '[][3]',
        '(COUNT, *)'               : '',
    }
    dim = mapping.get(fdim, 'not found')
    if (dim == 'not found'):
        print(f"-------- warning: arg {param.name} has unrecognized dims {param.dimensions}")
        print(f"-------- (Those mappings from Fortran array to C-array are hard coded, you")
        print(f"-------- can just add more to the mapping dictionary above this print).")
        dim = ''
    if (dim != ''):
        ctype = re.sub('\s*\*$', '', ctype)
 
    if (param.direction == std.Direction.IN):
        ctype = "const " + ctype
    return(ctype, dim)

def f90_arginfo_to_fndef_parameters_in_c(args):
    str = ''
    string_arguments_list = []  # because those get length args on the end in C interface
    for arg in args:
        name = arg.name

        c_type, c_dimension = f90_param_to_c_param_type(arg)
        if (str != ''):
            str += ', '
        str += c_type + ' ' + name + c_dimension

        if (arg.kind.lis == 'string' or arg.kind.lis == 'array of strings' or
                arg.kind.lis == 'array of array of strings'):
            string_arguments_list.append(name)

    for varname in string_arguments_list:
        str += ', int ' + varname + '_len'

    if (str == ''):
        str = 'void'

    return str

def f90_arginfo_to_fncall_parameters_in_c(args):
    str = ''
    string_arguments_list = []  # because those get length args on the end in C interface
    for arg in args:
        name = arg.name

        if (str != ''):
            str += ', '
        str += name

        if (arg.kind.lis == 'string' or arg.kind.lis == 'array of strings' or
                arg.kind.lis == 'array of array of strings'):
            string_arguments_list.append(name)

    for varname in string_arguments_list:
        str += ', ' + varname + '_len'

    return str

def find_lis_arg(fn, name):
    if (name.lower() == 'ierror'):
        return None

    for lis_arg in (fn.express.lis.parameters):
        if (lis_arg.name.lower() == name.lower()):
            return lis_arg
    print(f"*** ERROR, Cant find match for arg named {name} in {fn.name}")
    exit(-1)

def find_c_arg(fn, name):
    if (name.lower() == 'ierror'):
        return None

    for carg in (fn.express.iso_c.parameters):
        if (carg.name.lower() == name.lower()):
            return carg
    print(f"*** ERROR, Cant find match for arg named {name} in {fn.name}")
    exit(-1)

main()
