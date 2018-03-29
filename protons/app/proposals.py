# coding=utf-8
"""Residue selection moves for protons MC"""
from abc import ABCMeta, abstractmethod
from .logger import log
import copy
import random
import numpy as np
from simtk import unit
from scipy.misc import comb

class _StateProposal(metaclass=ABCMeta):
    """An abstract base class describing the common public interface of residue selection moves."""

    @abstractmethod
    def propose_states(self, drive, residue_pool_indices):
        """ Pick new states for a set of titration groups.

            Parameters
            ----------
            drive - subclass of NCMCProtonDrive
                A proton drive with a set of titratable residues.
            residue_pool_indices - list of int
                List of the residues that could be titrated

            Returns
            -------
            final_titration_states - list of the final titration state of every residue
            titration_group_indices - the indices of the residues that are changing
            float, log (probability of reverse proposal)/(probability of forward proposal)
        """
        return list(), list(), float()


class UniformProposal(_StateProposal):
    """Selects residues uniformly from the supplied residue pool."""

    def __init__(self):
        """Instantiate a UniformProposal"""
        pass

    def propose_states(self, drive, residue_pool_indices):
        """ Pick new states for a set of titration groups.

            Parameters
            ----------
            drive - subclass of NCMCProtonDrive
                A protondrive to update
            residue_pool_indices - list of int
                List of the residues that could be titrated

            Returns
            -------
            final_titration_states - list of the final titration state of every residue
            titration_group_indices - the indices of the residues that are changing
            float, log (probability of reverse proposal)/(probability of forward proposal)

        """
        final_titration_states = copy.deepcopy(drive.titrationStates)
        titration_group_indices = random.sample(residue_pool_indices, 1)
        # Select new titration states.
        for titration_group_index in titration_group_indices:
            # Choose a titration state with uniform probability (even if it is the same as the current state).
            titration_state_index = random.choice(range(drive.get_num_titration_states(titration_group_index)))
            final_titration_states[titration_group_index] = titration_state_index
        return final_titration_states, titration_group_indices, 0.0


class DoubleProposal(_StateProposal):
    """Uniformly selects one, or two residues with some probability from the supplied residue pool."""

    def __init__(self, simultaneous_proposal_probability):
        """Instantiate a DoubleProposal

        Parameters
        ----------
        simultaneous_proposal_probability - float
            The probability of drawing two residues instead of one. Must be between 0 and 1.
        """

        self.simultaneous_proposal_probability = simultaneous_proposal_probability

        return

    def propose_states(self, drive, residue_pool_indices):
        """Uniformly select new titrationstates from the provided residue pool, with a probability of selecting
        two residues.

        Parameters
        ----------
        drive - subclass of NCMCProtonDrive
            A protondrive
        residue_pool_indices - list of int
            List of the residues that could be titrated

        Returns
        -------
        final_titration_states - list of the final titration state of every residue
        titration_group_indices - the indices of the residues that are changing
        float - log (probability of reverse proposal)/(probability of forward proposal)

        """
        final_titration_states = copy.deepcopy(drive.titrationStates)

        # Choose how many titratable groups to simultaneously attempt to update.

        # Update one residue by default
        ndraw = 1
        # Draw two residues with some probability
        if (len(residue_pool_indices) > 1) and (random.random() < self.simultaneous_proposal_probability):
            ndraw = 2

        log.debug("Updating %i residues.", ndraw)

        titration_group_indices = random.sample(residue_pool_indices, ndraw)
        # Select new titration states.
        for titration_group_index in titration_group_indices:
            # Choose a titration state with uniform probability (even if it is the same as the current state).
            titration_state_index = random.choice(range(drive.get_num_titration_states(titration_group_index)))
            final_titration_states[titration_group_index] = titration_state_index
        return final_titration_states, titration_group_indices, 0.0


