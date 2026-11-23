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
! Fortran (mpi_f08) unit test for user-defined error classes and codes:
! MPI_Add_error_class, MPI_Add_error_code, MPI_Add_error_string,
! MPI_Error_class, MPI_Error_string, MPI_Remove_error_string,
! MPI_Remove_error_code and MPI_Remove_error_class.
!
! These routines are generated from the templates in
! ompi/mpi/fortran/use-mpi-f08/*.c.in.  The test checks that:
!
!   - MPI_Add_error_code returns a new code distinct from its class (a
!     template bug once wrote the class back instead of the code), and
!     MPI_Error_class maps the code back to the class;
!   - a string added to the code is returned by MPI_Error_string and is
!     gone after MPI_Remove_error_string, and removing the string of a
!     predefined code is an error;
!   - a code and then its class can be removed, and removing either a
!     second time, or removing a predefined class/code, is an error;
!   - the PMPI_ entry points and the forms without ierror work.
!
! The program is single-process and needs no launcher.  It reports each
! failure with an ERROR line and finishes with "error stop 1" if anything
! failed, so that "make check" sees a non-zero exit status.
!
      program error_class_f08
      use mpi_f08
      implicit none

      character(len=MPI_MAX_ERROR_STRING) :: estr
      integer :: ierr, eclass, ecode, rclass, rlen, nfail

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
!     Errors that are not associated with a handle are raised on
!     MPI_COMM_SELF; make every expected error return instead of abort.
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)

!     ---------------------------------------------------------------
!     Add a class and a code in it.
!     ---------------------------------------------------------------
      call MPI_Add_error_class(eclass, ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Add_error_class")
      call MPI_Add_error_code(eclass, ecode, ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Add_error_code")
      call check(ecode /= eclass, &
                 "MPI_Add_error_code returned the class, not a new code")
      call MPI_Error_class(ecode, rclass, ierr)
      call check(MPI_SUCCESS == ierr .and. rclass == eclass, &
                 "MPI_Error_class(new code) /= new class")

!     ---------------------------------------------------------------
!     Add a string to the code, then remove it again.
!     ---------------------------------------------------------------
      call MPI_Add_error_string(ecode, "error_class_f08 test code", ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Add_error_string")
      call MPI_Error_string(ecode, estr, rlen, ierr)
      call check(MPI_SUCCESS == ierr .and. &
                 estr == "error_class_f08 test code", &
                 "MPI_Error_string of the added string")
      call MPI_Remove_error_string(ecode, ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Remove_error_string")
      call MPI_Error_string(ecode, estr, rlen, ierr)
      call check(MPI_SUCCESS == ierr .and. &
                 estr /= "error_class_f08 test code", &
                 "string still present after MPI_Remove_error_string")
      call MPI_Remove_error_string(MPI_ERR_ARG, ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "MPI_Remove_error_string(MPI_ERR_ARG) succeeded")

!     ---------------------------------------------------------------
!     Remove the code, then the class; removing again must fail.
!     ---------------------------------------------------------------
      call MPI_Remove_error_code(ecode, ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Remove_error_code")
      call MPI_Remove_error_class(eclass, ierr)
      call check(MPI_SUCCESS == ierr, "MPI_Remove_error_class")
      call MPI_Remove_error_code(ecode, ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "MPI_Remove_error_code of a removed code succeeded")
      call MPI_Remove_error_class(eclass, ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "MPI_Remove_error_class of a removed class succeeded")

!     Predefined classes and codes cannot be removed.
      call MPI_Remove_error_code(MPI_ERR_ARG, ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "MPI_Remove_error_code(MPI_ERR_ARG) succeeded")
      call MPI_Remove_error_class(MPI_ERR_ARG, ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "MPI_Remove_error_class(MPI_ERR_ARG) succeeded")

!     ---------------------------------------------------------------
!     PMPI_ entry points and the optional ierror argument.  The final
!     removal must fail, proving the PMPI_ call really removed the class.
!     ---------------------------------------------------------------
      call MPI_Add_error_class(eclass)
      call PMPI_Add_error_code(eclass, ecode)
      call MPI_Add_error_string(ecode, "error_class_f08 PMPI code")
      call PMPI_Remove_error_string(errorcode=ecode)
      call MPI_Error_string(ecode, estr, rlen, ierr)
      call check(MPI_SUCCESS == ierr .and. &
                 estr /= "error_class_f08 PMPI code", &
                 "PMPI_Remove_error_string did not remove the string")
      call PMPI_Remove_error_code(ecode)
      call PMPI_Remove_error_class(eclass)
      call MPI_Remove_error_class(errorclass=eclass, ierror=ierr)
      call check(MPI_SUCCESS /= ierr, &
                 "PMPI_Remove_error_class did not remove the class")

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

      end program error_class_f08
