! -*- fortran -*-
!
! Copyright (c) 2026      Triad National Security, LLC. All rights
!                         reserved.
! $COPYRIGHT$
!
! Additional copyrights may follow
!
! $HEADER$
! SPDX-License-Identifier: BSD-3-Clause-Open-MPI
!
! Fortran (mpi_f08) test for MPI_Op_create and MPI_Op_create_c, generated
! from ompi/mpi/fortran/use-mpi-f08/op_create.c.in and the USER_FUNCTION
! type in ompi/mpi/bindings/ompi_bindings/fortran_type.py.
!
! Open MPI calls a Fortran user function with Fortran arguments: the
! buffers as addresses (TYPE(C_PTR), VALUE), and len and the datatype by
! reference.  The user functions here check that len and the datatype
! are what the reduction passed, and record any mismatch.  The test
! checks:
!
!   - MPI_Op_create: an MPI_Allreduce with the user op gives the right
!     sum, and the function sees the right len and datatype;
!   - MPI_Op_create_c: the same, with the MPI_User_function_c interface
!     (INTEGER(KIND=MPI_COUNT_KIND) len);
!   - commute is passed through, as seen by MPI_Op_commutative;
!   - the PMPI_ names, keyword arguments, and an omitted ierror;
!   - MPI_Op_free resets the handle to MPI_OP_NULL.
!
! Run it with 2 processes.  Each failure is reported with an ERROR line,
! and the program finishes with "error stop 1" if anything failed.
!
      module op_create_f08_fns
      use mpi_f08
      implicit none
      integer, parameter :: N = 5
      integer :: bad_calls = 0
      contains

      subroutine my_sum(invec, inoutvec, len, datatype)
      use, intrinsic :: iso_c_binding, only : c_ptr, c_f_pointer
      type(c_ptr), value :: invec, inoutvec
      integer :: len
      type(MPI_Datatype) :: datatype
      integer, pointer :: a(:), b(:)
      if (N /= len .or. MPI_INTEGER /= datatype) then
         bad_calls = bad_calls + 1
         return
      endif
      call c_f_pointer(invec, a, [len])
      call c_f_pointer(inoutvec, b, [len])
      b = a + b
      end subroutine my_sum

      subroutine my_sum_c(invec, inoutvec, len, datatype) bind(c)
      use, intrinsic :: iso_c_binding, only : c_ptr, c_f_pointer
      type(c_ptr), value :: invec, inoutvec
      integer(kind=MPI_COUNT_KIND) :: len
      type(MPI_Datatype) :: datatype
      integer, pointer :: a(:), b(:)
      if (N /= len .or. MPI_INTEGER /= datatype) then
         bad_calls = bad_calls + 1
         return
      endif
      call c_f_pointer(invec, a, [len])
      call c_f_pointer(inoutvec, b, [len])
      b = a + b
      end subroutine my_sum_c

      end module op_create_f08_fns

      program op_create_f08
      use mpi_f08
      use op_create_f08_fns
      implicit none

      type(MPI_Op) :: op
      integer :: rank, p, ierr, nfail, i
      integer :: sbuf(N), rbuf(N), expect(N)
      logical :: commute

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Comm_rank(MPI_COMM_WORLD, rank)
      call MPI_Comm_size(MPI_COMM_WORLD, p)
      sbuf = [(rank * 10 + i, i = 1, N)]
      expect = [(10 * p * (p - 1) / 2 + p * i, i = 1, N)]

!     ---------------------------------------------------------------
!     MPI_Op_create, commutative
!     ---------------------------------------------------------------
      call MPI_Op_create(my_sum, .true., op, ierr)
      call check(MPI_SUCCESS == ierr, "op_create")
      call MPI_Op_commutative(op, commute)
      call check(commute, "op_create commute=.true.")
      rbuf = -1
      call MPI_Allreduce(sbuf, rbuf, N, MPI_INTEGER, op, MPI_COMM_WORLD, ierr)
      call check(MPI_SUCCESS == ierr .and. all(expect == rbuf), &
                 "op_create allreduce")
      call MPI_Op_free(op)
      call check(MPI_OP_NULL == op, "op_free")

!     PMPI, keywords, no ierror, not commutative
      call PMPI_Op_create(user_fn=my_sum, commute=.false., op=op)
      call MPI_Op_commutative(op, commute)
      call check(.not. commute, "PMPI op_create commute=.false.")
      rbuf = -1
      call MPI_Allreduce(sbuf, rbuf, N, MPI_INTEGER, op, MPI_COMM_WORLD, ierr)
      call check(MPI_SUCCESS == ierr .and. all(expect == rbuf), &
                 "PMPI op_create allreduce")
      call MPI_Op_free(op)

!     ---------------------------------------------------------------
!     MPI_Op_create_c
!     ---------------------------------------------------------------
      call MPI_Op_create_c(my_sum_c, .true., op, ierr)
      call check(MPI_SUCCESS == ierr, "op_create_c")
      call MPI_Op_commutative(op, commute)
      call check(commute, "op_create_c commute=.true.")
      rbuf = -1
      call MPI_Allreduce(sbuf, rbuf, N, MPI_INTEGER, op, MPI_COMM_WORLD, ierr)
      call check(MPI_SUCCESS == ierr .and. all(expect == rbuf), &
                 "op_create_c allreduce")
      call MPI_Op_free(op)

      call PMPI_Op_create_c(user_fn=my_sum_c, commute=.false., op=op)
      call MPI_Op_commutative(op, commute)
      call check(.not. commute, "PMPI op_create_c commute=.false.")
      call MPI_Op_free(op)

      call check(0 == bad_calls, "user function got the wrong len or datatype")

      call MPI_Finalize(ierr)
      if (nfail > 0) then
         print *, "ERROR: ", nfail, " check(s) failed"
         error stop 1
      endif

      contains

      subroutine check(ok, what)
      logical, intent(in) :: ok
      character(len=*), intent(in) :: what
      if (.not. ok) then
         print *, "ERROR: ", what, " (ierr=", ierr, ") rbuf=", rbuf, &
                  " expected=", expect, " bad calls=", bad_calls
         nfail = nfail + 1
      endif
      end subroutine check

      end program op_create_f08
