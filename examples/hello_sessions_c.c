#include "mpi.h"
#include <stdio.h>

/*
 * Simple test to demonstrate several aspects of MPI 4 Sessions and related
 * functionality.  See sections 11.3 and 11.4 of the MPI 4 standard for more
 * details.
 */

int main(int argc, char** argv) {
  MPI_Info info;
  MPI_Session s1, s2;

#if 0
/* need PR https://github.com/open-mpi/ompi/pull/12868 to be merged in
 * before this can be uncommented.
 */
  MPI_Info_create(&info);
#endif
  MPI_Session_init(MPI_INFO_NULL, MPI_ERRORS_RETURN, &s1);
  MPI_Session_finalize(&s1);
  MPI_Session_init(MPI_INFO_NULL, MPI_ERRORS_RETURN, &s2);
  MPI_Session_finalize(&s2);
}
