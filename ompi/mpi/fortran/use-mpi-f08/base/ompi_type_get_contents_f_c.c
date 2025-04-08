/*
 * Copyright (c) 2004-2005 The Trustees of Indiana University and Indiana
 *                         University Research and Technology
 *                         Corporation.  All rights reserved.
 * Copyright (c) 2004-2020 The University of Tennessee and The University
 *                         of Tennessee Research Foundation.  All rights
 *                         reserved.
 * Copyright (c) 2004-2005 High Performance Computing Center Stuttgart,
 *                         University of Stuttgart.  All rights reserved.
 * Copyright (c) 2004-2005 The Regents of the University of California.
 *                         All rights reserved.
 * Copyright (c) 2011-2012 Cisco Systems, Inc.  All rights reserved.
 * Copyright (c) 2015      Research Organization for Information Science
 *                         and Technology (RIST). All rights reserved.
 * Copyright (c) 2024-2025 Triad National Security, LLC. All rights
 *                         reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include "ompi_config.h"

#include "ompi/datatype/ompi_datatype.h"
#include "ompi/errhandler/errhandler.h"
#include "ompi/mpi/fortran/base/fint_2_int.h"
#include "ompi/mpi/fortran/use-mpi-f08/base/bigcount.h"

/*
 * big count entry point, only needed by F08 bindings.
 */

static const char FUNC_NAME[] = "MPI_TYPE_GET_CONTENTS_C";

void ompi_type_get_contents_f_c(MPI_Fint *mtype, MPI_Count *max_integers,
                             MPI_Count *max_addresses, MPI_Count *max_large_counts,
			     MPI_Count *max_datatypes,
                             MPI_Fint *array_of_integers,
                             MPI_Aint *array_of_addresses,
                             MPI_Count *array_of_large_counts,
                             MPI_Fint *array_of_datatypes, MPI_Fint *ierr);
void ompi_type_get_contents_f_c(MPI_Fint *mtype, MPI_Count *max_integers,
                             MPI_Count *max_addresses, MPI_Count *max_large_counts,
			     MPI_Count *max_datatypes,
                             MPI_Fint *array_of_integers,
                             MPI_Aint *array_of_addresses,
                             MPI_Count *array_of_large_counts,
                             MPI_Fint *array_of_datatypes, MPI_Fint *ierr)
{
    MPI_Aint *tmp_array_of_addresses = NULL;
    MPI_Count *tmp_array_of_large_counts = NULL;
    MPI_Datatype *c_datatype_array = NULL;
    int *tmp_array_of_integers = NULL;
    MPI_Datatype c_mtype = PMPI_Type_f2c(*mtype);
    int i, c_ierr;

    if (*max_datatypes) {
        c_datatype_array = (MPI_Datatype *) malloc(*max_datatypes * sizeof(MPI_Datatype));
        if (NULL == c_datatype_array) {
            c_ierr = OMPI_ERRHANDLER_NOHANDLE_INVOKE(MPI_ERR_NO_MEM,
                                            FUNC_NAME);
            if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);
            return;
        }
    }

    if (*max_addresses) {
        OMPI_FORTRAN_BIGCOUNT_ARRAY_SET(array_of_addresses, tmp_array_of_addresses, *max_addresses);
    }
    if (*max_integers) {
        OMPI_FORTRAN_BIGCOUNT_ARRAY_SET(array_of_integers, tmp_array_of_integers, *max_integers);
    }

    if (*max_large_counts) {
        OMPI_FORTRAN_BIGCOUNT_ARRAY_SET(array_of_large_counts, tmp_array_of_large_counts, *max_large_counts);
    }

    c_ierr = PMPI_Type_get_contents_c(c_mtype,
                                      *max_integers,
                                      *max_addresses,
                                      *max_large_counts,
                                      *max_datatypes,
                                      tmp_array_of_integers,
                                      tmp_array_of_addresses,
                                      tmp_array_of_large_counts,
			              c_datatype_array);
    if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);

    if (MPI_SUCCESS == c_ierr) {
        for (i = 0; i < *max_integers; i++) {
            array_of_integers[i] = tmp_array_of_integers[i];
        }
        for (i = 0; i < *max_addresses; i++) {
            array_of_addresses[i] = tmp_array_of_addresses[i];
        }
        for (i = 0; i < *max_large_counts; i++) {
            array_of_large_counts[i] = tmp_array_of_large_counts[i];
        }
        for (i = 0; i < *max_datatypes; i++) {
          array_of_datatypes[i] = PMPI_Type_c2f(c_datatype_array[i]);
        }
    }

    OMPI_FORTRAN_BIGCOUNT_ARRAY_CLEANUP(array_of_addresses, tmp_array_of_addresses);
    OMPI_FORTRAN_BIGCOUNT_ARRAY_CLEANUP(array_of_integers, tmp_array_of_integers);
    OMPI_FORTRAN_BIGCOUNT_ARRAY_CLEANUP(array_of_large_counts, tmp_array_of_large_counts);

    if (NULL != c_datatype_array) {
        free(c_datatype_array);
    }
}
