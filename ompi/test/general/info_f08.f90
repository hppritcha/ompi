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
! Fortran (mpi_f08) unit test for the info query routines generated from
! ompi/mpi/fortran/use-mpi-f08/info_get*.c.in: MPI_Info_get_nthkey,
! MPI_Info_get, MPI_Info_get_valuelen and MPI_Info_get_string.
!
! The test checks:
!
!   - the canonical loop: MPI_Info_get_nthkey into a blank-padded
!     CHARACTER(LEN=MPI_MAX_INFO_KEY) buffer, then MPI_Info_get with that
!     buffer as the key;
!   - MPI_Info_get truncates the value at valuelen, strips blanks from
!     stored values, and leaves value unchanged and flag .false. for a
!     missing key (also right after a successful lookup);
!   - MPI_Info_get_string's buflen: 0 queries the length; on output it is
!     the value length; the value is truncated to min(buflen,
!     len(value)), so an over-stated buflen cannot overrun the buffer;
!   - negative valuelen/buflen and an out-of-range n are errors, and a
!     zero-length key buffer is left untouched.
!
! Every output buffer is followed by guard characters that must not be
! modified.  The program is single-process and needs no launcher.  It
! reports each failure with an ERROR line and finishes with "error stop 1"
! if anything failed, so that "make check" sees a non-zero exit status.
!
      program info_f08
      use mpi_f08
      implicit none

!     Number of guard characters after each output buffer.
      integer, parameter :: G = 8
      character(len=MPI_MAX_INFO_KEY) :: key
      character(len=64 + G) :: buf
      character(len=G) :: guard
      type(MPI_Info) :: info
      integer :: nkeys, k, vlen, buflen, ierr, nfail
      logical :: flag

      nfail = 0
      guard = repeat('X', G)
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
!     Info errors are not associated with a handle and are raised on
!     MPI_COMM_SELF; make every expected error return instead of abort.
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)

      call MPI_Info_create(info)
      call MPI_Info_set(info, "color", "blue")
      call MPI_Info_set(info, "  shape  ", "  round  ")
      call MPI_Info_set(info, "size", "extra-large")

!     ---------------------------------------------------------------
!     nthkey -> get loop with blank-padded keys
!     ---------------------------------------------------------------
      call MPI_Info_get_nkeys(info, nkeys)
      call check(3 == nkeys, "MPI_Info_get_nkeys /= 3")
      do k = 0, nkeys - 1
         call MPI_Info_get_nthkey(info, k, key, ierr)
         call check(MPI_SUCCESS == ierr .and. 0 == index(key, char(0)), &
                    "MPI_Info_get_nthkey")
         buf = repeat('X', len(buf))
         call MPI_Info_get(info, key, 64, buf(1:64), flag, ierr)
         call check(MPI_SUCCESS == ierr .and. flag .and. &
                    0 == index(buf(1:64), char(0)) .and. &
                    buf(65:) == guard, &
                    "MPI_Info_get with key from MPI_Info_get_nthkey")
      end do

!     ---------------------------------------------------------------
!     MPI_Info_get
!     ---------------------------------------------------------------
      buf = repeat('X', len(buf))
      call MPI_Info_get(info=info, key="size", valuelen=5, &
                        value=buf(1:5), flag=flag, ierror=ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. &
                 buf(1:5) == "extra" .and. buf(6:5+G) == guard, &
                 "MPI_Info_get truncation at valuelen")
      buf = repeat('X', len(buf))
      call PMPI_Info_get(info, "shape", 10, buf(1:10), flag, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. &
                 buf(1:10) == "round" .and. buf(11:10+G) == guard, &
                 "PMPI_Info_get of a blank-stripped value")
!     A missing key straight after a successful lookup.
      buf = repeat('X', len(buf))
      call MPI_Info_get(info, "nosuch", 10, buf(1:10), flag, ierr)
      call check(MPI_SUCCESS == ierr .and. .not. flag .and. &
                 buf == repeat('X', len(buf)), &
                 "MPI_Info_get of a missing key")
      call MPI_Info_get(info, "color", -1, buf(1:1), flag, ierr)
      call check(MPI_SUCCESS /= ierr, "MPI_Info_get(valuelen=-1) succeeded")

