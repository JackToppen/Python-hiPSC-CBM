import random as r
import numpy as np
import csv
import cv2
import os
import platform
import sys
import webbrowser
import pickle
import igraph
import distutils.dir_util

import output


# used to hold all values necessary to the simulation as it moves from one step to the next
class Simulation:
    def __init__(self, templates_path, name, path, mode):
        # open the following template files
        with open(templates_path + "general.txt") as general_file:
            general = general_file.readlines()

        with open(templates_path + "imaging.txt") as imaging_file:
            imaging = imaging_file.readlines()

        with open(templates_path + "experimental.txt") as experimental_file:
            experimental = experimental_file.readlines()

        # hold the name and the output path of the simulation
        self.name = name
        self.path = path

        # general template file
        self.parallel = eval(general[4][2:-3])
        self.end_step = int(general[7][2:-3])
        self.number_cells = int(general[10][2:-3])

        # imaging template file
        self.output_images = eval(imaging[4][2:-3])
        self.image_quality = eval(imaging[8][2:-3])
        self.fps = float(imaging[11][2:-3])
        self.background_color = eval(imaging[15][2:-3])
        self.color_mode = eval(imaging[19][2:-3])
        self.output_gradient = eval(imaging[22][2:-3])

        # experimental template file
        self.pluri_div_thresh = int(experimental[4][2:-3])
        self.diff_div_thresh = int(experimental[7][2:-3])
        self.pluri_to_diff = int(experimental[10][2:-3])
        self.death_thresh = int(experimental[13][2:-3])
        self.fds_thresh = int(experimental[16][2:-3])
        self.move_thresh = int(experimental[19][2:-3])
        self.lonely_cell = int(experimental[22][2:-3])
        self.diff_surround = int(experimental[25][2:-3])
        self.contact_inhibit = int(experimental[28][2:-3])
        self.group = int(experimental[31][2:-3])
        self.guye_move = eval(experimental[34][2:-3])
        self.eunbi_move = eval(experimental[37][2:-3])
        self.max_fgf4 = float(experimental[40][2:-3])
        self.fgf4_move = eval(experimental[43][2:-3])

        # the following only need to be created if this is a normal simulation and not a special mode
        if mode == 0:
            # these arrays hold all values of the cells, each index corresponds to a cell.
            self.cell_locations = np.empty((self.number_cells, 3), dtype=float)
            self.cell_radii = np.empty(self.number_cells, dtype=float)
            self.cell_motion = np.empty(self.number_cells, dtype=bool)
            self.cell_fds = np.empty((self.number_cells, 4), dtype=float)
            self.cell_states = np.empty(self.number_cells, dtype='<U14')
            self.cell_diff_counter = np.empty(self.number_cells, dtype=int)
            self.cell_div_counter = np.empty(self.number_cells, dtype=int)
            self.cell_death_counter = np.empty(self.number_cells, dtype=int)
            self.cell_fds_counter = np.empty(self.number_cells, dtype=int)
            self.cell_motility_force = np.empty((self.number_cells, 3), dtype=float)
            self.cell_jkr_force = np.empty((self.number_cells, 3), dtype=float)
            self.cell_nearest_gata6 = np.empty(self.number_cells)
            self.cell_nearest_nanog = np.empty(self.number_cells)
            self.cell_nearest_diff = np.empty(self.number_cells)
            self.cell_highest_fgf4 = np.empty((self.number_cells, 3))

            # add the "cell arrays" attribute names to the list so that indices can be copied/removed from when
            # cells are entering or leaving the simulation, saves the user from adding more code that just this
            self.cell_array_names = ["cell_locations", "cell_radii", "cell_motion", "cell_fds", "cell_states",
                                     "cell_diff_counter", "cell_div_counter", "cell_death_counter", "cell_fds_counter",
                                     "cell_motility_force", "cell_jkr_force", "cell_nearest_gata6",
                                     "cell_nearest_nanog", "cell_nearest_diff", "cell_highest_fgf4"]

            # holds all indices of cells that will divide at a current step or be removed at that step
            self.cells_to_divide, self.cells_to_remove = np.empty((0, 1), dtype=int), np.empty((0, 1), dtype=int)

            # create graphs used to all cells and their neighbors, initialize them with the number of cells
            self.neighbor_graph, self.jkr_graph = igraph.Graph(self.number_cells), igraph.Graph(self.number_cells)

            # min and max radius lengths are used to calculate linear growth of the radius over time in 2D
            self.max_radius = 0.000005
            self.min_radius = self.max_radius / 2 ** 0.5
            self.pluri_growth = (self.max_radius - self.min_radius) / self.pluri_div_thresh
            self.diff_growth = (self.max_radius - self.min_radius) / self.diff_div_thresh

            # get the size of the space and the approximation of the differential
            self.size = np.array([0.001, 0.001, 0.0])
            self.dx, self.dy, self.dz = 0.00001, 0.00001, 1
            self.dx2, self.dy2, self.dz2 = self.dx ** 2, self.dy ** 2, self.dz ** 2

            # the diffusion constant for the molecule gradients
            self.diffuse = 0.00000000000001
            self.diffuse_radius = 0.000025

            # get the time step value for diffusion updates depending on whether 2D or 3D
            if self.size[2] == 0:
                self.dt = (self.dx2 * self.dy2) / (2 * self.diffuse * (self.dx2 + self.dy2))
            else:
                self.dt = (self.dx2 * self.dy2 * self.dz2) / (2 * self.diffuse * (self.dx2 + self.dy2 + self.dz2))

            # the points at which the diffusion values are calculated
            gradient_size = self.size / np.array([self.dx, self.dy, self.dz]) + np.ones(3)
            self.fgf4_values = np.zeros(gradient_size.astype(int))

            # much like the cell arrays add any gradients here to be updated
            self.extracellular_names = ["fgf4_values"]

            # the time in seconds for incremental movement
            self.time_step_value = 1800
            self.move_time_step = 200


