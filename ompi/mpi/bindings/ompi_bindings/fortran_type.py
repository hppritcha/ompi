#
# Copyright (c) 2024-2026 Triad National Security, LLC. All rights
#                         reserved.
#
# $COPYRIGHT$
#
# Additional copyrights may follow
#
# $HEADER$
# SPDX-License-Identifier: BSD-3-Clause-Open-MPI
#
"""Fortran types and corresponding template code.

All types used in the Fortran bindings are defined here as classes that derive
from the FortranType base class. These are used for generating both Fortran and
supporting C code for the mpi_f08 bindings.
"""
from abc import ABC, abstractmethod
from ompi_bindings import consts, util


class FortranType(ABC):

    def __init__(self, name, fn_name, bigcount=False, count_param=None, gen_f90=False, **kwargs):
        self.name = name
        self.fn_name = fn_name
        # Generate the bigcount interface version?
        self.bigcount = bigcount
        self.count_param = count_param
        self.gen_f90 = gen_f90
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

    @classmethod
    def construct(cls, type_name, **kwargs):
        type_ = cls.TYPES[type_name]
        return type_(**kwargs)

    @property
    def fn_api_name(self):
        """Return the MPI API name to be used in error messages, etc.."""
        return util.ext_api_func_name(self.fn_name, bigcount=self.bigcount).upper()

    @property
    def tmp_name(self):
        """Return a temporary name for use in C."""
        return f'c_{self.name}'

    @property
    def tmp_name2(self):
        """Return a secondary temporary name for use in C."""
        return f'c_{self.name}2'

    def tmp_counter(self):
        """Get a temporary counter variable to be used in a loop."""
        name = f'{self.name}_i_{self.used_counters}'
        self.used_counters += 1
        return name

    def interface_predeclare(self):
        """Return predeclaration code, if required for the interface."""
        return ''

    @abstractmethod
    def declare(self):
        """Return a declaration for the type."""

    def declare_tmp(self):
        """Declare temporaries on in the subroutine."""
        return ''

    def declare_cbinding_fortran(self):
        """Return the C binding declaration as seen from Fortran."""
        return self.declare()

    def argument(self):
        """Return the value to pass as an argument."""
        return self.name

    def cbinding_params(self):
        """Return the dummy argument names of the C binding as seen from Fortran."""
        return [self.name]

    def cbinding_arguments(self):
        """Return the values to pass to the C binding."""
        return [self.argument()]

    def use(self):
        """Return list of (module, name) for a Fortran use-statement."""
        return []

    def include(self):
        """Return an include file name needed for a Fortran datatype."""
        return ''

    def post(self):
        """Return post-processing code to be run after the call to c interface."""
        return ''

    def pre_c_call(self):
        """Return pre-processing code to be run before the call to c interface."""
        return ''

    def pre_c_call(self):
        """Return pre-processing code to be run before the call the c interface."""
        return ''

    @abstractmethod
    def c_parameter(self):
        """Return the parameter expression to be used in the C function."""

    def declare_result(self, name):
        """Return the declaration of the result of a function of this type."""
        raise util.BindingError(f'{type(self).__name__} cannot be the type of a function')

    def c_return_type(self):
        """Return the C type of the result of a function of this type."""
        raise util.BindingError(f'{type(self).__name__} cannot be the type of a function')

    @property
    def init_code(self):
        """Return the initialization code needed for an ABI wrapper."""
        return []
        
    @property
    def final_code(self):
        """Return the finalization code needed for an ABI wrapper."""
        return []


#
# Definitions of generic types in Fortran and how these can be converted
# to and from C.
#

@FortranType.add('BUFFER')
class BufferType(FortranType):
    def interface_predeclare(self):
        return f'!OMPI_F08_IGNORE_TKR_PREDECL {self.name}'

    def declare(self):
        return f'OMPI_F08_IGNORE_TKR_TYPE, INTENT(IN) :: {self.name}'

    def c_parameter(self):
        # See fortran/use-mpi-f08/base/ts.h; OMPI_CFI_BUFFER is expanded based
        # on whether or not the compiler supports TS 29113.
        return f'OMPI_CFI_BUFFER *{self.name}'


@FortranType.add('BUFFER_ASYNC')
class BufferAsyncType(BufferType):
    def declare(self):
        return f'OMPI_F08_IGNORE_TKR_TYPE, INTENT(IN) OMPI_ASYNCHRONOUS :: {self.name}'


@FortranType.add('BUFFER_OUT')
class BufferOutType(BufferType):
    def declare(self):
        return f'OMPI_F08_IGNORE_TKR_TYPE :: {self.name}'


@FortranType.add('BUFFER_ASYNC_OUT')
class BufferAsyncOutType(BufferType):
    def declare(self):
        return f'OMPI_F08_IGNORE_TKR_TYPE OMPI_ASYNCHRONOUS :: {self.name}'


@FortranType.add('VBUFFER')
class VBufferType(FortranType):
    """Variable buffer type, as used by MPI_*v() functions."""
    def declare(self):
        return f'OMPI_F08_IGNORE_TKR_TYPE, INTENT(IN) :: {self.name}'

    def c_parameter(self):
        return f'OMPI_CFI_BUFFER *{self.name}'


@FortranType.add('VBUFFER_OUT')
class VBufferType(FortranType):
    """Variable buffer receive type, as used by MPI_*v() functions."""
    def declare(self):
        return f'OMPI_F08_IGNORE_TKR_TYPE :: {self.name}'

    def c_parameter(self):
        return f'OMPI_CFI_BUFFER *{self.name}'


