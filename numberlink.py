from argparse import ArgumentParser
import subprocess
import time
from pathlib import Path
def build_graph(input_data):
    height, width, grid = input_data

    num_vertices = height * width
    graph = [[] for _ in range(num_vertices)]
    terminals = {}
    dims_x = [0, 0, 1, -1] 
    dims_y = [1, -1, 0, 0]
    for i in range(height):
        for j in range(width):
            for coord in range(len(dims_x)):
                new_x = j+dims_x[coord]
                new_y = i+dims_y[coord]
                if 0 <= new_x < width and 0 <= new_y < height:
                    current = i * width + j
                    neighbour = new_y * width + new_x
                    graph[current].append(neighbour)
            cell = grid[i][j]
            if cell != 0:
                vertex = i * width + j

                if cell not in terminals:
                    terminals[cell] = []
                terminals[cell].append(vertex)

    reverse_graph = [[] for _ in range(len(graph))]

    for u in range(len(graph)):
        for v in graph[u]:
            reverse_graph[v].append(u)

    for colour, vertices in terminals.items():
        if len(vertices)!=2:
            raise ValueError(f"Colour {colour} must appear exactly twice.")

    terminals = [terminals[colour] for colour in sorted(terminals)]
        
    return graph, reverse_graph, terminals

def create_variables(graph, num_colours, variable_counter):
    x = {}
    for colour in range(num_colours):
        for vertex in range(len(graph)):
            x[(colour, vertex)] = variable_counter
            variable_counter+=1

    y = {}
    for colour in range(num_colours):
        for vertex in range(len(graph)):
            for neighbour in graph[vertex]:
                y[(colour, vertex, neighbour)] = variable_counter
                variable_counter+=1

    p = {}
    for colour in range(num_colours):
        for vertex in range(len(graph)):
            for position in range(len(graph)):
                p[(colour, vertex, position)] = variable_counter
                variable_counter+=1
    return x, y, p, variable_counter

def encode_terminals(clauses, x, terminals):
    for colour in range(len(terminals)):
        clauses.append([x[colour, terminals[colour][0]]])
        clauses.append([x[colour, terminals[colour][1]]])


def encode_vertex_disjointness(clauses, x, num_vertices, num_colours):
    for colour_1 in range(num_colours):
        for colour_2 in range(colour_1+1, num_colours):
            for vertex in range(num_vertices):
                clauses.append([-x[colour_1, vertex], -x[colour_2, vertex]])

def encode_edge_constraint(clauses, x, y, graph, num_colours):
    for colour in range(num_colours):
        for u in range(len(graph)):
            for v in graph[u]:
                clauses.append([-y[colour, u, v], x[colour, u]])
                clauses.append([-y[colour, u, v], x[colour, v]])

def encode_degree_constraint(clauses, x, y, graph, reverse_graph, terminals):
    #these enforce outdegree(s{k})=1, indegree(s{k})=0)
    for colour in range(len(terminals)):
        source = terminals[colour][0]
        neighbours = graph[source]
        if not neighbours:
            clauses.append([])
            continue

        clauses.append([y[colour, source, neighbour] for neighbour in graph[source]])

        for i in range(len(neighbours)):
            for j in range(i+1, len(neighbours)):
                clauses.append([-y[colour, source, neighbours[i]], -y[colour, source, neighbours[j]]])

        for vertex in reverse_graph[source]:
            clauses.append([-y[colour, vertex, source]])

    #these enforce outdegree(t{k})=0, indegree(t{k})=1
        target = terminals[colour][1]
        neighbours = reverse_graph[target]
        if not neighbours:
            clauses.append([])
            continue

        clauses.append([y[colour, vertex, target] for vertex in neighbours])

        for i in range(len(neighbours)):
            for j in range(i + 1, len(neighbours)):
                clauses.append([-y[colour, neighbours[i], target], -y[colour, neighbours[j], target]])

        for vertex in graph[target]:
            clauses.append([-y[colour, target, vertex ]])

    #these enforce outdegree(v{k})=1, indegree(v{k})=1 for chosen vertex v
        source, target = terminals[colour]

        for vertex in range(len(graph)):
            if vertex == source or vertex == target:
                continue
            
            clauses.append([-x[colour, vertex]] + [y[colour, neighbour, vertex] for neighbour in reverse_graph[vertex]])
            clauses.append([-x[colour, vertex]] + [y[colour, vertex, neighbour] for neighbour in graph[vertex]])
            incoming_neighbours = reverse_graph[vertex]
            outgoing_neighbours = graph[vertex]

            for i in range(len(incoming_neighbours)):
                for j in range(i + 1, len(incoming_neighbours)):
                    clauses.append([-y[colour, incoming_neighbours[i], vertex], -y[colour, incoming_neighbours[j], vertex]])

            for i in range(len(outgoing_neighbours)):
                for j in range(i + 1, len(outgoing_neighbours)):
                    clauses.append([-y[colour, outgoing_neighbours[i], vertex], -y[colour, outgoing_neighbours[j], vertex]])

def encode_positions(clauses, x, p, graph, terminals):
    for colour in range(len(terminals)):

        #each selected vertex has at least one position
        for vertex in range(len(graph)):
            clauses.append([-x[colour, vertex]]+[p[colour, vertex, i] for i in range(len(graph))])

            #each vertex has at most one position
            for i in range(len(graph)):
                for j in range(i+1, len(graph)):
                    clauses.append([-p[colour, vertex, i], -p[colour, vertex, j]])

            #unselected vertices cannot have positions
            for i in range(len(graph)):
                clauses.append([-p[colour, vertex, i], x[colour, vertex]])

        #the source must occupy position zero
        source = terminals[colour][0]
        clauses.append([p[colour, source, 0]])

