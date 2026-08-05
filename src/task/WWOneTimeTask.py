from ok import BrowserInteraction, PostMessageInteraction
from src.task.MouseResetTask import MouseResetTask
import sys


class WWOneTimeTask:

    def run(self):
        mouse_reset_task = self.executor.get_task_by_class(MouseResetTask)
        if mouse_reset_task is not None:
            mouse_reset_task.run()
        if sys.platform == 'win32' and PostMessageInteraction is not None and isinstance(self.executor.interaction, PostMessageInteraction):
            self.executor.interaction.activate()
        self.sleep(0.5)
