# Example of Hen egg-white lysozyme (HEWL)

## Data files
`4lzt.pdb` - Original data file, as obtained from rcsb.org
`preprocessed.pdb` - Manually removed comments, waters and NO3 from original file.
`input.pdb` - processed version of preprocessed.pdb, with constph residue names and without hydrogens
`complex.inpcrd` - tleap output, system coordinates
`complex.prmtop` - tleap output, system topology and parameters
`complex.pdb` - tleap output, system coordinates as pdb file
`complex.cpin` - cpinutil.py output, contains constant-pH parameters
`tleap.out` - tleap stdout/stderr
`leap.log` - log file generated by leap.

## Scripts

`fix-names-and-delete-hydrogen.sh` - sed and awk tool to rename residues and strip hydrogens.
`tleap.in` - a script file for tleap, run using `tleap -f tleap.in`

