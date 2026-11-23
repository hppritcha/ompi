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
! Fortran (mpi_f08) test for MPI_Type_get_envelope and
! MPI_Type_get_contents, generated from the type_get_envelope.c.in_nbc,
! type_get_envelope_c.c.in_obc, type_get_contents.c.in_nbc and
! type_get_contents_c.c.in_obc templates in
! ompi/mpi/fortran/use-mpi-f08.  The large count versions have extra
! arguments, and are chosen by the generic interfaces.  The test checks:
!
!   - the envelope and contents of named, vector, hvector and struct
!     datatypes, including that a derived constituent datatype is
!     returned as a new datatype;
!   - array elements beyond the ones that the datatype has are left
!     alone, when the max_* arguments are larger than needed;
!   - the large count versions, for a datatype made with a count that
!     needs more than 32 bits, and for an ordinary datatype; the regular
!     versions give MPI_ERR_TYPE for the former;
!   - the PMPI_ names, keyword arguments, and an omitted ierror;
!   - MPI_DATATYPE_NULL gives MPI_ERR_TYPE in ierror.
!
! The datatypes are never used to move data.  The test is local; run it
! with 2 processes.  Each failure is reported with an ERROR line, and the
! program finishes with "error stop 1" if anything failed.
!
      program type_get_contents_f08
      use mpi_f08
      implicit none

      integer(kind=MPI_COUNT_KIND), parameter :: BIG = 2_MPI_COUNT_KIND**33
      type(MPI_Datatype) :: vec, hvec, st, big_type, dts(4)
      integer :: ints(6), ni, na, nd, comb, ierr, nfail
      integer(kind=MPI_ADDRESS_KIND) :: addrs(4)
      integer(kind=MPI_COUNT_KIND) :: cni, cna, cnl, cnd, lcs(4)
      integer :: sz1, sz2

      nfail = 0
      call MPI_Init(ierr)
      if (MPI_SUCCESS /= ierr) then
         print *, "ERROR: MPI_Init returned ", ierr
         error stop 1
      endif
      call MPI_Comm_set_errhandler(MPI_COMM_SELF, MPI_ERRORS_RETURN)
      call MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN)

      call MPI_Type_vector(3, 2, 5, MPI_INTEGER, vec)
      call MPI_Type_create_hvector(4, 1, 24_MPI_ADDRESS_KIND, MPI_REAL, hvec)
      call MPI_Type_create_struct(2, [1, 2], &
                                  [0_MPI_ADDRESS_KIND, 64_MPI_ADDRESS_KIND], &
                                  [MPI_DOUBLE_PRECISION, vec], st)
      call MPI_Type_contiguous(BIG, MPI_BYTE, big_type)

!     ---------------------------------------------------------------
!     MPI_Type_get_envelope
!     ---------------------------------------------------------------
      call MPI_Type_get_envelope(MPI_INTEGER, ni, na, nd, comb, ierr)
      call check(MPI_SUCCESS == ierr .and. MPI_COMBINER_NAMED == comb .and. &
                 0 == ni .and. 0 == na .and. 0 == nd, "envelope named")
      call MPI_Type_get_envelope(vec, ni, na, nd, comb, ierr)
      call check(MPI_SUCCESS == ierr .and. MPI_COMBINER_VECTOR == comb .and. &
                 3 == ni .and. 0 == na .and. 1 == nd, "envelope vector")
      call PMPI_Type_get_envelope(datatype=hvec, num_integers=ni, &
                                  num_addresses=na, num_datatypes=nd, &
                                  combiner=comb)
      call check(MPI_COMBINER_HVECTOR == comb .and. 2 == ni .and. &
                 1 == na .and. 1 == nd, "PMPI envelope hvector keywords")

!     ---------------------------------------------------------------
!     MPI_Type_get_contents, with arrays larger than needed
!     ---------------------------------------------------------------
      ints = -7
      addrs = -7
      dts = MPI_REAL
      call MPI_Type_get_contents(vec, 6, 4, 4, ints, addrs, dts, ierr)
      call check(MPI_SUCCESS == ierr .and. all([3, 2, 5] == ints(1:3)) .and. &
                 MPI_INTEGER == dts(1), "contents vector")
      call check(all(-7 == ints(4:)) .and. all(-7 == addrs) .and. &
                 all(MPI_REAL == dts(2:)), "contents vector, rest untouched")

      ints = -7
      addrs = -7
      dts = MPI_REAL
      call PMPI_Type_get_contents(datatype=hvec, max_integers=2, &
                                  max_addresses=1, max_datatypes=1, &
                                  array_of_integers=ints, &
                                  array_of_addresses=addrs, &
                                  array_of_datatypes=dts)
      call check(all([4, 1] == ints(1:2)) .and. 24 == addrs(1) .and. &
                 MPI_REAL == dts(1), "PMPI contents hvector keywords")
      call check(all(-7 == ints(3:)) .and. all(-7 == addrs(2:)), &
                 "PMPI contents hvector, rest untouched")

