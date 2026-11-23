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
! Fortran (mpi_f08) test for the procedures that complete, or report
! on, several requests at once, generated from the templates in
! ompi/mpi/fortran/use-mpi-f08.  Each process sends to itself on
! MPI_COMM_SELF.  The test checks:
!
!   - MPI_Testsome reports the completed request with a 1-based index
!     and its status, and sets it to MPI_REQUEST_NULL; the other is left
!     alone;
!   - outcount is MPI_UNDEFINED when there are no active requests, and
!     when incount is 0;
!   - the PMPI_ name, keyword arguments, and an omitted ierror (these
!     need the explicit interface: without one, a call would be linked
!     to the mpif.h binding);
!   - MPI_Waitsome, MPI_Testsome and MPI_Request_get_status_some leave
!     the statuses beyond outcount alone;
!   - MPI_Request_get_status_all and MPI_Request_get_status_any leave
!     the statuses alone when flag is .false., and return flag = .true.
!     for no requests;
!   - when one receive is truncated, MPI_Waitall, MPI_Testall,
!     MPI_Waitsome and MPI_Testsome return MPI_ERR_IN_STATUS together
!     with their other outputs: the statuses tell which request failed.
!
! The test is local; run it with 2 processes.  Each failure is reported
! with an ERROR line, and the program finishes with "error stop 1" if
! anything failed.
!
      program completion_f08
      use mpi_f08
      implicit none

      type(MPI_Request) :: reqs(2), saved
      type(MPI_Status) :: statuses(2), status
      integer :: rbuf(2), sbuf, sbuf2(2), outcount, indices(2), indx
      integer :: ierr, nfail
      logical :: flag

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)

!     ---------------------------------------------------------------
!     MPI_Testsome
!     ---------------------------------------------------------------
      rbuf = -7
      call MPI_Irecv(rbuf(1), 1, MPI_INTEGER, 0, 1, MPI_COMM_SELF, reqs(1))
      call MPI_Irecv(rbuf(2), 1, MPI_INTEGER, 0, 2, MPI_COMM_SELF, reqs(2))
      saved = reqs(2)
      sbuf = 11
      call MPI_Send(sbuf, 1, MPI_INTEGER, 0, 1, MPI_COMM_SELF)
      outcount = 0
      do while (0 == outcount)
         call MPI_Testsome(2, reqs, outcount, indices, statuses, ierr)
         if (MPI_SUCCESS /= ierr) exit
      end do
      call check(MPI_SUCCESS == ierr .and. 1 == outcount .and. &
                 1 == indices(1) .and. 1 == statuses(1)%MPI_TAG .and. &
                 11 == rbuf(1), "testsome first")
      call check(MPI_REQUEST_NULL == reqs(1) .and. saved == reqs(2), &
                 "testsome first, requests")

      sbuf = 12
      call MPI_Send(sbuf, 1, MPI_INTEGER, 0, 2, MPI_COMM_SELF)
      outcount = 0
      do while (0 == outcount)
         call PMPI_Testsome(incount=2, array_of_requests=reqs, &
                            outcount=outcount, array_of_indices=indices, &
                            array_of_statuses=statuses)
      end do
      call check(1 == outcount .and. 2 == indices(1) .and. &
                 2 == statuses(1)%MPI_TAG .and. 12 == rbuf(2) .and. &
                 MPI_REQUEST_NULL == reqs(2), "PMPI testsome keywords")

      call MPI_Testsome(2, reqs, outcount, indices, MPI_STATUSES_IGNORE, ierr)
      call check(MPI_SUCCESS == ierr .and. MPI_UNDEFINED == outcount, &
                 "testsome, no active requests")
      outcount = -7
      call MPI_Testsome(0, reqs, outcount, indices, statuses, ierr)
      call check(MPI_SUCCESS == ierr .and. MPI_UNDEFINED == outcount, &
                 "testsome, incount 0")