class CategoricalProposal(_StateProposal):
    """Select N residues, with probability p_N"""

    def __init__(self, p_N):
        """
        Instantiate a CategoricalProposal.

        Parameters
        ----------
        p_N -  sequence of floats, length N
        Probability of updating 1...N  states. These should sum to 1.
        """

        if not sum(p_N) == 1.0:
            raise ValueError("p_N should sum to 1.0")

        self.p_N = p_N
        self.N = len(p_N)

    def propose_states(self, drive, residue_pool_indices):
        """Propose new titration states."""

        final_titration_states = copy.deepcopy(drive.titrationStates)

        # Choose how many titratable groups to simultaneously attempt to update.

        # Update one residue by default
        ndraw = np.random.choice(self.N, 1, p=self.p_N) + 1
        log.debug("Updating %i residues.", ndraw)

        titration_group_indices = random.sample(residue_pool_indices, ndraw)
        # Select new titration states.
        for titration_group_index in titration_group_indices:
            # Choose a titration state with uniform probability (even if it is the same as the current state).
            titration_state_index = random.choice(range(drive.get_num_titration_states(titration_group_index)))
            final_titration_states[titration_group_index] = titration_state_index

        return final_titration_states, titration_group_indices, 0.0


class SaltSwapProposal:
    """This class is a baseclass for selecting water molecules or ions to maintain charge neutrality."""

    def propose_swaps(self, drive, initial_charge: int, final_charge: int):
        """Select a series of water molecules/ions to swap.

        Parameters
        ----------

        drive - a ProtonDrive object with a swapper attached.
        initial_charge - the total charge of the changing residue before the state change
        total_charge - the total charge of the changing residue after the state change

        Please note
        -----------
        The net charge difference will have the opposite charge of the ions that will be added to the system,
        such that the resulting total charge change will be 0.

        Returns
        -------
        list(int) - indices of water molecule in saltswap that are swapped
        list(tuple(int,int),) -  list of tuples with (initial, final) states of the water molecule/ion as int, one tuple for each requested swap
            By saltswap convention
             - 0 is water
             - 1 is cation
             - 2 is anion
        float - log (probability of reverse proposal)/(probability of forward proposal)
        """

        return list(), list(), float()

    @staticmethod
    def _validate_swaps(swaps):
        """Perform sanity checks. Swaps should only add charge in one direction.

        Raises
        ------
        RuntimeError - in case conflicting swaps occur at the same time.
            The error message will detail what the conflict is.
        """

        if swaps['water_to_cation'] != 0 and swaps['water_to_anion'] != 0:
            raise RuntimeError("Opposing charge ions are added. This is a bug in the code.")
        elif swaps['cation_to_water'] != 0 and swaps['anion_to_water'] != 0:
            raise RuntimeError("Opposing charge ions are removed. This is a bug in the code.")
        elif swaps['cation_to_water'] != 0 and swaps['water_to_cation'] != 0:
            raise RuntimeError("Cations are being added and removed at the same time. This is a bug in the code.")
        elif swaps['anion_to_water'] != 0 and swaps['water_to_anion'] != 0:
            raise RuntimeError("Anions are being added and removed at the same time. This is a bug in the code.")


