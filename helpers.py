"""Helper functions for the CLI and GUI sudoku solver"""

from dokusan import generators


def generate_sudoku_list() -> list[list[int]]:
    """Generates random sudoku puzzle and transforms it into list of lists representing
    each row of the sudoku puzzle"""
    sudoku = str(generators.random_sudoku(avg_rank=150))
    return [[int(i) for i in list(sudoku[j : j + 9])] for j in range(0, 81, 9)]


def is_valid(board: list[list[int]], row: int, col: int, num: int) -> bool:
    """Helper function that checks whether a candidate value is a valid choice"""
    # Check if the number is already present in the row
    if num in board[row]:
        return False

    # Check if the number is already present in the column
    if num in [board[i][col] for i in range(9)]:
        return False

    # Check if the number is already present in the 3x3 grid
    start_row, start_col = 3 * (row // 3), 3 * (col // 3)
    for i in range(3):
        for j in range(3):
            if board[start_row + i][start_col + j] == num:
                return False

    return True


def find_empty_location(board: list[list[int]]) -> tuple[int, int]:
    """Helper function that finds the first empty cell in a board"""

    for i in range(9):
        for j in range(9):
            if board[i][j] == 0:
                return i, j
    return -1, -1  # If no empty cell is found