def encode_ordering(clauses, y, p, graph, terminals):
    #whenever an edge is selected, its destination must have
    #a strictly greater position than its source
    for colour in range(len(terminals)):
        for vertex in range(len(graph)):
            for neighbour in graph[vertex]:
                for i in range(len(graph)):
                    clauses.append([-y[colour, vertex, neighbour], -p[colour, vertex, i]]+
                                   [p[colour, neighbour, j] for j in range(i+1, len(graph))])

def generate_dimacs(clauses, num_variables, filename):
    with open(filename, "w") as file:
        file.write(f"p cnf {num_variables} {len(clauses)}\n")

        for clause in clauses:
            file.write(" ".join(map(str, clause)) + " 0\n")

def parse_input(filename):
    with open(filename, "r") as file:
        height, width = map(int, file.readline().split())

        if height <= 0 or width <= 0:
            raise ValueError("Grid dimensions must be positive.")
        
        grid = []
        for line in file:
            if not line.strip():
                continue
            grid.append(list(map(int, line.split())))

        #checking the number of rows
        if len(grid) != height:
            raise ValueError("Incorrect number of grid rows.")
        
        #checking the number of columns
        for row in grid:
            if len(row) != width:
                raise ValueError("Incorrect number of columns.")

        #checking for negative cells
        for row in grid:
            for cell in row:
                if cell < 0:
                    raise ValueError("Grid cells cannot be negative.")
                
    return height, width, grid
def parse_model(output):
    assignment = {}

    for line in output.splitlines():
        line = line.strip()

        if line.startswith("v "):
            for literal in map(int, line.split()[1: ]):
                if literal == 0:
                    continue

                variable = abs(literal)
                assignment[variable] = literal > 0
    return assignment

def decode_path(assignment, y, terminals):
    paths = []

    for colour, (source, target) in enumerate(terminals):
        next_vertex = {}

        #finding all selected edges for this code
        for (c, u, v), variable in y.items():
            if c == colour and assignment.get(variable, False):
                next_vertex[u] = v

        path = [source]
        current = source

        while current != target:
            if current not in next_vertex:
                raise ValueError(
                    f"Missing outgoing edge for colour {colour + 1}"
                    f"at vertex {current}."
                )
            current = next_vertex[current]

            if current in path:
                raise ValueError(
                    f"Cycle deteced for a colour {colour + 1}."
                )
            path.append(current)

        paths.append(path)
    return paths

def create_solution_grid(paths, height, width):
    solution_grid = [[0 for _ in range(width)] for _ in range(height)]

    for colour, path in enumerate(paths, start=1):
        for vertex in path:
            row = vertex // width
            column = vertex % width

            solution_grid[row][column] = colour
    return solution_grid

def print_solution(solution):
    print("\nSolution:")

    for row in solution:
        print(" ".join(map(str, row)))

def run_glucose(output_name, verbosity=0):
    project_dir = Path(__file__).resolve().parent
    solver = project_dir / "glucose" / "simp" / "glucose"
    cnf_file = project_dir / output_name

    result = subprocess.run(
        [str(solver), "-model", f"-verb={verbosity}", str(cnf_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return result

if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "-i", "--input",
        default="instances/input_3by3_sat.in",
        type=str,
        help="The instance file."
    )

    parser.add_argument(
        "-o", "--output",
        default="formula.cnf",
        type=str,
        help="The output file for the DIMACS formula."
    )

    parser.add_argument(
        "-v", "--verbose",
        default=0,
        type=int,
        choices=range(0, 2),
        help="Verbosity of the SAT solver."
    )

    args = parser.parse_args()

    given_input = parse_input(args.input)
    graph, reverse_graph, terminals = build_graph(given_input)
    
    clauses = []
    variable_counter = 1
    num_colours = len(terminals)
    num_vertices = len(graph)
    
    x, y, p, variable_counter = create_variables(graph, num_colours, variable_counter)
    encode_terminals(clauses, x, terminals)
    encode_vertex_disjointness(clauses, x, num_vertices, num_colours)
    encode_edge_constraint(clauses, x, y, graph, num_colours)
    encode_degree_constraint(clauses, x, y, graph, reverse_graph, terminals)
    encode_positions(clauses, x, p, graph, terminals)
    encode_ordering(clauses, y, p, graph, terminals)

    generate_dimacs(clauses, variable_counter - 1, args.output)
    start_time = time.perf_counter()

    result = run_glucose(args.output, args.verbose)

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Solving time: {elapsed_time:.3f} seconds") 
    
    if result.returncode not in (10, 20):
        raise RuntimeError(f"Glucose failed:\n{result.stderr}")

    if result.returncode == 10:
        assignment = parse_model(result.stdout)
        paths = decode_path(assignment, y, terminals)
        height, width, grid = given_input
        solution = create_solution_grid(paths, height, width)

        print("SATISFIABLE")
        print_solution(solution)
    else:
        print("UNSATISFIABLE")

    if args.verbose >= 1:
        print("\nGlucose statistics:")
        for line in result.stdout.splitlines():
            if line.startswith("c "):
                print(line)