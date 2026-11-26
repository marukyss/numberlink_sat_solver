## Problem description

Numberlink is a type of the logic puzzle involving finding paths to connect numbers in a grid. The version chosen for this project is **non-covering variant** of Numberlink, meaning that a valid solution does not require every cell of the grid to be a part of some path. However, each pair of identical numbers must be connected by a continuous path. 

All paths must satisfy the following conditions:
- Each path consists of horizontally or vertically adjacent cells (diagonal connections are not allowed)
- Each path connects exactly two cells containing the same number
- Paths cannot intersect, overlap or pass through the cells belonging to other paths
- Every cell with a number inside must belong to its corresponding path
- Empty cells may be used by paths, but are not required to be.

**Parameters:**
- **H:** height of the grid.
- **W:** width of the grid.
- **K:** set of path identifiers (numbers/colours).
- **s(k):** starting cell of path k.
- **t(k):** ending cell of path k.
  
The set of all grid cells:
V = {(i, j) | 0 <= i < H, 0 <= j < W}

**Decision variables:**
- x(v, k): 1 if cell v belongs to path k, and 0 otherwise.
- y(u, v, k): 1 if path k uses the directed connection from cell u to cell v, and 0 otherwise.

## Chosen CNF encoding and possible alternatives

The problem is encoded as a SAT problem using Boolean variables and constraints expressed in Conjunctive Normal Form (CNF). The generated CNF formula is then passed to the Glucose SAT solver.

### Boolean variables

The encoding uses three types of Boolean variables:

- **Vertex variables** \(x(k,v)\): indicate whether cell \(v\) belongs to the path identified by \(k\).
- **Edge variables** \(y(k,u,v)\): indicate whether path \(k\) uses the directed edge from cell \(u\) to cell \(v\).
- **Position variables** \(p(k,v,i)\): indicate whether cell \(v\) occupies position \(i\) in path \(k\).

All variables are Boolean and can take only the values 0 or 1.

### Encoding the constraints

The following constraints are translated into CNF clauses:

1. **Terminals:** Both endpoints of every path must belong to that path. This is encoded using unit clauses forcing the corresponding vertex variables to true.

2. **Vertex disjointness:** A cell cannot belong to more than one path. For every cell and every pair of different paths, a clause prevents both corresponding vertex variables from being true.

3. **Edge selection:** If a directed edge is used by a path, both of its endpoint cells must belong to that path.

4. **Degree constraints:** These ensure that the selected edges form a continuous path:
   - The starting cell has exactly one outgoing edge and no incoming edges.
   - The ending cell has exactly one incoming edge and no outgoing edges.
   - Every other selected cell has exactly one incoming and one outgoing edge.

   At-most-one conditions are encoded using pairwise clauses, while at-least-one conditions are encoded using a single clause containing all possible choices.

### Preventing cycles using position variables

Degree constraints alone are not sufficient to guarantee a single path between the two endpoints. They could also allow disconnected cycles.

To prevent this, the encoding introduces position variables \(p_{k,v,i}\). Each selected cell must have exactly one position, while cells not belonging to the path cannot have a position. The starting cell is assigned position 0.

The ordering constraint ensures that whenever a directed edge from cell \(u\) to cell \(v\) is selected, the position of \(v\) must be strictly greater than the position of \(u\).

In other words:
y(k,u,v)=1 -> pos(v) > pos(u)

This prevents cycles because following selected edges must always lead to cells with greater positions. A cycle would eventually require a position to be greater than itself, which is impossible.

Together with the degree constraints, this guarantees that the selected cells form one continuous path from the starting endpoint to the ending endpoint.

### Possible alternatives

There are several other ways to encode connectivity and prevent cycles:

- **Flow-based encoding:** Additional variables can represent a flow from the starting endpoint to the ending endpoint. Flow conservation constraints can be used to ensure that all selected cells are connected.
- **Subtour elimination:** Constraints can explicitly forbid disconnected cycles. However, this may require a large number of additional clauses or generating constraints iteratively.
- **Binary-encoded positions:** Instead of using one Boolean variable for every possible position of a cell, its position could be represented using binary bits. This could reduce the number of variables, but would require more complicated constraints for comparing positions.

The chosen approach uses one-hot position variables: each cell has a separate Boolean variable for every possible position. This makes the ordering constraints relatively straightforward to express in CNF, although it introduces additional variables and clauses.
## User documentation

### Requirements

The project requires:
- Python 3.
- Glucose SAT solver.

The Glucose executable must be located at `glucose/simp/glucose` relative to the Python script.

### Running the program

The program can be executed from the terminal:

```bash
python3 numberlink.py
```

The script supports the following command-line arguments:

| Argument | Description | Default value |
|---|---|---|
| `-i`, `--input` | Path to the input instance file. | `instances/input_3by3_sat.in` |
| `-o`, `--output` | Name of the output DIMACS CNF file. | `formula.cnf` |
| `-v`, `--verbose` | Enables additional Glucose statistics (0 or 1). | `0` |

For example:

```bash
python3 numberlink.py -i instances/input_13by13_sat.in -o formula.cnf -v 1
```

### Input format

The input file describes a rectangular grid.

- The first line contains two integers: the grid height and width.
- The following lines contain the grid cells, represented by integers separated by spaces.
- `0` represents an empty cell.
- Positive integers represent path identifiers. Each identifier must appear exactly twice, indicating the two endpoints of its path.

For example, a valid input for a 3 × 4 grid could look like this:

```text
3 4
1 0 0 2
0 0 0 0
1 0 2 0
```

The program checks that:
- Grid dimensions are positive.
- The number of rows matches the specified height.
- Every row contains the specified number of columns.
- Grid cells are non-negative.
- Every non-zero path identifier occurs exactly twice.

If the input does not satisfy these conditions, the program raises an error.

### Output

The program first generates a DIMACS CNF formula and saves it to the specified output file.

It then runs Glucose to solve the formula and prints the solving time.

If a solution exists, the program prints `SATISFIABLE` followed by the solution grid. Each path is represented by a different positive integer, while unused cells are represented by `0`.

If no solution exists, the program prints `UNSATISFIABLE`.

When verbose mode is enabled (`-v 1`), additional Glucose statistics are also displayed.

## Description of the included instances

The project includes four Numberlink instances located in the `instances/` directory. They have different grid sizes and are used to test the program on both satisfiable and unsatisfiable inputs.

| Instance | Grid size | Expected result |
|---|---:|---|
| `input_3by3_sat.in` | 3 × 3 | SAT |
| `input_5by5_unsat.in` | 5 × 5 | UNSAT |
| `input_13by13_sat.in` | 13 × 13 | SAT |
| `input_20by20_sat.in` | 20 × 20 | SAT |

The instances allow testing the program on grids of different sizes and checking whether it correctly identifies both satisfiable and unsatisfiable instances.
  
## Experiments

To evaluate the performance of the implementation, I tested it on all four included instances. The instances have different grid sizes and include both satisfiable and unsatisfiable cases.

The experiments were conducted using the Glucose SAT solver. For each instance, I recorded the solver's result and the time required to solve it.

| Instance | Grid size | Result | Solving time (s) |
|---|---:|---|---:|
| `input_3by3_sat.in` | 3 × 3 | SAT | 0.005 |
| `input_5by5_unsat.in` | 5 × 5 | UNSAT | 0.025 |
| `input_13by13_sat.in` | 13 × 13 | SAT | 12.288 |
| `input_20by20_sat.in` | 20 × 20 | SAT | not enough memory |

The results show how the solver performs on instances of increasing size and whether it correctly identifies both satisfiable and unsatisfiable instances.
