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
! Fortran (mpi_f08) test for MPI_Register_datarep and
! MPI_Register_datarep_c, generated from
! ompi/mpi/fortran/use-mpi-f08/register_datarep.c.in with the C intercepts
! in ompi/mpi/fortran/use-mpi-f08/base/datarep_f08.c.
!
! The mpi_f08 binding registers C intercepts that call the Fortran
! callbacks.  The MPI-IO components may not support user datareps (ompio
! does not), so nothing in MPI would ever call them.  Instead,
! register_datarep_f08_c.c defines PMPI_Register_datarep{_c} for this
! program: it records what the binding passes, and calls the registered
! callbacks itself.  The test checks, for both MPI_Register_datarep and
! MPI_Register_datarep_c:
!
!   - the datarep name loses its leading and trailing blanks;
!   - the mpi_f08 MPI_CONVERSION_FN_NULL{_C} is registered as the C
!     MPI_CONVERSION_FN_NULL{_C} (no conversion), a real procedure is not;
!   - the extent and conversion intercepts call the Fortran callbacks
!     with the right datatype, count, buffers, position and extra_state,
!     and return their ierror;
!   - extra_state is passed by value: the callbacks get the value it had
!     at registration, even if the variable was changed afterwards, or
!     was a constant;
!   - the PMPI_ name, keyword arguments, and an omitted ierror;
!   - MPI_Register_datarep_c passes a count that needs more than 32 bits.
!
! Run it with 2 processes.  Each failure is reported with an ERROR line,
! and the program finishes with "error stop 1" if anything failed.
!
      module register_datarep_f08_fns
      use, intrinsic :: iso_c_binding
      use mpi_f08
      implicit none
      integer(kind=MPI_ADDRESS_KIND), parameter :: BIG = 2_MPI_ADDRESS_KIND**40
      logical :: type_ok
      integer :: seen_count = -1
      integer(kind=MPI_COUNT_KIND) :: seen_count_c = -1
      integer(kind=MPI_OFFSET_KIND) :: seen_position = -1
      integer(kind=MPI_ADDRESS_KIND) :: seen_es = -1

      interface
         function captured_datarep_is(expected) bind(c)
         import :: c_char, c_int
         character(kind=c_char), intent(in) :: expected(*)
         integer(c_int) :: captured_datarep_is
         end function
         function captured_read_fn_is_null() bind(c)
         import :: c_int
         integer(c_int) :: captured_read_fn_is_null
         end function
         function captured_write_fn_is_null() bind(c)
         import :: c_int
         integer(c_int) :: captured_write_fn_is_null
         end function
         function call_extent_fn(extent) bind(c)
         import :: c_int, MPI_ADDRESS_KIND
         integer(kind=MPI_ADDRESS_KIND) :: extent
         integer(c_int) :: call_extent_fn
         end function
         function call_conversion_fn(write, userbuf, count, filebuf, &
                                     position) bind(c)
         import :: c_int, MPI_OFFSET_KIND
         integer(c_int), value :: write, count
         integer(c_int) :: userbuf(*), filebuf(*)
         integer(kind=MPI_OFFSET_KIND), value :: position
         integer(c_int) :: call_conversion_fn
         end function
         function captured_bigcount() bind(c)
         import :: c_int
         integer(c_int) :: captured_bigcount
         end function
         function call_conversion_fn_c(write, userbuf, count, filebuf, &
                                       position) bind(c)
         import :: c_int, MPI_COUNT_KIND, MPI_OFFSET_KIND
         integer(c_int), value :: write
         integer(c_int) :: userbuf(*), filebuf(*)
         integer(kind=MPI_COUNT_KIND), value :: count
         integer(kind=MPI_OFFSET_KIND), value :: position
         integer(c_int) :: call_conversion_fn_c
         end function
      end interface

      contains

!     userbuf = filebuf + 100; fails with MPI_ERR_OTHER at position 99
      subroutine read_fn(userbuf, datatype, count, filebuf, position, &
                         extra_state, ierror)
      type(c_ptr), value :: userbuf, filebuf
      type(MPI_Datatype) :: datatype
      integer :: count, ierror
      integer(kind=MPI_OFFSET_KIND) :: position
      integer(kind=MPI_ADDRESS_KIND) :: extra_state
      integer, pointer :: u(:), f(:)
      type_ok = MPI_INTEGER == datatype
      seen_count = count
      seen_position = position
      seen_es = extra_state
      call c_f_pointer(userbuf, u, [count])
      call c_f_pointer(filebuf, f, [count])
      u = f + 100
      ierror = MPI_SUCCESS
      if (99 == position) ierror = MPI_ERR_OTHER
      end subroutine read_fn

