.. _mpi_test_cancelled:


MPI_Test_cancelled
==================

.. include_body

:ref:`MPI_Test_cancelled` |mdash| Tests whether a request was canceled.

.. The following file was automatically generated
.. include:: ./bindings/mpi_test_cancelled.rst

INPUT PARAMETER
---------------
* ``status``: Status object (status).

OUTPUT PARAMETERS
-----------------
* ``flag``: True if operation was cancelled (logical).
* ``ierror``: Fortran only: Error status (integer).

DESCRIPTION
-----------

Returns *flag* = true if the communication associated with the status
object was canceled successfully. In such a case, all other fields of
status (such as *count* or *tag*) are undefined. Otherwise, returns
*flag* = false. If a receive operation might be canceled, one should
call :ref:`MPI_Test_cancelled` first, to check whether the operation was
canceled, before checking on the other fields of the return status.


NOTES
-----

Cancel can be an expensive operation that should be used only
exceptionally.


ERRORS
------

.. include:: ./ERRORS.rst
