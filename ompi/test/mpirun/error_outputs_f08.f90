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
! Fortran (mpi_f08) test that a call which fails its argument checks
! leaves its output handles alone, rather than converting a C handle
! that was never set.  It uses the win_allocate.c.in,
! win_allocate_shared.c.in, win_get_info.c.in and ialltoallw_ts.c.in
! templates in ompi/mpi/fortran/use-mpi-f08.  The test checks, with
! MPI_ERRORS_RETURN:
!
!   - MPI_Win_allocate and MPI_Win_allocate_shared with a negative size
!     give MPI_ERR_SIZE and leave win alone;
!   - MPI_Win_get_info on MPI_WIN_NULL gives MPI_ERR_WIN and leaves
!     info alone;
!   - MPI_Ialltoallw with MPI_DATATYPE_NULL receive types gives
!     MPI_ERR_TYPE and leaves request alone (the binding used to hand
!     its datatype arrays to the request it did not get);
!   - the same calls with valid arguments still work.
!
! Run it with 2 processes.  Each failure is reported with an ERROR line,
! and the program finishes with "error stop 1" if anything failed.
!
      program error_outputs_f08
      use mpi_f08
      use, intrinsic :: iso_c_binding, only: c_ptr
      implicit none

      type(MPI_Win) :: win, win_saved
      type(MPI_Info) :: info, info_saved
      type(MPI_Request) :: req, req_saved
      type(MPI_Datatype) :: types(2)
      type(c_ptr) :: baseptr
      integer :: nprocs, counts(2), displs(2), sbuf(2), rbuf(2)
      integer :: ierr, nfail

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Comm_size(MPI_COMM_WORLD, nprocs)
      if (2 /= nprocs) then
         print *, "ERROR: run with 2 processes, not ", nprocs
         error stop 1
      endif

!     A handle that no call here should return
      call MPI_Win_create_dynamic(MPI_INFO_NULL, MPI_COMM_WORLD, win_saved)
      call MPI_Info_create(info_saved)

!     ---------------------------------------------------------------
!     MPI_Win_allocate / MPI_Win_allocate_shared
!     ---------------------------------------------------------------
      win = win_saved
      call MPI_Win_allocate(-1_MPI_ADDRESS_KIND, 1, MPI_INFO_NULL, &
                            MPI_COMM_WORLD, baseptr, win, ierr)
      call check(MPI_ERR_SIZE == ierr .and. win_saved == win, &
                 "win_allocate negative size")
      win = win_saved
      call MPI_Win_allocate_shared(-1_MPI_ADDRESS_KIND, 1, MPI_INFO_NULL, &
                                   MPI_COMM_WORLD, baseptr, win, ierr)
      call check(MPI_ERR_SIZE == ierr .and. win_saved == win, &
                 "win_allocate_shared negative size")

      call MPI_Win_allocate(64_MPI_ADDRESS_KIND, 1, MPI_INFO_NULL, &
                            MPI_COMM_WORLD, baseptr, win, ierr)
      call check(MPI_SUCCESS == ierr .and. win_saved /= win .and. &
                 MPI_WIN_NULL /= win, "win_allocate")

!     ---------------------------------------------------------------
!     MPI_Win_get_info
!     ---------------------------------------------------------------
      info = info_saved
      call MPI_Win_get_info(MPI_WIN_NULL, info, ierr)
      call check(MPI_ERR_WIN == ierr .and. info_saved == info, &
                 "win_get_info MPI_WIN_NULL")
      call MPI_Win_get_info(win, info, ierr)
      call check(MPI_SUCCESS == ierr .and. info_saved /= info .and. &
                 MPI_INFO_NULL /= info, "win_get_info")
      call MPI_Info_free(info)
      call MPI_Win_free(win)

!     ---------------------------------------------------------------
!     MPI_Ialltoallw
!     ---------------------------------------------------------------
      counts = 1
      displs = [0, 4]
      sbuf = [1, 2]
      rbuf = -7
      req_saved = MPI_REQUEST_NULL
      req = req_saved
      types = MPI_INTEGER
      call MPI_Ialltoallw(sbuf, counts, displs, types, rbuf, counts, &
                          displs, [MPI_DATATYPE_NULL, MPI_DATATYPE_NULL], &
                          MPI_COMM_WORLD, req, ierr)
      call check(MPI_ERR_TYPE == ierr .and. req_saved == req, &
                 "ialltoallw MPI_DATATYPE_NULL")
      call MPI_Ialltoallw(sbuf, counts, displs, types, rbuf, counts, &
                          displs, types, MPI_COMM_WORLD, req, ierr)
      call check(MPI_SUCCESS == ierr, "ialltoallw")
      call MPI_Wait(req, MPI_STATUS_IGNORE)

      call MPI_Info_free(info_saved)
      call MPI_Win_free(win_saved)
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

      end program error_outputs_f08