def setup():
    """ controls which mode of the model is run and
        sets up the model accordingly
    """
    # if no command line attributes besides the file, run the mini gui to get the name and the mode
    if len(sys.argv) == 1:
        while True:
            name = input("What is the name of the simulation? Type ""help"" for more information: ")
            if name == "help":
                print("Type the name of the simulation. Don't include quotes or a path")
            else:
                break

        while True:
            mode = input("What is the mode of the simulation? Type ""help"" for more information: ")
            if mode == "help":
                print("normal simulation: 0")
                print("continuation of past simulation: 1")
                print("images to video: 2")
                print("csvs to images/video: 3")
            else:
                mode = int(mode)
                break

    # if both the name and the mode are provided, do nothing
    elif len(sys.argv) == 3:
        name, mode = sys.argv[1], int(sys.argv[2])

    # if anything else
    else:
        print("Either run \"python Run.py\" without arguments or \"python Run.py (simulation name) (simulation mode)\"")
        exit()

    # open the path.txt file containing information about template locations and output directory
    with open('paths.txt', 'r') as file:
        lines = file.readlines()

    # get the paths to the directory of template files and the output directory
    templates_path = lines[7].strip()
    output_path = lines[13].strip()

    # keep track of the file separator to use
    if platform.system() == "Windows":
        # windows
        separator = "\\"
    else:
        # not windows
        separator = "/"

    # check the name of the simulation and create a path to simulation output directory
    name, output_path, path = check_name(name, mode, templates_path, output_path, separator)

    # run the model normally
    if mode == 0:
        # create instance of Simulation class
        simulation = Simulation(templates_path, name, path, mode)

        # initialize the data csv and the video
        output.initialize_csv(simulation)
        output.initialize_video(simulation)

        # go through all cell arrays giving initial parameters of the cells
        for i in range(simulation.number_cells):
            div_counter = r.randint(0, simulation.pluri_div_thresh)
            simulation.cell_locations[i] = np.array([r.random() * simulation.size[0],
                                                     r.random() * simulation.size[1],
                                                     r.random() * simulation.size[2]])
            simulation.cell_radii[i] = simulation.min_radius + simulation.pluri_growth * div_counter
            simulation.cell_motion[i] = True
            simulation.cell_fds[i] = np.array([r.randint(0, 1), r.randint(0, 1), 0, 1])
            simulation.cell_states[i] = "Pluripotent"
            simulation.cell_diff_counter[i] = r.randint(0, simulation.pluri_to_diff)
            simulation.cell_div_counter[i] = div_counter
            simulation.cell_death_counter[i] = r.randint(0, simulation.death_thresh)
            simulation.cell_fds_counter[i] = r.randint(0, simulation.fds_thresh)
            simulation.cell_motility_force[i] = np.zeros(3, dtype=float)
            simulation.cell_jkr_force[i] = np.zeros(3, dtype=float)
            simulation.cell_nearest_gata6[i] = np.nan
            simulation.cell_nearest_nanog[i] = np.nan
            simulation.cell_nearest_diff[i] = np.nan
            simulation.cell_highest_fgf4[i] = np.array([np.nan, np.nan, np.nan])

    # continue a past simulation
    elif mode == 1:
        # open the temporary pickled simulation an
        with open(path + name + "_temp.pkl", "rb") as temp_file:
            simulation = pickle.load(temp_file)

    # images to video mode
    elif mode == 2:
        # create instance of Simulation class
        simulation = Simulation(templates_path, name, path, separator, mode)

        # prepare a video file to write to
        output.initialize_video(simulation)

        # get all files ending in ".png" in the directory with a simulation name, sort that list
        file_list = [file for file in os.listdir(path) if file.endswith('.png')]
        file_list.sort()

        # loop over all images defined in the template file
        for image_name in file_list:
            # read the image and write it to the video file
            image = cv2.imread(simulation.path + image_name)
            simulation.video_object.write(image)

        # exits out as the conversion from images to video is done
        exit()

    # turn a collection of csvs into images and a video
    elif mode == 3:
        # hold the number of csvs -1 as there will be an extra csv
        csv_count = -1

        # go through all files in directory counting the csv files
        for file in os.listdir(path):
            if file.endswith('.csv'):
                csv_count += 1

        # create simulation instance
        simulation = Simulation(templates_path, name, path, separator, mode)

        # loop over all csvs defined in the template file
        for i in range(1, csv_count + 1):
            # updates the instance variables as they aren't updated by anything else
            simulation.current_step = i

            # opens the csv and create a list of the rows
            with open(simulation.path + simulation.name + "_values_" + str(int(i)) + ".csv", newline="") as csv_file:
                # skip the first row as this is a header
                csv_rows = list(csv.reader(csv_file))[1:]

            # updates the number of cells and adds that amount of vertices to the graphs
            simulation.number_cells = len(csv_rows)
            simulation.neighbor_graph.add_vertices(simulation.number_cells)
            simulation.jkr_graph.add_vertices(simulation.number_cells)

            # turn all of the rows into a matrix
            cell_data = np.column_stack(csv_rows)

            # each row of the matrix will correspond to a cell value holder. the 2D arrays must be handled differently
            simulation.cell_locations = cell_data[0:3, :].transpose().astype(float)
            simulation.cell_radii = cell_data[3].astype(float)
            simulation.cell_motion = cell_data[4] == "True"
            simulation.cell_fds = cell_data[5:9, :].transpose().astype(float).astype(int)
            simulation.cell_states = cell_data[9].astype(str)
            simulation.cell_diff_counter = cell_data[10].astype(int)
            simulation.cell_div_counter = cell_data[11].astype(int)
            simulation.cell_death_counter = cell_data[12].astype(int)
            simulation.cell_fds_counter = cell_data[12].astype(int)
            simulation.cell_motility_force = np.zeros((simulation.number_cells, 3), dtype=float)
            simulation.cell_jkr_force = np.zeros((simulation.number_cells, 3), dtype=float)
            simulation.cell_nearest_gata6 = np.empty((simulation.number_cells, 3))
            simulation.cell_nearest_nanog = np.empty((simulation.number_cells, 3))
            simulation.cell_nearest_diff = np.empty((simulation.number_cells, 3))
            simulation.cell_highest_fgf4 = np.empty((simulation.number_cells, 3))

            # saves a snapshot of the simulation
            output.step_image(simulation)

            # clear the number of cells holder
            simulation.number_cells = 0

        # turns the images into a video
        output.finish_files(simulation)

        # exits out as the conversion from .csv to images/video is done
        exit()

    else:
        print("Incorrect mode")

    # return the modified simulation instance
    return simulation


