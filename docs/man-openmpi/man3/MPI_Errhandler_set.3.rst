.. _mpi_errhandler_set:


MPI_Errhandler_set
==================

.. include_body

:ref:`MPI_Errhandler_set` |mdash| Sets the error handler for a communicator |mdash| |deprecated_favor| :ref:`MPI_Comm_set_errhandler`.


SYNTAX
------

.. NOTE: The bindings for this man page are not automatically
   generated from the official MPI Forum JSON/Python library because
   this function is deprecated.  Hence, this function is not included
   in the MPI Forum JSON data, and we therefore have to hard-code the
   bindings here ourselves.

C Syntax
^^^^^^^^

.. code-block:: c

   #include <mpi.h>

   int MPI_Errhandler_set(MPI_Comm comm, MPI_Errhandler errhandler)


Fortran Syntax
^^^^^^^^^^^^^^

.. code-block:: fortran

   USE MPI
   ! or the older form: INCLUDE 'mpif.h'

   MPI_ERRHANDLER_SET(COMM, ERRHANDLER, IERROR)
   	INTEGER	COMM, ERRHANDLER, IERROR


INPUT PARAMETERS
----------------
* ``comm``: Communicator to set the error handler for (handle).
* ``errhandler``: New MPI error handler for communicator (handle).

OUTPUT PARAMETER
----------------
* ``ierror``: Fortran only: Error status (integer).

DESCRIPTION
-----------

Note that use of this routine is *deprecated* as of MPI-2. Please use
:ref:`MPI_Comm_set_errhandler` instead.

Associates the new error handler errhandler with communicator comm at
the calling process. Note that an error handler is always associated
with the communicator.


ERRORS
------

.. include:: ./ERRORS.rst

.. seealso::
   * :ref:`MPI_Comm_create_errhandler`
   * :ref:`MPI_Comm_get_errhandler`
   * :ref:`MPI_Comm_set_errhandler`