!     ---------------------------------------------------------------
!     MPI_Info_get_valuelen
!     ---------------------------------------------------------------
      call MPI_Info_get_valuelen(info, " size ", vlen, flag, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. 11 == vlen, &
                 "MPI_Info_get_valuelen")
      call MPI_Info_get_valuelen(info, "nosuch", vlen, flag, ierr)
      call check(MPI_SUCCESS == ierr .and. .not. flag, &
                 "MPI_Info_get_valuelen of a missing key")

!     ---------------------------------------------------------------
!     MPI_Info_get_string
!     ---------------------------------------------------------------
      buf = repeat('X', len(buf))
      buflen = 0
      call MPI_Info_get_string(info, "size", buflen, buf(1:20), flag, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. 11 == buflen .and. &
                 buf == repeat('X', len(buf)), &
                 "MPI_Info_get_string(buflen=0) length query")
      buflen = 20
      call MPI_Info_get_string(info, "size", buflen, buf(1:20), flag, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. 11 == buflen .and. &
                 buf(1:20) == "extra-large" .and. buf(21:20+G) == guard, &
                 "MPI_Info_get_string")
      buf = repeat('X', len(buf))
      buflen = 5
      call MPI_Info_get_string(info, "size", buflen, buf(1:20), flag, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. 11 == buflen .and. &
                 buf(1:20) == "extra" .and. buf(21:20+G) == guard, &
                 "MPI_Info_get_string truncation at buflen")
!     buflen claims more space than the actual argument has.
      buf = repeat('X', len(buf))
      buflen = 100
      call PMPI_Info_get_string(info, "size", buflen, buf(1:4), flag, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. 11 == buflen .and. &
                 buf(1:4) == "extr" .and. buf(5:4+G) == guard, &
                 "PMPI_Info_get_string with buflen > len(value)")
      buf = repeat('X', len(buf))
      buflen = 7
      call MPI_Info_get_string(info, "nosuch", buflen, buf(1:20), flag, &
                               ierr)
      call check(MPI_SUCCESS == ierr .and. .not. flag .and. 7 == buflen &
                 .and. buf == repeat('X', len(buf)), &
                 "MPI_Info_get_string of a missing key")
      buflen = -1
      call MPI_Info_get_string(info, "size", buflen, buf(1:20), flag, ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "MPI_Info_get_string(buflen=-1) succeeded")

!     ---------------------------------------------------------------
!     MPI_Info_get_nthkey edge cases
!     ---------------------------------------------------------------
      call MPI_Info_get_nthkey(info, nkeys, key, ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "MPI_Info_get_nthkey(n=nkeys) succeeded")
      buf = repeat('X', len(buf))
      call MPI_Info_get_nthkey(info, 0, buf(5:4), ierr)
      call check(MPI_SUCCESS == ierr .and. buf == repeat('X', len(buf)), &
                 "MPI_Info_get_nthkey into a zero-length key")
      buf = repeat('X', len(buf))
      call MPI_Info_get_nthkey(info=info, n=2, key=buf(1:2), ierror=ierr)
      call check(MPI_SUCCESS == ierr .and. buf(1:2) == "si" .and. &
                 buf(3:2+G) == guard, &
                 "MPI_Info_get_nthkey into a short key")

      call MPI_Info_free(info)
      call MPI_Finalize(ierr)
      if (nfail > 0) then
         print *, "ERROR: ", nfail, " check(s) failed"
         error stop 1
      endif
      print *, "PASS"

      contains

      subroutine check(ok, what)
      logical, intent(in) :: ok
      character(len=*), intent(in) :: what
      if (.not. ok) then
         print *, "ERROR: ", what, " (ierr=", ierr, ") buf=[", buf, "]"
         nfail = nfail + 1
      endif
      end subroutine check

      end program info_f08