def check_name(name, mode, templates_path, output_path, separator):
    """ renames the file if another simulation has the same name
        or checks to make sure such a simulation exists
    """
    # for a new simulation
    if mode == 0:
        # keeps the loop running until one condition is met
        while True:
            # if the path does not already exist, make that directory and break out of the loop
            try:
                os.mkdir(output_path + name)
                break

            # prompt to either rename or overwrite
            except OSError:
                print("Simulation with identical name: " + name)
                user = input("Would you like to overwrite that simulation? (y/n): ")
                if user == "n":
                    name = input("New name: ")
                elif user == "y":
                    # clear current directory to prevent another possible future errors
                    files = os.listdir(output_path + name)
                    for file in files:
                        os.remove(output_path + name + separator + file)
                    break
                else:
                    print("Either type ""y"" or ""n""")

        # copy the template directory to the new simulation directory
        distutils.dir_util.copy_tree(templates_path, output_path + name)

    # this will look for an existing directory for modes other than 0
    else:
        # keeps the loop running until one condition is met
        while True:
            # see if the directory exists
            if os.path.isdir(output_path + name):
                break

            # if not prompt to change name or end the simulation
            else:
                print("No directory exists with name/path: " + output_path + name)
                user = input("Would you like to continue? (y/n): ")
                if user == "n":
                    exit()
                elif user == "y":
                    print(output_path)
                    user = input("Is the above path correct? (y/n): ")
                    if user == "n":
                        output_path = input("Type correct path:")
                    print(name)
                    user = input("Is the above name correct? (y/n): ")
                    if user == "n":
                        name = input("Type correct name:")
                else:
                    pass

    # return the updated name, directory, and path
    return name, output_path, output_path + name + separator