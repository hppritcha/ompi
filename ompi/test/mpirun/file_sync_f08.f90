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
! Fortran (mpi_f08) test for MPI_File_preallocate and MPI_File_sync,
! generated from the file_preallocate.c.in and file_sync.c.in templates
! in ompi/mpi/fortran/use-mpi-f08.  Each process opens a scratch file of
! its own on MPI_COMM_SELF, which is deleted when it is closed.  The test
! checks:
!
!   - MPI_File_preallocate makes the file at least the requested size,
!     and leaves a larger file alone;
!   - data written and synced with MPI_File_sync reads back;
!   - the PMPI_ names, keyword arguments, and an omitted ierror (these
!     need the explicit interface: without one, a call would be linked
!     to the mpif.h binding);
!   - MPI_FILE_NULL gives MPI_ERR_FILE in ierror.
!
! The test is local; run it with 2 processes.  Each failure is reported
! with an ERROR line, and the program finishes with "error stop 1" if
! anything failed.
!
      program file_sync_f08
      use mpi_f08
      implicit none

      type(MPI_File) :: fh
      integer :: rank, wbuf(4), rbuf(4), ierr, nfail
      integer(kind=MPI_OFFSET_KIND) :: fsize
      character(len=64) :: fname

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_rank(MPI_COMM_WORLD, rank)
      write(fname, '(a,i0,a)') "file_sync_f08.", rank, ".tmp"

      call MPI_File_open(MPI_COMM_SELF, fname, &
                         ior(ior(MPI_MODE_CREATE, MPI_MODE_RDWR), &
                             MPI_MODE_DELETE_ON_CLOSE), &
                         MPI_INFO_NULL, fh, ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_File_open returned ", ierr
         error stop 1
      endif

!     ---------------------------------------------------------------
!     MPI_File_preallocate
!     ---------------------------------------------------------------
      call MPI_File_preallocate(fh, 4096_MPI_OFFSET_KIND, ierr)
      call MPI_File_get_size(fh, fsize)
      call check(MPI_SUCCESS == ierr .and. fsize >= 4096, "preallocate")
      call PMPI_File_preallocate(fh=fh, size=16_MPI_OFFSET_KIND)
      call MPI_File_get_size(fh, fsize)
      call check(fsize >= 4096, "PMPI preallocate keywords, smaller size")

!     ---------------------------------------------------------------
!     MPI_File_sync
!     ---------------------------------------------------------------
      wbuf = [1, 2, 3, 4] + 10 * rank
      call MPI_File_write_at(fh, 0_MPI_OFFSET_KIND, wbuf, 4, MPI_INTEGER, &
                             MPI_STATUS_IGNORE)
      call MPI_File_sync(fh, ierr)
      call check(MPI_SUCCESS == ierr, "sync")
      call PMPI_File_sync(fh=fh)
      rbuf = -7
      call MPI_File_read_at(fh, 0_MPI_OFFSET_KIND, rbuf, 4, MPI_INTEGER, &
                            MPI_STATUS_IGNORE)
      call check(all(wbuf == rbuf), "sync, data read back")

      call MPI_File_close(fh)

!     ---------------------------------------------------------------
!     Errors are returned in ierror (the default file error handler
!     is MPI_ERRORS_RETURN)
!     ---------------------------------------------------------------
      call MPI_File_sync(MPI_FILE_NULL, ierr)
      call check(MPI_ERR_FILE == ierr, "sync MPI_FILE_NULL")
      call MPI_File_preallocate(MPI_FILE_NULL, 16_MPI_OFFSET_KIND, ierr)
      call check(MPI_ERR_FILE == ierr, "preallocate MPI_FILE_NULL")

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

      end program file_sync_f08
