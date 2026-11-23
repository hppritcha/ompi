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
! Fortran (mpi_f08) test for MPI_Type_set_name, generated from
! ompi/mpi/fortran/use-mpi-f08/type_set_name.c.in and the CHAR_ARRAY type
! in ompi/mpi/bindings/ompi_bindings/fortran_type.py.
!
! The Fortran wrapper passes trim(adjustl(type_name)) with a terminating
! NUL to C, matching the mpif-h binding, which also discards leading and
! trailing blanks.  The test reads the name back with MPI_Type_get_name
! and checks:
!
!   - leading and trailing blanks are dropped, interior blanks are kept;
!   - the PMPI_ name, keyword arguments, and an omitted ierror;
!   - an empty (or all-blank) name gives a zero-length name;
!   - a name longer than MPI_MAX_OBJECT_NAME is truncated to
!     MPI_MAX_OBJECT_NAME characters, not an error.  (In Fortran,
!     MPI_MAX_OBJECT_NAME is one less than in C: there is no NUL.)
!
! Naming a datatype is local; run it with 2 processes.  Each failure is
! reported with an ERROR line, and the program finishes with
! "error stop 1" if anything failed.
!
      program type_set_name_f08
      use mpi_f08
      implicit none

      type(MPI_Datatype) :: t
      character(len=MPI_MAX_OBJECT_NAME) :: name
      character(len=MPI_MAX_OBJECT_NAME + 8) :: long_name
      integer :: rl, ierr, nfail

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Type_contiguous(2, MPI_INTEGER, t)

!     Leading and trailing blanks
      call MPI_Type_set_name(t, "  my type  ", ierr)
      call MPI_Type_get_name(t, name, rl)
      call check(MPI_SUCCESS == ierr .and. "my type" == name .and. 7 == rl, &
                 "blanks")

!     PMPI, keywords, no ierror
      call PMPI_Type_set_name(datatype=t, type_name="other")
      call MPI_Type_get_name(t, name, rl)
      call check("other" == name .and. 5 == rl, "PMPI keywords")

!     Empty and all-blank names
      call MPI_Type_set_name(t, "", ierr)
      call MPI_Type_get_name(t, name, rl)
      call check(MPI_SUCCESS == ierr .and. 0 == rl, "empty name")
      call MPI_Type_set_name(t, "other", ierr)
      call MPI_Type_set_name(t, "    ", ierr)
      call MPI_Type_get_name(t, name, rl)
      call check(MPI_SUCCESS == ierr .and. 0 == rl, "all-blank name")

!     Too long: truncated to MPI_MAX_OBJECT_NAME characters
      long_name = repeat("x", len(long_name))
      call MPI_Type_set_name(t, long_name, ierr)
      call MPI_Type_get_name(t, name, rl)
      call check(MPI_SUCCESS == ierr .and. MPI_MAX_OBJECT_NAME == rl &
                 .and. long_name(1:rl) == name, "long name")

      call MPI_Type_free(t)
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
         print *, "ERROR: ", what, " (ierr=", ierr, ") name='", &
                  trim(name), "' resultlen=", rl
         nfail = nfail + 1
      endif
      end subroutine check

      end program type_set_name_f08