!     ---------------------------------------------------------------
!     The statuses beyond outcount are left alone
!     ---------------------------------------------------------------
      call post(10, reqs)
      call MPI_Send(sbuf, 1, MPI_INTEGER, 0, 10, MPI_COMM_SELF)
      statuses%MPI_TAG = -7
      outcount = -7
      call MPI_Waitsome(2, reqs, outcount, indices, statuses, ierr)
      call check(MPI_SUCCESS == ierr .and. 1 == outcount .and. &
                 1 == indices(1) .and. 10 == statuses(1)%MPI_TAG, &
                 "waitsome one of two")
      call check(-7 == statuses(2)%MPI_TAG, &
                 "waitsome one of two, rest untouched")

      statuses%MPI_TAG = -7
      outcount = -7
      call MPI_Testsome(2, reqs, outcount, indices, statuses, ierr)
      call check(MPI_SUCCESS == ierr .and. 0 == outcount .and. &
                 all(-7 == statuses%MPI_TAG), "testsome none of one")

      call MPI_Send(sbuf, 1, MPI_INTEGER, 0, 11, MPI_COMM_SELF)
      reqs(1) = MPI_REQUEST_NULL
      call MPI_Irecv(rbuf(1), 1, MPI_INTEGER, 0, 12, MPI_COMM_SELF, reqs(1))
      saved = reqs(2)
      statuses%MPI_TAG = -7
      outcount = 0
      do while (0 == outcount)
         call MPI_Request_get_status_some(2, reqs, outcount, indices, &
                                          statuses, ierr)
         if (MPI_SUCCESS /= ierr) exit
      end do
      call check(MPI_SUCCESS == ierr .and. 1 == outcount .and. &
                 2 == indices(1) .and. 11 == statuses(1)%MPI_TAG, &
                 "request_get_status_some one of two")
      call check(-7 == statuses(2)%MPI_TAG .and. saved == reqs(2), &
                 "request_get_status_some one of two, rest untouched")

      statuses%MPI_TAG = -7
      flag = .true.
      call MPI_Request_get_status_all(2, reqs, flag, statuses, ierr)
      call check(MPI_SUCCESS == ierr .and. .not. flag .and. &
                 all(-7 == statuses%MPI_TAG), &
                 "request_get_status_all one of two")
      flag = .false.
      call MPI_Request_get_status_all(0, reqs, flag, statuses, ierr)
      call check(MPI_SUCCESS == ierr .and. flag, "request_get_status_all, count 0")

      status%MPI_TAG = -7
      indx = -7
      flag = .true.
      call MPI_Request_get_status_any(1, reqs(1:1), indx, flag, status, ierr)
      call check(MPI_SUCCESS == ierr .and. .not. flag .and. &
                 MPI_UNDEFINED == indx .and. -7 == status%MPI_TAG, &
                 "request_get_status_any none of one")
      call MPI_Request_get_status_any(2, reqs, indx, flag, status, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. 2 == indx .and. &
                 11 == status%MPI_TAG, "request_get_status_any one of two")
      flag = .false.
      call MPI_Request_get_status_any(0, reqs, indx, flag, status, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. &
                 MPI_UNDEFINED == indx, "request_get_status_any, count 0")

      call MPI_Send(sbuf, 1, MPI_INTEGER, 0, 12, MPI_COMM_SELF)
      call MPI_Waitall(2, reqs, MPI_STATUSES_IGNORE, ierr)
      call check(MPI_SUCCESS == ierr .and. all(MPI_REQUEST_NULL == reqs), &
                 "waitall the rest")

!     ---------------------------------------------------------------
!     MPI_ERR_IN_STATUS: the second receive is truncated
!     ---------------------------------------------------------------
      call post(20, reqs)
      call send_pair(20)
      statuses%MPI_ERROR = -7
      call MPI_Waitall(2, reqs, statuses, ierr)
      call check_in_status("waitall")

      call post(30, reqs)
      call send_pair(30)
      statuses%MPI_ERROR = -7
      flag = .false.
      do while (.not. flag)
         call MPI_Testall(2, reqs, flag, statuses, ierr)
         if (MPI_SUCCESS /= ierr) exit
      end do
      call check(flag, "testall MPI_ERR_IN_STATUS, flag")
      call check_in_status("testall")

      call post(40, reqs)
      call send_pair(40)
      statuses%MPI_ERROR = -7
      outcount = -7
      call MPI_Waitsome(2, reqs, outcount, indices, statuses, ierr)
      call check(2 == outcount .and. all([1, 2] == indices), &
                 "waitsome MPI_ERR_IN_STATUS, indices")
      call check_in_status("waitsome")

      call post(50, reqs)
      call send_pair(50)
      statuses%MPI_ERROR = -7
      outcount = -7
      call MPI_Testsome(2, reqs, outcount, indices, statuses, ierr)
      call check(2 == outcount .and. all([1, 2] == indices), &
                 "testsome MPI_ERR_IN_STATUS, indices")
      call check_in_status("testsome")

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
         print *, "ERROR: ", what, " (ierr=", ierr, ")"
         nfail = nfail + 1
      endif
      end subroutine check

!     Post a receive of one INTEGER with tag t, and one with tag t+1
      subroutine post(t, r)
      integer, intent(in) :: t
      type(MPI_Request), intent(out) :: r(2)
      rbuf = -7
      call MPI_Irecv(rbuf(1), 1, MPI_INTEGER, 0, t, MPI_COMM_SELF, r(1))
      call MPI_Irecv(rbuf(2), 1, MPI_INTEGER, 0, t + 1, MPI_COMM_SELF, r(2))
      end subroutine post

!     Send one INTEGER with tag t, and two (too many) with tag t+1
      subroutine send_pair(t)
      integer, intent(in) :: t
      sbuf2 = [21, 22]
      call MPI_Send(sbuf, 1, MPI_INTEGER, 0, t, MPI_COMM_SELF)
      call MPI_Send(sbuf2, 2, MPI_INTEGER, 0, t + 1, MPI_COMM_SELF)
      end subroutine send_pair

!     Both receives have completed, and only the second one failed
      subroutine check_in_status(what)
      character(len=*), intent(in) :: what
      call check(MPI_ERR_IN_STATUS == ierr, what // " MPI_ERR_IN_STATUS")
      call check(MPI_SUCCESS == statuses(1)%MPI_ERROR .and. &
                 MPI_ERR_TRUNCATE == statuses(2)%MPI_ERROR, &
                 what // " MPI_ERR_IN_STATUS, statuses")
      call check(MPI_REQUEST_NULL == reqs(1) .and. sbuf == rbuf(1), &
                 what // " MPI_ERR_IN_STATUS, request")
      if (MPI_REQUEST_NULL /= reqs(2)) then
         call MPI_Request_free(reqs(2))
      endif
      end subroutine check_in_status

      end program completion_f08