@FortranType.add('WBUFFER')
class WBufferType(FortranType):
    """Variable buffer send type, used with MPI_*w() functions."""
    def declare(self):
        return f'OMPI_F08_IGNORE_TKR_TYPE, INTENT(IN) :: {self.name}'

    def c_parameter(self):
        return f'OMPI_CFI_BUFFER *{self.name}'


@FortranType.add('WBUFFER_OUT')
class WBufferType(FortranType):
    """Variable buffer receive type, used with MPI_*w() functions."""
    def declare(self):
        return f'OMPI_F08_IGNORE_TKR_TYPE :: {self.name}'

    def c_parameter(self):
        return f'OMPI_CFI_BUFFER *{self.name}'


@FortranType.add('C_PTR_OUT')
class CptrType(FortranType):
    def declare(self):
        return f'TYPE(C_PTR), INTENT(OUT) :: {self.name}'

    def use(self):
        return [('ISO_C_BINDING', 'C_PTR')]

    def c_parameter(self):
        return f'char *{self.name}'

@FortranType.add('COUNT')
class CountType(FortranType):
    def declare(self):
        if self.bigcount:
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_COUNT_KIND')]
        else:
            return []

    def include(self):
        if self.gen_f90 == False:
            return ''
        else:
            return f"mpif-config.h"

    def c_parameter(self):
        type_ = 'MPI_Count' if self.bigcount else 'MPI_Fint'
        return f'{type_} *{self.name}'

@FortranType.add('COUNT_INOUT')
class CountTypeInOut(CountType):
    """COUNT type with INOUT INTENT"""
    def declare(self):
        if self.bigcount:
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'

@FortranType.add('COUNT_OUT')
class CountTypeInOut(CountType):
    """COUNT type with OUT INTENT"""
    def declare(self):
        if self.bigcount:
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'


@FortranType.add('COUNT_ONLY')
class CountTypeOnly(CountType):
    """COUNT type only"""
    def declare(self):
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(IN) :: {self.name}'

    def c_parameter(self):
        return f'MPI_Count *{self.name}'

@FortranType.add('COUNT_ONLY_OUT')
class CountTypeOnlyOut(CountTypeOnly):
    """COUNT type only with intent OUT"""
    def declare(self):
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(OUT) :: {self.name}'

@FortranType.add('DATATYPE')
class DatatypeType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Datatype), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Datatype')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('DATATYPE_OUT')
class DatatypeTypeOut(DatatypeType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Datatype), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'

@FortranType.add('DATATYPE_INOUT')
class DatatypeTypeInOut(DatatypeType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Datatype), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'

@FortranType.add('DATATYPE_ARRAY')
class DatatypeArrayType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Datatype), INTENT(IN) :: {self.name}(*)'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}(*)'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Datatype')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'


@FortranType.add('DATATYPE_ARRAY_OUT')
class DatatypeArrayOutType(DatatypeArrayType):
    """Array of datatype handles set by the procedure.

    As for DATATYPE_ARRAY, C sees the MPI_VAL members as an array of
    MPI_Fint.
    """

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        if self.gen_f90 == False:
            return f'TYPE(MPI_Datatype), INTENT(OUT) :: {self.name}({size})'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}({size})'


