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
! Fortran (mpi_f08) unit test for character-string arguments of the
! generated mpi_f08 bindings (ompi/mpi/fortran/use-mpi-f08/*.c.in and the
! CHAR_ARRAY / CHAR_ARRAY_OUT types in
! ompi/mpi/bindings/ompi_bindings/fortran_type.py).
!
! String OUT arguments: C returns '\0'-terminated strings whose MPI_MAX_*
! bounds are one larger than the Fortran values, while Fortran expects
! the result blank-padded to the length of the actual argument.  For each
! routine below the result is written into a buffer followed by guard
! characters, and the test checks that the value is correct, contains no
! NUL, is blank-padded after resultlen, and that the guard characters are
! untouched (no overrun):
!
!   MPI_Comm_get_name, MPI_Type_get_name, MPI_Win_get_name (including a
!   name of exactly MPI_MAX_OBJECT_NAME characters), MPI_Error_string,
!   MPI_Get_processor_name, MPI_Get_library_version, MPI_Open_port, and
!   MPI_File_get_view (CHARACTER(LEN=*) datarep: full, truncated, and
!   zero-length).  MPI_Lookup_name of an unknown service must fail and
!   leave port_name unchanged.
!
! String IN arguments: leading and trailing blanks are not significant,
! so blank-padded keys, values, names and file names passed to
! MPI_Info_set, MPI_Info_delete, MPI_Comm_set_name and MPI_File_open must
! behave as if they were trimmed.
!
! The program is single-process and needs no launcher.  It reports each
! failure with an ERROR line and finishes with "error stop 1" if anything
! failed, so that "make check" sees a non-zero exit status.
!
      program strings_f08
      use mpi_f08
      implicit none

!     Number of guard characters after each output buffer.
      integer, parameter :: G = 8
      character(len=max(MPI_MAX_OBJECT_NAME, MPI_MAX_ERROR_STRING, &
                        MPI_MAX_PROCESSOR_NAME, MPI_MAX_PORT_NAME, &
                        MPI_MAX_LIBRARY_VERSION_STRING, &
                        MPI_MAX_DATAREP_STRING) + G) :: buf
      character(len=MPI_MAX_OBJECT_NAME) :: longname
      character(len=MPI_MAX_INFO_KEY) :: key
      character(len=MPI_MAX_INFO_VAL) :: val
      character(len=64) :: fname
      integer :: ierr, rlen, vlen, i, nfail
      integer, target :: winbuf(4)
      integer(MPI_OFFSET_KIND) :: disp
      logical :: flag
      type(MPI_Comm) :: comm
      type(MPI_Datatype) :: dtype, etype, ftype
      type(MPI_Win) :: win
      type(MPI_File) :: fh
      type(MPI_Info) :: info

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)

!     A name that exactly fills a Fortran MPI_MAX_OBJECT_NAME buffer; C
!     needs one more byte for its '\0'.
      do i = 1, MPI_MAX_OBJECT_NAME
         longname(i:i) = achar(iachar('a') + mod(i - 1, 26))
      end do

!     ---------------------------------------------------------------
!     Object names
!     ---------------------------------------------------------------
      buf = repeat('X', len(buf))
      call MPI_Comm_get_name(MPI_COMM_WORLD, buf(1:MPI_MAX_OBJECT_NAME), &
                             rlen, ierr)
      call check_out("MPI_Comm_get_name(MPI_COMM_WORLD)", &
                     MPI_MAX_OBJECT_NAME, rlen, "MPI_COMM_WORLD")

      call MPI_Comm_dup(MPI_COMM_WORLD, comm)
      call MPI_Comm_set_name(comm, longname)
      buf = repeat('X', len(buf))
      call MPI_Comm_get_name(comm=comm, &
                             comm_name=buf(1:MPI_MAX_OBJECT_NAME), &
                             resultlen=rlen, ierror=ierr)
      call check_out("MPI_Comm_get_name(max length)", &
                     MPI_MAX_OBJECT_NAME, rlen, longname)
!     IN: leading blanks are stripped from the name.
      call MPI_Comm_set_name(comm, "   dup comm")
      buf = repeat('X', len(buf))
      call MPI_Comm_get_name(comm, buf(1:MPI_MAX_OBJECT_NAME), rlen, ierr)
      call check_out("MPI_Comm_set_name(blank-padded)", &
                     MPI_MAX_OBJECT_NAME, rlen, "dup comm")
      call MPI_Comm_free(comm)

      buf = repeat('X', len(buf))
      call MPI_Type_get_name(MPI_INTEGER, buf(1:MPI_MAX_OBJECT_NAME), &
                             rlen, ierr)
      call check_out("MPI_Type_get_name(MPI_INTEGER)", &
                     MPI_MAX_OBJECT_NAME, rlen, "MPI_INTEGER")
      call MPI_Type_contiguous(2, MPI_INTEGER, dtype)
      call MPI_Type_set_name(dtype, longname)
      buf = repeat('X', len(buf))
      call PMPI_Type_get_name(dtype, buf(1:MPI_MAX_OBJECT_NAME), rlen, &
                              ierr)
      call check_out("PMPI_Type_get_name(max length)", &
                     MPI_MAX_OBJECT_NAME, rlen, longname)
      call MPI_Type_free(dtype)

      call MPI_Win_create(winbuf, int(16, MPI_ADDRESS_KIND), 4, &
                          MPI_INFO_NULL, MPI_COMM_SELF, win)
      call MPI_Win_set_name(win, longname)
      buf = repeat('X', len(buf))
      call MPI_Win_get_name(win, buf(1:MPI_MAX_OBJECT_NAME), rlen, ierr)
      call check_out("MPI_Win_get_name(max length)", &
                     MPI_MAX_OBJECT_NAME, rlen, longname)
      call MPI_Win_free(win)

!     ---------------------------------------------------------------
!     Other fixed-length string results.  The exact text is
!     implementation-defined, so only the format is checked.
!     ---------------------------------------------------------------
      buf = repeat('X', len(buf))
      call MPI_Error_string(MPI_ERR_ARG, buf(1:MPI_MAX_ERROR_STRING), &
                            rlen, ierr)
      call check_out("MPI_Error_string", MPI_MAX_ERROR_STRING, rlen, "")

      buf = repeat('X', len(buf))
      call MPI_Get_processor_name(buf(1:MPI_MAX_PROCESSOR_NAME), rlen, &
                                  ierr)
      call check_out("MPI_Get_processor_name", MPI_MAX_PROCESSOR_NAME, &
                     rlen, "")

      buf = repeat('X', len(buf))
      call MPI_Get_library_version(buf(1:MPI_MAX_LIBRARY_VERSION_STRING), &
                                   rlen, ierr)
      call check_out("MPI_Get_library_version", &
                     MPI_MAX_LIBRARY_VERSION_STRING, rlen, "")

      buf = repeat('X', len(buf))
      call MPI_Open_port(MPI_INFO_NULL, buf(1:MPI_MAX_PORT_NAME), ierr)
      call check_out("MPI_Open_port", MPI_MAX_PORT_NAME, &
                     len_trim(buf(1:MPI_MAX_PORT_NAME)), "")
      if (MPI_SUCCESS == ierr) then
         call MPI_Close_port(buf(1:MPI_MAX_PORT_NAME), ierr)
      endif

!     Publishing needs a name server, which a singleton does not have,
!     but a failed lookup must leave port_name unchanged.
      buf = repeat('X', len(buf))
      call MPI_Lookup_name("ompi-test-no-such-service", MPI_INFO_NULL, &
                           buf(1:MPI_MAX_PORT_NAME), ierr)
      call check(MPI_SUCCESS /= ierr .and. buf == repeat('X', len(buf)), &
                 "MPI_Lookup_name(unknown service)")

!     ---------------------------------------------------------------
!     MPI_File_open with a blank-padded file name, then
!     MPI_File_get_view's CHARACTER(LEN=*) datarep.
!     ---------------------------------------------------------------
      fname = "strings_f08.tmp"
      call MPI_File_open(MPI_COMM_SELF, fname, &
                         MPI_MODE_CREATE + MPI_MODE_RDWR + &
                         MPI_MODE_DELETE_ON_CLOSE, MPI_INFO_NULL, fh, ierr)
      call check(MPI_SUCCESS == ierr, "MPI_File_open(blank-padded name)")
      if (MPI_SUCCESS /= ierr) then
         print *, "  (if this is a sandboxed macOS environment, try ", &
                  "OMPI_MCA_sharedfp=^sm; see README.md)"
      else
         call MPI_File_set_view(fh, 0_MPI_OFFSET_KIND, MPI_INTEGER, &
                                MPI_INTEGER, "native", MPI_INFO_NULL, ierr)
         buf = repeat('X', len(buf))
         call MPI_File_get_view(fh, disp, etype, ftype, &
                                buf(1:MPI_MAX_DATAREP_STRING), ierr)
         call check_out("MPI_File_get_view", MPI_MAX_DATAREP_STRING, &
                        len_trim("native"), "native")
!        Shorter than the value: truncated, no overrun.
         buf = repeat('X', len(buf))
         call MPI_File_get_view(fh, disp, etype, ftype, buf(1:4), ierr)
         call check(MPI_SUCCESS == ierr .and. buf(1:4) == "nati" .and. &
                    buf(5:) == repeat('X', len(buf) - 4), &
                    "MPI_File_get_view(truncated datarep)")
!        Zero length: nothing written at all.
         buf = repeat('X', len(buf))
         call MPI_File_get_view(fh, disp, etype, ftype, buf(5:4), ierr)
         call check(MPI_SUCCESS == ierr .and. &
                    buf == repeat('X', len(buf)), &
                    "MPI_File_get_view(zero-length datarep)")
         call MPI_File_close(fh, ierr)
      endif

!     ---------------------------------------------------------------
!     Blank-padded info keys and values.
!     ---------------------------------------------------------------
      call MPI_Info_create(info)
      key = "color"
      val = "  blue"
      call MPI_Info_set(info, key, val, ierr)
      call MPI_Info_get_valuelen(info, "color", vlen, flag, ierr)
      call check(MPI_SUCCESS == ierr .and. flag .and. 4 == vlen, &
                 "MPI_Info_set(blank-padded key/value)")
      call MPI_Info_delete(info, "  color   ", ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Info_delete(blank-padded key)")
      call MPI_Info_get_valuelen(info, "color", vlen, flag, ierr)
      call check(.not. flag, "key still present after MPI_Info_delete")
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
         print *, "ERROR: ", what, " (ierr=", ierr, ")"
         nfail = nfail + 1
      endif
      end subroutine check

!     Check a string result of length n in buf(1:n) with resultlen r.  If
!     expect is non-empty the value must equal it.
      subroutine check_out(what, n, r, expect)
      character(len=*), intent(in) :: what, expect
      integer, intent(in) :: n, r
      logical :: ok
      ok = MPI_SUCCESS == ierr .and. r >= 1 .and. r <= n
      ok = ok .and. 0 == index(buf(1:n), char(0))
      ok = ok .and. buf(n+1:n+G) == repeat('X', G)
      if (ok) ok = buf(r+1:n) == ""
      if (ok .and. len(expect) > 0) ok = buf(1:n) == expect
      if (.not. ok) then
         print *, "ERROR: ", what, " (ierr=", ierr, " resultlen=", r, &
                  ") got [", buf(1:n+G), "]"
         nfail = nfail + 1
      endif
      end subroutine check_out

      end program strings_f08
