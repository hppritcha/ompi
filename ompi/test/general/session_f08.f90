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
! Fortran (mpi_f08) unit test for the process set routines generated from
! ompi/mpi/fortran/use-mpi-f08/session_get_nth_pset.c.in and
! session_get_pset_info.c.in.
!
! The test checks:
!
!   - MPI_Session_get_nth_pset with pset_len = 0 only returns the length
!     of the name (without a '\0', unlike C) and leaves pset_name
!     unchanged;
!   - with pset_len > 0 the name is returned blank-padded, truncated to
!     min(pset_len, len(pset_name)) characters, without overrunning the
!     Fortran buffer, and pset_len is set to the full length of the name;
!   - a negative pset_len and an out-of-range n are errors;
!   - MPI_Session_get_pset_info accepts the blank-padded names returned
!     by MPI_Session_get_nth_pset, ignores leading blanks, and returns the
!     "mpi_size" of the built-in process sets.
!
! Every output buffer is followed by guard characters that must not be
! modified.  The program is single-process and needs no launcher.  It
! reports each failure with an ERROR line and finishes with "error stop 1"
! if anything failed, so that "make check" sees a non-zero exit status.
!
      program session_f08
      use mpi_f08
      implicit none

!     Number of guard characters after each output buffer.
      integer, parameter :: G = 8
      character(len=64 + G) :: buf
      character(len=G) :: guard
      character(len=16) :: val
      type(MPI_Session) :: session
      type(MPI_Info) :: info
      integer :: npsets, n, plen, plen2, vlen, ierr, nfail
      logical :: flag

      nfail = 0
      guard = repeat('X', G)
      call MPI_Session_init(MPI_INFO_NULL, MPI_ERRORS_RETURN, session, ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Session_init returned ", ierr
         error stop 1
      endif

      call MPI_Session_get_num_psets(session, MPI_INFO_NULL, npsets, ierr)
      call check(MPI_SUCCESS == ierr .and. npsets >= 2, &
                 "MPI_Session_get_num_psets")

!     ---------------------------------------------------------------
!     Length query, then fetch, for every process set
!     ---------------------------------------------------------------
      do n = 0, npsets - 1
         buf = repeat('X', len(buf))
         plen = 0
         call MPI_Session_get_nth_pset(session, MPI_INFO_NULL, n, plen, &
                                       buf(1:64), ierr)
         call check(MPI_SUCCESS == ierr .and. plen > 0 .and. &
                    buf == repeat('X', len(buf)), &
                    "MPI_Session_get_nth_pset(pset_len=0) length query")
         if (MPI_SUCCESS /= ierr .or. plen <= 0 .or. plen > 64) cycle
         plen2 = plen
         call MPI_Session_get_nth_pset(session, MPI_INFO_NULL, n, plen2, &
                                       buf(1:64), ierr)
         call check(MPI_SUCCESS == ierr .and. plen2 == plen .and. &
                    0 == index(buf(1:64), char(0)) .and. &
                    len_trim(buf(1:64)) == plen .and. &
                    buf(65:) == guard, &
                    "MPI_Session_get_nth_pset")
         if (0 == n) call check(buf(1:64) == "mpi://WORLD", &
                                "pset 0 is not mpi://WORLD")
         if (1 == n) call check(buf(1:64) == "mpi://SELF", &
                                "pset 1 is not mpi://SELF")
!        The blank-padded name is a valid process set name.
         call MPI_Session_get_pset_info(session, buf(1:64), info, ierr)
         call check(MPI_SUCCESS == ierr, &
                    "MPI_Session_get_pset_info(blank-padded name)")
         if (MPI_SUCCESS == ierr) then
            call MPI_Info_free(info)
         endif
      end do

!     ---------------------------------------------------------------
!     Truncation and buffer bounds
!     ---------------------------------------------------------------
      buf = repeat('X', len(buf))
      plen = 6
      call MPI_Session_get_nth_pset(session=session, info=MPI_INFO_NULL, &
                                    n=0, pset_len=plen, &
                                    pset_name=buf(1:20), ierror=ierr)
      call check(MPI_SUCCESS == ierr .and. 11 == plen .and. &
                 buf(1:20) == "mpi://" .and. buf(21:20+G) == guard, &
                 "MPI_Session_get_nth_pset truncation at pset_len")
!     pset_len claims more space than the actual argument has.
      buf = repeat('X', len(buf))
      plen = 100
      call PMPI_Session_get_nth_pset(session, MPI_INFO_NULL, 0, plen, &
                                     buf(1:4), ierr)
      call check(MPI_SUCCESS == ierr .and. 11 == plen .and. &
                 buf(1:4) == "mpi:" .and. buf(5:4+G) == guard, &
                 "PMPI_Session_get_nth_pset with pset_len > len(pset_name)")
!     A zero-length pset_name is never written.
      buf = repeat('X', len(buf))
      plen = 10
      call MPI_Session_get_nth_pset(session, MPI_INFO_NULL, 0, plen, &
                                    buf(5:4), ierr)
      call check(MPI_SUCCESS == ierr .and. 11 == plen .and. &
                 buf == repeat('X', len(buf)), &
                 "MPI_Session_get_nth_pset into a zero-length pset_name")

!     ---------------------------------------------------------------
!     Errors
!     ---------------------------------------------------------------
      buf = repeat('X', len(buf))
      plen = -1
      call MPI_Session_get_nth_pset(session, MPI_INFO_NULL, 0, plen, &
                                    buf(1:20), ierr)
      call check(MPI_SUCCESS /= ierr .and. buf == repeat('X', len(buf)), &
                 "MPI_Session_get_nth_pset(pset_len=-1) succeeded")
      plen = 20
      call MPI_Session_get_nth_pset(session, MPI_INFO_NULL, npsets, plen, &
                                    buf(1:20), ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "MPI_Session_get_nth_pset(n=npsets) succeeded")

!     ---------------------------------------------------------------
!     MPI_Session_get_pset_info
!     ---------------------------------------------------------------
      call PMPI_Session_get_pset_info(session, "  mpi://SELF  ", info, ierr)
      call check(MPI_SUCCESS == ierr, &
                 "PMPI_Session_get_pset_info(blank-padded mpi://SELF)")
      if (MPI_SUCCESS == ierr) then
         vlen = len(val)
         call MPI_Info_get_string(info, "mpi_size", vlen, val, flag, ierr)
         call check(MPI_SUCCESS == ierr .and. flag .and. val == "1", &
                    "mpi_size of mpi://SELF /= 1")
         call MPI_Info_free(info)
      endif
      call MPI_Session_get_pset_info(session=session, &
                                     pset_name="mpi://WORLD", info=info, &
                                     ierror=ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Session_get_pset_info(WORLD)")
      if (MPI_SUCCESS == ierr) then
         vlen = len(val)
         call MPI_Info_get_string(info, "mpi_size", vlen, val, flag, ierr)
         call check(MPI_SUCCESS == ierr .and. flag .and. val == "1", &
                    "mpi_size of mpi://WORLD /= 1")
         call MPI_Info_free(info)
      endif

      call MPI_Session_finalize(session, ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Session_finalize")
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

      end program session_f08
