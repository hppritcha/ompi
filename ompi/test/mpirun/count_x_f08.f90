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
! Fortran (mpi_f08) test for MPI_Type_size_x, MPI_Type_get_extent_x,
! MPI_Type_get_true_extent_x and MPI_Status_set_elements_x, generated
! from the *_x.c.in templates in ompi/mpi/fortran/use-mpi-f08.  Their
! count arguments are always INTEGER(KIND=MPI_COUNT_KIND), and there is
! no _c version.  The test checks:
!
!   - sizes, bounds and extents that need more than 32 bits;
!   - MPI_Status_set_elements_x with a count that needs more than 32
!     bits (read back with MPI_Get_elements_x), and with a small one
!     (read back with MPI_Get_count);
!   - the PMPI_ names, keyword arguments, and an omitted ierror;
!   - MPI_DATATYPE_NULL gives MPI_ERR_TYPE in ierror;
!   - MPI_Type_get_extent and MPI_Type_get_true_extent, with keyword
!     arguments (so an explicit interface is needed), give the same
!     results as the _x versions.
!
! The datatypes are never used to move data, so no large buffers are
! needed.  The test is local; run it with 2 processes.  Each failure is
! reported with an ERROR line, and the program finishes with
! "error stop 1" if anything failed.
!
      program count_x_f08
      use mpi_f08
      implicit none

      integer(kind=MPI_COUNT_KIND), parameter :: G = 2_MPI_COUNT_KIND**32
      integer(kind=MPI_ADDRESS_KIND), parameter :: LB = 8
      type(MPI_Datatype) :: t64k, t4g, tres
      type(MPI_Status) :: status
      integer(kind=MPI_COUNT_KIND) :: sz, lbx, extx, cnt
      integer(kind=MPI_ADDRESS_KIND) :: lba, exta
      integer :: icount, ierr, nfail

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)

!     t4g is 2**32 bytes; tres is t4g with lb 8 and extent 2**33
      call MPI_Type_contiguous(2**16, MPI_BYTE, t64k)
      call MPI_Type_contiguous(2**16, t64k, t4g)
      call MPI_Type_create_resized(t4g, LB, 2_MPI_ADDRESS_KIND**33, tres)
      call MPI_Type_commit(tres)

!     ---------------------------------------------------------------
!     MPI_Type_size_x
!     ---------------------------------------------------------------
      sz = -1
      call MPI_Type_size_x(tres, sz, ierr)
      call check(MPI_SUCCESS == ierr .and. G == sz, "type_size_x")
      sz = -1
      call PMPI_Type_size_x(datatype=MPI_INTEGER, size=sz)
      call check(storage_size(1) / 8 == sz, "PMPI type_size_x keywords")

!     ---------------------------------------------------------------
!     MPI_Type_get_extent_x
!     ---------------------------------------------------------------
      lbx = -1
      extx = -1
      call MPI_Type_get_extent_x(tres, lbx, extx, ierr)
      call check(MPI_SUCCESS == ierr .and. LB == lbx .and. 2 * G == extx, &
                 "type_get_extent_x")
      lbx = -1
      extx = -1
      call PMPI_Type_get_extent_x(datatype=t4g, lb=lbx, extent=extx)
      call check(0 == lbx .and. G == extx, "PMPI type_get_extent_x keywords")

!     ---------------------------------------------------------------
!     MPI_Type_get_true_extent_x: the resize does not change it
!     ---------------------------------------------------------------
      lbx = -1
      extx = -1
      call MPI_Type_get_true_extent_x(tres, lbx, extx, ierr)
      call check(MPI_SUCCESS == ierr .and. 0 == lbx .and. G == extx, &
                 "type_get_true_extent_x")
      lbx = -1
      extx = -1
      call PMPI_Type_get_true_extent_x(datatype=tres, true_lb=lbx, &
                                       true_extent=extx)
      call check(0 == lbx .and. G == extx, &
                 "PMPI type_get_true_extent_x keywords")

!     ---------------------------------------------------------------
!     MPI_Type_get_extent and MPI_Type_get_true_extent
!     ---------------------------------------------------------------
      lba = -1
      exta = -1
      call MPI_Type_get_extent(datatype=tres, lb=lba, extent=exta, &
                               ierror=ierr)
      call check(MPI_SUCCESS == ierr .and. LB == lba .and. 2 * G == exta, &
                 "type_get_extent")
      lba = -1
      exta = -1
      call PMPI_Type_get_true_extent(datatype=tres, true_lb=lba, &
                                     true_extent=exta)
      call check(0 == lba .and. G == exta, "PMPI type_get_true_extent")

!     ---------------------------------------------------------------
!     MPI_Status_set_elements_x
!     ---------------------------------------------------------------
      call MPI_Status_set_elements_x(status, MPI_BYTE, 2 * G + 3, ierr)
      cnt = -1
      call MPI_Get_elements_x(status, MPI_BYTE, cnt)
      call check(MPI_SUCCESS == ierr .and. 2 * G + 3 == cnt, &
                 "status_set_elements_x large count")
      call MPI_Get_count(status, MPI_BYTE, icount)
      call check(MPI_UNDEFINED == icount, &
                 "status_set_elements_x large count, get_count")

      call PMPI_Status_set_elements_x(status=status, datatype=MPI_INTEGER, &
                                      count=5_MPI_COUNT_KIND)
      icount = -1
      call MPI_Get_count(status, MPI_INTEGER, icount)
      call check(5 == icount, "PMPI status_set_elements_x keywords")

!     ---------------------------------------------------------------
!     Errors are returned in ierror
!     ---------------------------------------------------------------
      call MPI_Type_size_x(MPI_DATATYPE_NULL, sz, ierr)
      call check(MPI_ERR_TYPE == ierr, "type_size_x MPI_DATATYPE_NULL")
      call MPI_Type_get_extent_x(MPI_DATATYPE_NULL, lbx, extx, ierr)
      call check(MPI_ERR_TYPE == ierr, "type_get_extent_x MPI_DATATYPE_NULL")
      call MPI_Type_get_true_extent_x(MPI_DATATYPE_NULL, lbx, extx, ierr)
      call check(MPI_ERR_TYPE == ierr, &
                 "type_get_true_extent_x MPI_DATATYPE_NULL")
      call MPI_Status_set_elements_x(status, MPI_DATATYPE_NULL, &
                                     1_MPI_COUNT_KIND, ierr)
      call check(MPI_ERR_TYPE == ierr, &
                 "status_set_elements_x MPI_DATATYPE_NULL")

      call MPI_Type_free(tres)
      call MPI_Type_free(t4g)
      call MPI_Type_free(t64k)
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

      end program count_x_f08