@FortranType.add('INT')
class IntType(FortranType):
    def declare(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('INT_OUT')
class IntOutType(FortranType):
    def declare(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('INT_INOUT')
class IntInOutType(FortranType):
    def declare(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('RANK')
class RankType(IntType):
    pass

@FortranType.add('RANK_OUT')
class RankType(IntOutType):
    pass

@FortranType.add('TAG')
class TagType(IntType):
    pass


@FortranType.add('INDEX_OUT')
class IndexOutType(IntType):
    def declare(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'


@FortranType.add('LOGICAL')
class LogicalType(IntType):
    """Logical type.

    NOTE: Since the logical type causes difficulties when passed to C code,
    this code uses a temporary integer in Fortran to pass to the C code. The 
    logical type is set based on C's true/false rules prior.

    The temporary must not be initialized in its declaration: that would
    give it the SAVE attribute, making it shared between threads.
    """

    def declare(self):
        return f'LOGICAL, INTENT(IN) :: {self.name}'

    def declare_tmp(self):
        return f'INTEGER :: {self.tmp_name}'
    
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def argument(self):
        return self.tmp_name
        
    def pre_c_call(self):
        return f'{self.tmp_name} = merge(1,0,{self.name})'
    
    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('LOGICAL_PTR')
class LogicalPtrType(LogicalType):
    """Logical pointer type.

    This type is used for LOGICAL parameters that need to be passed directly
    as memory addresses (void*) to the C layer, rather than going through
    integer conversion. This is particularly useful for functions like
    MPI_Abi_set_fortran_booleans where the C code needs to read the actual
    bit pattern of the LOGICAL value, not an integer representation.

    A temporary LOGICAL variable is passed by reference to the C binding
    interface, which declares the corresponding dummy argument as a plain
    (non-VALUE) LOGICAL.  Fortran therefore passes the address of the native
    LOGICAL temporary, and the C wrapper receives it as a void*.  This is the
    same by-reference convention the generator uses for default INTEGER
    arguments (passed to C as MPI_Fint *).

    Note: we deliberately do not use C_LOC()/TYPE(C_PTR) here.  C_LOC() applied
    to a default-kind LOGICAL is not standard-interoperable and makes compilers
    such as flang emit a -Winteroperability warning; passing the LOGICAL by
    reference avoids that while still handing C the native bit pattern.
    """

    def declare(self):
        return f'LOGICAL, INTENT(IN) :: {self.name}'

    def use(self):
        return []

    def declare_tmp(self):
        return f'LOGICAL :: {self.tmp_name}'

    def declare_cbinding_fortran(self):
        return f'LOGICAL :: {self.name}'

    def argument(self):
        return f'{self.tmp_name}'

    def pre_c_call(self):
        return f'{self.tmp_name} = {self.name}'

    def c_parameter(self):
        return f'void *{self.tmp_name}'

@FortranType.add('LOGICAL_ARRAY')
class LogicalArrayType(IntType):
    """Logical array type.

    NOTE: Since the logical type causes difficulties when passed to C code,
    this code uses a temporary integer array in Fortran to pass to the C code. The 
    logical type is set based on C's true/false rules prior using fortran merge intrinsic
    procedure.
    """ 
        
    def declare(self):
        return f'LOGICAL, INTENT(IN) :: {self.name}({self.count_param})'
            
    def declare_tmp(self):
        return f'INTEGER :: {self.tmp_name}({self.count_param})'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}({self.count_param})'

    def argument(self):
        return self.tmp_name

    def pre_c_call(self):
        return f'{self.tmp_name} = merge(1,0,{self.name})'
    
    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('LOGICAL_OUT')
class LogicalOutType(IntType):
    """Logical type.

    NOTE: Since the logical type causes difficulties when passed to C code,
    this code uses a temporary integer in Fortran to pass to the C code. On
    completion the logical type is set based on C's true/false rules.  The
    temporary is zeroed before each call, not in its declaration, which
    would give it the SAVE attribute: a value left by an earlier call (or
    by another thread) would then be returned if C does not set it.
    """

    def declare(self):
        return f'LOGICAL, INTENT(OUT) :: {self.name}'

    def declare_tmp(self):
        return f'INTEGER :: {self.tmp_name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'

    def argument(self):
        return self.tmp_name

    def pre_c_call(self):
        return f'{self.tmp_name} = 0'

    def post(self):
        return f'{self.name} = {self.tmp_name} /= 0'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('LOGICAL_PTR_OUT')
class LogicalPtrOutType(LogicalPtrType):
    """Logical pointer out type.
    
    Similar to LogicalPtrType, but for output parameters. The C layer writes
    directly to the memory address, and the Fortran wrapper copies the result
    back to the actual output variable. This is used for functions like
    MPI_Abi_get_fortran_booleans where the C code needs to set the bit pattern
    of LOGICAL values directly, not integer representations that need conversion.
    """

    def declare(self):
        return f'LOGICAL, INTENT(OUT) :: {self.name}'

    def pre_c_call(self):
        return ''
    
    def post(self):
        return f'{self.name} = {self.tmp_name}'

@FortranType.add('LOGICAL_ARRAY_OUT')
class LogicalArrayOutType(IntType):
    """Logical array out type.

    NOTE: Since the logical type causes difficulties when passed to C code,
    this code uses a temporary integer array in Fortran to pass to the C code.
    On completion the logical array is set based on C's true/false rules.  The
    temporary is zeroed first so that elements C does not set (e.g. beyond
    ndims in MPI_Cart_get) are not read uninitialized.
    """

    def declare(self):
        return f'LOGICAL, INTENT(OUT) :: {self.name}({self.count_param})'

    def declare_tmp(self):
        return f'INTEGER :: {self.tmp_name}({self.count_param})'
    
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}({self.count_param})'
        
    def argument(self):
        return self.tmp_name

    def pre_c_call(self):
        return f'{self.tmp_name} = 0'

    def post(self):
        return f'{self.name} = {self.tmp_name} /= 0'
   
    def c_parameter(self):
        return f'MPI_Fint *{self.name}'
        
@FortranType.add('LOGICAL_PTR_ARRAY')
class LogicalPtrArrayType(FortranType):
    """Logical array passed to C without conversion.

    LOGICAL_ARRAY converts to an integer array in Fortran, which needs the
    array length.  Some arguments have no length argument, e.g. remain_dims
    of MPI_Cart_sub, whose length is the number of dimensions of the
    communicator's Cartesian topology.  This type passes the native LOGICAL
    array by reference, as LOGICAL_PTR does for a scalar, and the C wrapper
    receives it as ompi_fortran_logical_t * and must do the conversion,
    e.g. with the OMPI_ARRAY_LOGICAL_2_INT macros.
    """

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'LOGICAL, INTENT(IN) :: {self.name}({size})'

    def c_parameter(self):
        return f'ompi_fortran_logical_t *{self.name}'

@FortranType.add('COMM')
class CommType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Comm), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def argument(self):
        if not self.gen_f90:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Comm')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('COMM_OUT')
class CommOutType(CommType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Comm), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'
    
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'
        
@FortranType.add('COMM_INOUT')
class CommInOutType(CommType):

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Comm), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'
    
    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Comm')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'
            
    def argument(self):
        return f'{self.name}%MPI_VAL'
    
    def use(self):
        return [('mpi_f08_types', 'MPI_Comm')]

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('GROUP')
class GroupType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Group), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'
            
    def argument(self):
        if not self.gen_f90:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'
    
    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Group')]
        else:
            return []
        
    def c_parameter(self):
        return f'MPI_Fint *{self.name}'
    
@FortranType.add('GROUP_OUT')
class GroupOutType(GroupType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Group), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'
    
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'
            
@FortranType.add('GROUP_INOUT')
class GroupInOutType(GroupType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Group), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'
    
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'

@FortranType.add('SESSION')
class SessionType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Session), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'
    
    def argument(self):
        if not self.gen_f90:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Session')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('SESSION_OUT')
class SessionOutType(SessionType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Session), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'
    
@FortranType.add('SESSION_INOUT')
class SessionInOutType(SessionType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Session), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'
    
