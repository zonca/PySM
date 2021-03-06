import pytest
import numpy as np
import healpy as hp
import pysm

try:
    from mpi4py import MPI
except ImportError:
    pytest.skip("mpi4py failed to import, skip MPI tests", allow_module_level=True)


@pytest.fixture
def mpi_comm():
    comm = MPI.COMM_WORLD
    return comm


def test_read_map_mpi_pixel_indices(mpi_comm):
    # Reads pixel [0] on rank 0
    # pixels [0,1] on rank 1
    # pixels [0,1,2] on rank 2 and so on.
    m = pysm.read_map(
        "pysm_2/dust_temp.fits",
        nside=8,
        field=0,
        pixel_indices=list(range(0, mpi_comm.rank + 1)),
        mpi_comm=mpi_comm,
    )
    assert len(m) == mpi_comm.rank + 1


def test_read_map_mpi_uniform_distribution(mpi_comm):
    # Spreads the map equally across processes
    pixel_indices = pysm.mpi.distribute_pixels_uniformly(mpi_comm, nside=8)
    m = pysm.read_map(
        "pysm_2/dust_temp.fits",
        nside=8,
        field=0,
        pixel_indices=pixel_indices,
        mpi_comm=mpi_comm,
    )
    npix = hp.nside2npix(8)
    assert (
        npix % mpi_comm.size == 0
    ), "This test requires the size of the communicator to divide the number of pixels {}".format(
        npix
    )
    assert len(m) == npix / mpi_comm.size


def test_distribute_rings_libsharp(mpi_comm):
    pytest.importorskip("libsharp")  # execute only if libsharp is available
    nside = 1
    two_processes_comm = mpi_comm.Split(
        color=0 if mpi_comm.rank in [0, 1] else MPI.UNDEFINED, key=mpi_comm.rank
    )
    if mpi_comm.rank in [0, 1]:
        local_pixels, grid, order = pysm.mpi.distribute_rings_libsharp(
            two_processes_comm, nside, lmax=2 * nside
        )

        if mpi_comm.size == 1:  # serial
            expected_local_pixels = np.arange(12)
        else:
            expected_local_pixels = (
                np.concatenate([np.arange(4), np.arange(8, 12)])
                if mpi_comm.rank == 0
                else np.arange(4, 8)
            )
        np.testing.assert_allclose(local_pixels, expected_local_pixels)
