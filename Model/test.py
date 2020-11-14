import test_backend
import random as r
import numpy as np

# create a Simulation instance used to store information of the simulation as it runs
simulation = test_backend.Simulation()

# define the cell arrays used to store values of the cell. each tuple corresponds to a cell array with the first index
# being the reference name, the second being the data type, and the last can be providing for a 2D array
simulation.cell_arrays(("locations", float, 3), ("radii", float), ("motion", bool), ("FGFR", int), ("ERK", int),
                       ("GATA6", int), ("NANOG", int), ("state", "<U14"), ("diff_counter", int), ("div_counter", int),
                       ("death_counter", int), ("fds_counter", int), ("motility_force", float, 3),
                       ("jkr_force", float, 3), ("rotation", float))

# define the initial parameters for all cells. these can be overridden when defining specific cell types though this
# is meant to reduce writing for cell types that only differ slightly from the base parameters.
n = simulation.field
simulation.initials("locations", lambda: r.random())
simulation.initials("motion", lambda: True)
simulation.initials("FGFR", lambda: r.randrange(0, n))
simulation.initials("ERK", lambda: r.randrange(0, n))
simulation.initials("GATA6", lambda: r.randrange(0, n))
simulation.initials("NANOG", lambda: r.randrange(0, n))
simulation.initials("state", lambda: "Pluripotent")



simulation.initials("motility_force", lambda: np.zeros(3, dtype=float))
simulation.initials("jkr_force", lambda: np.zeros(3, dtype=float))
simulation.initials("rotation", lambda: r.random() * 360)




# # iterate through all cell arrays setting initial values
# for i in range(self.number_cells):
#     n = self.field    # get the fds field
#     div_counter = r.randrange(0, self.pluri_div_thresh)    # get division counter for division/cell size
#
#     # apply initial value for each cell
#     self.cell_locations[i] = np.random.rand(3) * self.size
#     self.cell_radii[i] = self.min_radius + self.pluri_growth * div_counter
#     self.cell_diff_counter[i] = r.randrange(0, self.pluri_to_diff)
#     self.cell_div_counter[i] = div_counter
#     self.cell_death_counter[i] = r.randrange(0, self.death_thresh)
#     self.cell_fds_counter[i] = r.randrange(0, self.fds_thresh)