@FortranType.add('STATUS')
class StatusType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Status) :: {self.name}'
        else:
            return f'INTEGER :: {self.name}(MPI_STATUS_SIZE)'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Status')]
        else:
            return []

    def include(self):
        if self.gen_f90 == False:
            return ''
        else:
            return f"mpif-config.h"

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'


@FortranType.add('STATUS_OUT')
class StatusOutType(StatusType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Status), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}(MPI_STATUS_SIZE)'

    def c_parameter(self):
        # TODO: Is this correct? (I've listed it as TYPE(MPI_Status) in the binding)
        return f'MPI_Fint *{self.name}'

@FortranType.add('STATUS_INOUT')
class StatusInOutType(StatusType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Status), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}(MPI_STATUS_SIZE)'

    def c_parameter(self):
        # TODO: Is this correct? (I've listed it as TYPE(MPI_Status) in the binding)
        return f'MPI_Fint *{self.name}'


@FortranType.add('REQUEST')
class RequestType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Request), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Request')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('REQUEST_OUT')
class RequestTypeOut(RequestType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Request), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Request')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('REQUEST_INOUT')
class RequestTypeInOut(RequestType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Request), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'

@FortranType.add('REQUEST_ARRAY')
class RequestArrayType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Request), INTENT(IN) :: {self.name}({self.count_param})'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}(*)'

    def declare_cbinding_fortran(self):
        if self.gen_f90 == False:
            return f'INTEGER, INTENT(IN) :: {self.name}({self.count_param})'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}(*)'
   
    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}(:)%MPI_VAL'
        else:
            return f'{self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Request')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('REQUEST_ARRAY_INOUT') 
class RequestArrayTypeInOut(RequestArrayType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Request), INTENT(INOUT) :: {self.name}({self.count_param})'
        else:
            return f'TYPE(MPI_Request), INTENT(INOUT) :: {self.name}(*)'

    def declare_cbinding_fortran(self):
        if self.gen_f90 == False:
            return f'INTEGER, INTENT(INOUT) :: {self.name}({self.count_param})'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}(*)'

@FortranType.add('STATUS_ARRAY')
class StatusArrayType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Status), INTENT(OUT) :: {self.name}(*)'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}(MPI_STATUS_SIZE,*)'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Status')]
        else:
            return []

    def include(self):
        if self.gen_f90 == False:
            return ''
        else:
            return f"mpif-config.h"

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('INT_ARRAY')
class IntArray(FortranType):
    """Integer array as used for MPI_*v() variable length functions."""

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER, INTENT(IN) :: {self.name}({size})'

    def use(self):
        if self.count_param == 'MPI_STATUS_SIZE':
            return [('mpi_f08_types', 'MPI_STATUS_SIZE')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('INT_ARRAY_OUT')
class IntArrayOut(IntArray):
    """Integer out array as used for MPI_*v() variable length functions."""

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER, INTENT(OUT) :: {self.name}({size})'
        
    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('ERRCODES_ARRAY')
class ErrcodesArray(IntArray):
    """array_of_errcodes of MPI_Comm_spawn and MPI_Comm_spawn_multiple.

    The standard gives it no INTENT, since the actual argument may be the
    MPI_ERRCODES_IGNORE sentinel; the C wrapper must check for that with
    OMPI_IS_FORTRAN_ERRCODES_IGNORE() before converting.
    """

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER :: {self.name}({size})'

@FortranType.add('INT_ARRAY_INOUT')
class IntArrayInOut(IntArray):
    """Integer out array as used for MPI_*v() variable length functions."""
        
    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER, INTENT(INOUT) :: {self.name}({size})'
        
@FortranType.add('COUNT_ARRAY')
class CountArray(IntArray):
    """Array of MPI_Count or int."""

    def declare(self):
        kind = '(KIND=MPI_COUNT_KIND)' if self.bigcount else ''
        size = '*' if self.count_param == None else self.count_param
#       print("size " + size + "count_param" + str(self.count_param))
        return f'INTEGER{kind}, INTENT(IN) :: {self.name}({size})'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_COUNT_KIND')]
        return []

    def c_parameter(self):
        count_type = 'MPI_Count' if self.bigcount else 'MPI_Fint'
        return f'{count_type} *{self.name}'

@FortranType.add('COUNT_ARRAY_OUT')
class CountArrayOut(IntArray):
    """Array of MPI_Count or int set by the procedure."""

    def declare(self):
        kind = '(KIND=MPI_COUNT_KIND)' if self.bigcount else ''
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER{kind}, INTENT(OUT) :: {self.name}({size})'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_COUNT_KIND')]
        return []

    def c_parameter(self):
        count_type = 'MPI_Count' if self.bigcount else 'MPI_Fint'
        return f'{count_type} *{self.name}'


@FortranType.add('AINT_COUNT_ARRAY')
class CountArray(IntArray):
    """Array of MPI_Count or int."""

    def declare(self):
        kind = '(KIND=MPI_COUNT_KIND)' if self.bigcount else '(KIND=MPI_ADDRESS_KIND)'
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER{kind}, INTENT(IN) :: {self.name}({size})'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_COUNT_KIND')]
        else:
            return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]

    def include(self):
        if self.gen_f90 == False:
            return ''
        else:
            return f"mpif-config.h"

    def c_parameter(self):
        count_type = 'MPI_Count' if self.bigcount else 'MPI_Aint'
        return f'{count_type} *{self.name}'



@FortranType.add('AINT')
class Aint(FortranType):
    """MPI_Aint type."""

    def declare(self):
        return f'INTEGER(MPI_ADDRESS_KIND), INTENT(IN) :: {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]
        else:
            return []

    def include(self):
        if self.gen_f90 == False:
            return ''
        else:
            return "mpif-config.h"

    def c_parameter(self):
        return f'MPI_Aint *{self.name}'

    def declare_result(self, name):
        return f'INTEGER(MPI_ADDRESS_KIND) :: {name}'

    def c_return_type(self):
        return 'MPI_Aint'


