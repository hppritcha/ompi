.. _mpi_comm_rank:


MPI_Comm_rank
=============

.. include_body

:ref:`MPI_Comm_rank` |mdash| Determines the rank of the calling process in the
communicator.

.. The following file was automatically generated
.. include:: ./bindings/mpi_comm_rank.rst

INPUT PARAMETERS
----------------
* ``comm``: Communicator (handle).

OUTPUT PARAMETERS
-----------------
* ``rank``: Rank of the calling process in group of comm (integer).
* ``ierror``: Fortran only: Error status (integer).

DESCRIPTION
-----------

This function gives the rank of the process in the particular
communicator's group. It is equivalent to accessing the communicator's
group with :ref:`MPI_Comm_group`, computing the rank using :ref:`MPI_Group_rank`, and
then freeing the temporary group via :ref:`MPI_Group_free`.

Many programs will be written with the manager-worker model, where one
process (such as the rank-zero process) will play a supervisory role,
and the other processes will serve as compute nodes. In this framework,
:ref:`MPI_Comm_size` and :ref:`MPI_Comm_rank` are useful for determining the roles of
the various processes of a communicator.


ERRORS
------

.. include:: ./ERRORS.rst

.. seealso::
   * :ref:`MPI_Comm_group`
   * :ref:`MPI_Comm_size`
   * :ref:`MPI_Comm_compare`
