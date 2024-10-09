from functools import partial
import time
import threading

from helpers import (
    find_empty_location,
    is_valid,
    generate_sudoku_list,
)

from kivy.clock import Clock
from kivy.config import Config
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import (
    MDButton,
    MDButtonText,
)
from kivymd.uix.dialog import MDDialog, MDDialogButtonContainer, MDDialogHeadlineText
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.slider import MDSlider, MDSliderHandle


sudoku_solve_speed = 5000


class GridCell(MDLabel):
    """Defines a single cell of the sudoku grid"""

    def __init__(self, *args, **kwargs):
        super(MDLabel, self).__init__(*args, **kwargs)
        self.border_width = 1

        # Sets the border and background of the grid cells
        with self.canvas.before:
            Color(0, 0, 0, 0.1)  # Grey border color
            self.border = Rectangle(size=self.size, pos=self.pos)
            Color(1, 1, 1, 1)  # White background color
            self.bg = Rectangle(
                size=(
                    self.size[0] - self.border_width * 2,
                    self.size[1] - self.border_width * 2,
                ),
                pos=(self.pos[0] + self.border_width, self.pos[1] + self.border_width),
            )
        self.bind(size=self._update_rect, pos=self._update_rect)

        self.halign = "center"
        self.valign = "center"
        self.size = (dp(110), dp(50))
        self.font_size = "30sp"

    def _update_rect(self, *args):
        """Formats the borders of the grid cells on move/resize"""
        self.border.size = self.size
        self.border.pos = self.pos
        self.bg.size = (
            self.size[0] - self.border_width * 2,
            self.size[1] - self.border_width * 2,
        )
        self.bg.pos = (self.pos[0] + self.border_width, self.pos[1] + self.border_width)