@FortranType.add('AINT_OUT')
class AintOut(Aint):
    """MPI_Aint out type."""

    def declare(self):
        return f'INTEGER(MPI_ADDRESS_KIND), INTENT(OUT) :: {self.name}'


@FortranType.add('AINT_COUNT')
class AintCountTypeIn(FortranType):
    """AINT/COUNT type with ININTENT"""
    def declare(self):
        if self.bigcount:
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER(KIND=MPI_ADDRESS_KIND), INTENT(IN) :: {self.name}'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_COUNT_KIND')]
        else:
            if self.gen_f90 == False:
                return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]
            else:
                return []

    def include(self):
        if self.gen_f90 == False:
            return ''
        else:
            return "mpif-config.h"

    def c_parameter(self):
        type_ = 'MPI_Count' if self.bigcount else 'MPI_Aint'
        return f'{type_} *{self.name}'


@FortranType.add('AINT_COUNT_INOUT')
class AintCountTypeInOut(FortranType):
    """AINT/COUNT type with INOUT INTENT"""
    def declare(self):
        if self.bigcount:
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER(KIND=MPI_ADDRESS_KIND), INTENT(INOUT) :: {self.name}'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_COUNT_KIND')]
        else:
            return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]

    def c_parameter(self):
        type_ = 'MPI_Count' if self.bigcount else 'MPI_Aint'
        return f'{type_} *{self.name}'


@FortranType.add('AINT_COUNT_OUT')
class AintCountTypeOut(FortranType):
    """AINT/COUNT type with OUT INTENT"""
    def declare(self):
        if self.bigcount:
            return f'INTEGER(KIND=MPI_COUNT_KIND), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER(KIND=MPI_ADDRESS_KIND), INTENT(OUT) :: {self.name}'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_COUNT_KIND')]
        else:
            return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]

    def c_parameter(self):
        type_ = 'MPI_Count' if self.bigcount else 'MPI_Aint'
        return f'{type_} *{self.name}'


@FortranType.add('AINT_ARRAY')
class AintArrayType(FortranType):
    """Array of MPI_Aint."""

    def declare(self):
        # TODO: Should there be a separate ASYNC version here, when the OMPI_ASYNCHRONOUS attr is required?
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER(KIND=MPI_ADDRESS_KIND), INTENT(IN) OMPI_ASYNCHRONOUS :: {self.name}({size})'

    def use(self):
        return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]

    def c_parameter(self):
        return f'MPI_Aint *{self.name}'


@FortranType.add('AINT_ARRAY_OUT')
class AintArrayOutType(AintArrayType):
    """Array of MPI_Aint set by the procedure."""

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER(KIND=MPI_ADDRESS_KIND), INTENT(OUT) :: {self.name}({size})'


@FortranType.add('DISP')
class Disp(FortranType):
    """Displacecment type."""

    def declare(self):
        kind = '(KIND=MPI_ADDRESS_KIND)' if self.bigcount else ''
        return f'INTEGER{kind}, INTENT(IN) :: {self.name}'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]
        return []

    def c_parameter(self):
        count_type = 'MPI_Aint' if self.bigcount else 'MPI_Fint'
        return f'{count_type} *{self.name}'

@FortranType.add('DISP_OUT')
class DispOut(FortranType):
    """Displacecment out type."""

    def declare(self):
        kind = '(KIND=MPI_ADDRESS_KIND)' if self.bigcount else ''
        return f'INTEGER{kind}, INTENT(OUT) :: {self.name}'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]
        return []

    def c_parameter(self):
        count_type = 'MPI_Aint' if self.bigcount else 'MPI_Fint'
        return f'{count_type} *{self.name}'


@FortranType.add('DISP_ARRAY')
class DispArray(IntArray):
    """Array of MPI_Aint or int."""

    def declare(self):
        kind = '(KIND=MPI_ADDRESS_KIND)' if self.bigcount else ''
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER{kind}, INTENT(IN) :: {self.name}({size})'

    def use(self):
        if self.bigcount:
            return [('mpi_f08_types', 'MPI_ADDRESS_KIND')]
        return []

    def c_parameter(self):
        count_type = 'MPI_Aint' if self.bigcount else 'MPI_Fint'
        return f'{count_type} *{self.name}'


