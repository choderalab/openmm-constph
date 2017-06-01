# coding=utf-8
"""
Tests the storing of specific protons objects in netcdf files.
"""
import shutil
import tempfile

from simtk import unit
from simtk.openmm import openmm, app

from protons import ForceFieldProtonDrive
from protons import record, ff
import pytest
from protons.integrators import GHMCIntegrator
from . import get_test_data
from .utilities import SystemSetup, create_compound_gbaoab_integrator


def setup_forcefield_drive():
    """
    Set up a forcefield drive containing the imidazole system
    """
    testsystem = SystemSetup()
    testsystem.temperature = 300.0 * unit.kelvin
    testsystem.pressure = 1.0 * unit.atmospheres
    testsystem.timestep = 1.0 * unit.femtoseconds
    testsystem.collision_rate = 1.0 / unit.picoseconds
    testsystem.pH = 9.6
    testsystems = get_test_data('imidazole_explicit', 'testsystems')

    testsystem.positions = openmm.XmlSerializer.deserialize(
        open('{}/imidazole-explicit.state.xml'.format(testsystems)).read()).getPositions(asNumpy=True)
    testsystem.system = openmm.XmlSerializer.deserialize(
        open('{}/imidazole-explicit.sys.xml'.format(testsystems)).read())
    testsystem.ffxml_filename = '{}/protons-imidazole.xml'.format(testsystems)
    testsystem.forcefield = app.ForceField(ff.gaff, testsystem.ffxml_filename)
    testsystem.gaff = get_test_data("gaff.xml", "../forcefields/")
    testsystem.pdbfile = app.PDBFile(
        get_test_data("imidazole-solvated-minimized.pdb", "testsystems/imidazole_explicit"))
    testsystem.topology = testsystem.pdbfile.topology
    testsystem.nsteps_per_ghmc = 1
    testsystem.constraint_tolerance = 1.e-7
    integrator = create_compound_gbaoab_integrator(testsystem)

    drive = ForceFieldProtonDrive(testsystem.system, testsystem.temperature, testsystem.pH,
                                  [testsystem.ffxml_filename], testsystem.forcefield,
                                  testsystem.topology, integrator, debug=False,
                                  pressure=testsystem.pressure, ncmc_steps_per_trial=2, implicit=False,
                                  residues_by_name=['LIG'], nattempts_per_update=1)
    platform = openmm.Platform.getPlatformByName('CPU')
    context = openmm.Context(testsystem.system, drive.compound_integrator, platform)
    context.setPositions(testsystem.positions)  # set to minimized positions
    context.setVelocitiesToTemperature(testsystem.temperature)
    integrator.step(1)
    drive.update(context)

    return drive, integrator, context, testsystem.system


def test_record_drive():
    """
    Record the variables of a ForceFieldProtonDrive
    """
    tmpdir = tempfile.mkdtemp(prefix="protons-test-")
    drive, integrator, context, system = setup_forcefield_drive()
    ncfile = record.netcdf_file('{}/new.nc'.format(tmpdir), len(drive.titrationGroups), 2, 1)
    for iteration in range(10):
        record.record_drive_data(ncfile, drive, iteration=iteration)
    record.display_content_structure(ncfile)
    ncfile.close()
    shutil.rmtree(tmpdir)

@pytest.mark.skip("Needs revamping.")
def test_record_ghmc_integrator():
    """
    Record the variables of a GHMCIntegrator
    """
    tmpdir = tempfile.mkdtemp(prefix="protons-test-")
    drive, integrator, context, system = setup_forcefield_drive()
    ncfile = record.netcdf_file('{}/new.nc'.format(tmpdir), len(drive.titrationGroups), 2, 1)
    for iteration in range(10):
        record.record_ghmc_integrator_data(ncfile, integrator, iteration)
    record.display_content_structure(ncfile)
    ncfile.close()
    shutil.rmtree(tmpdir)


def test_record_state():
    """
    Record the variables of a Context State
    """
    tmpdir = tempfile.mkdtemp(prefix="protons-test-")
    drive, integrator, context, system = setup_forcefield_drive()
    ncfile = record.netcdf_file('{}/new.nc'.format(tmpdir), len(drive.titrationGroups), 2, 1)
    for iteration in range(10):
        record.record_state_data(ncfile, context, system, iteration)
    record.display_content_structure(ncfile)
    ncfile.close()
    shutil.rmtree(tmpdir)


def test_record_all():
    """
    Record the variables of multiple objects using convenience function
    """
    tmpdir = tempfile.mkdtemp(prefix="protons-test-")
    drive, integrator, context, system = setup_forcefield_drive()
    ncfile = record.netcdf_file('{}/new.nc'.format(tmpdir), len(drive.titrationGroups),2 , 1)
    # TODO Disabled integrator writing for now!
    for iteration in range(10):
        record.record_all(ncfile, iteration, drive, integrator=None, context=context, system=system)
    record.display_content_structure(ncfile)
    ncfile.close()
    shutil.rmtree(tmpdir)


def test_read_ncfile():
    """
    Read a protons netcdf file
    """

    from netCDF4 import Dataset
    from protons.record import display_content_structure
    filename = get_test_data('sample.nc', 'testsystems/record')
    rootgrp = Dataset(filename, "r", format="NETCDF4")
    print(rootgrp['GHMCIntegrator/naccept'][:] / rootgrp['GHMCIntegrator/ntrials'][:])
    display_content_structure(rootgrp)
    rootgrp.close()