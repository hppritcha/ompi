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
! Fortran (mpi_f08) test for MPI_Grequest_start, generated from
! ompi/mpi/fortran/use-mpi-f08/grequest_start.c.in and the
! GREQUEST_{QUERY,FREE,CANCEL}_FN types in
! ompi/mpi/bindings/ompi_bindings/fortran_type.py.
!
! Open MPI calls the callbacks of a request started from Fortran with
! Fortran arguments.  The callbacks here record what they are called
! with, and the test checks:
!
!   - MPI_Wait on a completed request calls query_fn and free_fn once
!     each, with the request's extra_state (a value that does not fit in
!     32 bits), and returns the status query_fn filled in;
!   - MPI_Cancel calls cancel_fn with complete = .false. before
!     MPI_Grequest_complete, and .true. after it;
!   - an error that query_fn returns in ierror is reported by MPI_Wait;
!   - the callbacks get the value extra_state had when the request was
!     started, even when it was an expression, or a local variable that
!     was then changed and went out of scope;
!   - the PMPI_ name, keyword arguments, and an omitted ierror.
!
! Generalized requests are local; run it with 2 processes.  Each failure
! is reported with an ERROR line, and the program finishes with
! "error stop 1" if anything failed.
!
      module grequest_start_f08_fns
      use mpi_f08
      implicit none
      integer(kind=MPI_ADDRESS_KIND), parameter :: BIG = 2_MPI_ADDRESS_KIND**40
!     extra_state of the request whose query_fn fails
      integer(kind=MPI_ADDRESS_KIND), parameter :: FAIL = BIG + 4
      integer :: nquery = 0, nfree = 0, ncancel = 0
      integer(kind=MPI_ADDRESS_KIND) :: query_es = -1, free_es = -1, &
                                        cancel_es = -1
      logical :: cancel_complete
      contains

      subroutine query_fn(extra_state, status, ierror)
      integer(kind=MPI_ADDRESS_KIND) :: extra_state
      type(MPI_Status) :: status
      integer :: ierror
      nquery = nquery + 1
      query_es = extra_state
      status%MPI_SOURCE = 3
      status%MPI_TAG = 7
      call MPI_Status_set_elements(status, MPI_INTEGER, 4)
      call MPI_Status_set_cancelled(status, .false.)
      ierror = MPI_SUCCESS
      if (FAIL == extra_state) ierror = MPI_ERR_OTHER
      end subroutine query_fn

      subroutine free_fn(extra_state, ierror)
      integer(kind=MPI_ADDRESS_KIND) :: extra_state
      integer :: ierror
      nfree = nfree + 1
      free_es = extra_state
      ierror = MPI_SUCCESS
      end subroutine free_fn

      subroutine cancel_fn(extra_state, complete, ierror)
      integer(kind=MPI_ADDRESS_KIND) :: extra_state
      logical :: complete
      integer :: ierror
      ncancel = ncancel + 1
      cancel_es = extra_state
      cancel_complete = complete
      ierror = MPI_SUCCESS
      end subroutine cancel_fn

!     Start a request with a local extra_state, then overwrite it before
!     the local goes away
      subroutine start_with_local(es, req)
      integer(kind=MPI_ADDRESS_KIND), intent(in) :: es
      type(MPI_Request), intent(out) :: req
      integer(kind=MPI_ADDRESS_KIND) :: local
      local = es
      call MPI_Grequest_start(query_fn, free_fn, cancel_fn, local, req)
      local = -1
      end subroutine start_with_local

      end module grequest_start_f08_fns

      program grequest_start_f08
      use mpi_f08
      use grequest_start_f08_fns
      implicit none

      type(MPI_Request) :: req
      type(MPI_Status) :: status
      integer(kind=MPI_ADDRESS_KIND) :: es1, es2, es3, es4
      integer :: ierr, nfail, count

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      es1 = BIG + 1
      es2 = BIG + 2
      es3 = BIG + 3
      es4 = FAIL

