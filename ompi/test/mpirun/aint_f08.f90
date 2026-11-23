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
! Fortran (mpi_f08) test for the MPI_Aint_add and MPI_Aint_diff
! functions, generated from the aint_add.c.in and aint_diff.c.in
! templates in ompi/mpi/fortran/use-mpi-f08.  The test checks, with
! addresses from MPI_Get_address:
!
!   - MPI_Aint_diff gives the distance between two array elements, and
!     MPI_Aint_add with that distance, or its negation, gives the other
!     address back;
!   - the functions can be used within expressions, as arguments of
!     each other;
!   - the PMPI_ names, and keyword arguments.
!
! The test is local; run it with 2 processes.  Each failure is reported
! with an ERROR line, and the program finishes with "error stop 1" if
! anything failed.
!
      program aint_f08
      use mpi_f08
      implicit none

      double precision :: arr(4)
      integer(kind=MPI_ADDRESS_KIND) :: a1, a3, d
      integer :: ierr, nfail

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif

      arr = 0.0d0
      call MPI_Get_address(arr(1), a1)
      call MPI_Get_address(arr(3), a3)

      d = MPI_Aint_diff(a3, a1)
      call check(16 == d, "aint_diff")
      call check(-16 == MPI_Aint_diff(a1, a3), "aint_diff negative")
      call check(a3 == MPI_Aint_add(a1, d), "aint_add")
      call check(a1 == MPI_Aint_add(a3, -d), "aint_add negative")
      call check(8 == MPI_Aint_diff(MPI_Aint_add(a1, 8_MPI_ADDRESS_KIND), a1), &
                 "aint_add within aint_diff")

      call check(16 == PMPI_Aint_diff(addr1=a3, addr2=a1), &
                 "PMPI aint_diff keywords")
      call check(16 == PMPI_Aint_diff(addr2=a1, addr1=a3), &
                 "PMPI aint_diff keywords, reversed")
      call check(a3 == PMPI_Aint_add(base=a1, disp=d), &
                 "PMPI aint_add keywords")
      call check(a3 == MPI_Aint_add(disp=d, base=a1), &
                 "aint_add keywords, reversed")

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
         print *, "ERROR: ", what
         nfail = nfail + 1
      endif
      end subroutine check

      end program aint_f08