!     A derived constituent datatype is returned as a new datatype
      ints = -7
      addrs = -7
      dts = MPI_REAL
      call MPI_Type_get_contents(st, 3, 2, 2, ints, addrs, dts, ierr)
      call check(MPI_SUCCESS == ierr .and. all([2, 1, 2] == ints(1:3)) .and. &
                 0 == addrs(1) .and. 64 == addrs(2) .and. &
                 MPI_DOUBLE_PRECISION == dts(1), "contents struct")
      call MPI_Type_size(dts(2), sz1)
      call MPI_Type_size(vec, sz2)
      call check(vec /= dts(2) .and. sz1 == sz2, "contents struct, new datatype")
      call MPI_Type_free(dts(2))

!     ---------------------------------------------------------------
!     The large count versions
!     ---------------------------------------------------------------
      call MPI_Type_get_envelope(big_type, cni, cna, cnl, cnd, comb, ierr)
      call check(MPI_SUCCESS == ierr .and. MPI_COMBINER_CONTIGUOUS == comb .and. &
                 0 == cni .and. 0 == cna .and. 1 == cnl .and. 1 == cnd, &
                 "envelope_c large count")
      lcs = -7
      ints = -7
      dts = MPI_REAL
      call MPI_Type_get_contents(big_type, 1_MPI_COUNT_KIND, 0_MPI_COUNT_KIND, &
                                 4_MPI_COUNT_KIND, 2_MPI_COUNT_KIND, ints, &
                                 addrs, lcs, dts, ierr)
      call check(MPI_SUCCESS == ierr .and. BIG == lcs(1) .and. &
                 MPI_BYTE == dts(1), "contents_c large count")
      call check(all(-7 == ints) .and. all(-7 == lcs(2:)) .and. &
                 MPI_REAL == dts(2), "contents_c large count, rest untouched")

      call PMPI_Type_get_envelope(datatype=vec, num_integers=cni, &
                                  num_addresses=cna, num_large_counts=cnl, &
                                  num_datatypes=cnd, combiner=comb)
      call check(MPI_COMBINER_VECTOR == comb .and. 3 == cni .and. &
                 0 == cna .and. 0 == cnl .and. 1 == cnd, &
                 "PMPI envelope_c vector keywords")
      ints = -7
      dts = MPI_REAL
      call PMPI_Type_get_contents(datatype=vec, max_integers=3_MPI_COUNT_KIND, &
                                  max_addresses=0_MPI_COUNT_KIND, &
                                  max_large_counts=0_MPI_COUNT_KIND, &
                                  max_datatypes=1_MPI_COUNT_KIND, &
                                  array_of_integers=ints, &
                                  array_of_addresses=addrs, &
                                  array_of_large_counts=lcs, &
                                  array_of_datatypes=dts)
      call check(all([3, 2, 5] == ints(1:3)) .and. MPI_INTEGER == dts(1), &
                 "PMPI contents_c vector keywords")

!     The regular versions cannot describe a large count datatype
      call MPI_Type_get_envelope(big_type, ni, na, nd, comb, ierr)
      call check(MPI_ERR_TYPE == ierr, "envelope of a large count datatype")
      call MPI_Type_get_contents(big_type, 4, 4, 4, ints, addrs, dts, ierr)
      call check(MPI_ERR_TYPE == ierr, "contents of a large count datatype")

!     ---------------------------------------------------------------
!     Errors are returned in ierror
!     ---------------------------------------------------------------
      call MPI_Type_get_envelope(MPI_DATATYPE_NULL, ni, na, nd, comb, ierr)
      call check(MPI_ERR_TYPE == ierr, "envelope MPI_DATATYPE_NULL")
      call MPI_Type_get_envelope(MPI_DATATYPE_NULL, cni, cna, cnl, cnd, comb, &
                                 ierr)
      call check(MPI_ERR_TYPE == ierr, "envelope_c MPI_DATATYPE_NULL")
      call MPI_Type_get_contents(MPI_DATATYPE_NULL, 4, 4, 4, ints, addrs, dts, &
                                 ierr)
      call check(MPI_ERR_TYPE == ierr, "contents MPI_DATATYPE_NULL")
      call MPI_Type_get_contents(MPI_DATATYPE_NULL, 4_MPI_COUNT_KIND, &
                                 4_MPI_COUNT_KIND, 4_MPI_COUNT_KIND, &
                                 4_MPI_COUNT_KIND, ints, addrs, lcs, dts, ierr)
      call check(MPI_ERR_TYPE == ierr, "contents_c MPI_DATATYPE_NULL")

      call MPI_Type_free(big_type)
      call MPI_Type_free(st)
      call MPI_Type_free(hvec)
      call MPI_Type_free(vec)
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

      end program type_get_contents_f08
