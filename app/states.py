from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    timezone = State()


class NewTaskStates(StatesGroup):
    text = State()
    flags = State()
    deadline_choice = State()
    deadline_input = State()
    reminders = State()
    custom_reminder = State()


class RescheduleStates(StatesGroup):
    deadline_input = State()
    reminders = State()
    custom_reminder = State()


class SearchStates(StatesGroup):
    query = State()
    results = State()


class BulkDeleteStates(StatesGroup):
    select = State()


class EditTaskStates(StatesGroup):
    menu = State()
    text = State()
    quadrant = State()