@FortranType.add('OP')
class Op(FortranType):
    """MPI_Op type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Op), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Op')]
        else:
            return []

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('OP_INOUT')
class OpInOut(Op):
    """MPI_Op INOUT type."""
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Op), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'

@FortranType.add('OP_OUT')
class OpOut(Op):
    """MPI_Op OUT type."""
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Op), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'

@FortranType.add('USER_FUNCTION')
class UserFunctionType(FortranType):
    """MPI_User_function (MPI_User_function_c for bigcount) of MPI_Op_create.

    The procedure is passed to C with c_funloc(), as for the error handler
    and attribute callbacks.  The C wrapper receives it typed as the
    function the PMPI_Op_create{_c} call takes, but it must mark the new op
    as a Fortran one (OMPI_OP_FLAGS_FORTRAN_FUNC), after which Open MPI
    calls it as an ompi_op_fortran_handler{_bc}_fn_t: (void *invec,
    void *inoutvec, MPI_Fint *len or size_t *len, MPI_Fint *datatype).
    That matches the mpi_f08 interfaces, where invec and inoutvec are
    TYPE(C_PTR), VALUE, and len and the TYPE(MPI_Datatype) datatype are
    passed by reference.
    """

    @property
    def interface_name(self):
        return 'MPI_User_function_c' if self.bigcount else 'MPI_User_function'

    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE({self.interface_name}) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def declare_cbinding_fortran(self):
        return f'type(c_funptr), value :: {self.name}'

    def argument(self):
        return f'{self.tmp_name}'

    def declare_tmp(self):
        return f'type(c_funptr) :: {self.tmp_name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', self.interface_name), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

    def c_parameter(self):
        type_ = 'MPI_User_function_c' if self.bigcount else 'MPI_User_function'
        return f'{type_} *{self.name}'

    def pre_c_call(self):
        return f'{self.tmp_name} = c_funloc({self.name})'

@FortranType.add('GREQUEST_QUERY_FN')
class GrequestQueryFnType(FortranType):
    """MPI_Grequest_query_function of MPI_Grequest_start.

    The procedure is passed to C with c_funloc(), as for the other
    callbacks.  The C wrapper receives it typed as the function
    PMPI_Grequest_start takes, but it must mark the request as having
    Fortran callbacks (greq_funcs_are_c = false), after which Open MPI
    calls them with Fortran arguments: extra_state, the status, and
    complete by reference, and an MPI_Fint *ierror.
    """

    interface_name = 'MPI_Grequest_query_function'

    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE({self.interface_name}) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def declare_cbinding_fortran(self):
        return f'type(c_funptr), value :: {self.name}'

    def argument(self):
        return f'{self.tmp_name}'

    def declare_tmp(self):
        return f'type(c_funptr) :: {self.tmp_name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', self.interface_name), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

    def c_parameter(self):
        return f'{self.interface_name} *{self.name}'

    def pre_c_call(self):
        return f'{self.tmp_name} = c_funloc({self.name})'

@FortranType.add('GREQUEST_FREE_FN')
class GrequestFreeFnType(GrequestQueryFnType):
    """MPI_Grequest_free_function of MPI_Grequest_start."""

    interface_name = 'MPI_Grequest_free_function'

@FortranType.add('GREQUEST_CANCEL_FN')
class GrequestCancelFnType(GrequestQueryFnType):
    """MPI_Grequest_cancel_function of MPI_Grequest_start."""

    interface_name = 'MPI_Grequest_cancel_function'

@FortranType.add('WIN')
class Win(FortranType):
    """MPI_Win type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Win), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Win')]
        else:
            return []

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('WIN_OUT')
class WinOut(Win):
    """MPI_Win out type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Win), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'

@FortranType.add('WIN_INOUT')
class WinInOut(Win):
    """MPI_Win inout type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Win), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'

@FortranType.add('FILE')
class File(FortranType):
    """MPI_File type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_File), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_File')]
        else:
            return []

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('FILE_INOUT')
class FileOut(File):
    """MPI_File INOUT type."""
        
    def declare(self):
        if self.gen_f90 == False:
           return f'TYPE(MPI_File), INTENT(INOUT) :: {self.name}'
        else:
           return f'INTEGER, INTENT(INOUT) :: {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'

@FortranType.add('FILE_OUT')
class FileOut(File):
    """MPI_File OUT type."""
        
    def declare(self):
        if self.gen_f90 == False:
           return f'TYPE(MPI_File), INTENT(OUT) :: {self.name}'
        else:
           return f'INTEGER, INTENT(OUT) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'

@FortranType.add('INFO')
class Info(FortranType):
    """MPI_Info type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Info), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Info')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('INFO_ARRAY')
class InfoArray(FortranType):
    """Array of MPI_Info handles, e.g. array_of_info of MPI_Comm_spawn_multiple.

    Like DATATYPE_ARRAY, the array of derived types is passed as is; C sees
    the MPI_VAL members as an array of MPI_Fint.
    """

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        if self.gen_f90 == False:
            return f'TYPE(MPI_Info), INTENT(IN) :: {self.name}({size})'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}({size})'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Info')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('INFO_OUT')
class InfoOut(Info):
    """MPI_Info out type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Info), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'

@FortranType.add('INFO_INOUT')
class InfoInOut(Info):
    """MPI_Info inout type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Info), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'

@FortranType.add('OFFSET')
class Offset(FortranType):
    """MPI_Offset type."""

    def declare(self):
        return f'INTEGER(MPI_OFFSET_KIND), INTENT(IN) :: {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_OFFSET_KIND')]
        else:
            return []

    def include(self):
        if self.gen_f90 == False:
            return ''
        else:
            return "mpif-config.h"

    def c_parameter(self):
        return f'MPI_Offset *{self.name}'

@FortranType.add('OFFSET_OUT')
class OffsetOut(Offset):
    """MPI_Offset OUT type."""
    
    def declare(self):
        return f'INTEGER(MPI_OFFSET_KIND), INTENT(OUT) :: {self.name}'
        

@FortranType.add('CHAR_ARRAY')
class CharArray(FortranType):
    """Fortran CHAR type."""

    def declare(self):
        return f'CHARACTER(LEN=*), INTENT(IN) :: {self.name}'

    def use(self):
        return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_null_char')]

    def declare_cbinding_fortran(self):
        return f'CHARACTER(KIND=C_CHAR), INTENT(IN) :: {self.name}(*)'

    def argument(self):
        # Leading and trailing blanks of Fortran string arguments are not
        # significant (see e.g. MPI_INFO_SET), so strip them before adding
        # the C terminator, as ompi_fortran_string_f2c() does for mpif-h.
        return f'trim(adjustl({self.name}))//c_null_char'

    def c_parameter(self):
        return f'char *{self.name}'

@FortranType.add('CHAR_ARRAY_OUT')
class CharArrayOut(FortranType):
    """Fortran CHAR OUT type."""
            
    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'CHARACTER(LEN={size}), INTENT(OUT) :: {self.name}'
    
    def use(self):
