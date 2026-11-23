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
! Fortran (mpi_f08) test for MPI_Parrived, generated from the
! parrived.c.in template in ompi/mpi/fortran/use-mpi-f08.  Rank 1 sends
! two partitions to rank 0, and readies the second one only once rank 0
! has seen the first one arrive.  The test checks:
!
!   - flag is .false. for a partition that has not arrived, after a call
!     that returned .true. for another one (the LOGICAL temporary of the
!     generated procedure used to keep its value between calls);
!   - flag is .true. for an inactive request and for MPI_REQUEST_NULL;
!   - the PMPI_ name, keyword arguments, and an omitted ierror.
!
! Run it with 2 processes.  Each failure is reported with an ERROR line,
! and the program finishes with "error stop 1" if anything failed.
!
      program parrived_f08
      use mpi_f08
      implicit none

      integer :: rank, nprocs, buf(2), go, ierr, nfail
      logical :: flag
      type(MPI_Request) :: req

      nfail = 0
      go = 1
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Comm_rank(MPI_COMM_WORLD, rank)
      call MPI_Comm_size(MPI_COMM_WORLD, nprocs)
      if (2 /= nprocs) then
         print *, "ERROR: run with 2 processes, not ", nprocs
         error stop 1
      endif

      if (0 == rank) then
         buf = -7
         call MPI_Precv_init(buf, 2, 1_MPI_COUNT_KIND, MPI_INTEGER, 1, 0, &
                             MPI_COMM_WORLD, MPI_INFO_NULL, req)
         flag = .false.
         call MPI_Parrived(req, 0, flag, ierr)
         call check(MPI_SUCCESS == ierr .and. flag, "inactive request")

         call MPI_Start(req)
         flag = .false.
         do while (.not. flag)
            call MPI_Parrived(req, 0, flag, ierr)
            if (MPI_SUCCESS /= ierr) exit
         end do
         call check(MPI_SUCCESS == ierr .and. flag, "partition 0 arrived")

!        Rank 1 has not readied partition 1 yet
         flag = .true.
         call MPI_Parrived(req, 1, flag, ierr)
         call check(MPI_SUCCESS == ierr .and. .not. flag, &
                    "partition 1 not arrived")
         flag = .true.
         call PMPI_Parrived(request=req, partition=1, flag=flag)
         call check(.not. flag, "PMPI partition 1 not arrived, keywords")

         call MPI_Send(go, 1, MPI_INTEGER, 1, 1, MPI_COMM_WORLD)
         flag = .false.
         do while (.not. flag)
            call MPI_Parrived(req, 1, flag, ierr)
            if (MPI_SUCCESS /= ierr) exit
         end do
         call check(MPI_SUCCESS == ierr .and. flag, "partition 1 arrived")
         call MPI_Wait(req, MPI_STATUS_IGNORE)
         call check(all([10, 11] == buf), "received data")
         call MPI_Request_free(req)

         flag = .false.
         call MPI_Parrived(MPI_REQUEST_NULL, 0, flag, ierr)
         call check(MPI_SUCCESS == ierr .and. flag, "MPI_REQUEST_NULL")
      else
         buf = [10, 11]
         call MPI_Psend_init(buf, 2, 1_MPI_COUNT_KIND, MPI_INTEGER, 0, 0, &
                             MPI_COMM_WORLD, MPI_INFO_NULL, req)
         call MPI_Start(req)
         call MPI_Pready(0, req)
         call MPI_Recv(go, 1, MPI_INTEGER, 0, 1, MPI_COMM_WORLD, &
                       MPI_STATUS_IGNORE)
         call MPI_Pready(1, req)
         call MPI_Wait(req, MPI_STATUS_IGNORE)
         call MPI_Request_free(req)
      endif

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

      end program parrived_f08
