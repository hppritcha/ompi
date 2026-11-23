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
! Fortran (mpi_f08) test of the collectives whose count arrays have a
! length other than the size of the communicator, generated from the
! *_ts.c.in templates in ompi/mpi/fortran/use-mpi-f08.  Where Fortran
! INTEGER is not a C int, the bindings convert these arrays, and must
! convert exactly as many entries as the C call reads.  Every array here
! has exactly that many entries.  The test checks:
!
!   - MPI_Neighbor_allgatherv, MPI_Ineighbor_allgatherv and
!     MPI_Neighbor_allgatherv_init on a distributed graph where each
!     process receives from one neighbor (indegree 1, of 3 processes);
!   - MPI_Scatterv, MPI_Iscatterv and MPI_Scatterv_init with MPI_ROOT,
!     and MPI_Alltoallv_init, on an intercommunicator between groups of
!     1 and 2 processes.
!
! Run it with 3 processes.  Each failure is reported with an ERROR line,
! and the program finishes with "error stop 1" if anything failed.
!
      program vcoll_sizes_f08
      use mpi_f08
      implicit none

      type(MPI_Comm) :: gcomm, local, inter
      type(MPI_Request) :: req
      integer :: rank, nprocs, src, dst, color, rsize, root, i
      integer :: sbuf1, rbuf1(1), ierr, nfail
      integer, allocatable :: counts(:), displs(:), sbuf(:), rbuf(:)
      integer, allocatable :: rcounts(:), rdispls(:), expect(:)

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Comm_rank(MPI_COMM_WORLD, rank)
      call MPI_Comm_size(MPI_COMM_WORLD, nprocs)
      if (3 /= nprocs) then
         print *, "ERROR: run with 3 processes, not ", nprocs
         error stop 1
      endif

!     ---------------------------------------------------------------
!     Neighborhood collectives, indegree 1
!     ---------------------------------------------------------------
      src = mod(rank + 1, nprocs)
      dst = mod(rank + nprocs - 1, nprocs)
      call MPI_Dist_graph_create_adjacent(MPI_COMM_WORLD, 1, [src], &
                                          MPI_UNWEIGHTED, 1, [dst], &
                                          MPI_UNWEIGHTED, MPI_INFO_NULL, &
                                          .false., gcomm, ierr)
      call check(MPI_SUCCESS == ierr, "dist_graph_create_adjacent")
      call MPI_Comm_set_errhandler(gcomm, MPI_ERRORS_RETURN)
      allocate(counts(1), displs(1))
      counts = 1
      displs = 0
      sbuf1 = 10 * rank

      rbuf1 = -7
      call MPI_Neighbor_allgatherv(sbuf1, 1, MPI_INTEGER, rbuf1, counts, &
                                   displs, MPI_INTEGER, gcomm, ierr)
      call check(MPI_SUCCESS == ierr .and. 10 * src == rbuf1(1), &
                 "neighbor_allgatherv")
      rbuf1 = -7
      call MPI_Ineighbor_allgatherv(sbuf1, 1, MPI_INTEGER, rbuf1, counts, &
                                    displs, MPI_INTEGER, gcomm, req, ierr)
      call check(MPI_SUCCESS == ierr, "ineighbor_allgatherv")
      call MPI_Wait(req, MPI_STATUS_IGNORE)
      call check(10 * src == rbuf1(1), "ineighbor_allgatherv data")
      rbuf1 = -7
      call MPI_Neighbor_allgatherv_init(sbuf1, 1, MPI_INTEGER, rbuf1, &
                                        counts, displs, MPI_INTEGER, gcomm, &
                                        MPI_INFO_NULL, req, ierr)
      call check(MPI_SUCCESS == ierr, "neighbor_allgatherv_init")
      call MPI_Start(req)
      call MPI_Wait(req, MPI_STATUS_IGNORE)
      call check(10 * src == rbuf1(1), "neighbor_allgatherv_init data")
      call MPI_Request_free(req)
      call MPI_Comm_free(gcomm)
      deallocate(counts, displs)