#       print("self COUNT count_param" + str(self.count_param))
        if self.count_param == 'MPI_MAX_OBJECT_NAME':
            return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_int'), ('mpi_f08_types', 'MPI_MAX_OBJECT_NAME')]
        elif self.count_param == 'MPI_MAX_PORT_NAME':
            return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_int'), ('mpi_f08_types', 'MPI_MAX_PORT_NAME')]
        elif self.count_param == 'MPI_MAX_ERROR_STRING':
            return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_int'), ('mpi_f08_types', 'MPI_MAX_ERROR_STRING')]
        elif self.count_param == 'MPI_MAX_PROCESSOR_NAME':
            return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_int'), ('mpi_f08_types', 'MPI_MAX_PROCESSOR_NAME')]
        elif self.count_param == 'MPI_MAX_LIBRARY_VERSION_STRING':
            return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_int'), ('mpi_f08_types', 'MPI_MAX_LIBRARY_VERSION_STRING')]
        elif self.count_param == 'MPI_STATUS_SIZE':
            return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_int'), ('mpi_f08_types', 'MPI_STATUS_SIZE')]
        else:
            return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_int')]

    # The C wrapper also receives the length of the Fortran string as
    # {name}_len: C writes '\0'-terminated strings whose MPI_MAX_* bound
    # is one larger than the Fortran value, while Fortran expects the
    # result blank-padded, so templates fetch into a C buffer and copy it
    # out with ompi_fortran_string_c2f({c_buffer}, {name}, {name}_len).
    @property
    def len_name(self):
        return f'{self.name}_len'

    def cbinding_params(self):
        return [self.name, self.len_name]

    def cbinding_arguments(self):
        return [self.name, f'len({self.name}, KIND=C_INT)']

    def declare_cbinding_fortran(self):
        return (f'CHARACTER(KIND=C_CHAR), INTENT(OUT) :: {self.name}(*)\n'
                f'INTEGER(KIND=C_INT), VALUE, INTENT(IN) :: {self.len_name}')

    def c_parameter(self):
        return f'char *{self.name}, int {self.len_name}'


@FortranType.add('STRING_ARRAY')
class StringArray(FortranType):
    """Array of Fortran strings, e.g. argv of MPI_Comm_spawn.

    The array is passed to C as laid out in Fortran memory, and the length
    of each string -- the hidden length argument, which a BIND(C) interface
    does not provide -- as {name}_len.  The C wrapper converts it with the
    ompi_fortran_argv_*_f2c() functions.  Passing the array itself, rather
    than a copy, keeps sentinels such as MPI_ARGV_NULL recognizable by
    address.
    """

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'CHARACTER(LEN=*), INTENT(IN) :: {self.name}({size})'

    def use(self):
        return [('iso_c_binding', 'c_char'), ('iso_c_binding', 'c_int')]

    @property
    def len_name(self):
        return f'{self.name}_len'

    def cbinding_params(self):
        return [self.name, self.len_name]

    def cbinding_arguments(self):
        return [self.name, f'len({self.name}, KIND=C_INT)']

    def declare_cbinding_fortran(self):
        return (f'CHARACTER(KIND=C_CHAR), INTENT(IN) :: {self.name}(*)\n'
                f'INTEGER(KIND=C_INT), VALUE, INTENT(IN) :: {self.len_name}')

    def c_parameter(self):
        return f'char *{self.name}, int {self.len_name}'


@FortranType.add('STRING_ARRAY_2D')
class StringArray2D(StringArray):
    """Two-dimensional array of Fortran strings, (count_param, *).

    Used for array_of_argv of MPI_Comm_spawn_multiple: column i holds the
    arguments of command i, so in memory the strings of the different argv
    vectors are interleaved.
    """

    def declare(self):
        return f'CHARACTER(LEN=*), INTENT(IN) :: {self.name}({self.count_param},*)'