class OneDirectionChargeProposal(SaltSwapProposal):
    """Swaps ions in a way that does not create opposite charges during the alchemical protocol.
    This is an implementation of the method outlined in Chen and Roux 2015
    """

    def __init__(self, cation_coefficient: float=0.5, err_on_depletion: bool=True):
        """Instantiate a UniformSwapProposal.

        Parameters
        ----------
        cation_coefficient - optional. Must be between 0 and 1, default 0.5.
            The fraction of the chemical potential of a water pair -> salt pair transformation that is attributed to the
            cation -> water transformation.
        err_on_depletion - optional.
            If ions get depleted, raise an error. If false, add opposite charge ion to fix.


        """
        if not 0.0 <= cation_coefficient <= 1.0:
            raise ValueError("The cation coefficient should be between 0 and 1.")

        self._cation_weight = cation_coefficient
        self._anion_weight = 1.0 - cation_coefficient

        self._err_on_depletion = err_on_depletion

    def select_ions(self, chem_potential: float, drive, log_ratio: float, saltswap_residue_indices:list, saltswap_state_pairs:list, swaps: dict):
        """

        Parameters
        ----------
        chem_potential - used to calculate the probability of the swap
        drive - ProtonDrive object that has a swapper attached
        log_ratio - starting log_ratio estimate
        saltswap_residue_indices - list to append residue indices to
        saltswap_state_pairs - list to append initial and final states of residues to
        swaps - dict of the type of swaps to perform

        Returns
        -------

        """
        all_waters = np.where(drive.swapper.stateVector == 0)[0]
        all_cations = np.where(drive.swapper.stateVector == 1)[0]
        all_anions = np.where(drive.swapper.stateVector == 2)[0]
        # This code should only perform water_to_cation OR water_to_anion, not both.
        # The sanity check should prevent the same waters/ions from being selected twice.
        # individual types of swaps should be completely independent for the purpose of calculating
        # the proposal probabilities.
        if swaps['water_to_cation'] > 0:
            for water_index in np.random.choice(a=all_waters, size=swaps['water_to_cation'], replace=False):
                saltswap_residue_indices.append(water_index)
                saltswap_state_pairs.append(tuple([0, 1]))

            # Forward: choose m water to change into cations, probability of one pick is
            # 1.0 / (n_water choose m); e.g. from all waters select m (the water_to_cation count).
            log_p_forward = -np.log(comb(all_waters.size, swaps['water_to_cation'], exact=True))
            # Reverse: choose m cations to change into water, probability of one pick is
            # 1.0 / (n_cation + m choose m); e.g. from current cations plus m (the water_to_cation count), select m
            log_p_reverse = -np.log(
                comb(all_cations.size + swaps['water_to_cation'], swaps['water_to_cation'], exact=True))
            log_ratio += (log_p_reverse - log_p_forward)
            # Calculate the work of transforming one water molecule into a cation
            work = chem_potential * self._cation_weight
            # Subtract the work from the acceptance probability
            log_ratio -= work
        if swaps['water_to_anion'] > 0:
            for water_index in np.random.choice(a=all_waters, size=swaps['water_to_anion'], replace=False):
                saltswap_residue_indices.append(water_index)
                saltswap_state_pairs.append(tuple([0, 2]))

            # Forward: probability of one pick is
            # 1.0 / (n_water choose m); e.g. from all waters select m (the water_to_anion count).
            log_p_forward = -np.log(comb(all_waters.size, swaps['water_to_anion'], exact=True))
            # Reverse: probability of one pick is
            # 1.0 / (n_anion + m choose m); e.g. from all current anions plus m (the water_to_anion count), select m
            log_p_reverse = -np.log(
                comb(all_anions.size + swaps['water_to_anion'], swaps['water_to_anion'], exact=True))
            log_ratio += (log_p_reverse - log_p_forward)
            # Calculate the work of transforming one water into one anion
            work = chem_potential * self._anion_weight
            # Subtract the work from the acceptance probability
            log_ratio -= work
        if swaps['cation_to_water'] > 0:
            for cation_index in np.random.choice(a=all_cations, size=swaps['cation_to_water'], replace=False):
                saltswap_residue_indices.append(cation_index)
                saltswap_state_pairs.append(tuple([1, 0]))

            # Forward: choose m cations to change into water, probability of one pick is
            # 1.0 / (n_cations choose m); e.g. from all cations select m (the cation_to_water count).
            log_p_forward = -np.log(comb(all_cations.size, swaps['cation_to_water'], exact=True))
            # Reverse: choose m water to change into cations, probability of one pick is
            # 1.0 / (n_water + m choose m); e.g. from current waters plus m (the anion_to_water count), select m
            log_p_reverse = -np.log(
                comb(all_cations.size + swaps['cation_to_water'], swaps['cation_to_water'], exact=True))
            log_ratio += (log_p_reverse - log_p_forward)
            # Calculate the work of transforming one cation into one water molecule
            work = -chem_potential * self._cation_weight
            # Subtract the work from the acceptance probability
            log_ratio -= work
        if swaps['anion_to_water'] > 0:
            for anion_index in np.random.choice(a=all_anions, size=swaps['anion_to_water'], replace=False):
                saltswap_residue_indices.append(anion_index)
                saltswap_state_pairs.append(tuple([2, 0]))

            # Forward: probability of one pick is
            # 1.0 / (n_anions choose m); e.g. from all anions select m (the anion_to_water count).
            log_p_forward = -np.log(comb(all_anions.size, swaps['anion_to_water'], exact=True))
            # Reverse: probability of one pick is
            # 1.0 / (n_water + m choose m); e.g. from water plus m (the anion_to_water count), select m
            log_p_reverse = -np.log(
                comb(all_waters.size + swaps['anion_to_water'], swaps['anion_to_water'], exact=True))
            log_ratio += (log_p_reverse - log_p_forward)
            # Calculate the work of transforming one anion into water based on the chemical potential
            work = -chem_potential * self._anion_weight
            # Subtract the work from the acceptance probability
            log_ratio -= work
        return log_ratio

    def propose_swaps(self, drive, initial_charge: int, final_charge: int):
        """Select a series of water molecules/ions to swap uniformly from all waters/ions.

            Parameters
            ----------

            drive - a ProtonDrive object with a swapper attached.
            initial_charge - the total charge of the changing residue before the state change
            total_charge - the total charge of the changing residue after the state change

            Returns
            -------
            list(int) - indices of water molecule in saltswap that are swapped
            list(tuple(int,int),) -  list of tuples with (initial, final) states of the water molecule/ion as dict, one tuple for each requested swap
                By saltswap convention:
                - 0 is water
                - 1 is cation
                - 2 is anion

            float - log (probability of reverse proposal)/(probability of forward proposal)
        """
        net_charge_difference = final_charge - initial_charge
        # Defaults. If no swaps are necessary, this will be all that is needed.
        saltswap_residue_indices = list()
        saltswap_state_pairs = list()
        log_ratio = 0.0 # fully symmetrical proposal if no swaps occur.

        # the chemical potential for switching two water molecules into cation + anion
        chem_potential = drive.swapper.delta_chem

        # If no cost is supplied, use the supplied chemical potential

        # Check the type of the chemical potential, and reduce units if necessary
        if isinstance(chem_potential, unit.Quantity):
            chem_potential *= drive.beta
            if unit.is_quantity(chem_potential):
                raise ValueError('The chemical potential has irreducible units ({}).'.format(str(chem_potential.unit)))

        # If swaps are needed
        if net_charge_difference != 0:

            # There is a net charge difference, find which swaps are necessary to compute.
            swaps = self._select_swaps_chenroux(initial_charge, final_charge)

            # Apply sanity checks
            SaltSwapProposal._validate_swaps(swaps)

            log_ratio = self.select_ions(chem_potential, drive, log_ratio, saltswap_residue_indices,
                                         saltswap_state_pairs, swaps)

        return saltswap_residue_indices, saltswap_state_pairs, log_ratio

    @staticmethod
    def _select_swaps_chenroux(initial_charge: int, final_charge: int) -> dict:
        """Select ions or water molecule swap procedure to facilitate maintaining charge neutrality while changing protonation states.

        Notes
        -----
        Based on the method from Chen and Roux 2015.

        Parameters
        ----------
        initial_charge - the initial charge of the residue
        final_charge - the state of the residue after changing protonation states

        Returns
        -------
        dict(water_to_cation, water_to_anion, cation_to_water, anion_to_water)

        """

        # Note that we don't allow for direct transitions between ions of different charge.
        swaps = dict(water_to_cation=0, water_to_anion=0, cation_to_water=0, anion_to_water=0)
        charge_to_counter = final_charge - initial_charge

        while abs(charge_to_counter) > 0:
            # The protonation state change annihilates a positive charge
            if (initial_charge > 0 >= final_charge) or (0 < final_charge < initial_charge):
                swaps['water_to_cation'] += 1
                charge_to_counter += 1
                initial_charge -= 1 # One part of the initial charge has been countered

            # The protonation state change annihilates a negative charge
            elif initial_charge < 0 <= final_charge or (0 > final_charge > initial_charge):
                swaps['water_to_anion'] += 1
                charge_to_counter -= 1
                initial_charge += 1
            # The protonation state change adds a negative charge
            elif initial_charge == 0 > final_charge or (0 > initial_charge > final_charge):
                swaps['anion_to_water'] += 1
                charge_to_counter += 1
                initial_charge -= 1
            # The protonation state adds a positive charge
            elif (initial_charge == 0 < final_charge) or (0 < initial_charge < final_charge):
                swaps['cation_to_water'] += 1
                charge_to_counter -= 1
                initial_charge += 1
            else:
                raise ValueError("Impossible scenario reached.")
        return swaps