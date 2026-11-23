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
! Fortran (mpi_f08) test for MPI_Group_range_incl and
! MPI_Group_range_excl, generated from
! ompi/mpi/fortran/use-mpi-f08/group_range_{incl,excl}.c.in and the
! RANGE_ARRAY type in ompi/mpi/bindings/ompi_bindings/fortran_type.py.
!
! The ranges argument is INTEGER ranges(3,*), which must reach C as
! int ranges[][3]: each column is one (first, last, stride) triplet.  The
! test checks:
!
!   - strided and reversed (negative stride) ranges;
!   - n smaller than the actual array, with garbage in the unused
!     columns, and n = 2, which is where a transposed layout shows up;
!   - a non-contiguous array section as the actual argument;
!   - n = 0, which gives MPI_GROUP_EMPTY for incl and a copy of the group
!     for excl;
!   - out-of-range ranks and a zero stride are errors;
!   - the PMPI_ names and keyword arguments.
!
! A stride other than 1 can only be told apart from a contiguous range
! with more than two ranks, so this test needs exactly 4 processes.  The
! group operations are all local; there is no communication.  Each
! failure is reported with an ERROR line, and the program finishes with
! "error stop 1" if anything failed.
!
      program group_range_f08
      use mpi_f08
      implicit none

      type(MPI_Group) :: wgroup, g
      integer :: ranges(3,5), p, sz, ierr, nfail, res
      integer :: r(4), wr(4)

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
!     Group errors are not associated with a communicator; make every
!     expected error return instead of abort.
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Comm_group(MPI_COMM_WORLD, wgroup)
      call MPI_Group_size(wgroup, p)
      if (4 /= p) then
         print *, "ERROR: run with 4 processes, not ", p
         error stop 1
      endif
      r = [0, 1, 2, 3]

!     ---------------------------------------------------------------
!     MPI_Group_range_incl
!     ---------------------------------------------------------------
!     Strided: {0,2}
      wr = -1
      ranges(:,1) = [0, p-1, 2]
      call MPI_Group_range_incl(wgroup, 1, ranges, g, ierr)
      call MPI_Group_size(g, sz)
      call MPI_Group_translate_ranks(g, 2, r, wgroup, wr)
      call check(MPI_SUCCESS == ierr .and. 2 == sz .and. &
                 all(wr(1:2) == [0, 2]), "incl stride 2")
      call MPI_Group_free(g)

!     Reversed: {3,2,1,0}
      wr = -1
      ranges(:,1) = [p-1, 0, -1]
      call PMPI_Group_range_incl(group=wgroup, n=1, ranges=ranges, &
                                 newgroup=g, ierror=ierr)
      call MPI_Group_translate_ranks(g, 4, r, wgroup, wr)
      call check(MPI_SUCCESS == ierr .and. all(wr == [3, 2, 1, 0]), &
                 "PMPI incl reversed")
      call MPI_Group_free(g)

!     Two ranges, in an array larger than n: {0,3}
      wr = -1
      ranges = -99
      ranges(:,1) = [0, 0, 1]
      ranges(:,2) = [p-1, p-1, 1]
      call MPI_Group_range_incl(wgroup, 2, ranges, g, ierr)
      call MPI_Group_size(g, sz)
      call MPI_Group_translate_ranks(g, 2, r, wgroup, wr)
      call check(MPI_SUCCESS == ierr .and. 2 == sz .and. &
                 all(wr(1:2) == [0, 3]), "incl n=2")
      call MPI_Group_free(g)

!     Non-contiguous section: columns 1 and 3, {1,2}
      wr = -1
      ranges(:,1) = [1, 1, 1]
      ranges(:,2) = [-1, -1, -1]
      ranges(:,3) = [2, 2, 1]
      call MPI_Group_range_incl(wgroup, 2, ranges(:,1:3:2), g, ierr)
      call MPI_Group_translate_ranks(g, 2, r, wgroup, wr)
      call check(MPI_SUCCESS == ierr .and. all(wr(1:2) == [1, 2]), &
                 "incl array section")
      call MPI_Group_free(g)

!     ---------------------------------------------------------------
!     MPI_Group_range_excl
!     ---------------------------------------------------------------
!     Strided: {1,3}
      wr = -1
      ranges(:,1) = [0, p-1, 2]
      call MPI_Group_range_excl(wgroup, 1, ranges, g, ierr)
      call MPI_Group_size(g, sz)
      call MPI_Group_translate_ranks(g, 2, r, wgroup, wr)
      call check(MPI_SUCCESS == ierr .and. 2 == sz .and. &
                 all(wr(1:2) == [1, 3]), "excl stride 2")
      call MPI_Group_free(g)

!     Reversed: excluding {2,1} leaves {0,3}
      wr = -1
      ranges(:,1) = [2, 1, -1]
      call PMPI_Group_range_excl(group=wgroup, n=1, ranges=ranges, &
                                 newgroup=g, ierror=ierr)
      call MPI_Group_size(g, sz)
      call MPI_Group_translate_ranks(g, 2, r, wgroup, wr)
      call check(MPI_SUCCESS == ierr .and. 2 == sz .and. &
                 all(wr(1:2) == [0, 3]), "PMPI excl reversed")
      call MPI_Group_free(g)

!     Two ranges: excluding {0} and {2,3} leaves {1}
      wr = -1
      ranges = -99
      ranges(:,1) = [0, 0, 1]
      ranges(:,2) = [2, 3, 1]
      call MPI_Group_range_excl(wgroup, 2, ranges, g, ierr)
      call MPI_Group_size(g, sz)
      call MPI_Group_translate_ranks(g, 1, r, wgroup, wr)
      call check(MPI_SUCCESS == ierr .and. 1 == sz .and. 1 == wr(1), &
                 "excl n=2")
      call MPI_Group_free(g)

!     ---------------------------------------------------------------
!     n = 0
!     ---------------------------------------------------------------
      call MPI_Group_range_incl(wgroup, 0, ranges, g, ierr)
      call MPI_Group_size(g, sz)
      call check(MPI_SUCCESS == ierr .and. 0 == sz, "incl n=0")
      if (MPI_SUCCESS == ierr .and. g /= MPI_GROUP_EMPTY) then
         call MPI_Group_free(g)
      endif
      call MPI_Group_range_excl(wgroup, 0, ranges, g, ierr)
      call MPI_Group_compare(g, wgroup, res)
      call check(MPI_SUCCESS == ierr .and. MPI_IDENT == res, "excl n=0")
      call MPI_Group_free(g)

!     ---------------------------------------------------------------
!     Errors
!     ---------------------------------------------------------------
      ranges(:,1) = [0, p, 1]
      call MPI_Group_range_incl(wgroup, 1, ranges, g, ierr)
      call check(MPI_SUCCESS /= ierr, "incl out of range succeeded")
      call MPI_Group_range_excl(wgroup, 1, ranges, g, ierr)
      call check(MPI_SUCCESS /= ierr, "excl out of range succeeded")
      ranges(:,1) = [0, p-1, 0]
      call MPI_Group_range_incl(wgroup, 1, ranges, g, ierr)
      call check(MPI_SUCCESS /= ierr, "incl stride 0 succeeded")
      call MPI_Group_range_excl(wgroup, 1, ranges, g, ierr)
      call check(MPI_SUCCESS /= ierr, "excl stride 0 succeeded")

      call MPI_Group_free(wgroup)
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
         print *, "ERROR: ", what, " (ierr=", ierr, ") ranks=", wr
         nfail = nfail + 1
      endif
      end subroutine check

      end program group_range_f08
