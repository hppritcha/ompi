! -*- f90 -*-
!
! Copyright (c) 2009-2012 Cisco Systems, Inc.  All rights reserved.
! Copyright (c) 2009-2012 Los Alamos National Security, LLC.
!                         All rights reserved.
! Copyright (c) 2018-2020 Research Organization for Information Science
!                         and Technology (RIST).  All rights reserved.
! $COPYRIGHT$

#include "mpi-f08-rename.h"

subroutine MPI_Type_get_contents_f08_c(datatype, max_integers, max_addresses, max_large_counts, &
                                       max_datatypes, array_of_integers, array_of_addresses, &
                                       array_of_large_counts, array_of_datatypes, ierror)
   use :: mpi_f08_types, only : MPI_Datatype, MPI_ADDRESS_KIND, MPI_COUNT_KIND
   use :: ompi_mpifh_bindings, only : ompi_type_get_contents_f_c
   implicit none
   TYPE(MPI_Datatype), INTENT(IN) :: datatype
   INTEGER(KIND=MPI_COUNT_KIND), INTENT(IN) :: max_integers, max_addresses, &
                                               max_large_counts, max_datatypes
   INTEGER, INTENT(OUT) :: array_of_integers(max_integers)
   INTEGER(MPI_ADDRESS_KIND), INTENT(OUT) :: array_of_addresses(max_addresses)
   INTEGER(KIND=MPI_COUNT_KIND), INTENT(OUT) :: array_of_large_counts(max_large_counts)
   TYPE(MPI_Datatype), INTENT(OUT) :: array_of_datatypes(max_datatypes)
   INTEGER, OPTIONAL, INTENT(OUT) :: ierror
   integer :: c_ierror

   call ompi_type_get_contents_f_c(datatype%MPI_VAL,max_integers,max_addresses, &
                    max_large_counts, max_datatypes,array_of_integers,array_of_addresses, &
                    array_of_large_counts, array_of_datatypes(:)%MPI_VAL,c_ierror)
   if (present(ierror)) ierror = c_ierror

end subroutine MPI_Type_get_contents_f08_c