!     filebuf = userbuf - 100
      subroutine write_fn(userbuf, datatype, count, filebuf, position, &
                          extra_state, ierror)
      type(c_ptr), value :: userbuf, filebuf
      type(MPI_Datatype) :: datatype
      integer :: count, ierror
      integer(kind=MPI_OFFSET_KIND) :: position
      integer(kind=MPI_ADDRESS_KIND) :: extra_state
      integer, pointer :: u(:), f(:)
      type_ok = MPI_INTEGER == datatype
      seen_count = count
      seen_position = position
      seen_es = extra_state
      call c_f_pointer(userbuf, u, [count])
      call c_f_pointer(filebuf, f, [count])
      f = u - 100
      ierror = MPI_SUCCESS
      end subroutine write_fn

!     The _c versions: they only touch the buffers for count <= 3, so
!     that a count that needs 64 bits can be passed through
      subroutine read_fn_c(userbuf, datatype, count, filebuf, position, &
                           extra_state, ierror)
      type(c_ptr), value :: userbuf, filebuf
      type(MPI_Datatype) :: datatype
      integer(kind=MPI_COUNT_KIND) :: count
      integer(kind=MPI_OFFSET_KIND) :: position
      integer(kind=MPI_ADDRESS_KIND) :: extra_state
      integer :: ierror
      integer, pointer :: u(:), f(:)
      type_ok = MPI_INTEGER == datatype
      seen_count_c = count
      seen_position = position
      seen_es = extra_state
      if (count <= 3) then
         call c_f_pointer(userbuf, u, [count])
         call c_f_pointer(filebuf, f, [count])
         u = f + 100
      endif
      ierror = MPI_SUCCESS
      end subroutine read_fn_c

      subroutine write_fn_c(userbuf, datatype, count, filebuf, position, &
                            extra_state, ierror)
      type(c_ptr), value :: userbuf, filebuf
      type(MPI_Datatype) :: datatype
      integer(kind=MPI_COUNT_KIND) :: count
      integer(kind=MPI_OFFSET_KIND) :: position
      integer(kind=MPI_ADDRESS_KIND) :: extra_state
      integer :: ierror
      integer, pointer :: u(:), f(:)
      type_ok = MPI_INTEGER == datatype
      seen_count_c = count
      seen_position = position
      seen_es = extra_state
      if (count <= 3) then
         call c_f_pointer(userbuf, u, [count])
         call c_f_pointer(filebuf, f, [count])
         f = u - 100
      endif
      ierror = MPI_SUCCESS
      if (99 == position) ierror = MPI_ERR_OTHER
      end subroutine write_fn_c

      subroutine extent_fn(datatype, extent, extra_state, ierror)
      type(MPI_Datatype) :: datatype
      integer(kind=MPI_ADDRESS_KIND) :: extent, extra_state
      integer :: ierror
      type_ok = MPI_DOUBLE_PRECISION == datatype
      seen_es = extra_state
      extent = 12
      ierror = MPI_SUCCESS
      end subroutine extent_fn

      end module register_datarep_f08_fns

      program register_datarep_f08
      use, intrinsic :: iso_c_binding
      use mpi_f08
      use register_datarep_f08_fns
      implicit none

      integer(kind=MPI_ADDRESS_KIND) :: es, extent
      integer(c_int) :: ubuf(3), fbuf(3)
      integer :: ierr, nfail, rc

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif

