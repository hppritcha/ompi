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
! Fortran (mpi_f08) test for MPI_Comm_spawn and MPI_Comm_spawn_multiple,
! generated from ompi/mpi/fortran/use-mpi-f08/comm_spawn{,_multiple}.c.in
! and the STRING_ARRAY, STRING_ARRAY_2D, INFO_ARRAY and ERRCODES_ARRAY
! types in ompi/mpi/bindings/ompi_bindings/fortran_type.py.
!
! The parent spawns copies of this program.  Every child checks the
! command-line arguments it got against what its first argument says it
! should have, and the size of its MPI_COMM_WORLD, and reports the
! result to the parents with an MPI_Allreduce over the intercommunicator.
! The parents check:
!
!   - MPI_Comm_spawn with an argv array whose strings have leading,
!     trailing and interior blanks and which ends at a blank string:
!     leading and trailing blanks are dropped, interior ones kept;
!   - MPI_Comm_spawn with MPI_ARGV_NULL and MPI_ERRCODES_IGNORE, through
!     the PMPI_ name with keyword arguments and no ierror;
!   - MPI_Comm_spawn_multiple with two commands, whose argv columns are
!     interleaved in memory, an array of infos, and error codes for
!     all the spawned processes;
!   - MPI_Comm_spawn_multiple with MPI_ARGVS_NULL and
!     MPI_ERRCODES_IGNORE;
!   - the error codes returned at the root are MPI_SUCCESS.
!
! Run it with 2 processes and --oversubscribe: up to 3 children are
! alive at a time.  Each failure is reported with an ERROR line, and the
! program finishes with "error stop 1" if anything failed.
!
      program comm_spawn_f08
      use mpi_f08
      implicit none

      type(MPI_Comm) :: parent, inter
      character(len=256) :: prog, cmds(2)
      character(len=8) :: argv(4), argvs(2,3)
      integer :: rank, ierr, nfail, ok, nok, errs(3)

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_get_parent(parent)
      if (MPI_COMM_NULL /= parent) then
         call child(parent)
         call MPI_Finalize(ierr)
         stop
      endif

      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)
      call MPI_Comm_rank(MPI_COMM_WORLD, rank)
      call get_command_argument(0, prog)

!     ---------------------------------------------------------------
!     MPI_Comm_spawn
!     ---------------------------------------------------------------
!     argv: "  a b  " keeps its interior blank; " " ends the list, so
!     the last entry is never seen.
      argv = [character(len=8) :: "spawn", "  a b  ", " ", "unseen"]
      errs = -1
      call MPI_Comm_spawn("  " // trim(prog) // "  ", argv, 2, &
                          MPI_INFO_NULL, 0, MPI_COMM_WORLD, inter, &
                          errs, ierr)
      call check(MPI_SUCCESS == ierr, "spawn")
      if (0 == rank) then
         call check(all(MPI_SUCCESS == errs(1:2)), "spawn errcodes")
      endif
      call collect(inter, 2, "spawn children")

!     MPI_ARGV_NULL, MPI_ERRCODES_IGNORE, PMPI_, keywords, no ierror
      call PMPI_Comm_spawn(command=prog, argv=MPI_ARGV_NULL, maxprocs=1, &
                           info=MPI_INFO_NULL, root=0, &
                           comm=MPI_COMM_WORLD, intercomm=inter, &
                           array_of_errcodes=MPI_ERRCODES_IGNORE)
      call collect(inter, 1, "spawn MPI_ARGV_NULL children")

!     ---------------------------------------------------------------
!     MPI_Comm_spawn_multiple
!     ---------------------------------------------------------------
!     argvs(i,:) are the arguments of command i
      cmds = prog
      argvs(1,:) = [character(len=8) :: "multi1", "p", ""]
      argvs(2,:) = [character(len=8) :: "multi2", " q r", ""]
      errs = -1
      call MPI_Comm_spawn_multiple(2, cmds, argvs, [1, 2], &
                                   [MPI_INFO_NULL, MPI_INFO_NULL], 0, &
                                   MPI_COMM_WORLD, inter, errs, ierr)
      call check(MPI_SUCCESS == ierr, "spawn_multiple")
      if (0 == rank) then
         call check(all(MPI_SUCCESS == errs), "spawn_multiple errcodes")
      endif
      call collect(inter, 3, "spawn_multiple children")

!     MPI_ARGVS_NULL, MPI_ERRCODES_IGNORE
      call MPI_Comm_spawn_multiple(1, cmds, MPI_ARGVS_NULL, [1], &
                                   [MPI_INFO_NULL], 0, MPI_COMM_WORLD, &
                                   inter, MPI_ERRCODES_IGNORE, ierr)
      call check(MPI_SUCCESS == ierr, "spawn_multiple MPI_ARGVS_NULL")
      call collect(inter, 1, "spawn_multiple MPI_ARGVS_NULL children")

      call MPI_Finalize(ierr)
      if (nfail > 0) then
         print *, "ERROR: ", nfail, " check(s) failed"
         error stop 1
      endif

      contains

!     Parent side: every child contributes 1 if its checks passed
      subroutine collect(comm, nchildren, what)
      type(MPI_Comm), intent(inout) :: comm
      integer, intent(in) :: nchildren
      character(len=*), intent(in) :: what
      nok = -1
      call MPI_Allreduce(1, nok, 1, MPI_INTEGER, MPI_SUM, comm, ierr)
      call check(MPI_SUCCESS == ierr .and. nchildren == nok, what)
      call MPI_Comm_disconnect(comm)
      end subroutine collect

      subroutine child(comm)
      type(MPI_Comm), intent(inout) :: comm
      character(len=16) :: arg1, arg2
      integer :: nargs, wsize, ndummy
      nargs = command_argument_count()
      arg1 = ""
      arg2 = ""
      if (nargs >= 1) call get_command_argument(1, arg1)
      if (nargs >= 2) call get_command_argument(2, arg2)
      call MPI_Comm_size(MPI_COMM_WORLD, wsize)
      select case (arg1)
      case ("spawn")
         ok = merge(1, 0, 2 == nargs .and. "a b" == arg2 .and. 2 == wsize)
      case ("multi1")
         ok = merge(1, 0, 2 == nargs .and. "p" == arg2 .and. 3 == wsize)
      case ("multi2")
         ok = merge(1, 0, 2 == nargs .and. "q r" == arg2 .and. 3 == wsize)
      case default
!        MPI_ARGV_NULL / MPI_ARGVS_NULL: no arguments at all
         ok = merge(1, 0, 0 == nargs .and. 1 == wsize)
      end select
      if (1 /= ok) then
         print *, "ERROR: child got ", nargs, " args '", trim(arg1), &
                  "' '", trim(arg2), "', world size ", wsize
      endif
      call MPI_Allreduce(ok, ndummy, 1, MPI_INTEGER, MPI_SUM, comm)
      call MPI_Comm_disconnect(comm)
      end subroutine child

      subroutine check(good, what)
      logical, intent(in) :: good
      character(len=*), intent(in) :: what
      if (.not. good) then
         print *, "ERROR: ", what, " (ierr=", ierr, ") nok=", nok, &
                  " errcodes=", errs
         nfail = nfail + 1
      endif
      end subroutine check

      end program comm_spawn_f08