class BoardArea(MDGridLayout):
    """Defines the area of the game board that holds the sudoku grid itself. Consists of 81 labels representing each cell in a sudoku grid."""

    def __init__(self, *args, **kwargs):
        super(BoardArea, self).__init__(*args, **kwargs)

        self.border_width = 1.5
        self.label_indexes = dict()
        self.sudoku_board = generate_sudoku_list()

        for _ in range(9):
            for _ in range(9):
                label = GridCell(text="")
                self.add_widget(label)

        # Sets the values of the label_indexes dictionary, e.g. {(0,0): 80, (0,1): 79, ...}
        index = 80
        for i in range(9):
            for j in range(9):
                self.label_indexes[(i, j)] = index
                index -= 1

        # Formats the board area borders and background
        with self.canvas:
            Color(0, 0, 0, 1)  # White background color
            self.border_line = Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=self.border_width,
            )

            for i in range(4):
                setattr(
                    self,
                    f"inner_line_{i+1}",
                    Line(
                        points=[self.x, self.y, self.x, self.y],
                        width=self.border_width,
                    ),
                )
                setattr(self, f"vertical_line_{i+1}", Line(points=[], width=self.width))
        self.bind(size=self._update_border, pos=self._update_border)

        self._populate_board()

    def _update_border(self, *args):
        """Formats the borders of the board area on move/resize"""
        self.border_line.rectangle = (
            self.x + self.padding[0],
            self.y,
            self.width - self.padding[2] * 2,
            self.height,
        )

        self.inner_line_1.points = [
            self.x
            + self.padding[0]
            + ((self.width - self.padding[0] - self.padding[2]) / 3),
            self.y,
            self.x
            + self.padding[0]
            + ((self.width - self.padding[0] - self.padding[2]) / 3),
            self.y + self.height,
        ]

        self.inner_line_2.points = [
            self.x
            + self.padding[0]
            + ((self.width - self.padding[0] - self.padding[2]) / 3) * 2,
            self.y,
            self.x
            + self.padding[0]
            + ((self.width - self.padding[0] - self.padding[2]) / 3) * 2,
            self.y + self.height,
        ]

        self.inner_line_3.points = [
            self.x + self.padding[0],
            self.y + ((self.height - self.padding[1] - self.padding[3]) / 3),
            self.x + self.width - self.padding[2],
            self.y + ((self.height - self.padding[1] - self.padding[3]) / 3),
        ]

        self.inner_line_4.points = [
            self.x + self.padding[0],
            self.y + ((self.height - self.padding[1] - self.padding[3]) / 3) * 2,
            self.x + self.width - self.padding[2],
            self.y + ((self.height - self.padding[1] - self.padding[3]) / 3) * 2,
        ]

    def _populate_board(self):
        """Populates the sudoku grid with the generated sudoku upon instance initialisation."""
        for i in range(9):
            for j in range(9):
                index = self.label_indexes[(i, j)]

                if self.sudoku_board[i][j] == 0:
                    self.children[index].text = ""

                    continue

                self.children[index].text = str(self.sudoku_board[i][j])

        return

    def generate_new_board(self, instance):
        """Generates new sudoku board and displays it on the GUI"""

        def reformat_text(index):
            """Reformats the sudoku cells that have been changed by previous runs of the game."""
            self.children[index].color = (0, 0, 0, 1)  # White font color

        self.sudoku_board = generate_sudoku_list()

        for i in range(9):
            for j in range(9):
                index = self.label_indexes[(i, j)]

                if self.sudoku_board[i][j] == 0:
                    self.children[index].text = ""
                    reformat_text(index)
                else:
                    self.children[index].text = str(self.sudoku_board[i][j])
                    reformat_text(index)

        return

    def solve_board(
        self,
        sudoku_board,
        first_call=True,
        start_time=0,
        sleep_time=1 / sudoku_solve_speed,
    ):
        """Solves a sudoku board using backtracking algorithm. 'first_call' and 'start_time' are used to calculate the total runtime of the solve function.
        'sleep_time' is used to delay the code execution and allow for more clear visualisation of the solving algorithm.
        """

        if sleep_time != 1 / sudoku_solve_speed:
            sleep_time = 1 / sudoku_solve_speed

        if first_call:
            start_time = time.time()

        empty_row, empty_col = find_empty_location(sudoku_board)

        if empty_row is None:
            execution_time = time.time() - start_time

            Clock.schedule_once(
                partial(self.show_execution_time_popup, str(execution_time)), -1
            )

            return True

        cell_index = self.label_indexes[(empty_row, empty_col)]

        for num in range(1, 10):
            if is_valid(sudoku_board, empty_row, empty_col, num):
                sudoku_board[empty_row][empty_col] = num

                Clock.schedule_once(
                    partial(self.format_current_label, cell_index, num), -1
                )
                time.sleep(sleep_time)

                if self.solve_board(
                    sudoku_board,
                    first_call=False,
                    start_time=start_time,
                    sleep_time=sleep_time,
                ):
                    Clock.schedule_once(
                        partial(self.format_valid_label, cell_index, num), -1
                    )
                    time.sleep(sleep_time)

                    return True

                sudoku_board[empty_row][empty_col] = 0

                Clock.schedule_once(
                    partial(self.format_current_invalid_label, cell_index, num), -1
                )
                time.sleep(sleep_time)

                Clock.schedule_once(partial(self.format_invalid_label, cell_index), -1)

        first_call = False
        return False

    def format_current_invalid_label(self, label_id, label_text, dt):
        """Formats sudoku cell that is confirmed to be invalid"""
        self.children[label_id].text = str(label_text)
        self.children[label_id].color = (1, 0, 0, 1)  # Red font color

    def format_current_label(self, label_id, label_text, dt):
        """Formats the currently evaluated sudoku cell"""
        self.children[label_id].text = str(label_text)
        self.children[label_id].color = (0, 0, 1, 1)  # Blue font color

    def format_valid_label(self, label_id, label_text, dt):
        """Formats sudoku cell that is confirmed to be valid"""
        self.children[label_id].text = str(label_text)
        self.children[label_id].color = (0, 1, 0, 1)  # Green font color

    def format_invalid_label(self, label_id, dt):
        """Formats all cells up to the last confirmed to be invalid cell"""
        self.children[label_id].color = (1, 0, 0, 0.3)  # Light red font color

    def show_execution_time_popup(self, elapsed_time, dt):
        """Shows a popup with the execution time"""
        minutes = int(float(elapsed_time) // 60)
        seconds = int(float(elapsed_time) % 60)
        milliseconds = int((float(elapsed_time) - int(float(elapsed_time))) * 10000)

        formatted_time = f"{minutes:02}m:{seconds:02}s:{milliseconds:05}ms"

        self.completion_dialog = MDDialog(
            MDDialogHeadlineText(text=f"Solve time: \n{formatted_time}"),
            MDDialogButtonContainer(
                Widget(),
                MDButton(
                    MDButtonText(text="ОК"),
                    style="text",
                    on_release=lambda _: self.completion_dialog.dismiss(),
                ),
                spacing="8dp",
            ),
        )

        self.completion_dialog.open()


class SliderArea(MDBoxLayout):

    def __init__(self, *args, **kwargs):
        super(SliderArea, self).__init__(*args, **kwargs)

        self.add_widget(
            MDLabel(
                font_style="Title",
                halign="left",
                theme_text_color="Secondary",
                text="Solve speed:",
                padding=(120, 0, 0, 0),
            )
        )

        solve_speed_slider = MDSlider(MDSliderHandle(), min=1, max=100000, value=50000)
        self.add_widget(solve_speed_slider)

        solve_speed_slider.bind(value=self.OnSliderValueChange)

    def OnSliderValueChange(self, instance, value):
        global sudoku_solve_speed
        sudoku_solve_speed = value


class ButtonsArea(MDFloatLayout):
    """Defines the area of the game board that holds the action buttons"""

    def __init__(self, *args, **kwargs):
        super(MDFloatLayout, self).__init__(*args, **kwargs)

        self.add_widget(
            MDButton(
                MDButtonText(text="Solve"),
                pos_hint={"center_x": 0.3, "center_y": 0.5},
                style="filled",
            )
        )

        self.add_widget(
            MDButton(
                MDButtonText(text="Generate new"),
                pos_hint={"center_x": 0.7, "center_y": 0.5},
                style="filled",
            )
        )


class SudokuGame(MDBoxLayout):
    """Contains the complete game area and consists of all the vertically stacked sub-elements."""

    def __init__(self, *args, **kwargs):
        super(SudokuGame, self).__init__(*args, **kwargs)

        self.add_widget(
            MDLabel(
                font_style="Display",
                halign="center",
                padding=(0, 40, 0, 0),
                size_hint=(1, 0.1),
                theme_text_color="Secondary",
                text="Sudoku Solver",
            )
        )

        self.add_widget(
            BoardArea(
                cols=9,
                rows=9,
                padding=(70, 0, 70, 0),
                size_hint=(1, 0.6),
            )
        )

        slider_widget = SliderArea(size_hint=(0.9, 0.05))
        self.add_widget(slider_widget)

        buttons_widget = ButtonsArea(size_hint=(1, 0.05))
        self.add_widget(buttons_widget)

        buttons_widget.children[1].bind(on_press=self.start_threaded_solving)

        buttons_widget.children[0].bind(  #'Generate new' button
            on_press=self.children[2].generate_new_board
        )

        self.thread = None
        self.thread_running = threading.Event()

        print(self.children)

    def trigger_solving(self):
        self.thread_running.set()
        self.children[2].solve_board(
            sudoku_board=self.children[2].sudoku_board
        )  # BoardArea solve_board function call
        self.thread_running.clear()

        self.children[0].children[
            0
        ].disabled = False  # Re-enable 'Generate new' button after thread finishes

    def start_threaded_solving(self, instance):
        if self.thread is None or not self.thread.is_alive():
            self.children[0].children[
                0
            ].disabled = True  # Disable 'Generate new' button
            self.thread = threading.Thread(target=self.trigger_solving)
            self.thread.start()


class MainApp(MDApp):

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Whitesmoke"

        Config.set("kivy", "exit_on_escape", "0")
        game = SudokuGame(
            orientation="vertical", md_bg_color=self.theme_cls.backgroundColor
        )
        return game


if __name__ == "__main__":
    MainApp().run()