!     ---------------------------------------------------------------
!     No read conversion; extra_state changed after registration
!     ---------------------------------------------------------------
      es = BIG + 1
      call MPI_Register_datarep("  rep1  ", MPI_CONVERSION_FN_NULL, &
                                write_fn, extent_fn, es, ierr)
      es = -1
      call check(MPI_SUCCESS == ierr, "register_datarep")
      call check(0 /= captured_datarep_is("rep1" // c_null_char), "datarep name")
      call check(0 /= captured_read_fn_is_null(), &
                 "MPI_CONVERSION_FN_NULL is not NULL in C")
      call check(0 == captured_write_fn_is_null(), "write_fn is NULL in C")

      extent = -1
      rc = call_extent_fn(extent)
      call check(MPI_SUCCESS == rc .and. 12 == extent .and. type_ok .and. &
                 BIG + 1 == seen_es, "extent_fn")

      ubuf = [1, 2, 3]
      fbuf = -1
      rc = call_conversion_fn(1, ubuf, 3, fbuf, 17_MPI_OFFSET_KIND)
      call check(MPI_SUCCESS == rc .and. all([-99, -98, -97] == fbuf) .and. &
                 type_ok .and. 3 == seen_count .and. 17 == seen_position .and. &
                 BIG + 1 == seen_es, "write_fn")

!     ---------------------------------------------------------------
!     No write conversion; PMPI, keywords, no ierror, constant
!     extra_state
!     ---------------------------------------------------------------
      call PMPI_Register_datarep(datarep="rep2", read_conversion_fn=read_fn, &
                                 write_conversion_fn=MPI_CONVERSION_FN_NULL, &
                                 dtype_file_extent_fn=extent_fn, &
                                 extra_state=BIG + 2)
      call check(0 /= captured_datarep_is("rep2" // c_null_char), &
                 "PMPI datarep name")
      call check(0 == captured_read_fn_is_null(), "PMPI read_fn is NULL in C")
      call check(0 /= captured_write_fn_is_null(), &
                 "PMPI MPI_CONVERSION_FN_NULL is not NULL in C")

      fbuf = [4, 5, 6]
      ubuf = -1
      rc = call_conversion_fn(0, ubuf, 3, fbuf, 0_MPI_OFFSET_KIND)
      call check(MPI_SUCCESS == rc .and. all([104, 105, 106] == ubuf) .and. &
                 type_ok .and. BIG + 2 == seen_es, "read_fn")
      rc = call_conversion_fn(0, ubuf, 3, fbuf, 99_MPI_OFFSET_KIND)
      call check(MPI_ERR_OTHER == rc, "read_fn error returned")

!     ---------------------------------------------------------------
!     MPI_Register_datarep_c: no read conversion
!     ---------------------------------------------------------------
      es = BIG + 3
      call MPI_Register_datarep_c("rep3", MPI_CONVERSION_FN_NULL_C, &
                                  write_fn_c, extent_fn, es, ierr)
      es = -1
      call check(MPI_SUCCESS == ierr .and. 0 /= captured_bigcount(), &
                 "register_datarep_c")
      call check(0 /= captured_datarep_is("rep3" // c_null_char), &
                 "datarep_c name")
      call check(0 /= captured_read_fn_is_null(), &
                 "MPI_CONVERSION_FN_NULL_C is not NULL in C")
      call check(0 == captured_write_fn_is_null(), "write_fn_c is NULL in C")

      extent = -1
      rc = call_extent_fn(extent)
      call check(MPI_SUCCESS == rc .and. 12 == extent .and. type_ok .and. &
                 BIG + 3 == seen_es, "datarep_c extent_fn")

      ubuf = [7, 8, 9]
      fbuf = -1
      rc = call_conversion_fn_c(1, ubuf, 3_MPI_COUNT_KIND, fbuf, &
                                17_MPI_OFFSET_KIND)
      call check(MPI_SUCCESS == rc .and. all([-93, -92, -91] == fbuf) .and. &
                 type_ok .and. 3 == seen_count_c .and. &
                 17 == seen_position .and. BIG + 3 == seen_es, "write_fn_c")
      rc = call_conversion_fn_c(1, ubuf, 2_MPI_COUNT_KIND**31 + 5, fbuf, &
                                99_MPI_OFFSET_KIND)
      call check(MPI_ERR_OTHER == rc .and. &
                 2_MPI_COUNT_KIND**31 + 5 == seen_count_c, &
                 "write_fn_c large count, error returned")

!     No write conversion; PMPI, keywords, no ierror, constant
!     extra_state
      call PMPI_Register_datarep_c(datarep="rep4", read_conversion_fn=read_fn_c, &
                                   write_conversion_fn=MPI_CONVERSION_FN_NULL_C, &
                                   dtype_file_extent_fn=extent_fn, &
                                   extra_state=BIG + 4)
      call check(0 /= captured_bigcount() .and. &
                 0 /= captured_datarep_is("rep4" // c_null_char), &
                 "PMPI register_datarep_c")
      call check(0 == captured_read_fn_is_null(), &
                 "PMPI read_fn_c is NULL in C")
      call check(0 /= captured_write_fn_is_null(), &
                 "PMPI MPI_CONVERSION_FN_NULL_C is not NULL in C")
      fbuf = [1, 2, 3]
      ubuf = -1
      rc = call_conversion_fn_c(0, ubuf, 3_MPI_COUNT_KIND, fbuf, &
                                0_MPI_OFFSET_KIND)
      call check(MPI_SUCCESS == rc .and. all([101, 102, 103] == ubuf) .and. &
                 type_ok .and. BIG + 4 == seen_es, "read_fn_c")

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
         print *, "ERROR: ", what, " (ierr=", ierr, " rc=", rc, &
                  ") extra_state seen=", seen_es
         nfail = nfail + 1
      endif
      end subroutine check

      end program register_datarep_f08