!     ---------------------------------------------------------------
!     Complete, then wait: query_fn and free_fn
!     ---------------------------------------------------------------
      call MPI_Grequest_start(query_fn, free_fn, cancel_fn, es1, req, ierr)
      call check(MPI_SUCCESS == ierr, "grequest_start")
      call MPI_Grequest_complete(req)
      call MPI_Wait(req, status, ierr)
      call MPI_Get_elements(status, MPI_INTEGER, count)
      call check(MPI_SUCCESS == ierr .and. MPI_REQUEST_NULL == req, "wait")
      call check(1 == nquery .and. es1 == query_es, "query_fn called")
      call check(1 == nfree .and. es1 == free_es, "free_fn called")
      call check(0 == ncancel, "cancel_fn not called")
      call check(3 == status%MPI_SOURCE .and. 7 == status%MPI_TAG .and. &
                 4 == count, "status from query_fn")

!     ---------------------------------------------------------------
!     Cancel before and after MPI_Grequest_complete
!     ---------------------------------------------------------------
      call PMPI_Grequest_start(query_fn=query_fn, free_fn=free_fn, &
                               cancel_fn=cancel_fn, extra_state=es2, &
                               request=req)
      call MPI_Cancel(req)
      call check(1 == ncancel .and. es2 == cancel_es .and. &
                 .not. cancel_complete, "cancel before complete")
      call MPI_Grequest_complete(req)
      call MPI_Wait(req, status, ierr)
      call check(MPI_SUCCESS == ierr .and. 2 == nfree .and. &
                 es2 == free_es, "PMPI grequest_start wait")

      call MPI_Grequest_start(query_fn, free_fn, cancel_fn, es3, req, ierr)
      call MPI_Grequest_complete(req)
      call MPI_Cancel(req)
      call check(2 == ncancel .and. es3 == cancel_es .and. &
                 cancel_complete, "cancel after complete")
      call MPI_Wait(req, status, ierr)
      call check(MPI_SUCCESS == ierr .and. 3 == nfree, "wait after cancel")

!     ---------------------------------------------------------------
!     An error from query_fn
!     ---------------------------------------------------------------
      call MPI_Grequest_start(query_fn, free_fn, cancel_fn, es4, req, ierr)
      call MPI_Grequest_complete(req)
      call MPI_Wait(req, status, ierr)
      call check(MPI_SUCCESS /= ierr .and. FAIL == query_es, &
                 "query_fn error reported")

!     ---------------------------------------------------------------
!     extra_state is passed by value
!     ---------------------------------------------------------------
      call MPI_Grequest_start(query_fn, free_fn, cancel_fn, BIG + 5, req, ierr)
      call MPI_Grequest_complete(req)
      call MPI_Wait(req, status, ierr)
      call check(MPI_SUCCESS == ierr .and. BIG + 5 == query_es .and. &
                 BIG + 5 == free_es, "extra_state expression")

      es1 = BIG + 6
      call MPI_Grequest_start(query_fn, free_fn, cancel_fn, es1, req, ierr)
      es1 = -1
      call MPI_Grequest_complete(req)
      call MPI_Wait(req, status, ierr)
      call check(MPI_SUCCESS == ierr .and. BIG + 6 == query_es, &
                 "extra_state variable changed after start")

      call start_with_local(BIG + 7, req)
      call MPI_Grequest_complete(req)
      call MPI_Cancel(req)
      call MPI_Wait(req, status, ierr)
      call check(MPI_SUCCESS == ierr .and. BIG + 7 == cancel_es .and. &
                 BIG + 7 == query_es .and. BIG + 7 == free_es, &
                 "extra_state local out of scope")

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
         print *, "ERROR: ", what, " (ierr=", ierr, ") calls: query=", &
                  nquery, " free=", nfree, " cancel=", ncancel
         nfail = nfail + 1
      endif
      end subroutine check

      end program grequest_start_f08
