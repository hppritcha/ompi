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
! Fortran (mpi_f08) test for the LOGICAL array arguments of MPI_Cart_sub
! and MPI_Cart_get, generated from
! ompi/mpi/fortran/use-mpi-f08/cart_{sub,get}.c.in and the
! LOGICAL_PTR_ARRAY and LOGICAL_ARRAY_OUT types in
! ompi/mpi/bindings/ompi_bindings/fortran_type.py.
!
! MPI_Cart_sub: remain_dims(*) has no length argument and is passed to C
! as the native LOGICAL array.  The test checks:
!
!   - keeping either dimension of a 1 x p grid, which tells the two
!     apart (and so catches a reversed or misread array);
!   - a non-contiguous array section as the actual argument;
!   - the PMPI_ name, keyword arguments, and an omitted ierror;
!   - a communicator without a Cartesian topology is MPI_ERR_TOPOLOGY.
!
! MPI_Cart_get: periods(maxdims) is an INTENT(OUT) LOGICAL array that is
! converted from C integers after the call.  The test checks:
!
!   - periods is set, starting from the opposite values, for both
!     [T,F] and [F,T];
!   - dims and coords are returned;
!   - with maxdims smaller than the actual array, the element past
!     maxdims is left alone;
!   - the PMPI_ name and keyword arguments.
!
! Topology queries are local, and any number of processes works; run it
! with 2.  Each failure is reported with an ERROR line, and the program
! finishes with "error stop 1" if anything failed.
!
      program cart_f08
      use mpi_f08
      implicit none

      type(MPI_Comm) :: cart, sub
      integer :: p, rank, sz, ierr, nfail
      integer :: dims(3), coords(3)
      logical :: rd(4), periods(3)

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Comm_size(MPI_COMM_WORLD, p)

!     ---------------------------------------------------------------
!     MPI_Cart_sub on a 1 x p grid
!     ---------------------------------------------------------------
      call MPI_Cart_create(MPI_COMM_WORLD, 2, [1, p], [.false., .false.], &
                           .false., cart)

!     Keep dimension 2: size p
      sz = -1
      rd = [.false., .true., .true., .false.]
      call MPI_Cart_sub(cart, rd, sub, ierr)
      call MPI_Comm_size(sub, sz)
      call check(MPI_SUCCESS == ierr .and. p == sz, "cart_sub keep dim 2")
      call MPI_Comm_free(sub)

!     Keep dimension 1: size 1
      sz = -1
      call PMPI_Cart_sub(comm=cart, remain_dims=[.true., .false.], &
                         newcomm=sub)
      call MPI_Comm_size(sub, sz)
      call check(1 == sz, "PMPI cart_sub keep dim 1")
      call MPI_Comm_free(sub)

!     Non-contiguous section: rd(2:4:2) is [T,F], so size 1
      sz = -1
      call MPI_Cart_sub(cart, rd(2:4:2), sub, ierr)
      call MPI_Comm_size(sub, sz)
      call check(MPI_SUCCESS == ierr .and. 1 == sz, "cart_sub array section")
      call MPI_Comm_free(sub)

      call MPI_Comm_free(cart)

!     No Cartesian topology
      call MPI_Cart_sub(MPI_COMM_WORLD, rd, sub, ierr)
      call check(MPI_ERR_TOPOLOGY == ierr, "cart_sub non-Cartesian")

!     ---------------------------------------------------------------
!     MPI_Cart_get
!     ---------------------------------------------------------------
!     1 x p grid, periods [T,F]
      call MPI_Cart_create(MPI_COMM_WORLD, 2, [1, p], [.true., .false.], &
                           .false., cart)
      call MPI_Comm_rank(cart, rank)
      dims = -1
      coords = -1
      periods = [.false., .true., .true.]
      call MPI_Cart_get(cart, 2, dims, periods, coords, ierr)
      call check(MPI_SUCCESS == ierr .and. &
                 periods(1) .and. .not. periods(2) .and. &
                 all(dims(1:2) == [1, p]) .and. &
                 all(coords(1:2) == [0, rank]), "cart_get [T,F]")
      call check(periods(3), "cart_get wrote past maxdims")
      call MPI_Comm_free(cart)

!     p x 1 grid, periods [F,T]
      call MPI_Cart_create(MPI_COMM_WORLD, 2, [p, 1], [.false., .true.], &
                           .false., cart)
      periods = [.true., .false., .false.]
      call PMPI_Cart_get(comm=cart, maxdims=2, dims=dims, periods=periods, &
                         coords=coords, ierror=ierr)
      call check(MPI_SUCCESS == ierr .and. &
                 .not. periods(1) .and. periods(2) .and. &
                 all(dims(1:2) == [p, 1]), "PMPI cart_get [F,T]")
      call MPI_Comm_free(cart)

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
         print *, "ERROR: ", what, " (ierr=", ierr, ") size=", sz, &
                  " periods=", periods, " dims=", dims, " coords=", coords
         nfail = nfail + 1
      endif
      end subroutine check

      end program cart_f08