@FortranType.add('MESSAGE_OUT')
class MessageOut(FortranType):
    """MPI_Message OUT type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Message), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Message')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('MESSAGE_INOUT')
class MessageInOut(MessageOut):
    """MPI_Message INOUT type."""

    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Message), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'


@FortranType.add('ERRHANDLER')
class ErrhandlerType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Errhandler), INTENT(IN) :: {self.name}'
        else:
            return f'INTEGER, INTENT(IN) :: {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(IN) :: {self.name}'

    def argument(self):
        if self.gen_f90 == False:
            return f'{self.name}%MPI_VAL'
        else:
            return f'{self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_types', 'MPI_Errhandler')]
        else:
            return []

    def c_parameter(self):
        return f'MPI_Fint *{self.name}'

@FortranType.add('ERRHANDLER_OUT')
class ErrhandlerOutType(ErrhandlerType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Errhandler), INTENT(OUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(OUT) :: {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(OUT) :: {self.name}'
    
@FortranType.add('ERRHANDLER_INOUT')
class ErrhandlerOutType(ErrhandlerOutType):
    def declare(self):
        if self.gen_f90 == False:
            return f'TYPE(MPI_Errhandler), INTENT(INOUT) :: {self.name}'
        else:
            return f'INTEGER, INTENT(INOUT) :: {self.name}'

    def declare_cbinding_fortran(self):
        return f'INTEGER, INTENT(INOUT) :: {self.name}'
   
@FortranType.add('COMM_COPY_ATTR_FN')
class CommCopyAttrFnType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Comm_copy_attr_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'type(c_funptr), value :: {self.name}'
    
    def argument(self):
        return f'{self.tmp_name}'
    
    def declare_tmp(self):
        return f'type(c_funptr)::{self.tmp_name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Comm_copy_attr_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []
        
    def c_parameter(self):
        return f'ompi_aint_copy_attr_function {self.name}'
    
    def pre_c_call(self): 
        return f'{self.tmp_name} = c_funloc({self.name})'

@FortranType.add('TYPE_COPY_ATTR_FN')
class TypeCopyAttrFnType(CommCopyAttrFnType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Type_copy_attr_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'
        
    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Type_copy_attr_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []
        
@FortranType.add('WIN_COPY_ATTR_FN')
class WinCopyAttrFnType(CommCopyAttrFnType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Win_copy_attr_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Win_copy_attr_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

@FortranType.add('COMM_DELETE_ATTR_FN')
class CommDeleteAttrFnType(FortranType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Comm_delete_attr_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def declare_cbinding_fortran(self):
        return f'type(c_funptr), value :: {self.name}'

    def argument(self):
        return f'{self.tmp_name}'

    def declare_tmp(self):
        return f'type(c_funptr) :: {self.tmp_name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Comm_delete_attr_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

    def c_parameter(self):
        return f'ompi_aint_delete_attr_function {self.name}'

    def pre_c_call(self):
        return f'{self.tmp_name} = c_funloc({self.name})'

@FortranType.add('TYPE_DELETE_ATTR_FN')
class TypeDeleteAttrFnType(CommDeleteAttrFnType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Type_delete_attr_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Type_delete_attr_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

@FortranType.add('WIN_DELETE_ATTR_FN')
class WinDeleteAttrFnType(CommDeleteAttrFnType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Win_delete_attr_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Win_delete_attr_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []


@FortranType.add('COMM_ERRHANDLER_FN')
class CommErrhandlerFnType(FortranType):
    def declare(self): 
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Comm_errhandler_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'
        
    def declare_cbinding_fortran(self):
        return f'type(c_funptr), value :: {self.name}'

    def argument(self):
        return f'{self.tmp_name}'
    
    def declare_tmp(self):
        return f'type(c_funptr) :: {self.tmp_name}'
        
    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Comm_errhandler_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []
        
    def c_parameter(self):
        return f'ompi_errhandler_fortran_handler_fn_t {self.name}'
    
    def pre_c_call(self):
        return f'{self.tmp_name} = c_funloc({self.name})'


@FortranType.add('FILE_ERRHANDLER_FN')
class FileErrhandlerFnType(CommErrhandlerFnType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_File_errhandler_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_File_errhandler_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

@FortranType.add('SESSION_ERRHANDLER_FN')
class SessionErrhandlerFnType(CommErrhandlerFnType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Session_errhandler_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Session_errhandler_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

@FortranType.add('WIN_ERRHANDLER_FN')
class WinErrhandlerFnType(CommErrhandlerFnType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Win_errhandler_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Win_errhandler_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

@FortranType.add('DATAREP_CONVERSION_FN')
class DataRepConversionFnType(FortranType):
    """MPI_Datarep_conversion_function{_c} of MPI_Register_datarep{_c}.

    The procedure is passed to C with c_funloc().  The mpi_f08
    MPI_CONVERSION_FN_NULL{_C} is a procedure of the mpi_f08_callbacks
    module, which the C side cannot recognize, so it is passed as a null
    pointer, the C MPI_CONVERSION_FN_NULL{_C}.
    """

    @property
    def interface_name(self):
        suffix = '_c' if self.bigcount else ''
        return f'MPI_Datarep_conversion_function{suffix}'

    @property
    def null_fn_name(self):
        suffix = '_C' if self.bigcount else ''
        return f'MPI_CONVERSION_FN_NULL{suffix}'

    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE({self.interface_name}) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def declare_cbinding_fortran(self):
        return f'type(c_funptr), value :: {self.name}'

    def argument(self):
        return f'{self.tmp_name}'

    def declare_tmp(self):
        return f'type(c_funptr) :: {self.tmp_name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', self.interface_name),
                    ('mpi_f08_callbacks', self.null_fn_name),
                    ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr'),
                    ('iso_c_binding', 'c_associated'), ('iso_c_binding', 'c_null_funptr')]
        else:
            return []

    def c_parameter(self):
        suffix = '_c' if self.bigcount else ''
        return f'ompi_f08_datarep_conversion{suffix}_fn_t *{self.name}'

    def pre_c_call(self):
        return (f'{self.tmp_name} = c_funloc({self.name})\n'
                f'if (c_associated({self.tmp_name}, c_funloc({self.null_fn_name}))) then\n'
                f'    {self.tmp_name} = c_null_funptr\n'
                f'end if')

@FortranType.add('DATAREP_EXTENT_FN')
class DataRepExtentFnType(DataRepConversionFnType):
    def declare(self):
        if self.gen_f90 == False:
            return f'PROCEDURE(MPI_Datarep_extent_function) :: {self.name}'
        else:
            return f'EXTERNAL {self.name}'

    def use(self):
        if self.gen_f90 == False:
            return [('mpi_f08_interfaces_callbacks', 'MPI_Datarep_extent_function'), ('iso_c_binding', 'c_funloc'), ('iso_c_binding', 'c_funptr')]
        else:
            return []

    def c_parameter(self):
        return f'ompi_f08_datarep_extent_fn_t *{self.name}'

    def pre_c_call(self):
        return f'{self.tmp_name} = c_funloc({self.name})'


@FortranType.add('RANGE_ARRAY')
class RangeArray(FortranType):
    """Range as used for MPI_Group_range_incl/excl functions."""

    def declare(self):
        size = '*' if self.count_param == None else self.count_param
        return f'INTEGER, INTENT(IN) :: {self.name}(3,{size})'

    def c_parameter(self):
        return f'MPI_Fint {self.name}[][3]'