!     ---------------------------------------------------------------
!     Intercommunicator: rank 0 against ranks 1 and 2
!     ---------------------------------------------------------------
      color = min(rank, 1)
      call MPI_Comm_split(MPI_COMM_WORLD, color, rank, local)
      call MPI_Intercomm_create(local, 0, MPI_COMM_WORLD, 1 - color, 7, &
                                inter, ierr)
      call check(MPI_SUCCESS == ierr, "intercomm_create")
      call MPI_Comm_set_errhandler(inter, MPI_ERRORS_RETURN)
      call MPI_Comm_remote_size(inter, rsize)

!     Scatterv from rank 0: counts and displs have 2 entries there
      if (0 == color) then
         root = MPI_ROOT
         allocate(counts(rsize), displs(rsize), sbuf(rsize))
         counts = 1
         displs = [(i - 1, i = 1, rsize)]
         sbuf = [(100 + i, i = 1, rsize)]
      else
         root = 0
         allocate(counts(1), displs(1), sbuf(1))
      endif

      rbuf1 = -7
      call MPI_Scatterv(sbuf, counts, displs, MPI_INTEGER, rbuf1, 1, &
                        MPI_INTEGER, root, inter, ierr)
      call check(MPI_SUCCESS == ierr, "scatterv")
      if (1 == color) call check(100 + rank == rbuf1(1), "scatterv data")

      rbuf1 = -7
      call MPI_Iscatterv(sbuf, counts, displs, MPI_INTEGER, rbuf1, 1, &
                         MPI_INTEGER, root, inter, req, ierr)
      call check(MPI_SUCCESS == ierr, "iscatterv")
      call MPI_Wait(req, MPI_STATUS_IGNORE)
      if (1 == color) call check(100 + rank == rbuf1(1), "iscatterv data")

      rbuf1 = -7
      call MPI_Scatterv_init(sbuf, counts, displs, MPI_INTEGER, rbuf1, 1, &
                             MPI_INTEGER, root, inter, MPI_INFO_NULL, req, &
                             ierr)
      call check(MPI_SUCCESS == ierr, "scatterv_init")
      call MPI_Start(req)
      call MPI_Wait(req, MPI_STATUS_IGNORE)
      call MPI_Request_free(req)
      if (1 == color) call check(100 + rank == rbuf1(1), &
                                 "scatterv_init data")
      deallocate(counts, displs, sbuf)

!     Alltoallv_init: all the arrays have one entry per remote process
      allocate(counts(rsize), displs(rsize), sbuf(rsize), rbuf(rsize))
      allocate(rcounts(rsize), rdispls(rsize), expect(rsize))
      counts = 1
      displs = [(i - 1, i = 1, rsize)]
      rcounts = 1
      rdispls = displs
      sbuf = [(100 * rank + i, i = 1, rsize)]
      rbuf = -7
      if (0 == color) then
!        From rank i (local rank i - 1 in its group), which sends 100 * i + 1
         expect = [(100 * i + 1, i = 1, rsize)]
      else
!        From rank 0, which sends i to the process with local rank i - 1
         expect = rank
      endif
      call MPI_Alltoallv_init(sbuf, counts, displs, MPI_INTEGER, rbuf, &
                              rcounts, rdispls, MPI_INTEGER, inter, &
                              MPI_INFO_NULL, req, ierr)
      call check(MPI_SUCCESS == ierr, "alltoallv_init")
      call MPI_Start(req)
      call MPI_Wait(req, MPI_STATUS_IGNORE)
      call MPI_Request_free(req)
      call check(all(expect == rbuf), "alltoallv_init data")
      deallocate(counts, displs, sbuf, rbuf, rcounts, rdispls, expect)

      call MPI_Comm_free(inter)
      call MPI_Comm_free(local)
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

      end program vcoll_sizes_f08
